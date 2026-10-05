import asyncio
import shutil
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from config.settings import settings
from core.asset_providers import AssetProviderFactory  # noqa: F401  (usado por AssetOrchestrator)
from core.card_renderer import InfoCardRenderer
from core.fact_checker import FactChecker
from core.gemini_analyzer import GeminiVideoAnalyzer
from core.llm import LLMClient, safe_log
from core.models import ActionType, VideoEditingPlan
from core.orchestrator import AssetOrchestrator
from core.render_engine import VideoRenderEngine
from core.silence_detector import SilenceDetector
from core.timeline import TimelineMapper
from core.transcriber import WhisperTranscriber, highlight_terms_from_plan
from utils.file_manager import FileManager

StateCb = Callable[..., None]


class PipelineOptions:
    def __init__(self, silence_threshold: float = 1.5, broll: bool = True, captions: bool = True,
                 shorts: bool = True, cards: bool = True):
        self.silence_threshold = silence_threshold
        self.broll = broll
        self.captions = captions
        self.shorts = shorts
        self.cards = cards


class VideoPipeline:
    """
    Orquesta el flujo completo:
    Gemini (plan) -> silencios reales (audio) -> [B-Roll || verificación web + tarjetas] -> render -> subtítulos -> Short.
    """

    def __init__(self, task_id: str, input_file: Path, options: PipelineOptions, on_state: StateCb):
        self.task_id = task_id
        self.input_file = input_file
        self.opt = options
        self.on_state = on_state
        self.workdir = settings.TEMP_DIR / task_id
        self.workdir.mkdir(parents=True, exist_ok=True)

    def _state(self, step: str, progress: float, message: str, **extra: Any) -> None:
        self.on_state(step, progress, message, **extra)

    async def run(self) -> Dict[str, Any]:
        loop = asyncio.get_running_loop()
        try:
            return await self._run(loop)
        finally:
            shutil.rmtree(self.workdir, ignore_errors=True)  # no saturar el disco con temporales

    async def _run(self, loop) -> Dict[str, Any]:
        opt = self.opt
        meta = FileManager.get_media_metadata(self.input_file)
        duration = float(meta.get("duration") or 0.0)
        if duration <= 0:
            raise RuntimeError("No se pudo leer la duración del video. ¿El archivo está dañado?")
        frame_w, frame_h = meta.get("width") or 1920, meta.get("height") or 1080

        # ---- 0.5 Whisper Transcription (Full Text for LLM and Subtitles) ----
        self._state("transcribe", 2.0, "Transcribiendo el video para asegurar extracción exhaustiva...")
        transcript_text = None
        whisper_caps = None
        if opt.captions:
            try:
                whisper_caps = await loop.run_in_executor(None, lambda: WhisperTranscriber().transcribe(self.input_file, []))
                if whisper_caps:
                    transcript_text = "\n".join(f"[{c.start_sec:.1f}-{c.end_sec:.1f}] {c.text}" for c in whisper_caps)
            except Exception as exc:
                safe_log(f"[Pipeline] Error en Whisper pre-análisis: {exc}")

        # ---- 1. Gemini ----
        llm = LLMClient()
        self._state("gemini", 8.0, "Gemini: escaneando línea por línea la transcripción y el video...")
        analyzer = GeminiVideoAnalyzer(llm=llm)
        # Permitir hasta 40 tarjetas (sin límite artificial bajo) para extraer absolutamente todo
        calculated_cards = max(8, int(duration // 15)) if opt.cards else 0
        if calculated_cards > 40: calculated_cards = 40
        plan: VideoEditingPlan = await loop.run_in_executor(
            None,
            lambda: analyzer.analyze_video(
                self.input_file, opt.silence_threshold,
                max_cards=calculated_cards,
                progress=lambda m: self._state("gemini", 12.0, m),
                transcript=transcript_text
            ),
        )
        if not opt.broll:
            plan.b_rolls = []
        if not opt.cards:
            plan.info_cards = []
        if not opt.captions:
            plan.captions = []
        if not opt.shorts:
            plan.highlights = []

        # ---- 2. Silencios reales del audio (sobrescribe la estimación de Gemini) ----
        self._state("gemini", 26.0, "Detectando silencios reales en el audio...")
        detected = await loop.run_in_executor(
            None, lambda: SilenceDetector().build_timeline(self.input_file, duration, opt.silence_threshold)
        )
        if detected:
            plan.timeline = detected
            self._state("gemini", 28.0, "Silencios detectados desde el audio (precisión de milisegundos).")
        else:
            safe_log("[Pipeline] No se pudo analizar el audio; se usa la línea de tiempo de Gemini.")
        plan.total_original_duration_sec = duration

        # ---- 2.5 Sincronización y Subtítulos ----
        if whisper_caps:
            import re
            terms = highlight_terms_from_plan(plan)
            # Asignar highlight_words a whisper_caps
            for c in whisper_caps:
                hl = [w.strip(" .,;:!?¡¿\"'") for w in c.text.split() if w.strip(" .,;:!?¡¿\"'").lower() in terms]
                if hl:
                    c.highlight_words = hl[:2]
            
            # Sincronizar info_cards con Whisper!
            for card in plan.info_cards:
                card_words = set(re.findall(r"\w+", (card.headline + " " + card.claim).lower()))
                best_match = None
                best_score = 0
                for cap in whisper_caps:
                    if abs(cap.start_sec - card.start_sec) > 15: continue
                    cap_words = set(re.findall(r"\w+", cap.text.lower()))
                    score = len(card_words & cap_words)
                    if score > best_score:
                        best_score = score
                        best_match = cap.start_sec
                if best_match is not None and best_score > 0:
                    safe_log(f"[Sync] Tarjeta '{card.headline}' ajustada de {card.start_sec} a {best_match}")
                    card.start_sec = best_match
                    card.end_sec = best_match + 5.0
                    
            plan.captions = whisper_caps

        # ---- 3. B-Roll y verificación web en paralelo ----
        self._state("broll", 32.0, "Buscando B-Rolls y verificando datos en la web...")
        tasks = []
        if plan.b_rolls:
            tasks.append(AssetOrchestrator(target_dir=self.workdir / "assets").process_all_brolls(plan))
        if plan.info_cards:
            checker = FactChecker(llm, self.workdir)
            tasks.append(checker.verify_plan(plan, progress=lambda m: self._state("cards", 40.0, m)))
        if tasks:
            await asyncio.gather(*tasks)

        # ---- 4. Tarjetas (solo las confirmadas) + fotos enmarcadas ----
        self._state("cards", 46.0, "Diseñando tarjetas informativas...")
        renderer = InfoCardRenderer(frame_w, frame_h)

        def design():
            renderer.render_all(plan.info_cards, self.workdir)
            for cue in plan.b_rolls:
                p = cue.local_file_path
                if cue.download_status == "COMPLETED" and p and Path(p).suffix.lower() not in (".mp4", ".mov", ".webm", ".mkv"):
                    framed = renderer.render_photo_frame(p, cue.concept, self.workdir / f"{cue.cue_id}_frame.png")
                    cue.frame_path = str(framed) if framed else None

        await loop.run_in_executor(None, design)

        # ---- 5. Render (Smart Cut + overlays + subtítulos opcionales) ----
        mapper = TimelineMapper.from_plan_segments(plan.timeline, duration)
        engine = VideoRenderEngine(fps=30)
        final_master = settings.OUTPUTS_DIR / f"{self.task_id}_master.mp4"

        captions_provider = None
        if opt.captions:
            def captions_provider(cut_video: Path):
                return mapper.remap_captions(plan.captions)

        def render_cb(msg: str, pct: float) -> None:
            self._state("subtitles" if "ubt" in msg or "ranscrib" in msg else "render", 50.0 + pct * 42.0, msg)

        self._state("render", 50.0, "Renderizando con FFmpeg...")
        render_info = await loop.run_in_executor(
            None, lambda: engine.render(self.input_file, plan, mapper, self.workdir, final_master,
                                        captions_provider, render_cb)
        )

        # ---- 6. Short vertical (sale del master: incluye tarjetas y subtítulos) ----
        short_file: Optional[Path] = None
        if plan.highlights:
            self._state("finalizing", 94.0, "Generando Short vertical 9:16...")
            best = max(plan.highlights, key=lambda h: h.virality_score)
            placed = mapper.map_first(best.start_sec, best.end_sec)
            if placed:
                best = best.model_copy(update={"start_sec": placed[0], "end_sec": placed[1]})
                short_file = await loop.run_in_executor(
                    None, lambda: engine.extract_vertical_short(final_master, best, settings.OUTPUTS_DIR)
                )

        cut = [s for s in plan.timeline if s.action == ActionType.CUT_SILENCE]
        placed_cards = {o["path"] for o in render_info["overlays"] if o["kind"] == "card"}
        return {
            "master_video_url": f"/media/{final_master.name}",
            "short_video_url": f"/media/{short_file.name}" if short_file else None,
            "silences_cut_count": len(cut),
            "brolls_count": sum(1 for o in render_info["overlays"] if o["kind"] != "card"),
            "time_saved_sec": round(sum(s.end_sec - s.start_sec for s in cut), 2),
            "cards_shown": len(placed_cards),
            "captions_count": render_info["captions"],
            "cards": [
                {
                    "headline": c.headline, "kind": c.kind, "verdict": c.verdict, "body": c.body,
                    "claim": c.claim, "note": c.note, "shown": bool(c.card_path and c.card_path in placed_cards),
                    "at_sec": round(c.start_sec, 1),
                    "sources": [s.model_dump() for s in c.sources],
                }
                for c in plan.info_cards
            ],
            "model_used": llm.last_model_used,
        }
