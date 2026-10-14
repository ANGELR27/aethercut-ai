"""Motor de Escenas (Scene Engine) para KAI Streamer.

Renderiza cada escena diseñada por el AI Director de forma modular:
- Modulación emocional de voz y entonación por escena (excited, surprised, serious, skeptical).
- Layouts de cámara reactivos:
    * "avatar_cam": Plano principal de KAI hablando al espectador.
    * "video_reaction": Video / B-Roll 100% en pantalla con KAI en PIP en esquina reaccionando en vivo.
    * "card_focus": Tarjeta Bento destacada con datos clave verificados y KAI en PIP.
    * "chat_debate": Pantalla de debate con overlay de chat y preguntas de la comunidad.
- Ensamble y concatenación instantánea y estable sin desbordamiento de memoria de FFmpeg.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import re
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from config.settings import settings
from core.avatar_narrator import AvatarNarrator, DEFAULT_VOICE
from core.avatar_renderer import AvatarRenderer
from core.card_renderer import InfoCardRenderer
from core.chat_renderer import LiveChatRenderer
from core.director import DirectorBroadcastPlan, DirectorScene, SceneCard
from core.models import InfoCard
from core.orchestrator import AssetOrchestrator
from core.llm import safe_log
from utils.file_manager import FileManager


# Presets de subtítulos (ASS force_style). 'classic' = estilo original de la app.
SUBTITLE_STYLES: Dict[str, str] = {
    "classic": "FontName=Segoe UI,Bold=1,PrimaryColour=&H00FFFFFF,BorderStyle=3,OutlineColour=&HB2000000",
    "outline": "FontName=Segoe UI,Bold=1,PrimaryColour=&H00FFFFFF,BorderStyle=1,Outline=3,Shadow=0,OutlineColour=&H00000000",
    "viral": "FontName=Segoe UI Black,Bold=1,PrimaryColour=&H0000F5D4,BorderStyle=1,Outline=4,Shadow=1,OutlineColour=&H00000000",
    "hormozi": "FontName=Segoe UI Black,Bold=1,PrimaryColour=&H0000FFFF,BorderStyle=1,Outline=4,Shadow=2,OutlineColour=&H00000000",
    "mrbeast": "FontName=Segoe UI Black,Bold=1,PrimaryColour=&H0000FFFF,SecondaryColour=&H0038BDF8,BorderStyle=1,Outline=5,Shadow=2,OutlineColour=&H00000000",
    "cyber_glow": "FontName=Segoe UI,Bold=1,PrimaryColour=&H00F8BD38,BorderStyle=1,Outline=3,Shadow=2,OutlineColour=&H80000000",
    "neon": "FontName=Segoe UI,Bold=1,PrimaryColour=&H00FFE600,BorderStyle=1,Outline=2,Shadow=2,OutlineColour=&H00551A00",
    "minimal": "FontName=Segoe UI,Bold=0,PrimaryColour=&H00FFFFFF,BorderStyle=1,Outline=1,Shadow=0,OutlineColour=&H80000000",
    "cinema": "FontName=Georgia,Italic=1,Bold=0,PrimaryColour=&H00F2F2F2,BorderStyle=1,Outline=2,Shadow=1,OutlineColour=&H00000000",
}


def subtitle_force_style(sub_style: str, font_size: int, margin_v: int) -> str:
    """Devuelve el force_style de libass para el preset pedido (fallback: classic) con alineación centrada y márgenes seguros."""
    base = SUBTITLE_STYLES.get((sub_style or "classic").strip().lower(), SUBTITLE_STYLES["classic"])
    if (sub_style or "").strip().lower() == "viral":
        font_size = int(font_size * 1.15)
    return f"{base},FontSize={font_size},MarginV={margin_v},Alignment=2,MarginL=40,MarginR=40"


# Modulación de voz emocional real (rate=velocidad, pitch=tono)
# Estos valores cambian la prosodia del TTS para dar vida real a las escenas
EMOTION_VOICE_MODULATION: Dict[str, Tuple[str, str]] = {
    "excited":   ("+8%",  "+2Hz"),    # Más rápido y más agudo — entusiasmo alto
    "surprised": ("+4%",  "+4Hz"),    # Ligeramente más rápido y más agudo
    "serious":   ("-6%",  "-3Hz"),    # Más lento y más grave — peso y autoridad
    "skeptical": ("-4%",  "-2Hz"),    # Ligeramente más lento, tono bajo — escepticismo
    "confident": ("+2%",  "+0Hz"),    # Ritmo seguro, tono neutro — autoridad natural
    "humor":     ("+5%",  "+3Hz"),    # Más ágil y ligero — tono divertido
    "dramatic":  ("-10%", "-5Hz"),   # Muy lento y grave — efecto cinematográfico
    "podcast":   ("-3%",  "+0Hz"),    # Ritmo relajado, conversacional
    "breaking":  ("+12%", "+1Hz"),   # Urgente — breaking news
}

# Presets de color grading cinematico para FFmpeg eq+curves
# IMPORTANTE: todos los valores de curvas deben estar en el rango [0.0, 1.0]
COLOR_GRADE_FILTERS: Dict[str, str] = {
    "raw":             "",  # Sin filtro — salida nativa del encoder
    "cinema":          "eq=contrast=1.05:saturation=0.92:brightness=-0.01,curves=r='0/0 0.5/0.47 1/0.95':g='0/0 0.5/0.49 1/0.97':b='0/0.02 0.5/0.52 1/0.99'",
    "cinema_vignette": "eq=contrast=1.06:saturation=0.95:brightness=-0.01,vignette=PI/5",
    "documentary":     "eq=contrast=1.08:saturation=1.02:brightness=-0.01,unsharp=lx=3:ly=3:la=0.3,vignette=PI/5.5",
    "broadcast":       "eq=contrast=1.08:saturation=1.1:brightness=0.02,unsharp=lx=3:ly=3:la=0.4",
    "neon":            "eq=contrast=1.15:saturation=1.4:brightness=-0.02,curves=r='0/0 0.5/0.44 1/0.90':b='0/0.03 0.5/0.55 1/0.99'",
    "warm":            "eq=contrast=1.04:saturation=1.08,curves=r='0/0.04 0.5/0.54 1/0.98':g='0/0 0.5/0.49 1/0.96':b='0/0 0.5/0.44 1/0.88'",
    "cool":            "eq=contrast=1.03:saturation=0.88,curves=r='0/0 0.5/0.44 1/0.88':b='0/0.04 0.5/0.55 1/0.99'",
}


class SceneEngine:
    """Motor de composición y renderizado escena por escena."""

    def __init__(
        self,
        workdir: Path,
        aspect_ratio: str = "16:9",
        voice: str = DEFAULT_VOICE,
        card_theme: str = "dark",
        cancel_event: Optional[Any] = None,
        sub_style: str = "classic",
        subs_enabled: bool = True,
        burn_subtitles: bool = False,
        fps: int = 30,
        crf: int = 18,
        audio_normalize: bool = True,
        color_grade: str = "cinema",
        bgm_volume: float = 0.06,
        bgm_track: str = "default",
        style_spec: Optional[Dict[str, Any]] = None,
    ):
        self.style_spec = style_spec
        if style_spec:
            if not card_theme or card_theme in ("dark", "auto"):
                card_theme = style_spec.get("card_theme", card_theme)
            if not sub_style or sub_style in ("classic", "auto"):
                sub_style = style_spec.get("sub_style", sub_style)
        self.sub_style = sub_style
        self.subs_enabled = subs_enabled
        self.burn_subtitles = burn_subtitles
        self.workdir = workdir
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.aspect_ratio = aspect_ratio
        self.is_vertical = aspect_ratio == "9:16"
        self.W, self.H = (1080, 1920) if self.is_vertical else (1920, 1080)
        self.voice = voice
        self.card_theme = card_theme
        self.cancel_event = cancel_event
        self.fps = fps
        self.crf = crf
        self.audio_normalize = audio_normalize
        self.color_grade = color_grade
        self.bgm_volume = bgm_volume
        self.bgm_track = bgm_track
        self.narrator = AvatarNarrator(voice=voice)
        self.card_renderer = InfoCardRenderer(self.W, self.H, theme=card_theme)
        from core.web_card_renderer import WebCardRenderer
        self.web_renderer = WebCardRenderer()
        from core.kinetic_titles import KineticTitleRenderer
        self.title_renderer = KineticTitleRenderer(self.web_renderer)
        self.chat_renderer = LiveChatRenderer(width=340 if not self.is_vertical else 300)
        (self.workdir / "assets").mkdir(parents=True, exist_ok=True)
        self.orchestrator = AssetOrchestrator(target_dir=self.workdir / "assets")
        try:
            from core.glm_motion_director import GLMMotionDirector
            self.glm_motion_director = GLMMotionDirector()
        except Exception:
            self.glm_motion_director = None
        try:
            from core.motion_graphics_engine import MotionGraphicsEngine
            self.motion_engine = MotionGraphicsEngine(self.web_renderer, is_vertical=self.is_vertical)
        except Exception:
            self.motion_engine = None
        try:
            from core.ai_remotion_generator import AIRemotionGenerator
            self.ai_remotion = AIRemotionGenerator()
        except Exception:
            self.ai_remotion = None


    @staticmethod
    def _is_valid_media_clip(clip_p: Path) -> bool:
        """Comprueba si un archivo multimedia existe y tiene frames decodificables."""
        if not clip_p.exists() or clip_p.stat().st_size < 1000:
            return False
        if clip_p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
            return True
        try:
            res = subprocess.run(
                ["ffmpeg", "-i", str(clip_p), "-t", "0.5", "-f", "null", "-"],
                capture_output=True, text=True, timeout=5
            )
            if "Output file is empty" in res.stderr:
                return False
            return True
        except Exception:
            return False

    async def render_scene(
        self,
        scene: DirectorScene,
        avatar_clip: Optional[Path] = None,
        avatar_webm: Optional[Path] = None,
        bgm_path: Optional[Path] = None,
        chat_overlay_path: Optional[Path] = None,
        status_cb: Optional[Callable[[str], None]] = None,
    ) -> Path:
        """Renderiza una escena individual en su propio archivo MP4."""
        scene_dir = self.workdir / f"scene_{scene.scene_id}"
        scene_dir.mkdir(parents=True, exist_ok=True)
        scene_out = scene_dir / f"scene_{scene.scene_id}.mp4"
        # Escritura atómica con UUID único para evitar bloqueos de Windows [WinError 32]
        scene_tmp = scene_dir / f"scene_{scene.scene_id}_{uuid.uuid4().hex[:6]}.tmp.mp4"
        for old_tmp in scene_dir.glob(f"scene_{scene.scene_id}*.tmp.mp4"):
            try:
                old_tmp.unlink(missing_ok=True)
            except OSError:
                pass

        # 0. Cache inteligente de escenas (Reanudar sin rehacer lo que ya está listo).
        # Se valida tamaño Y la firma de settings + guion: una escena hecha con otro
        # formato (9:16 ↔ 16:9), otra voz u otro texto NO se reutiliza nunca.
        thumb_path = scene_dir / "scene_thumb.jpg"
        meta_path = scene_dir / "render_meta.json"
        if scene_out.exists() and scene_out.stat().st_size > 50000 and self._cache_meta_valid(meta_path, scene):
            for old_tmp in scene_dir.glob(f"scene_{scene.scene_id}*.tmp.mp4"):
                try:
                    old_tmp.unlink(missing_ok=True)
                except OSError:
                    pass
            if not thumb_path.exists():
                try:
                    import subprocess
                    subprocess.run([
                        "ffmpeg", "-y", "-ss", "0.5", "-i", str(scene_out),
                        "-vframes", "1", "-q:v", "3", str(thumb_path)
                    ], capture_output=True, timeout=5)
                except Exception:
                    pass
            safe_log(f"[SceneEngine] Reusando escena {scene.scene_id} ({scene.name}) ya renderizada.")
            if status_cb:
                status_cb(f"Escena {scene.scene_id} restaurada desde caché.")
            return scene_out

        if status_cb:
            status_cb(f"Dirigiendo Escena {scene.scene_id}: {scene.name} ({scene.type})")

        # 1. Síntesis de voz neural con modulación emocional y pronunciación fluida
        speech_text = scene.speech.strip()
        if not speech_text:
            speech_text = "Dato mata relato, analicemos este punto a fondo."

        from utils.speech_normalizer import normalize_speech_for_tts
        tts_speech_text = normalize_speech_for_tts(speech_text)

        rate_mod, pitch_mod = EMOTION_VOICE_MODULATION.get(scene.emotion, ("+0%", "+0Hz"))
        audio_path = scene_dir / "voice.mp3"

        sentence_boundaries = []
        audio_generated = False

        # 1. Síntesis neuronal de alta fidelidad con el narrador (Speechify / Gemini / Voz seleccionada por el usuario)
        try:
            safe_log(f"[SceneEngine] Sintetizando locución con la voz seleccionada ({self.voice}) para escena {scene.scene_id}...")
            _, tts_duration = await self.narrator.synthesize(tts_speech_text, audio_path, voice=self.voice)
            if audio_path.exists() and audio_path.stat().st_size > 500:
                audio_generated = True
                safe_log(f"[SceneEngine] Audio de escena {scene.scene_id} generado exitosamente con voz {self.voice} ({audio_path.stat().st_size} bytes)")
        except Exception as _narrator_err:
            safe_log(f"[SceneEngine] Error en síntesis neuronal con narrador: {_narrator_err}")

        # 2. Respaldo secundario con Edge-TTS (si la red lo permite)
        if not audio_generated:
            try:
                import edge_tts
                communicate = edge_tts.Communicate(tts_speech_text, self.voice, rate=rate_mod, pitch=pitch_mod)
                with open(audio_path, "wb") as f_audio:
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            f_audio.write(chunk["data"])
                        elif chunk["type"] == "SentenceBoundary":
                            s_sec = chunk["offset"] / 10_000_000
                            d_sec = chunk["duration"] / 10_000_000
                            sentence_boundaries.append((s_sec, s_sec + d_sec, chunk["text"].strip()))
                if audio_path.exists() and audio_path.stat().st_size > 500:
                    audio_generated = True
            except Exception as _edge_err:
                safe_log(f"[SceneEngine] Edge-TTS no disponible ({_edge_err}). Pasando a gTTS regional...")

        # 3. Respaldo terciario infalible con gTTS regional
        if not audio_generated:
            try:
                from gtts import gTTS
                v_lower = (self.voice or "").lower()
                tld = "com.mx"
                if any(x in v_lower for x in ["es-es", "alvaro"]):
                    tld = "es"
                elif any(x in v_lower for x in ["es-co", "gonzalo", "clon"]):
                    tld = "com.co"
                elif any(x in v_lower for x in ["es-ar", "tomas", "elena"]):
                    tld = "com.ar"
                gtts_obj = gTTS(text=tts_speech_text, lang="es", tld=tld)
                gtts_obj.save(str(audio_path))
                audio_generated = True
            except Exception as _gtts_err:
                safe_log(f"[SceneEngine] Error crítico generando voz fallback: {_gtts_err}")
                raise

        # Medir duración exacta del audio real de la escena generado limpiamente por el TTS neural
        tts_duration = self._get_audio_duration(audio_path)

        # Si sentence_boundaries no fue provisto por Edge-TTS, calcular boundaries de frases con la duración real del audio
        if not sentence_boundaries:
            raw_sentences = [s.strip() for s in re.split(r"([.!?…]+)", tts_speech_text) if s.strip()]
            full_sents = []
            cur_s = ""
            for part in raw_sentences:
                cur_s += (" " if cur_s else "") + part
                if re.search(r"[.!?…]$", part):
                    full_sents.append(cur_s.strip())
                    cur_s = ""
            if cur_s:
                full_sents.append(cur_s.strip())
            if not full_sents:
                full_sents = [tts_speech_text]

            cur_t = 0.0
            total_chars = max(1, sum(len(s) for s in full_sents))
            for s in full_sents:
                s_dur = (len(s) / total_chars) * tts_duration
                sentence_boundaries.append((round(cur_t, 2), round(cur_t + s_dur, 2), s))
                cur_t += s_dur

        # La escena se ajusta de forma milimétrica al audio hablado para evitar silencios y mantener sincronía exacta con los fotogramas
        duration = max(3.0, round(tts_duration + 0.15, 2))
        dur_str = f"{duration:.2f}"

        # 2. Curaduría Inteligente de Contenido y Apoyo Visual
        from core.smart_media_curator import SmartMediaCurator, VisualIntentType, VisualNature
        visual_intent = SmartMediaCurator.analyze_narration_intent(speech_text, scene.name)
        safe_log(f"[SmartMediaCurator] 🧠 Intención detectada para escena {scene.scene_id}: {visual_intent.intent_type.value} ('{visual_intent.entity_name}')")

        broll_img = None
        is_opening_scene = (int(getattr(scene, "scene_id", 1)) == 1)

        # Solo usar el estudio streamer si explícitamente se pide avatar_cam en escenas intermedias y NO hay visual_query
        # En la apertura (escena 1), SIEMPRE se busca material visual/documental relevante del tema
        if (scene.type == "avatar_cam" or scene.camera == "hero_center") and not is_opening_scene and not scene.visual_query:
            studio_blur_path = Path("assets/streamer_studio_blur_9_16.jpg" if self.is_vertical else "assets/streamer_studio_blur_16_9.jpg")
            if studio_blur_path.exists():
                broll_img = studio_blur_path
            elif Path("assets/streamer_studio_room.jpg").exists():
                broll_img = Path("assets/streamer_studio_room.jpg")

        if scene.type == "vector_motion":
            # Sustituir monigotes/stickmen vectoriales por B-Roll temático cinemático en alta definición
            try:
                v_concept = scene.visual_query or f"{scene.name} motion graphics 4k tech"
                safe_log(f"[SceneEngine] 🎬 Obteniendo B-Roll cinemático HD para escena conceptual {scene.scene_id}: '{v_concept}'")
                broll_img = await self._get_scene_visual(v_concept, scene_dir, is_video_scene=True, intent=visual_intent)
                if not broll_img or not broll_img.exists():
                    fallback_concept = f"{scene.name} concept documentary 4k"
                    broll_img = await self._get_scene_visual(fallback_concept, scene_dir, is_video_scene=True, intent=visual_intent)
            except Exception as _ev:
                safe_log(f"[SceneEngine] Fallback en visual conceptual: {_ev}")

        # MODO ANÁLISIS DE CASO: si el director ancló esta escena a un fotograma
        # REAL del video fuente, ese fotograma ES el fondo — evidencia visual
        # del caso concreto, jamás stock genérico. (Imagen → Ken Burns.)
        case_frame_idx = getattr(scene, "case_frame", None)
        if case_frame_idx is not None:
            case_frame_path = self.workdir / "case_frames" / f"frame_{int(case_frame_idx):02d}.jpg"
            if case_frame_path.exists():
                broll_img = case_frame_path
                safe_log(f"[SceneEngine] 🎯 Escena {scene.scene_id}: fotograma REAL del caso (frame {int(case_frame_idx)}) como fondo.")

        if not broll_img or not broll_img.exists():
            # Priorizar video en movimiento para todas las escenas con B-Roll, reacción, noticias o contexto
            # En la apertura (escena 1), SIEMPRE es video documental de alto impacto
            is_video_reaction = is_opening_scene or (scene.type != "avatar_cam") or ("video" in (scene.visual_query or "").lower())
            broll_img = await self._get_scene_visual(scene.visual_query, scene_dir, is_video_scene=is_video_reaction, intent=visual_intent)

        # Garantizar que NUNCA quede un fondo negro vacío: si la descarga no encontró imagen externa,
        # usar el set de estudio iluminado cinemático con bokeh de KAI
        if not broll_img or not broll_img.exists():
            fallback_bg = Path("assets/streamer_studio_blur_9_16.jpg" if self.is_vertical else "assets/streamer_studio_blur_16_9.jpg")
            if not fallback_bg.exists():
                fallback_bg = Path("assets/streamer_studio_room.jpg")
            if fallback_bg.exists():
                broll_img = fallback_bg

        # Registro y Verificación de Procedencia del Material Visual
        media_prov = self._get_media_provenance(broll_img)
        provenance_chip_path = None
        if media_prov and media_prov.get("attribution_badge"):
            b_text = str(media_prov.get("attribution_badge", "")).strip()
            s_name = str(media_prov.get("source_name", "Archivo Oficial")).strip()
            safe_log(f"[SmartMediaCurator] 🛡️ Proveniencia: {b_text} | Fuente: {s_name} | Licencia: {media_prov.get('license', 'Uso Libre')}")
            # Si es documental real, histórico, o reconstrucción, generar pastilla de transparencia en pantalla
            if any(k in b_text.upper() for k in ("HISTÓRICO", "HISTORICO", "DOCUMENTAL", "RECONSTRUCCIÓN", "RECONSTRUCCION", "SIMULACIÓN", "SIMULACION", "VERIFICADO")):
                try:
                    out_chip_p = scene_dir / f"provenance_chip_{scene.scene_id}.png"
                    provenance_chip_path = self.web_renderer.render_visual_template(
                        template_name="source_chip",
                        out_png=out_chip_p,
                        params={"source_name": s_name, "tag": b_text},
                        variant="orange_noir",
                    )
                except Exception as _p_err:
                    safe_log(f"[SmartMediaCurator] Fallback en source chip: {_p_err}")

        # 2b. Descargar clips secuenciales de referencia (visual_beats) o segundo clip complementario
        bg_clips: List[Tuple[Path, float]] = []
        if broll_img and broll_img.exists():
            bg_clips.append((broll_img, 0.0))

        # Si el director aportó visual_beats con frases exactas, sincronizar cortes con esas frases
        beats = getattr(scene, "visual_beats", []) or []
        vq2 = getattr(scene, "visual_query2", "") or ""
        if beats and len(beats) > 1 and duration >= 5.0:
            # Calcular momentos de corte para cada beat
            segment_step = duration / len(beats)
            for b_idx, beat in enumerate(beats[1:], start=1):
                b_query = beat.get("query") if isinstance(beat, dict) else str(beat)
                if not b_query or not b_query.strip():
                    continue
                # Si beat tiene trigger literal, intentar ubicar el timestamp exacto en boundaries
                b_time = round(b_idx * segment_step, 2)
                b_trig = (beat.get("trigger") or "").lower().strip() if isinstance(beat, dict) else ""
                if b_trig and sentence_boundaries:
                    for s_st, _s_en, s_txt in sentence_boundaries:
                        if b_trig in s_txt.lower() or any(w in s_txt.lower() for w in b_trig.split()[:3]):
                            b_time = max(1.5, min(duration - 2.0, round(s_st, 2)))
                            break
                try:
                    clip_path = await self._get_scene_visual(b_query, scene_dir, is_video_scene=True)
                    if clip_path and clip_path.exists():
                        bg_clips.append((clip_path, b_time))
                except Exception as _eb:
                    safe_log(f"[SceneEngine] Error obteniendo beat visual '{b_query}': {_eb}")
        elif vq2 and vq2.strip() and vq2.strip().lower() != (scene.visual_query or "").strip().lower():
            try:
                broll_img2 = await self._get_scene_visual(vq2, scene_dir, is_video_scene=True)
                if broll_img2 and broll_img2.exists():
                    bg_clips.append((broll_img2, round(duration * 0.5, 2)))
            except Exception as _e:
                safe_log(f"[SceneEngine] Fallback en segundo clip: {_e}")

        # 2c. Enriquecer ritmo visual: evitar permanecer demasiado tiempo en un mismo clip estatico
        # Salvo escenas de reaccion pura o avatar cam, garantizar variacion visual dinamica cada ~4.0 - 5.0s
        if scene.type not in ("video_reaction", "avatar_cam") and duration >= 6.5:
            existing_times = [t for _, t in bg_clips]
            all_pts = sorted(existing_times + [duration])
            max_gap = max((all_pts[i+1] - all_pts[i] for i in range(len(all_pts)-1)), default=duration)

            if max_gap > 5.2:
                target_cut = 4.5
                while target_cut <= duration - 2.2 and len(bg_clips) < 4:
                    if not any(abs(t - target_cut) < 2.0 for t in existing_times):
                        sub_q = ""
                        # 1. Usar visual_queries secundarias diseñadas por el director si existen
                        if scene.visual_queries and len(bg_clips) < len(scene.visual_queries):
                            cand_q = scene.visual_queries[len(bg_clips)]
                            if cand_q and cand_q != scene.visual_query:
                                sub_q = f"{cand_q} 4k"

                        # 2. Revisar si hay un beat visual del director cercano a este tiempo
                        if not sub_q and getattr(scene, "visual_beats", None):
                            for vb in scene.visual_beats:
                                if isinstance(vb, dict) and vb.get("query"):
                                    sub_q = f"{vb['query']} 4k"
                                    break

                        # 3. Variación cinemática en inglés sobre la query base (evita búsquedas en español)
                        if not sub_q:
                            base_q = scene.visual_query or "documentary cinematic"
                            variations = ["close up detail 4k", "wide angle perspective 4k", "slow motion cinematic 4k"]
                            var_suffix = variations[(len(bg_clips) - 1) % len(variations)]
                            sub_q = f"{base_q} {var_suffix}"

                        try:
                            supp_clip = await self._get_scene_visual(sub_q, scene_dir, is_video_scene=True)
                            if supp_clip and supp_clip.exists():
                                bg_clips.append((supp_clip, round(target_cut, 2)))
                                existing_times.append(round(target_cut, 2))
                                safe_log(f"[SceneEngine] Variacion B-Roll enriquecida en t={target_cut:.1f}s: '{sub_q}'")
                        except Exception as _esup:
                            safe_log(f"[SceneEngine] Fallback en B-Roll complementario: {_esup}")
                    target_cut += 4.5

        # Filtrar clips corruptos o sin frames decodificables
        valid_bg_clips = []
        for p, t in bg_clips:
            if self._is_valid_media_clip(p):
                valid_bg_clips.append((p, t))
            else:
                safe_log(f"[SceneEngine] ⚠️ Descartando clip corrupto o sin frames decodificables: {p.name}")
        bg_clips = valid_bg_clips

        # Ordenar clips de fondo por segundo de inicio
        bg_clips.sort(key=lambda x: x[1])
        if bg_clips and bg_clips[0][1] > 0.0:
            bg_clips[0] = (bg_clips[0][0], 0.0)

        # Si no se pudo obtener ningún B-Roll o falló la descarga, usar estudio ambiental
        if not bg_clips:
            studio_blur_path = Path("assets/streamer_studio_blur_9_16.jpg" if self.is_vertical else "assets/streamer_studio_blur_16_9.jpg")
            fallback_bg = studio_blur_path if studio_blur_path.exists() else Path("assets/streamer_studio_room.jpg")
            if fallback_bg.exists():
                bg_clips.append((fallback_bg, 0.0))

        # Generar clip de avatar con sincronización reactiva labial a la voz de la escena
        scene_avatar_clip = scene_dir / "kai_avatar_synced.mov"
        try:
            from core.avatar_renderer import AvatarRenderer
            rnd = AvatarRenderer()
            await asyncio.to_thread(
                rnd.render_reaction_clip,
                duration_sec=duration,
                out_path=scene_avatar_clip,
                audio_path=audio_path,
                fps=24
            )
            # Validar que el render realmente produjo un archivo utilizable:
            # en escenas consecutivas el render puede "completar" sin excepción
            # pero dejar un archivo vacío/corrupto (recursos agotados). Sin esta
            # verificación, el FFmpeg de la escena intentaba abrir un .mov roto
            # y la escena entera salía truncada (0.4s en vez de 15s).
            if not scene_avatar_clip.exists() or scene_avatar_clip.stat().st_size < 10000:
                safe_log(f"[SceneEngine] Avatar sincronizado inválido o vacío para escena {scene.scene_id}: fallback a base.")
                scene_avatar_clip = None
        except Exception as exc:
            safe_log(f"[SceneEngine] Fallback a avatar clip base: {exc}")
            scene_avatar_clip = None

        # 2d. Microelementos visuales cineticos sutiles disenados por GLM-5.3 (HyperFrames / Remotion / Native)
        motion_overlay_path = None
        if getattr(self, "motion_engine", None) and getattr(self, "glm_motion_director", None):
            try:
                acc_col = getattr(scene, "accent_color", "#ff9436") or "#ff9436"
                motion_spec = self.glm_motion_director.design_motion_spec(
                    scene_name=scene.name,
                    speech_text=speech_text,
                    duration=duration,
                    accent_color=acc_col,
                    scene_type=getattr(scene, "type", "broll_narration"),
                )
                motion_overlay_path = await self.motion_engine.render_scene_motion_overlay(
                    motion_spec=motion_spec,
                    duration=duration,
                    scene_dir=scene_dir,
                    scene_id=scene.scene_id,
                )
                if motion_overlay_path and motion_overlay_path.exists():
                    safe_log(f"[SceneEngine] ? Capa de microelementos cineticos GLM-5.3 lista para escena {scene.scene_id}")
            except Exception as _me:
                safe_log(f"[SceneEngine] Fallback en motion graphics: {_me}")
                motion_overlay_path = None

        # 3. Preparar tarjeta Bento moderna o alternativa visual honesta
        card_img_path = None
        card_visual_type = "bento"
        card_start_time = 0.5
        smart_card_dur = None

        # Si el director no asignó tarjeta pero la locución menciona una cifra, lugar, comparación,
        # frase impactante, acontecimiento o concepto difícil, generar la alternativa visual honesta adecuada:
        if not scene.card and visual_intent and visual_intent.intent_type != VisualIntentType.GENERAL_BROLL:
            from core.director import SceneCard
            if visual_intent.intent_type == VisualIntentType.STAT_NUMBER and visual_intent.stat_value:
                scene.card = SceneCard(
                    headline=visual_intent.entity_name,
                    stat=visual_intent.stat_value,
                    body=visual_intent.raw_sentence[:100],
                    badge="MÉTRICA VERIFICADA",
                    template="stat_counter",
                )
                safe_log(f"[SmartMediaCurator] 📊 Cifra en locución -> Generando Stat Counter: {visual_intent.stat_value}")
            elif visual_intent.intent_type == VisualIntentType.GEO_LOCATION:
                scene.card = SceneCard(
                    headline=visual_intent.entity_name,
                    stat=visual_intent.location or "ZONA TÁCTICA",
                    body=f"Ubicación geográfica clave: {visual_intent.entity_name} ({visual_intent.location})",
                    badge="MAPA TÁCTICO",
                    template="map",
                )
                safe_log(f"[SmartMediaCurator] 🗺️ Lugar en locución -> Generando Mapa GeoIntel: {visual_intent.entity_name}")
            elif visual_intent.intent_type == VisualIntentType.VERSUS_COMPARISON:
                scene.card = SceneCard(
                    headline=visual_intent.entity_name,
                    body=visual_intent.secondary_entity,
                    badge="COMPARATIVA",
                    template="versus_split",
                )
                safe_log(f"[SmartMediaCurator] ⚔️ Comparación en locución -> Generando Versus Split: {visual_intent.entity_name} vs {visual_intent.secondary_entity}")
            elif visual_intent.intent_type == VisualIntentType.IMPACT_PHRASE:
                scene.card = SceneCard(
                    headline=visual_intent.entity_name,
                    body=visual_intent.raw_sentence[:90],
                    badge="PUNTO CLAVE",
                    template="alert_banner",
                )
                safe_log(f"[SmartMediaCurator] ⚡ Frase impactante en locución -> Generando Alert Banner: {visual_intent.entity_name}")
            elif visual_intent.intent_type == VisualIntentType.COMPLEX_CONCEPT:
                scene.card = SceneCard(
                    headline=visual_intent.entity_name,
                    body=visual_intent.raw_sentence[:95],
                    badge="CONCEPTO TÉCNICO",
                    template="tech_card",
                )
                safe_log(f"[SmartMediaCurator] 💡 Concepto difícil en locución -> Generando Tech Card: {visual_intent.entity_name}")
            elif visual_intent.intent_type == VisualIntentType.HISTORICAL_EVENT and visual_intent.year:
                scene.card = SceneCard(
                    headline=visual_intent.entity_name,
                    body=visual_intent.raw_sentence[:110],
                    stat=str(visual_intent.year),
                    badge=f"ARCHIVO · {visual_intent.year}",
                    template="quote_evidence",
                )
                safe_log(f"[SmartMediaCurator] 📜 Acontecimiento con fecha -> Generando Registro Histórico: {visual_intent.year}")

        # Calcular temporización sincronizada para que aparezca cuando aporte contexto y se retire cuando deje de ser relevante
        if visual_intent:
            card_start_time, smart_card_dur = SmartMediaCurator.calculate_smart_timing(
                visual_intent, sentence_boundaries, duration
            )

        # 3b. Remotion AI: Evaluación prioritaria para animaciones React (MetricCounter / VersusComparison)
        ai_remotion_mov: Optional[Path] = None
        if getattr(self, "ai_remotion", None) and self.ai_remotion.remotion.available() and duration >= 3.0:
            c_templ_cand = str(getattr(scene.card, "template", "") if hasattr(scene.card, "template") else (scene.card.get("template", "") if isinstance(scene.card, dict) else "")).lower() if scene.card else ""
            c_stat_cand = str(getattr(scene.card, "stat", "") if hasattr(scene.card, "stat") else (scene.card.get("stat", "") if isinstance(scene.card, dict) else "")) if scene.card else ""
            is_stat_candidate = (
                c_templ_cand in ("stat_counter", "stat_card")
                or (visual_intent and visual_intent.intent_type == VisualIntentType.STAT_NUMBER)
                or ("%" in c_stat_cand or (c_stat_cand and any(ch.isdigit() for ch in c_stat_cand) and len(c_stat_cand) < 14))
            )
            is_versus_candidate = (
                c_templ_cand in ("versus_split", "versus", "vs")
                or (visual_intent and visual_intent.intent_type == VisualIntentType.VERSUS_COMPARISON)
                or (scene.card and " vs " in (getattr(scene.card, "headline", "") or "").lower())
            )
            if is_stat_candidate or is_versus_candidate:
                try:
                    ai_remotion_mov = await self.ai_remotion.render_ai_overlay(
                        scene_name=scene.name,
                        speech_text=speech_text,
                        duration=duration,
                        out_dir=scene_dir,
                        vertical=self.is_vertical,
                        theme_spec=getattr(self, "style_spec", None),
                        card=scene.card,
                        intent=visual_intent,
                    )
                    if ai_remotion_mov and ai_remotion_mov.exists() and ai_remotion_mov.stat().st_size > 20000:
                        safe_log(f"[SceneEngine] ⚛️ Remotion React overlay animado generado para escena {scene.scene_id}: {ai_remotion_mov.name}")
                        scene.card = None  # Remotion toma el protagonismo; evitamos tarjeta estática redundante
                except Exception as _re_err:
                    safe_log(f"[SceneEngine] Remotion React overlay omitido, fallback a estático: {_re_err}")
                    ai_remotion_mov = None

        if scene.card:
            card_img_path = scene_dir / f"card_{scene.scene_id}.png"
            c_badge = str(scene.card.get("badge") if isinstance(scene.card, dict) else getattr(scene.card, "badge", "") or "").upper()
            c_headline = str(scene.card.get("headline") if isinstance(scene.card, dict) else getattr(scene.card, "headline", "") or "")
            c_body = str(scene.card.get("body") if isinstance(scene.card, dict) else getattr(scene.card, "body", "") or c_headline)
            c_stat = str(scene.card.get("stat") if isinstance(scene.card, dict) else getattr(scene.card, "stat", "") or "")
            c_style = str(getattr(scene.card, "style", "auto") if hasattr(scene.card, "style") else (scene.card.get("style", "auto") if isinstance(scene.card, dict) else "auto")).lower().strip()
            c_icon = str(getattr(scene.card, "icon", "✓") if hasattr(scene.card, "icon") else (scene.card.get("icon", "✓") if isinstance(scene.card, dict) else "✓")).strip()
            c_sub = str(getattr(scene.card, "subtitle", "") if hasattr(scene.card, "subtitle") else (scene.card.get("subtitle", "") if isinstance(scene.card, dict) else "")).strip()

            # Sincronización temporal con la locución si se mencionan palabras clave del titular
            if sentence_boundaries and c_headline and not smart_card_dur:
                c_words = [w.lower() for w in re.findall(r'\w+', c_headline) if len(w) > 3]
                for s_st, _s_en, s_txt in sentence_boundaries:
                    low_txt = s_txt.lower()
                    if any(w in low_txt for w in c_words):
                        card_start_time = max(0.4, min(duration - 2.5, round(s_st, 2)))
                        break

            c_template = str(getattr(scene.card, "template", "auto") if hasattr(scene.card, "template") else (scene.card.get("template", "auto") if isinstance(scene.card, dict) else "auto")).lower().strip()
            c_variant = str(getattr(scene.card, "variant", "orange_noir") if hasattr(scene.card, "variant") else (scene.card.get("variant", "orange_noir") if isinstance(scene.card, dict) else "orange_noir")).lower().strip()
            c_params = dict(getattr(scene.card, "params", {}) if hasattr(scene.card, "params") else (scene.card.get("params", {}) if isinstance(scene.card, dict) else {}))

            try:
                # 0. Plantillas dedicadas del VisualTemplatesLibrary
                # 0a. Distintivo Viral Inclinado (Reels: '✓ ganó Opus', '100% Real', 'Confirmado')
                if c_template == "verdict_badge" or c_style == "verdict_badge" or any(k in c_badge for k in ("VEREDICTO", "GANADOR", "GANÓ", "GANO", "SELLO", "BADGE", "STAMP")) or any(k in c_headline.lower() for k in ("ganó", "gano", "ganador", "100% real", "veredicto")):
                    card_res = self.web_renderer.render_visual_template(
                        template_name="verdict_badge",
                        out_png=card_img_path,
                        params={"headline": c_headline, "icon": c_icon or "✓", "subtitle": c_sub or c_body, **c_params},
                        variant=c_variant,
                    )
                    if card_res and card_res.exists():
                        card_visual_type = "verdict_badge"
                        safe_log(f"[SceneEngine] 🏷️ Distintivo Viral (Verdict Badge) generado para escena {scene.scene_id}: {c_headline}")

                # 0b. Tarjeta Técnica Flotante Superior (Reels: 'find-skills por Vercel')
                elif c_template in ("tech_card", "tech_header") or c_style == "tech_card" or any(k in c_badge for k in ("TECH", "HERRAMIENTA", "SKILL", "TOOL", "DEV", "GITHUB", "CÓDIGO", "CODIGO")):
                    card_res = self.web_renderer.render_visual_template(
                        template_name="tech_card",
                        out_png=card_img_path,
                        params={"title": c_headline, "subtitle": c_sub or c_body or c_stat, **c_params},
                        variant=c_variant,
                    )
                    if card_res and card_res.exists():
                        card_visual_type = "tech_card"
                        safe_log(f"[SceneEngine] 💻 Tarjeta Técnica Flotante (Tech Card) generada para escena {scene.scene_id}: {c_headline}")

                # 0c. Cifra Récord / Métrica Clave con medidor en gradiente
                elif c_template in ("stat_counter", "stat_card") or any(k in c_badge for k in ("RÉCORD", "RECORD", "CIFRA", "MÉTRICA", "METRICA")) or ("%" in c_stat or (c_stat and any(ch.isdigit() for ch in c_stat) and len(c_stat) < 12 and not any(k in c_badge for k in ("MAPA", "GEO")))):
                    card_res = self.web_renderer.render_visual_template(
                        template_name="stat_counter",
                        out_png=card_img_path,
                        params={"stat_value": c_stat or "100%", "stat_label": c_body or c_headline, "headline": c_headline, "tag": c_badge or "MÉTRICA CLAVE", **c_params},
                        variant=c_variant,
                    )
                    if card_res and card_res.exists():
                        card_visual_type = "stat_counter"
                        safe_log(f"[SceneEngine] 📊 Métrica Clave (Stat Counter) generada para escena {scene.scene_id}: {c_stat}")

                # 0d. Comparativa Versus Dual (Lado A vs Lado B con divisor circular central)
                elif c_template in ("versus_split", "versus", "vs") or any(k in c_badge for k in ("VERSUS", "COMPARATIVA", "DUAL", "VS")) or (" vs " in c_headline.lower() or " vs " in c_body.lower() or " vs " in c_stat.lower()):
                    s_a = c_headline
                    s_b = c_body or "IA"
                    st_a, st_b = "", ""
                    if " vs " in c_headline.lower():
                        parts = c_headline.split(" vs ", 1)
                        s_a, s_b = parts[0].strip(), parts[1].strip()
                    if " vs " in c_stat.lower():
                        st_parts = c_stat.split(" vs ", 1)
                        st_a, st_b = st_parts[0].strip(), st_parts[1].strip()
                    card_res = self.web_renderer.render_visual_template(
                        template_name="versus_split",
                        out_png=card_img_path,
                        params={"side_a": s_a, "side_b": s_b, "stat_a": st_a, "stat_b": st_b, "tag": c_badge or "COMPARATIVA DIRECTA", **c_params},
                        variant=c_variant,
                    )
                    if card_res and card_res.exists():
                        card_visual_type = "versus_split"
                        safe_log(f"[SceneEngine] ⚔️ Comparativa Versus Dual generada para escena {scene.scene_id}: {s_a} vs {s_b}")

                # 0e. Insignia de Hito, Fase o Paso (Step Badge)
                elif c_template in ("step_badge", "step", "phase") or any(k in c_badge for k in ("PASO", "FASE", "HITO", "REGLA")) or (c_headline.lower().startswith("paso ") or c_headline.lower().startswith("fase ")):
                    step_num = c_stat or "01"
                    m_num = re.search(r'\d+', c_headline)
                    if m_num and not c_stat:
                        step_num = m_num.group(0)
                    card_res = self.web_renderer.render_visual_template(
                        template_name="step_badge",
                        out_png=card_img_path,
                        params={"step_number": step_num, "step_title": c_headline, "subtitle": c_body or c_sub, **c_params},
                        variant=c_variant,
                    )
                    if card_res and card_res.exists():
                        card_visual_type = "step_badge"
                        safe_log(f"[SceneEngine] 🔢 Insignia de Fase (Step Badge) generada para escena {scene.scene_id}: {c_headline}")

                # 0f. Banner de Alerta Crítica HUD
                elif c_template in ("alert_banner", "alert", "warning") or any(k in c_badge for k in ("ALERTA", "PELIGRO", "WARNING", "CRÍTICO", "CRITICO")):
                    card_res = self.web_renderer.render_visual_template(
                        template_name="alert_banner",
                        out_png=card_img_path,
                        params={"headline": c_headline, "body": c_body, "tag": c_badge or "ADVERTENCIA CRÍTICA", **c_params},
                        variant="crimson_hazard" if c_variant == "orange_noir" else c_variant,
                    )
                    if card_res and card_res.exists():
                        card_visual_type = "alert_banner"
                        safe_log(f"[SceneEngine] ⚠️ Banner de Alerta Táctica generado para escena {scene.scene_id}: {c_headline}")

                # 0g. Pastilla de Fuente Verificada (Source Chip)
                elif c_template in ("source_chip", "chip", "source") or any(k in c_badge for k in ("FUENTE", "ATRIBUCIÓN", "ATRIBUCION", "ORIGEN")):
                    card_res = self.web_renderer.render_visual_template(
                        template_name="source_chip",
                        out_png=card_img_path,
                        params={"source_name": c_headline, "tag": c_badge or "FUENTE OFICIAL", **c_params},
                        variant=c_variant,
                    )
                    if card_res and card_res.exists():
                        card_visual_type = "source_chip"
                        safe_log(f"[SceneEngine] 🛡️ Pastilla de Fuente (Source Chip) generada para escena {scene.scene_id}: {c_headline}")

                # 0h. Citas / Evidencias documentales -> Cita Vox Style de alta fidelidad
                elif c_template in ("quote_evidence", "quote", "citation") or any(k in c_badge for k in ("DOCUMENTAL", "EVIDENCIA", "INFORME", "CITA")):
                    card_res = self.web_renderer.render_visual_template(
                        template_name="quote_evidence",
                        out_png=card_img_path,
                        params={"quote_text": c_body or c_headline, "source": c_stat or "Registro Oficial 2026", **c_params},
                        variant=c_variant,
                    )
                    if card_res and card_res.exists():
                        card_visual_type = "quote_evidence"
                        safe_log(f"[SceneEngine] 📜 Cita/Evidencia Vox Style generada para escena {scene.scene_id}")

                # 0i. Recorte de Periódico / Prensa con Subrayador Neón (Estilo Adrià Solà Pastor / Vox)
                elif c_template in ("newspaper_clipping", "newspaper", "press_clipping", "titular_prensa") or any(k in c_badge for k in ("NOTICIA", "PRENSA", "PERIODICO", "PERIÓDICO", "TITULAR", "FINANCIAL", "BLOOMBERG", "WSJ", "REUTERS")):
                    card_res = self.web_renderer.render_visual_template(
                        template_name="newspaper_clipping",
                        out_png=card_img_path,
                        params={
                            "headline": c_headline,
                            "newspaper": c_stat or "FINANCIAL TIMES",
                            "body_lead": c_body if c_body != c_headline else "",
                            "tag": c_badge or "EVIDENCIA EDITORIAL",
                            **c_params
                        },
                        variant=c_variant,
                    )
                    if card_res and card_res.exists():
                        card_visual_type = "newspaper_clipping"
                        safe_log(f"[SceneEngine] 📰 Recorte de Prensa con Subrayador Neón generado para escena {scene.scene_id}: {c_headline}")

                # 0j. Publicación Verificada en Redes (X / Twitter Card)
                elif c_template in ("social_post", "tweet", "x_post", "comunicado_social") or any(k in c_badge for k in ("TWEET", "TWITTER", "POST", "DECLARACION", "DECLARACIÓN", "X")):
                    card_res = self.web_renderer.render_visual_template(
                        template_name="social_post",
                        out_png=card_img_path,
                        params={
                            "author_name": c_headline,
                            "handle": c_stat if c_stat.startswith("@") else f"@{c_headline.lower().replace(' ', '')}",
                            "post_text": c_body or c_headline,
                            **c_params
                        },
                        variant=c_variant,
                    )
                    if card_res and card_res.exists():
                        card_visual_type = "social_post"
                        safe_log(f"[SceneEngine] 🐦 Publicación Social Verificada generada para escena {scene.scene_id}: {c_headline}")

                # 0k. Cronología Documental / Línea de Tiempo
                elif c_template in ("timeline_milestone", "timeline", "cronologia", "hitos") or any(k in c_badge for k in ("CRONOLOGIA", "CRONOLOGÍA", "TIMELINE", "EVOLUCIÓN", "EVOLUCION")):
                    card_res = self.web_renderer.render_visual_template(
                        template_name="timeline_milestone",
                        out_png=card_img_path,
                        params={
                            "title": c_headline,
                            **c_params
                        },
                        variant=c_variant,
                    )
                    if card_res and card_res.exists():
                        card_visual_type = "timeline_milestone"
                        safe_log(f"[SceneEngine] ⏳ Línea de Tiempo Documental generada para escena {scene.scene_id}: {c_headline}")

                # 1. Mapa Geopolítico / Satelital Táctico GeoIntel (si aplica específicamente)
                elif c_template in ("map", "geointel_map") or any(k in c_badge for k in ("MAPA", "GEO", "GEOPOLÍTICA", "UBICACIÓN", "UBICACION")) or "mapa" in c_headline.lower():
                    map_result = self.web_renderer.render_geointel_map_to_image(
                        location_title=c_headline,
                        country_name=c_stat or "ZONA DE INVESTIGACIÓN",
                        out_png=card_img_path,
                        coordinates_str="COORDENADAS SATELITALES",
                        notes=c_body,
                        badge=c_badge or "RECONOCIMIENTO GEOGRÁFICO",
                    )
                    if map_result:
                        card_visual_type = "map"
                        safe_log(f"[SceneEngine] 🗺️ Mapa Geopolítico GeoIntel generado para escena {scene.scene_id}")
                    else:
                        self.web_renderer.render_to_image(
                            headline=c_headline,
                            out_png=card_img_path,
                            stat_value=c_stat or "DATO CLAVE",
                            stat_label="Cifra Verificada",
                            body=c_body,
                            badge=c_badge or "DATO VERIFICADO",
                            source="Registro Oficial 2026",
                            style="auto",
                            image_path=broll_img,
                        )
                        card_visual_type = "bento"
                        safe_log(f"[SceneEngine] 📊 Tarjeta Bento estándar generada para escena {scene.scene_id}")

                # 2. Bento estándar (Fallback final)
                else:
                    self.web_renderer.render_to_image(
                        headline=c_headline,
                        out_png=card_img_path,
                        stat_value=c_stat or "",
                        stat_label="Cifra Verificada" if c_stat else "",
                        body=c_body,
                        badge=c_badge or "INFO",
                        source="Registro Oficial 2026",
                        style="auto",
                        image_path=broll_img,
                    )
                    card_visual_type = "bento"
                    safe_log(f"[SceneEngine] 🎨 Tarjeta Bento moderna WebCardRenderer generada para escena {scene.scene_id}")
            except Exception as _we:
                safe_log(f"[SceneEngine] Fallback a WebCardRenderer simplificado: {_we}")
                try:
                    self.web_renderer.render_to_image(
                        headline=c_headline,
                        out_png=card_img_path,
                        stat_value=c_stat or "",
                        stat_label="",
                        body=c_body,
                        badge=c_badge or "INFO",
                        source="Registro Oficial 2026",
                        style="auto",
                        image_path=None,
                    )
                except Exception as _fe:
                    safe_log(f"[SceneEngine] Fallback final a CardRenderer: {_fe}")
                    card_obj = InfoCard(
                        card_id=f"sc_card_{scene.scene_id}",
                        headline=c_headline,
                        claim=c_body or c_headline,
                        search_query=c_headline,
                        body=c_body,
                        start_sec=0.8,
                        end_sec=max(3.0, duration - 0.5),
                        stat_value=c_stat,
                        verdict="supported",
                        kind="cifra" if c_stat else "dato",
                    )
                    self.card_renderer.render(card_obj, card_img_path)

        # 3b. Preparar chips / pastillas referenciales dinámicas sincronizadas con el momento en que se mencionan
        chips_img_path = None
        chip_start_time = 0.8
        if getattr(scene, "chips", None) and scene.chips:
            out_chip_path = scene_dir / f"chips_{scene.scene_id}.png"
            chips_img_path = self._render_chips_overlay(scene.chips, out_chip_path)
            if sentence_boundaries:
                chip_keywords = [str(c).lower() for c in scene.chips]
                for s_st, _s_en, s_txt in sentence_boundaries:
                    low_txt = s_txt.lower()
                    if any(kw in low_txt for kw in chip_keywords):
                        chip_start_time = max(0.5, round(s_st, 2))
                        break

        # 3c. Preparar Pop-up reactivo sincronizado si la escena tiene popups definidos
        popup_img_path = None
        popup_start_time = 1.2
        popups_list = getattr(scene, "popups", []) or []
        if popups_list and not card_img_path:
            p_data = popups_list[0] if isinstance(popups_list[0], dict) else {"text": str(popups_list[0])}
            p_txt = p_data.get("text", "").strip()
            p_kind = p_data.get("kind", "fact")
            p_trig = (p_data.get("trigger") or "").lower().strip()
            if p_txt:
                out_pop_path = scene_dir / f"popup_{scene.scene_id}.png"
                try:
                    popup_img_path = self.web_renderer.render_popup_to_image(
                        text=p_txt,
                        out_png=out_pop_path,
                        tag_label="CLAVE" if p_kind == "fact" else p_kind.upper(),
                        kind=p_kind,
                    )
                    safe_log(f"[SceneEngine] 💡 Micro Pop-up WebCardRenderer generado para escena {scene.scene_id}")
                except Exception as _wpe:
                    safe_log(f"[SceneEngine] Fallback a InfoCardRenderer para popup: {_wpe}")
                    try:
                        popup_img_path = self.card_renderer.render_info_popup(text=p_txt, kind=p_kind, out_path=out_pop_path)
                    except Exception as _ep:
                        safe_log(f"[SceneEngine] Error renderizando popup: {_ep}")
                        popup_img_path = None

                if p_trig and sentence_boundaries:
                    for s_st, _s_en, s_txt in sentence_boundaries:
                        if p_trig in s_txt.lower():
                            popup_start_time = max(0.6, round(s_st, 2))
                            break

        # 3d. Preparar Rótulo Broadcast Lower Third si no hay tarjeta Bento ni popup para contexto visual
        lower_third_img_path = None
        if not card_img_path and not popup_img_path and scene.type in ("video_reaction", "breaking_news", "avatar_cam") and duration >= 4.0:
            lt_tag = "NOTICIA EN VIVO" if scene.type == "breaking_news" else ("REACCIÓN EN VIVO" if scene.type == "video_reaction" else "EN VIVO")
            lt_sub = (scene.speech[:75].rsplit(" ", 1)[0] + "…") if len(scene.speech) > 75 else scene.speech
            out_lt_path = scene_dir / f"lower_third_{scene.scene_id}.png"
            try:
                lower_third_img_path = self.web_renderer.render_lower_third_to_image(
                    title=scene.name,
                    subtitle=lt_sub,
                    out_png=out_lt_path,
                    tag=lt_tag,
                )
                safe_log(f"[SceneEngine] 📺 Rótulo Broadcast WebCardRenderer generado para escena {scene.scene_id}")
            except Exception as _wlt:
                safe_log(f"[SceneEngine] Fallback a Pillow para lower third: {_wlt}")
                try:
                    lower_third_img_path = self.card_renderer.render_broadcast_lower_third(
                        headline=scene.name,
                        subtitle=lt_sub,
                        tag=lt_tag,
                        out_path=out_lt_path,
                    )
                except Exception as exc_lt:
                    safe_log(f"[SceneEngine] Fallback lower third: {exc_lt}")
                    lower_third_img_path = None

        # 3e. Preparar Texto Libre Cinemático Flotante (sin card) si la escena es un Top, ranking o enumeración
        free_title_img_path = None
        free_title_blur_bg = False
        kinetic_word_paths = []
        free_data = getattr(scene, "free_title", None)
        # Exclusión mutua Fase 2: si la escena ya cuenta con tarjeta renderizada, suprimir free_title
        if card_img_path and card_img_path.exists():
            free_data = None
        elif not free_data and not card_img_path:
            name_low = scene.name.lower()
            m_top = re.search(r"(?:puesto|número|numero|top|#|factor|punto|clave)\s*(\d+)", name_low)
            if m_top:
                num_val = int(m_top.group(1))
                num_str = f"{num_val:02d}"
                clean_title = re.sub(r"(?i)^(?:puesto|número|numero|top|#|factor|punto|clave)\s*\d+[\s:.-]*", "", scene.name).strip()
                free_data = {
                    "number": num_str if num_val < 100 else str(num_val),
                    "title": clean_title or scene.name,
                    "tag": f"PUESTO {num_str} · RANKING" if ("top" in name_low or "puesto" in name_low) else f"HITO #{num_str}",
                    "subtitle": (scene.speech[:65].rsplit(" ", 1)[0] + "…") if len(scene.speech) > 65 else scene.speech,
                    "blur_bg": True,
                }

        kinetic_layered = False
        if free_data:
            out_free_path = scene_dir / f"free_title_{scene.scene_id}.png"
            kinetic_word_paths = []
            kinetic_layered = False
            try:
                free_title_img_path = self.web_renderer.render_free_kinetic_text_to_image(
                    main_title=free_data.get("title") or scene.name,
                    out_png=out_free_path,
                    number=free_data.get("number", ""),
                    tag=free_data.get("tag", ""),
                    subtitle=free_data.get("subtitle", ""),
                    highlight=free_data.get("highlight", ""),
                    accent_color=free_data.get("accent_color", "#38bdf8"),
                )
                free_title_blur_bg = bool(free_data.get("blur_bg", True))
                safe_log(f"[SceneEngine] 🎬 Texto Libre Cinemático Flotante generado para escena {scene.scene_id}")
            except Exception as _fe:
                safe_log(f"[SceneEngine] Error generando texto libre cinemático: {_fe}")
                free_title_img_path = None

            # Tipografía cinética VIRAL: cada palabra como PNG bicolor gigante que
            # estalla en pantalla una a una (pop + rise) al ritmo de la locución.
            # Solo si Chromium funciona y el título tiene 1-4 palabras; el PNG
            # completo queda como fallback si la serie falla.
            if free_title_img_path is not None or free_data.get("title"):
                try:
                    from core.web_card_renderer import KINETIC_DUOTONES
                    duo = KINETIC_DUOTONES[int(scene.scene_id) % len(KINETIC_DUOTONES)]
                    from core.kinetic_titles import TITLE_STYLES
                    _tstyle = free_data.get("style")
                    if _tstyle not in TITLE_STYLES:
                        _tstyle = TITLE_STYLES[int(scene.scene_id) % len(TITLE_STYLES)]
                    _eyebrow = " · ".join([x for x in (str(free_data.get("number", "") or ""), str(free_data.get("tag", "") or "")) if x])
                    try:
                        kinetic_word_paths = self.title_renderer.render_title_layers(
                            title=free_data.get("title") or scene.name,
                            out_dir=scene_dir / f"kt_{scene.scene_id}",
                            style=_tstyle,
                            duo=duo,
                            eyebrow=_eyebrow,
                            canvas=(self.W, self.H),
                            max_words=4,
                        )
                        kinetic_layered = bool(kinetic_word_paths)
                    except Exception:
                        kinetic_word_paths = []
                    if not kinetic_word_paths:
                        kinetic_word_paths = self.web_renderer.render_kinetic_word_series(
                            title=free_data.get("title") or scene.name,
                            out_dir=scene_dir / f"kinetic_{scene.scene_id}",
                            duo=duo,
                            max_words=4,
                        )
                    if kinetic_word_paths:
                        safe_log(f"[SceneEngine] ⚡ {len(kinetic_word_paths)} palabras cinéticas bicolor listas (escena {scene.scene_id})")
                except Exception as _ke:
                    kinetic_word_paths = []

        # 4. Generar subtítulos para la escena
                # 3f. Rotulos flotantes cinematicos de palabras clave y anos (enfasis sin cards)
        keyword_callout_overlays: List[Dict[str, Any]] = []
        try:
            from core.kinetic_titles import KEYWORD_DUOTONES
            kw_duo = KEYWORD_DUOTONES[int(scene.scene_id) % len(KEYWORD_DUOTONES)]

            found_years = self.title_renderer.find_years(speech_text)
            found_kws = self.title_renderer.find_keywords(
                speech=speech_text,
                scene_name=scene.name,
                card_headline=getattr(scene.card, "headline", "") or ""
            )

            candidates = []
            for y_val, y_frac in found_years[:1]:
                candidates.append({"type": "year", "text": y_val, "frac": y_frac, "tag": "ANO HISTORICO"})
            for kw_item in found_kws[:2]:
                candidates.append({
                    "type": "keyword",
                    "text": kw_item["text"],
                    "frac": kw_item["frac"],
                    "tag": kw_item["tag"],
                    "style": kw_item.get("style", "badge_glow")
                })

            candidates.sort(key=lambda c: c["frac"])
            candidates = candidates[:2]

            for idx_c, cand in enumerate(candidates):
                kw_png = scene_dir / f"kw_{scene.scene_id}_{idx_c}.png"
                rendered_path = None
                if cand["type"] == "year":
                    res_y = self.title_renderer.render_year_callout(cand["text"], kw_png, style_idx=int(scene.scene_id) + idx_c)
                    if res_y:
                        rendered_path = res_y[0]
                else:
                    rendered_path = self.title_renderer.render_keyword_callout(
                        text=cand["text"],
                        out_png=kw_png,
                        style=cand.get("style", "badge_glow"),
                        tag=cand.get("tag", "CLAVE"),
                        duo=kw_duo,
                    )
                if rendered_path and rendered_path.exists():
                    keyword_callout_overlays.append({
                        "path": rendered_path,
                        "frac": cand["frac"],
                        "text": cand["text"],
                    })
        except Exception as _kwe:
            safe_log(f"[SceneEngine] Fallback en palabras clave flotantes: {_kwe}")

        # Remotion AI: Si no se renderizó antes, evaluar si la escena se beneficia de uno
        if not ai_remotion_mov:
            has_primary_foreground = bool(
                (card_img_path and card_img_path.exists())
                or (free_title_img_path and free_title_img_path.exists())
            )
            if getattr(self, "ai_remotion", None) and duration >= 3.0 and not has_primary_foreground:
                try:
                    ai_remotion_mov = await self.ai_remotion.render_ai_overlay(
                        scene_name=scene.name,
                        speech_text=speech_text,
                        duration=duration,
                        out_dir=scene_dir,
                        vertical=self.is_vertical,
                        theme_spec=getattr(self, "style_spec", None),
                        card=scene.card,
                        intent=visual_intent,
                    )
                except Exception as _re_err:
                    safe_log(f"[SceneEngine] Remotion AI overlay omitido: {_re_err}")

        srt_path = self._generate_scene_subtitles(speech_text, duration, scene_dir, sentence_boundaries)

        # 5. Montar filtergraph de FFmpeg específico para el layout de la escena
        inputs: List[str] = []
        filter_parts: List[str] = []
        num_in = 0

        # Montaje secuencial dinámico de todos los clips de fondo (bg_clips)
        if bg_clips:
            if len(bg_clips) == 1:
                first_bg_path, _ = bg_clips[0]
                first_is_image = first_bg_path.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
                if first_is_image:
                    inputs.extend(["-loop", "1", "-t", dur_str, "-r", "25", "-i", str(first_bg_path)])
                    kb_frames = max(1, int(float(dur_str) * 25))
                    filter_parts.append(
                        f"[0:v]scale={int(self.W * 1.12)}:{int(self.H * 1.12)}:force_original_aspect_ratio=increase,"
                        f"crop={int(self.W * 1.12)}:{int(self.H * 1.12)},"
                        f"zoompan=z='min(zoom+0.0003,1.08)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)-{self.H//10}*on/{kb_frames}':d={kb_frames}:s={self.W}x{self.H}:fps=25,"
                        f"setsar=1[v_bg0]"
                    )
                else:
                    inputs.extend(["-t", dur_str, "-r", "25", "-stream_loop", "-1", "-i", str(first_bg_path)])
                    filter_parts.append(
                        f"[0:v]scale={self.W}:{self.H}:force_original_aspect_ratio=increase,crop={self.W}:{self.H},setsar=1,"
                        f"tpad=stop_mode=clone:stop_duration={dur_str},trim=duration={dur_str},setpts=PTS-STARTPTS[v_bg0]"
                    )
                cur_v = "v_bg0"
                num_in += 1
            else:
                # Múltiples B-Rolls: Concat lineal sin frame buffering ni desincronización
                seg_cuts = [max(0.0, cut) for _, cut in bg_clips]
                seg_cuts[0] = 0.0
                seg_tags = []
                for i, (clip_p, _) in enumerate(bg_clips):
                    t_start = seg_cuts[i]
                    t_end = seg_cuts[i + 1] if (i + 1 < len(bg_clips)) else duration
                    seg_dur = max(0.5, round(t_end - t_start, 2))
                    seg_dur_str = f"{seg_dur:.2f}"
                    is_img = clip_p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
                    clip_in_idx = num_in
                    num_in += 1
                    seg_tag = f"v_seg_{i}"
                    seg_tags.append(f"[{seg_tag}]")

                    if is_img:
                        inputs.extend(["-loop", "1", "-t", seg_dur_str, "-r", "25", "-i", str(clip_p)])
                        kb_frames_sub = max(1, int(seg_dur * 25))
                        filter_parts.append(
                            f"[{clip_in_idx}:v]scale={int(self.W * 1.12)}:{int(self.H * 1.12)}:force_original_aspect_ratio=increase,"
                            f"crop={int(self.W * 1.12)}:{int(self.H * 1.12)},"
                            f"zoompan=z='min(zoom+0.0003,1.08)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={kb_frames_sub}:s={self.W}x{self.H}:fps=25,"
                            f"setsar=1,trim=duration={seg_dur_str},setpts=PTS-STARTPTS[{seg_tag}]"
                        )
                    else:
                        inputs.extend(["-t", seg_dur_str, "-r", "25", "-stream_loop", "-1", "-i", str(clip_p)])
                        filter_parts.append(
                            f"[{clip_in_idx}:v]scale={self.W}:{self.H}:force_original_aspect_ratio=increase,crop={self.W}:{self.H},setsar=1,"
                            f"tpad=stop_mode=clone:stop_duration={seg_dur_str},trim=duration={seg_dur_str},setpts=PTS-STARTPTS[{seg_tag}]"
                        )
                all_segs = "".join(seg_tags)
                filter_parts.append(f"{all_segs}concat=n={len(bg_clips)}:v=1:a=0[v_bg_seq]")
                cur_v = "v_bg_seq"
        else:
            inputs.extend(["-f", "lavfi", "-i", f"color=c=0x0a0a0c:s={self.W}x{self.H}:d={dur_str}:r=25"])
            filter_parts.append("[0:v]format=yuva420p[v_bg0]")
            cur_v = "v_bg0"
            num_in += 1

        # Superposicion sutil de microelementos cineticos de fondo (particulas y acentos HUD)
        if motion_overlay_path and motion_overlay_path.exists():
            inputs.extend(["-loop", "1", "-t", dur_str, "-r", "25", "-i", str(motion_overlay_path)])
            m_idx = num_in
            num_in += 1
            filter_parts.append(
                f"[{m_idx}:v]format=rgba,fade=t=in:st=0.3:d=0.35:alpha=1,fade=t=out:st={duration-0.35:.2f}:d=0.35:alpha=1[motion_in];"
                f"[{cur_v}][motion_in]overlay=x='8*sin(t*0.9)':y='6*cos(t*0.7)':enable='between(t,0.3,{duration-0.2:.2f})'[v_bg_motion]"
            )
            cur_v = "v_bg_motion"

        # Desenfoque temporal dinámico: si hay tarjeta o texto libre cinemático, desenfocar durante su aparición
        # Duración de la tarjeta por TIEMPO DE LECTURA (regla broadcast: ~1/3 s por
        # palabra + 1.2s de animación/buffer, acotado 4-6.5s). Antes usaba hasta 9.5s
        # fijos: la card se volvía un adorno permanente tapando el video.
        if card_img_path and card_img_path.exists():
            c_hl = scene.card.get("headline") if isinstance(scene.card, dict) else getattr(scene.card, "headline", "")
            c_bd = scene.card.get("body") if isinstance(scene.card, dict) else getattr(scene.card, "body", "")
            card_words = len(f"{c_hl or ''} {c_bd or ''}".split())
            # Tarjeta: acotada estrictamente por temporización inteligente (y sale antes del corte de escena)
            card_duration = max(2.2, min(smart_card_dur or 4.0, min(max(2.0, duration - card_start_time - 0.5), 0.20 * card_words + 1.8)))
        else:
            card_duration = 0.0
        # Duración del texto libre: con serie cinética la ventana cubre el
        # estallido escalonado de las palabras (0.32s por palabra) + 1.6s de
        # lectura final. Sin serie, el comportamiento clásico.
        if free_title_blur_bg and (free_title_img_path or kinetic_word_paths):
            if kinetic_word_paths:
                free_title_dur = max(2.4, min(4.6, 0.32 * len(kinetic_word_paths) + 1.6))
            else:
                free_title_dur = min(3.5, max(2.2, duration - 0.8))
        else:
            free_title_dur = 0.0

        if card_duration > 0:
            if card_visual_type in ("verdict_badge", "tech_card"):
                # Badges y tech cards flotan limpiamente sobre el video nítido sin desenfoque pesado
                filter_parts.append(f"[{cur_v}]drawbox=x=0:y=0:w={self.W}:h={self.H}:color=black@0.15:t=fill[v_dim]")
            else:
                # Bento Box / Cita / Mapa / Stat Counter: Dimming nítido y elegante sin boxblur CPU-bloat
                filter_parts.append(
                    f"[{cur_v}]drawbox=x=0:y=0:w={self.W}:h={self.H}:color=black@0.40:t=fill:enable='between(t,{card_start_time:.2f},{card_start_time + card_duration:.2f})'[v_dim]"
                )
        elif free_title_dur > 0:
            # Atenuación cinematográfica durante la aparición del gran texto libre
            filter_parts.append(f"[{cur_v}]drawbox=x=0:y=0:w={self.W}:h={self.H}:color=black@0.45:t=fill:enable='between(t,0.4,{0.4 + free_title_dur:.2f})'[v_dim]")
        else:
            filter_parts.append(f"[{cur_v}]drawbox=x=0:y=0:w={self.W}:h={self.H}:color=black@0.15:t=fill[v_dim]")
        cur_v = "v_dim"

        # Avatar según layout de cámara
        av_file = scene_avatar_clip if (scene_avatar_clip and scene_avatar_clip.exists()) else (avatar_clip or avatar_webm)
        if av_file and Path(av_file).exists():
            # SIN '-r' de entrada: el clip de avatar nace a 24 fps y su envolvente de
            # lip-sync está construida a 24 fps. Re-tiempearlo a 25 (-r 25) adelantaba
            # la boca ~4% y hacía que el loop reiniciara en el 96% de cada escena.
            # A fps nativos, el clip dura exactamente lo que duró el audio y el loop
            # reinicia justo al terminar la escena.
            inputs.extend(["-t", dur_str, "-stream_loop", "-1", "-i", str(av_file)])
            av_idx = num_in
            num_in += 1

            # REGLA AUDIOVISUAL (FASES 4 Y 5): ROL DEL AVATAR Y APERTURA DINÁMICA
            # El avatar actúa como presentador/narrador visual secundario.
            # En la apertura (escena 1), el video comienza mostrando INFORMACIÓN VISUAL RELEVANTE desde t=0.
            # El avatar NUNCA monopoliza el centro de la pantalla al inicio; entra suave en PIP a los ~2.2s
            # o se mantiene en esquina PIP para no tapar el gancho documental ni la tipografía cinética.
            is_opening = (int(getattr(scene, "scene_id", 1)) == 1)
            cam = str(getattr(scene, "camera", "pip_corner") or "pip_corner").lower().strip()
            sc_type = str(getattr(scene, "type", "video_reaction") or "video_reaction").lower().strip()

            av_w_pip = int(self.W * (0.24 if not self.is_vertical else 0.36))
            av_x_pip = int(self.W - av_w_pip - (40 if not self.is_vertical else 26))
            av_y_pip = int(self.H - av_w_pip - (40 if not self.is_vertical else 96))

            if cam in ("voice_over", "none", "hidden") or sc_type == "voice_over":
                # Escena puramente visual o voz en off: el avatar no se superpone
                safe_log(f"[SceneEngine] 🎙️ Escena {scene.scene_id}: Modo voz en off, pantalla completa para contenido visual.")

            elif is_opening or cam == "pip_delayed":
                # APERTURA DINÁMICA: Los primeros 2.0s a 2.5s están dedicados 100% al impacto visual
                # (video documental de fondo, kinetic typography o tarjeta). El avatar entra suavemente
                # en recuadro PIP en la esquina inferior derecha para apoyar la narración.
                delay_t = min(2.5, max(1.8, round(duration * 0.22, 2))) if duration >= 5.0 else 1.2
                filter_parts.append(
                    f"[{av_idx}:v]scale={av_w_pip}:{av_w_pip},format=rgba,"
                    f"fade=t=in:st={delay_t:.2f}:d=0.35:alpha=1[av_pip_delayed];"
                    f"[{cur_v}][av_pip_delayed]overlay={av_x_pip}:{av_y_pip}:enable='gte(t,{delay_t:.2f})':eof_action=pass[v_av]"
                )
                cur_v = "v_av"
                safe_log(f"[SceneEngine] 🎬 Apertura dinámica activa en escena {scene.scene_id}: Avatar entra en PIP a los {delay_t:.1f}s.")

            elif cam == "hero_center" and not is_opening and not (card_img_path and card_img_path.exists()):
                # Solo permitido en escenas intermedias/finales sin tarjeta que bloquee el centro
                av_w_hero = int(self.W * (0.50 if not self.is_vertical else 0.65))
                av_x_hero = int((self.W - av_w_hero) / 2)
                av_y_hero = int(self.H - av_w_hero + 30)
                filter_parts.append(
                    f"[{av_idx}:v]scale={av_w_hero}:{av_w_hero},format=rgba[avatar];"
                    f"[{cur_v}][avatar]overlay={av_x_hero}:{av_y_hero}:eof_action=pass[v_av]"
                )
                cur_v = "v_av"

            else:
                # Comportamiento estándar ergonómico: Presentador en recuadro PIP en la esquina inferior derecha
                filter_parts.append(
                    f"[{av_idx}:v]scale={av_w_pip}:{av_w_pip},format=rgba[avatar];"
                    f"[{cur_v}][avatar]overlay={av_x_pip}:{av_y_pip}:eof_action=pass[v_av]"
                )
                cur_v = "v_av"

        # Overlay adicional según tipo de escena: Texto Libre Cinemático o Tarjeta Bento
        if kinetic_word_paths and not (ai_remotion_mov and ai_remotion_mov.exists()):
            # ── TIPOGRAFÍA CINÉTICA VIRAL (palabra a palabra) ──
            # Cada palabra estalla en pantalla con fade + rise (ease-out cúbico)
            # escalonadas 0.32s, apiladas verticalmente como bloque central. La
            # serie completa respira junta y se funde a la vez al terminar.
            n_words = len(kinetic_word_paths)
            stagger = 0.32
            ft_start = 0.4
            ft_end = min(duration - 0.3, ft_start + (n_words - 1) * stagger + 1.7)
            for i_w, word_path in enumerate(kinetic_word_paths):
                inputs.extend(["-loop", "1", "-t", dur_str, "-r", "25", "-i", str(word_path)])
                w_idx = num_in
                num_in += 1
                st = ft_start + i_w * stagger
                # PNG a 2x: reducir al tamaño objetivo (palabra ~200px de alto en pantalla)
                _sc = "" if kinetic_layered else "scale=iw*0.5:ih*0.5,"
                filter_parts.append(
                    f"[{w_idx}:v]{_sc}format=rgba,"
                    f"fade=t=in:st={st:.2f}:d=0.20:alpha=1,"
                    f"fade=t=out:st={ft_end - 0.35:.2f}:d=0.35:alpha=1[kw{i_w}_a]"
                )
                # Pop con rise: entra subiendo 34px con easing cúbico y se apila
                # centrada como bloque (offset vertical por índice de palabra).
                pop_calc = f"min(max((t-{st:.2f})/0.30\\,0)\\,1)"
                row_off = (i_w - (n_words - 1) / 2.0)
                if kinetic_layered:
                    y_expr = f"34*(1-pow({pop_calc}\\,3))"
                    _kx = "0"
                else:
                    y_expr = f"(H-h)/2 + {row_off:.2f}*(h+14) + 34*(1-pow({pop_calc}\\,3))"
                    _kx = "(W-w)/2"
                filter_parts.append(
                    f"[{cur_v}][kw{i_w}_a]overlay=x='{_kx}':y='{y_expr}':"
                    f"enable='between(t,{st:.2f},{ft_end:.2f})'[v_kw{i_w}]"
                )
                cur_v = f"v_kw{i_w}"

        elif free_title_img_path and free_title_img_path.exists():
            inputs.extend(["-loop", "1", "-t", dur_str, "-r", "25", "-i", str(free_title_img_path)])
            ft_idx = num_in
            num_in += 1
            ft_end = 0.4 + free_title_dur
            ft_fo = max(0.4, ft_end - 0.35)
            # Entrada con fade in 0.25s + fade out suave 0.35s
            filter_parts.append(
                f"[{ft_idx}:v]format=rgba,fade=t=in:st=0.4:d=0.25:alpha=1,fade=t=out:st={ft_fo:.2f}:d=0.35:alpha=1[ft_animated]"
            )
            # Entrada con movimiento cinemático flotante (rise suave de 24px hacia el centro)
            ft_calc = f"min(max((t-0.4)/0.35\\,0)\\,1)"
            ft_y_expr = f"(H-h)/2 + 24*(1-pow({ft_calc}\\,3))"
            filter_parts.append(
                f"[{cur_v}][ft_animated]overlay=x='(W-w)/2':y='{ft_y_expr}':enable='between(t,0.4,{ft_end:.2f})'[v_ft]"
            )
            cur_v = "v_ft"

        elif card_img_path and card_img_path.exists():
            inputs.extend(["-loop", "1", "-t", dur_str, "-r", "25", "-i", str(card_img_path)])
            c_idx = num_in
            num_in += 1
            card_end = card_start_time + card_duration
            fo_start = max(card_start_time, card_end - 0.35)

            if card_visual_type == "verdict_badge":
                # Distintivo viral inclinado: Spring Bounce elástico (overshoot) + respiración flotante viva
                # Escala 0.65 -> 1.03 -> 1.00 en 0.28s
                bounce_calc = f"min(max((t-{card_start_time:.2f})/0.28\\,0)\\,1)"
                scale_expr = f"iw*min(1.0\\, 0.65 + 0.38*sin({bounce_calc}*1.9))"
                filter_parts.append(
                    f"[{c_idx}:v]scale=eval=frame:w='{scale_expr}':h=-2,format=rgba,"
                    f"fade=t=in:st={card_start_time:.2f}:d=0.18:alpha=1,fade=t=out:st={fo_start:.2f}:d=0.35:alpha=1[card_animated]"
                )
                ease_y = f"((H-h)/2) - 40 + 5*sin(t*2.8)"
                filter_parts.append(f"[{cur_v}][card_animated]overlay=x='(W-w)/2':y='{ease_y}':enable='between(t,{card_start_time:.2f},{card_end:.2f})'[v_card]")
                cur_v = "v_card"

            elif card_visual_type == "tech_card":
                # Tarjeta técnica moderna: Flotando en el tercio superior con deslizamiento suave y oscilación sutil
                top_y = int(self.H * 0.16) if self.is_vertical else int(self.H * 0.12)
                slide_dist = 28
                slide_calc = f"min(max((t-{card_start_time:.2f})/0.32\\,0)\\,1)"
                ease_y = f"{top_y} - {slide_dist}*(1-pow({slide_calc}\\,3)) + 4*sin(t*2.4)"
                filter_parts.append(
                    f"[{c_idx}:v]format=rgba,fade=t=in:st={card_start_time:.2f}:d=0.25:alpha=1,fade=t=out:st={fo_start:.2f}:d=0.35:alpha=1[card_animated]"
                )
                filter_parts.append(f"[{cur_v}][card_animated]overlay=x='(W-w)/2':y='{ease_y}':enable='between(t,{card_start_time:.2f},{card_end:.2f})'[v_card]")
                cur_v = "v_card"

            elif card_visual_type in ("step_badge", "source_chip"):
                # Insignia de paso o fuente: Entrada lateral flotante con rebote sutil desde la izquierda
                slide_dist = 40
                slide_calc = f"min(max((t-{card_start_time:.2f})/0.30\\,0)\\,1)"
                ease_x = f"50 - {slide_dist}*(1-pow({slide_calc}\\,3))"
                chip_y = int(self.H * 0.68) if self.is_vertical else int(self.H * 0.72)
                filter_parts.append(
                    f"[{c_idx}:v]format=rgba,fade=t=in:st={card_start_time:.2f}:d=0.20:alpha=1,fade=t=out:st={fo_start:.2f}:d=0.30:alpha=1[card_animated]"
                )
                filter_parts.append(f"[{cur_v}][card_animated]overlay=x='{ease_x}':y='{chip_y}':enable='between(t,{card_start_time:.2f},{card_end:.2f})'[v_card]")
                cur_v = "v_card"

            elif card_visual_type == "alert_banner":
                # Alerta táctica HUD: Caída rápida e impacto de advertencia en el tercio superior
                alert_y = int(self.H * 0.18) if self.is_vertical else int(self.H * 0.14)
                slide_dist = 35
                slide_calc = f"min(max((t-{card_start_time:.2f})/0.26\\,0)\\,1)"
                ease_y = f"{alert_y} - {slide_dist}*(1-pow({slide_calc}\\,3))"
                filter_parts.append(
                    f"[{c_idx}:v]format=rgba,fade=t=in:st={card_start_time:.2f}:d=0.15:alpha=1,fade=t=out:st={fo_start:.2f}:d=0.30:alpha=1[card_animated]"
                )
                filter_parts.append(f"[{cur_v}][card_animated]overlay=x='(W-w)/2':y='{ease_y}':enable='between(t,{card_start_time:.2f},{card_end:.2f})'[v_card]")
                cur_v = "v_card"

            elif card_visual_type == "stat_counter":
                # Métrica gigante: Escala suave y elevación centrada con micro-flotación
                slide_dist = 22
                slide_calc = f"min(max((t-{card_start_time:.2f})/0.32\\,0)\\,1)"
                ease_y = f"((H-h)/2) + {slide_dist}*(1-pow({slide_calc}\\,3)) + 3*sin(t*2.2)"
                filter_parts.append(
                    f"[{c_idx}:v]format=rgba,fade=t=in:st={card_start_time:.2f}:d=0.25:alpha=1,fade=t=out:st={fo_start:.2f}:d=0.35:alpha=1[card_animated]"
                )
                filter_parts.append(f"[{cur_v}][card_animated]overlay=x='(W-w)/2':y='{ease_y}':enable='between(t,{card_start_time:.2f},{card_end:.2f})'[v_card]")
                cur_v = "v_card"

            else:
                # Bento Box / Versus Split / Quote / Mapa estándar
                slide_dist = 26
                slide_calc = f"min(max((t-{card_start_time:.2f})/0.35\\,0)\\,1)"
                card_base_x = "((W-w)/2)"
                ease_y = f"((H-h)/2)+{slide_dist}*(1-pow({slide_calc}\\,3)) + 3*sin(t*2.0)"
                filter_parts.append(
                    f"[{c_idx}:v]format=rgba,fade=t=in:st={card_start_time:.2f}:d=0.35:alpha=1,fade=t=out:st={fo_start:.2f}:d=0.35:alpha=1[card_animated]"
                )
                filter_parts.append(f"[{cur_v}][card_animated]overlay=x='{card_base_x}':y='{ease_y}':enable='between(t,{card_start_time:.2f},{card_end:.2f})'[v_card]")
                cur_v = "v_card"


        elif popup_img_path and popup_img_path.exists():
            # Pop-up informativo HUD animado con entrada suave y salida centrada
            inputs.extend(["-loop", "1", "-t", dur_str, "-r", "25", "-i", str(popup_img_path)])
            pop_idx = num_in
            num_in += 1
            pop_start = popup_start_time
            pop_dur = min(4.5, duration - pop_start - 0.4)
            pop_end = pop_start + max(2.5, pop_dur)
            pop_fo = max(pop_start + 0.3, pop_end - 0.35)
            filter_parts.append(
                f"[{pop_idx}:v]format=rgba,fade=t=in:st={pop_start:.2f}:d=0.30:alpha=1,fade=t=out:st={pop_fo:.2f}:d=0.35:alpha=1[pop_animated]"
            )
            pop_base_x = "((W-w)/2)" if not self.is_vertical else "30"
            pop_y = 150 if not self.is_vertical else int(self.H * 0.36)
            slide_dist = 22
            slide_calc = f"min(max((t-{pop_start:.2f})/0.35\\,0)\\,1)"
            ease_x = f"{pop_base_x}-{slide_dist}*(1-pow({slide_calc}\\,3))"
            filter_parts.append(f"[{cur_v}][pop_animated]overlay=x='{ease_x}':y={pop_y}:enable='between(t,{pop_start:.2f},{pop_end:.2f})'[v_pop]")
            cur_v = "v_pop"

        elif lower_third_img_path and lower_third_img_path.exists():
            # Rótulo Broadcast Lower Third con entrada en el segundo 0.8 hasta el 4.8
            inputs.extend(["-loop", "1", "-t", dur_str, "-r", "25", "-i", str(lower_third_img_path)])
            lt_idx = num_in
            num_in += 1
            lt_start = 0.8
            lt_end = min(duration - 0.4, 4.8)
            lt_fo = max(lt_start, lt_end - 0.4)
            filter_parts.append(
                f"[{lt_idx}:v]format=rgba,fade=t=in:st={lt_start}:d=0.35:alpha=1,fade=t=out:st={lt_fo:.2f}:d=0.35:alpha=1[lt_animated]"
            )
            lt_x = "((W-w)/2)" if not self.is_vertical else 30
            lt_y = int(self.H - 180) if not self.is_vertical else int(self.H * 0.70)
            slide_dist = 26
            slide_calc = f"min(max((t-{lt_start})/0.4\\,0)\\,1)"
            ease_y = f"{lt_y}+{slide_dist}*(1-pow({slide_calc}\\,3))"
            filter_parts.append(f"[{cur_v}][lt_animated]overlay=x='{lt_x}':y='{ease_y}':enable='between(t,{lt_start},{lt_end:.2f})'[v_lt]")
            cur_v = "v_lt"

        elif scene.type == "chat_debate" and chat_overlay_path and chat_overlay_path.exists():
            inputs.extend(["-loop", "1", "-t", dur_str, "-r", "25", "-i", str(chat_overlay_path)])
            ch_idx = num_in
            num_in += 1
            cx = 60 if not self.is_vertical else 30
            cy = int(self.H - 330) if not self.is_vertical else int(self.H * 0.72)
            filter_parts.append(f"[{cur_v}][{ch_idx}:v]overlay={cx}:{cy}:enable='between(t,0.5,{duration-0.3:.2f})'[v_chat]")
            cur_v = "v_chat"

        # ── AÑOS FLOTANTES: cuando la locución menciona un año, aparece suelto
        # (sin tarjeta) con estilo tipográfico rotativo. Nunca rompe la escena.
        try:
            if card_duration <= 0:
                _yrs = self.title_renderer.find_years(speech_text or "")[:2]
                _busy_until = (0.4 + free_title_dur + 0.3) if free_title_dur > 0 else 0.0
                _last_end = 0.0
                for _yi, (_year, _frac) in enumerate(_yrs):
                    _t = _frac * duration
                    for (_s0, _s1, _stext) in (sentence_boundaries or []):
                        if _year in (_stext or ""):
                            _pos = (_stext.find(_year) / max(1, len(_stext)))
                            _t = float(_s0) + _pos * (float(_s1) - float(_s0))
                            break
                    _t = max(_t, _busy_until, _last_end + 0.2, 0.6)
                    _yd = 2.6
                    if _t + _yd > duration - 0.2:
                        _t = duration - 0.2 - _yd
                    if _t < _busy_until or _t < _last_end:
                        continue
                    _ypng = scene_dir / f"year_{scene.scene_id}_{_yi}.png"
                    _res = self.title_renderer.render_year_callout(_year, _ypng, style_idx=int(scene.scene_id) + _yi)
                    if not _res:
                        continue
                    _ypath = _res[0]
                    inputs.extend(["-loop", "1", "-t", dur_str, "-r", "25", "-i", str(_ypath)])
                    _y_idx = num_in
                    num_in += 1
                    _t_end = _t + _yd
                    _maxw = int(self.W * (0.30 if not self.is_vertical else 0.55))
                    filter_parts.append(
                        f"[{_y_idx}:v]scale=w=min(iw\\,{_maxw}):h=-2,format=rgba,"
                        f"fade=t=in:st={_t:.2f}:d=0.35:alpha=1,"
                        f"fade=t=out:st={_t_end - 0.4:.2f}:d=0.4:alpha=1[yr{_yi}_a]"
                    )
                    _ycalc = f"min(max((t-{_t:.2f})/0.5\\,0)\\,1)"
                    _yx = int(self.W * 0.06) if not self.is_vertical else int(self.W * 0.06)
                    _yy = f"(H-h)/2 + 30*(1-pow({_ycalc}\\,3))" if not self.is_vertical else f"{int(self.H * 0.14)} + 30*(1-pow({_ycalc}\\,3))"
                    filter_parts.append(
                        f"[{cur_v}][yr{_yi}_a]overlay=x={_yx}:y='{_yy}':"
                        f"enable='between(t,{_t:.2f},{_t_end:.2f})'[v_yr{_yi}]"
                    )
                    cur_v = f"v_yr{_yi}"
                    _last_end = _t_end
        except Exception as _ye:
            safe_log(f"[SceneEngine] Año flotante omitido: {_ye}")

        # Overlay de chips / pastillas referenciales dinámicas sincronizadas con la locución (popup de 3.5s a 4.5s)
        if chips_img_path and chips_img_path.exists():
            inputs.extend(["-loop", "1", "-t", dur_str, "-r", "25", "-i", str(chips_img_path)])
            chp_idx = num_in
            num_in += 1
            # Posición FIJA y predecible (regla broadcast): abajo-izquierda dentro
            # del área segura, sin importar el contenido. Antes flotaba al centro
            # o a 150px según la escena — el espectador nunca aprendía dónde mirar.
            # El PNG viene a 2x (device-scale-factor), se reduce al 78%: banderas
            # grandes (~70px) y texto nítido.
            chip_x = 64 if not self.is_vertical else 26
            chip_y = "main_h-overlay_h-88" if not self.is_vertical else "main_h-overlay_h-150"
            # Duración del pop-up: 3.5 segundos o hasta el final de la escena
            chip_dur = 3.5
            chip_end = min(duration - 0.25, round(chip_start_time + chip_dur, 2))
            ch_fo = max(chip_start_time + 0.3, chip_end - 0.35)
            filter_parts.append(
                f"[{chp_idx}:v]scale=iw*0.78:ih*0.78,format=rgba,fade=t=in:st={chip_start_time:.2f}:d=0.25:alpha=1,fade=t=out:st={ch_fo:.2f}:d=0.35:alpha=1[chips_animated]"
            )
            filter_parts.append(f"[{cur_v}][chips_animated]overlay=x={chip_x}:y='{chip_y}':enable='between(t,{chip_start_time:.2f},{chip_end:.2f})'[v_chips]")
            cur_v = "v_chips"

        # Overlay de Pastilla de Atribución y Proveniencia Verificada (Source / Transparency Chip)
        if provenance_chip_path and provenance_chip_path.exists():
            inputs.extend(["-loop", "1", "-t", dur_str, "-r", "25", "-i", str(provenance_chip_path)])
            prv_idx = num_in
            num_in += 1
            prv_start = 0.6
            prv_dur = 3.6
            prv_end = min(duration - 0.3, round(prv_start + prv_dur, 2))
            prv_fo = max(prv_start + 0.3, prv_end - 0.4)
            prv_x = "(W-w-40)" if not self.is_vertical else "(W-w-24)"
            prv_y = 40 if not self.is_vertical else 80
            filter_parts.append(
                f"[{prv_idx}:v]scale=iw*0.75:ih*0.75,format=rgba,fade=t=in:st={prv_start:.2f}:d=0.25:alpha=1,fade=t=out:st={prv_fo:.2f}:d=0.35:alpha=1[prv_animated]"
            )
            filter_parts.append(
                f"[{cur_v}][prv_animated]overlay=x='{prv_x}':y={prv_y}:enable='between(t,{prv_start:.2f},{prv_end:.2f})'[v_prv]"
            )
            cur_v = "v_prv"

        # Superposicion de palabras clave / anos flotantes (rotulos de enfasis sin cards)
        if keyword_callout_overlays:
            kw_dur = 2.1
            for k_i, k_data in enumerate(keyword_callout_overlays):
                k_path = k_data["path"]
                k_frac = k_data["frac"]
                # Determinar momento idoneo evitando colision con card o free_title
                ideal_t = max(0.8, min(duration - kw_dur - 0.4, k_frac * duration))
                if card_img_path and card_img_path.exists() and card_duration > 0:
                    c_start = card_start_time
                    c_exit = card_start_time + card_duration
                    # Si cabe antes de la tarjeta con margen suficiente
                    if c_start >= kw_dur + 0.8 and (ideal_t + kw_dur + 0.3) <= c_start:
                        kw_start = ideal_t
                    # O si cabe después de que finalice la tarjeta
                    elif duration >= c_exit + kw_dur + 0.5:
                        kw_start = max(c_exit + 0.5, ideal_t)
                    else:
                        safe_log(f"[SceneEngine] 🛡️ Keyword callout '{k_data.get('text')}' omitido en escena {scene.scene_id} por colisión con tarjeta [{c_start:.1f}s-{c_exit:.1f}s].")
                        continue
                elif free_title_img_path and free_title_img_path.exists() and free_title_dur > 0:
                    f_exit = 0.4 + free_title_dur
                    if duration >= f_exit + kw_dur + 0.6:
                        kw_start = max(f_exit + 0.6, ideal_t)
                    else:
                        safe_log(f"[SceneEngine] 🛡️ Keyword callout '{k_data.get('text')}' omitido en escena {scene.scene_id} por colisión con free_title.")
                        continue
                else:
                    kw_start = ideal_t

                kw_end = min(duration - 0.2, kw_start + kw_dur)
                if kw_end - kw_start >= 1.2:
                    inputs.extend(["-loop", "1", "-t", dur_str, "-r", "25", "-i", str(k_path)])
                    kw_in_idx = num_in
                    num_in += 1
                    fo_st = max(kw_start + 0.2, kw_end - 0.28)
                    filter_parts.append(
                        f"[{kw_in_idx}:v]format=rgba,fade=t=in:st={kw_start:.2f}:d=0.22:alpha=1,fade=t=out:st={fo_st:.2f}:d=0.28:alpha=1[kwo_{k_i}]"
                    )
                    kw_slide = f"min(max((t-{kw_start:.2f})/0.25\\,0)\\,1)"
                    kw_y_expr = f"((H-h)/2)+24*(1-pow({kw_slide}\\,3))"
                    filter_parts.append(
                        f"[{cur_v}][kwo_{k_i}]overlay=x='(W-w)/2':y='{kw_y_expr}':enable='between(t,{kw_start:.2f},{kw_end:.2f})'[v_kwo_{k_i}]"
                    )
                    cur_v = f"v_kwo_{k_i}"

        # Superposición de Overlay Cinemático Remotion (React + Alpha ProRes)
        # Exclusión mutua estricta: asegurar que nunca se superponga sobre una tarjeta existente
        if ai_remotion_mov and ai_remotion_mov.exists() and not (card_img_path and card_img_path.exists()):
            inputs.extend(["-t", dur_str, "-r", "25", "-i", str(ai_remotion_mov)])
            remo_idx = num_in
            num_in += 1
            filter_parts.append(
                f"[{remo_idx}:v]scale={self.W}:{self.H},format=rgba[v_remo]"
            )
            filter_parts.append(f"[{cur_v}][v_remo]overlay=0:0[v_with_remo]")
            cur_v = "v_with_remo"

        # Subtítulos con libass (solo si burn_subtitles está activo; de lo contrario quedan limpios para el editor frontend)
        if srt_path and srt_path.exists() and getattr(self, "burn_subtitles", False):
            esc_srt = str(srt_path.resolve()).replace("\\", "/").replace(":", "\\:")
            sub_size = 22 if self.is_vertical else 18
            margin_v = 75 if self.is_vertical else 35
            force_style = subtitle_force_style(self.sub_style, sub_size, margin_v)
            filter_parts.append(
                f"[{cur_v}]subtitles='{esc_srt}':force_style='{force_style}'[v_sub]"
            )
            cur_v = "v_sub"

        # Título superior / HUD y Marca de Agua Ángel R sutil
        font_p = FileManager.get_system_font_path()
        font_opt = f":fontfile='{font_p}'" if font_p else ""
        clean_tag = re.sub(r"[^\w\s-]", "", scene.name).strip()[:30] or "EN VIVO"
        hud_fontsize = 18 if self.is_vertical else 20
        wm_fontsize = 16 if self.is_vertical else 18
        filter_parts.append(
            f"[{cur_v}]drawtext{font_opt}:text='● EN VIVO  |  {clean_tag.upper()}':fontcolor=white:fontsize={hud_fontsize}:x=44:y=34:box=1:boxcolor=black@0.65:boxborderw=8,"
            f"drawtext{font_opt}:text='Ángel R':fontcolor=white@0.35:fontsize={wm_fontsize}:x=w-tw-44:y=34[v_out]"
        )

        # Audio mix: voz de la escena + BGM sutil + SFX de transición
        # Aseguramos que la pista de voz llene la duración si es necesario con apad
        inputs.extend(["-i", str(audio_path)])
        voice_in_idx = num_in
        num_in += 1

        # Audio profesional: loudnorm EBU R128 para broadcast (-16 LUFS target)
        if self.audio_normalize:
            voice_norm = f"[{voice_in_idx}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,loudnorm=I=-16:TP=-1.5:LRA=11,apad=whole_dur={dur_str}[a_voice]"
        else:
            voice_norm = f"[{voice_in_idx}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,apad=whole_dur={dur_str}[a_voice]"

        audio_filter_parts = [voice_norm]
        audio_mix_inputs = ["[a_voice]"]

        if bgm_path and bgm_path.exists():
            inputs.extend(["-t", dur_str, "-stream_loop", "-1", "-i", str(bgm_path)])
            bgm_idx = num_in
            num_in += 1
            bgm_vol = getattr(self, 'bgm_volume', 0.06)
            audio_filter_parts.append(f"[{bgm_idx}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,volume={bgm_vol:.3f}[a_bgm]")
            audio_mix_inputs.append("[a_bgm]")

        # SFX de escena general (si aplica)
        sfx_path = self._get_sfx_path(scene.sfx)
        if sfx_path and sfx_path.exists():
            inputs.extend(["-i", str(sfx_path)])
            sfx_idx = num_in
            num_in += 1
            audio_filter_parts.append(f"[{sfx_idx}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,adelay=delays=150:all=1,volume=0.35[a_sfx]")
            audio_mix_inputs.append("[a_sfx]")

        # SFX sincronizado al instante exacto de aparición para elementos visuales
        if card_img_path and card_img_path.exists():
            sfx_map_by_type = {
                "verdict_badge": "pop",
                "step_badge": "pop",
                "source_chip": "pop",
                "stat_counter": "chime",
                "versus_split": "impact",
                "alert_banner": "alert",
                "tech_card": "whoosh",
                "quote_evidence": "whoosh",
                "quote": "pop",
                "bento": "whoosh",
                "map": "whoosh",
            }
            card_sfx_type = sfx_map_by_type.get(card_visual_type, "whoosh")
            c_sfx_path = self._get_sfx_path(card_sfx_type)
            if c_sfx_path and c_sfx_path.exists():
                inputs.extend(["-i", str(c_sfx_path)])
                c_sfx_idx = num_in
                num_in += 1
                c_del_ms = max(50, int(card_start_time * 1000))
                audio_filter_parts.append(
                    f"[{c_sfx_idx}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
                    f"adelay=delays={c_del_ms}:all=1,volume=0.85[a_card_sfx]"
                )
                audio_mix_inputs.append("[a_card_sfx]")

        if popup_img_path and popup_img_path.exists():
            p_sfx_path = self._get_sfx_path("pop")
            if p_sfx_path and p_sfx_path.exists():
                inputs.extend(["-i", str(p_sfx_path)])
                p_sfx_idx = num_in
                num_in += 1
                p_del_ms = max(50, int(popup_start_time * 1000))
                audio_filter_parts.append(
                    f"[{p_sfx_idx}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
                    f"adelay=delays={p_del_ms}:all=1,volume=0.80[a_pop_sfx]"
                )
                audio_mix_inputs.append("[a_pop_sfx]")

        if chips_img_path and chips_img_path.exists():
            ch_sfx_path = self._get_sfx_path("pop")
            if ch_sfx_path and ch_sfx_path.exists():
                inputs.extend(["-i", str(ch_sfx_path)])
                ch_sfx_idx = num_in
                num_in += 1
                ch_del_ms = max(50, int(chip_start_time * 1000))
                audio_filter_parts.append(
                    f"[{ch_sfx_idx}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
                    f"adelay=delays={ch_del_ms}:all=1,volume=0.75[a_chip_sfx]"
                )
                audio_mix_inputs.append("[a_chip_sfx]")

        # Normalizar a espacio de color estándar broadcast (bt709, limitado tv, yuv420p)
        # Esto previene desfases de SPS o decodificación JPEG yuvj420p entre escenas en concat copy
        grade_filter = COLOR_GRADE_FILTERS.get(getattr(self, 'color_grade', 'cinema'), '')
        scale_limit = "scale=out_color_matrix=bt709:out_range=limited,format=yuv420p"
        if grade_filter:
            filter_parts.append(f"[v_out]{scale_limit},{grade_filter}[v_graded]")
            final_v = "v_graded"
        else:
            filter_parts.append(f"[v_out]{scale_limit}[v_graded]")
            final_v = "v_graded"

        # Corte directo limpio entre escenas (eliminando el apagón dip-to-black de 0.5s)
        # Permite continuidad fluida sin parpadeos negros que causaban pausas perceptibles en el reproductor
        filter_parts.append(f"[{final_v}]copy[v_final]")
        final_v = "v_final"

        inputs_tags = "".join(audio_mix_inputs)
        # normalize=0: amix por defecto divide cada entrada entre el número de
        # entradas activas → la voz bajaba 3-6 dB con BGM/SFX y sufría un "swell"
        # al expirar el SFX (dropout_transition). Sin normalización, la voz
        # mantiene el -16 LUFS del loudnorm y cada pista conserva su volumen.
        audio_filter_parts.append(f"{inputs_tags}amix=inputs={len(audio_mix_inputs)}:duration=longest:normalize=0,aformat=sample_rates=48000:channel_layouts=stereo[a_out]")

        full_filter = ";\n".join(filter_parts + audio_filter_parts)
        filter_file = scene_dir / "scene_filter.txt"
        filter_file.write_text(full_filter, encoding="utf-8")

        scene_fps = getattr(self, 'fps', 30)
        scene_crf = getattr(self, 'crf', 18)
        cmd = [
            "ffmpeg", "-y",
            "-threads", "4",
            *inputs,
            "-filter_complex_script", str(filter_file),
            "-map", f"[{final_v}]",
            "-map", "[a_out]",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", str(scene_crf),
            "-pix_fmt", "yuv420p",
            "-color_range", "tv",
            "-colorspace", "bt709",
            "-color_primaries", "bt709",
            "-color_trc", "bt709",
            "-r", str(scene_fps),
            "-x264-params", "threads=2:rc-lookahead=10:colorprim=bt709:transfer=bt709:colormatrix=bt709:fullrange=off",
            "-c:a", "aac",
            "-b:a", "256k",
            "-ar", "48000",
            "-max_muxing_queue_size", "1024",
            "-t", dur_str,
            str(scene_tmp),
        ]

        if self.cancel_event and self.cancel_event.is_set():
            raise asyncio.CancelledError("Render cancelado.")

        # Diagnóstico persistente: el comando completo queda junto al filtro de la
        # escena; si FFmpeg falla, su stderr completo se escribe en la carpeta
        # (antes solo iba a la consola del servidor y se perdía).
        try:
            (scene_dir / "scene_cmd.txt").write_text(" ".join(cmd), encoding="utf-8")
        except Exception:
            pass

        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)
        except asyncio.CancelledError:
            try:
                proc.kill()
            except Exception:
                pass
            if sys.platform == "win32":
                try:
                    subprocess.run(["taskkill", "/F", "/PID", str(proc.pid)], capture_output=True)
                except Exception:
                    pass
            raise
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            if sys.platform == "win32":
                try:
                    subprocess.run(["taskkill", "/F", "/PID", str(proc.pid)], capture_output=True)
                except Exception:
                    pass
            raise RuntimeError(f"FFmpeg agotó el tiempo (600 s) renderizando la escena {scene.scene_id}.")

        if self.cancel_event and self.cancel_event.is_set():
            raise asyncio.CancelledError("Render cancelado tras ejecución de escena.")

        if not scene_tmp.exists() or scene_tmp.stat().st_size < 10000:
            err_msg = stderr.decode(errors="replace") if stderr else "No stderr"
            try:
                (scene_dir / "scene_ffmpeg_stderr.log").write_text(err_msg, encoding="utf-8")
            except Exception:
                pass
            print(f"[SceneEngine] ERROR FFmpeg escena {scene.scene_id}:\n{err_msg}")
            raise RuntimeError(f"Fallo al renderizar la escena {scene.scene_id}: {err_msg[-300:]}")

        # Escena completa y válida: publicar atómicamente y registrar su firma (con reintentos para Windows).
        for attempt in range(5):
            try:
                scene_tmp.replace(scene_out)
                break
            except OSError:
                if attempt == 4:
                    raise
                await asyncio.sleep(0.2)
        self._write_cache_meta(meta_path, scene)

        # Extraer miniatura visual de alta definición para el monitor en vivo del frontend
        # (Se captura en t=1.8s cuando los gráficos y tarjetas Bento ya hicieron slide-in completo)
        thumb_path = scene_dir / "scene_thumb.jpg"
        try:
            import subprocess
            subprocess.run([
                "ffmpeg", "-y", "-ss", "1.8", "-i", str(scene_out),
                "-vframes", "1", "-q:v", "3", str(thumb_path)
            ], capture_output=True, timeout=5)
        except Exception:
            pass

        safe_log(f"[SceneEngine] Escena {scene.scene_id} ({scene.name}) lista: {duration:.1f}s")
        return scene_out

    async def assemble_broadcast(
        self,
        plan: DirectorBroadcastPlan,
        avatar_clip: Optional[Path] = None,
        avatar_webm: Optional[Path] = None,
        output_file: Optional[Path] = None,
        progress_cb: Optional[Callable[[float, str], None]] = None,
    ) -> Path:
        """Renderiza todas las escenas y las concatena en el master broadcast final."""
        # Selección de track BGM según preferencia de usuario.
        # Rutas absolutas contra BASE_DIR: relativas al CWD, un lanzamiento desde
        # otro directorio mataba el BGM y los SFX en silencio.
        _audio_dir = settings.BASE_DIR / "assets" / "audio"
        BGM_TRACKS = {
            "default":   _audio_dir / "bgm_streamer.wav",
            "tension":   _audio_dir / "bgm_tension.wav",
            "upbeat":    _audio_dir / "bgm_upbeat.wav",
            "ambient":   _audio_dir / "bgm_ambient.wav",
            "silent":    None,  # Sin música
        }
        bgm_track_key = getattr(self, 'bgm_track', 'default') if hasattr(self, 'bgm_track') else 'default'
        bgm_candidate = BGM_TRACKS.get(bgm_track_key, BGM_TRACKS["default"])
        # Si el track específico no existe, caer al default
        if bgm_candidate and not bgm_candidate.exists():
            bgm_candidate = BGM_TRACKS["default"]
        bgm_path = bgm_candidate  # None = sin música

        # Chat overlay pre-generado
        chat_overlay_path = self.workdir / "chat_overlay.png"
        raw_comments = plan.chat_comments or [
            {"user": "TechFan", "badge": "VIP", "text": "¡Increíble análisis KAI!"},
            {"user": "DevLucas", "badge": "SUB", "text": "Dato mata relato siempre."},
        ]
        formatted = [
            (f"[{c.get('badge', 'VIP')}] @{c.get('user', 'Viewer')}", "cyan" if i % 2 == 0 else "amber", c.get("text", "¡Gran dato!"))
            for i, c in enumerate(raw_comments[:3])
        ]
        self.chat_renderer.render(formatted, chat_overlay_path)

        scene_files: List[Path] = []
        total_scenes = len(plan.scenes)

        for i, scene in enumerate(plan.scenes):
            if self.cancel_event and self.cancel_event.is_set():
                safe_log(f"[SceneEngine] Cancelación solicitada antes de la escena {scene.scene_id}. Abortando render.")
                raise asyncio.CancelledError("Render de transmisión cancelado por el usuario.")

            pct = 70.0 + (float(i) / max(1, total_scenes)) * 18.0
            if progress_cb:
                progress_cb(pct, f"Grabando Escena {scene.scene_id}/{total_scenes}: {scene.name} ({scene.type})...")

            # Reintento por escena: FFmpeg falla a veces de forma transitoria bajo
            # carga (return -22, streams sin paquetes). Antes, una escena fallida
            # abortaba TODO el run aunque las demás ya estuvieran listas.
            try:
                sc_file = await self.render_scene(
                    scene=scene,
                    avatar_clip=avatar_clip,
                    avatar_webm=avatar_webm,
                    bgm_path=bgm_path,
                    chat_overlay_path=chat_overlay_path,
                )
            except asyncio.CancelledError:
                raise
            except Exception as scene_err:
                safe_log(f"[SceneEngine] Escena {scene.scene_id} falló ({str(scene_err)[:150]}). Reintentando 1 vez...")
                if progress_cb:
                    progress_cb(pct, f"Escena {scene.scene_id} falló por un error transitorio; reintentando...")
                sc_file = await self.render_scene(
                    scene=scene,
                    avatar_clip=avatar_clip,
                    avatar_webm=avatar_webm,
                    bgm_path=bgm_path,
                    chat_overlay_path=chat_overlay_path,
                )
            scene_files.append(sc_file)

        # Concatenación final instantánea
        if progress_cb:
            progress_cb(90.0, "Concatenando y masterizando transmisión final...")

        concat_list_file = self.workdir / "concat_scenes.txt"
        with open(concat_list_file, "w", encoding="utf-8") as f:
            for sc in scene_files:
                f.write(f"file '{sc.resolve().as_posix()}'\n")

        output_file.parent.mkdir(parents=True, exist_ok=True)
        concat_cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list_file),
            "-c", "copy",
            "-movflags", "+faststart",
            "-max_muxing_queue_size", "1024",
            str(output_file),
        ]

        proc = await asyncio.create_subprocess_exec(*concat_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        concat_out, concat_err = await proc.communicate()

        # 1) Verificar el código de salida: antes NO se comprobaba — un FFmpeg
        # interrumpido (p. ej. servidor reiniciado durante el +faststart de un
        # master de cientos de MB) dejaba el archivo con los datos pero SIN el
        # índice moov, pasaba el chequeo de tamaño y la transmisión terminaba
        # "done" con un video que ningún reproductor podía abrir.
        if proc.returncode != 0 or not output_file.exists() or output_file.stat().st_size < 50000:
            err_txt = (concat_err or b"").decode(errors="replace")[-300:]
            raise RuntimeError(
                f"Error concatenando las escenas de la transmisión (código {proc.returncode}): {err_txt}. "
                "Reanudar reconstruye el master al instante: las escenas están en caché."
            )

        # 2) Validar integridad real del MP4: el átomo moov (índice) debe existir.
        # Es una lectura de cabecera de milisegundos que evita entregar como
        # "done" un master decapitado.
        probe = await asyncio.create_subprocess_exec(
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(output_file),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        probe_out, _ = await probe.communicate()
        if probe.returncode != 0 or not probe_out.strip():
            output_file.unlink(missing_ok=True)
            raise RuntimeError(
                "El master quedó corrupto (sin índice MP4), se eliminó para forzar su reconstrucción. "
                "Reanudar la transmisión lo regenera en segundos con las escenas en caché."
            )

        # Liberar inmediatamente archivos temporales pesados de las escenas (.mov intermedios)
        # conservando el video master, thumbnails y metadata intactos
        try:
            for sc in scene_files:
                sc_dir = sc.parent
                for mov in sc_dir.glob("*.mov"):
                    try: mov.unlink()
                    except Exception: pass
            # Limpiar avatar base intermedio del workdir si existe — PERO conservar
            # kai_avatar.mov: es la caché del loop base que StreamerPipeline reutiliza
            # entre ejecuciones (dos estrategias de caché no deben pelearse).
            for mov in self.workdir.glob("*.mov"):
                if mov.name == "kai_avatar.mov":
                    continue
                try: mov.unlink()
                except Exception: pass
        except Exception as _e_clean:
            safe_log(f"[SceneEngine] Limpieza post-render: {_e_clean}")

        safe_log(f"[SceneEngine] Transmisión completa masterizada con {total_scenes} escenas en: {output_file}")
        return output_file

    def _settings_signature(self) -> Dict[str, Any]:
        """Huella de los parámetros que cambian el pixel/sonido de una escena.

        La caché de escenas la compara antes de reutilizar: reanudar con otro
        formato (9:16 ↔ 16:9), voz, calidad u otra línea de guion debe re-renderizar.
        """
        return {
            "aspect_ratio": self.aspect_ratio,
            "voice": self.voice,
            "fps": self.fps,
            "crf": self.crf,
            "color_grade": self.color_grade,
            "sub_style": self.sub_style,
            "subs_enabled": self.subs_enabled,
            "burn_subtitles": getattr(self, "burn_subtitles", False),
            "audio_normalize": self.audio_normalize,
            "bgm_volume": self.bgm_volume,
            "bgm_track": self.bgm_track,
            "card_theme": self.card_theme,
        }

    def _cache_meta_valid(self, meta_path: Path, scene: "DirectorScene") -> bool:
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            return False
        expected = self._settings_signature()
        expected["speech_hash"] = hashlib.md5((scene.speech or "").encode("utf-8")).hexdigest()
        return meta == expected

    def _write_cache_meta(self, meta_path: Path, scene: "DirectorScene") -> None:
        try:
            meta = self._settings_signature()
            meta["speech_hash"] = hashlib.md5((scene.speech or "").encode("utf-8")).hexdigest()
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _get_audio_duration(self, audio_path: Path) -> float:
        try:
            res = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
                capture_output=True, text=True, check=True
            )
            return float(res.stdout.strip())
        except Exception:
            return 8.0

    def _get_media_provenance(self, media_path: Optional[Path]) -> Optional[Dict[str, Any]]:
        """Recupera los metadatos de procedencia, licencia y verificación del archivo multimedia."""
        if not media_path:
            return None
        cand_files = [
            media_path.with_name(f"{media_path.stem}_provenance.json"),
            media_path.parent / f"{media_path.stem.split('_')[0]}_provenance.json",
            self.orchestrator.target_dir / f"{media_path.stem}_provenance.json",
        ]
        for cf in cand_files:
            if cf.exists():
                try:
                    return json.loads(cf.read_text(encoding="utf-8"))
                except Exception:
                    pass
        return None

    async def _get_scene_visual(
        self,
        query: str,
        scene_dir: Path,
        is_video_scene: bool = False,
        intent: Optional[Any] = None,
    ) -> Optional[Path]:
        """Obtiene un recurso visual verificado de stock o archivo documental para la escena."""
        try:
            from core.models import BRollCue
            from core.smart_media_curator import SmartMediaCurator

            search_q = query
            if intent:
                search_q = SmartMediaCurator.build_targeted_search_query(intent, query)
            elif query and len(query.split()) <= 2:
                search_q = f"{query} documentary evidence 4k"

            cue_id = f"scene_cue_{abs(hash(search_q or query)) % 10000}"
            cue = BRollCue(
                cue_id=cue_id,
                start_sec=0.0,
                end_sec=10.0,
                concept=query or "technology abstract",
                search_query_en=search_q or query or "technology abstract",
                reasoning="Escena visual de fondo",
                asset_type="video" if is_video_scene else "photo",
            )
            res = await self.orchestrator._resolve_single_cue(cue)
            if res.local_file_path and Path(res.local_file_path).exists():
                p = Path(res.local_file_path)
                # Copiar sidecar de procedencia al directorio de la escena si existe
                prov_file = self.orchestrator.target_dir / f"{cue_id}_provenance.json"
                if prov_file.exists():
                    dest_prov = scene_dir / f"{p.stem}_provenance.json"
                    try:
                        dest_prov.write_text(prov_file.read_text(encoding="utf-8"), encoding="utf-8")
                    except Exception:
                        pass
                return p
        except Exception as exc:
            safe_log(f"[SceneEngine] No se pudo descargar visual para '{query}': {exc}")
        return None
    def _render_chips_overlay(self, chips: List[str], out_path: Path) -> Optional[Path]:
        """Renderiza una hilera horizontal de pastillas (chips) con banderas/iconos para referencias dinámicas."""
        if not chips:
            return None
        try:
            return self.web_renderer.render_chips_to_image(chips, out_path)
        except Exception as _ce:
            safe_log(f"[SceneEngine] Fallback de chips a Pillow: {_ce}")

        import io
        import urllib.request
        from PIL import Image, ImageDraw, ImageFont, ImageFilter

        scale = 2
        pill_h = 60 * scale
        pad_x = 26 * scale
        gap = 16 * scale

        COUNTRY_CODES = {
            "estados unidos": "us", "ee.uu": "us", "eeuu": "us", "usa": "us", "us": "us",
            "china": "cn", "cn": "cn",
            "argentina": "ar", "ar": "ar",
            "españa": "es", "espana": "es", "es": "es",
            "colombia": "co", "co": "co",
            "méxico": "mx", "mexico": "mx", "mx": "mx",
            "chile": "cl", "cl": "cl",
            "brasil": "br", "brazil": "br", "br": "br",
            "alemania": "de", "germany": "de", "de": "de",
            "reino unido": "gb", "uk": "gb", "inglaterra": "gb", "gb": "gb",
            "francia": "fr", "fr": "fr",
            "japón": "jp", "japon": "jp", "jp": "jp",
            "italia": "it", "it": "it",
            "canadá": "ca", "canada": "ca", "ca": "ca",
            "rusia": "ru", "ru": "ru",
            "australia": "au", "au": "au",
            "perú": "pe", "peru": "pe", "pe": "pe",
        }

        flags_dir = settings.BASE_DIR / "assets" / "flags_cache"
        flags_dir.mkdir(parents=True, exist_ok=True)

        def _get_flag_img(country_code: str, target_h: int) -> Optional[Image.Image]:
            cache_file = flags_dir / f"{country_code}.png"
            if not cache_file.exists():
                try:
                    url = f"https://flagcdn.com/w80/{country_code}.png"
                    req = urllib.request.Request(url, headers={"User-Agent": "AetherCut-Studio/2.0"})
                    with urllib.request.urlopen(req, timeout=4) as resp:
                        cache_file.write_bytes(resp.read())
                except Exception:
                    pass
            if cache_file.exists():
                try:
                    im = Image.open(cache_file).convert("RGBA")
                    tw = int(im.width * (target_h / im.height))
                    res = im.resize((tw, target_h), Image.LANCZOS)
                    # Mascara redondeada sutil para la bandera
                    fmask = Image.new("L", (tw, target_h), 0)
                    ImageDraw.Draw(fmask).rounded_rectangle((0, 0, tw - 1, target_h - 1), radius=4 * scale, fill=255)
                    flag_rounded = Image.new("RGBA", (tw, target_h), (0, 0, 0, 0))
                    flag_rounded.paste(res, (0, 0), fmask)
                    return flag_rounded
                except Exception:
                    pass
            return None

        f_font = None
        for fn in ["segoeuib.ttf", "arialbd.ttf", "seguiemj.ttf"]:
            p = Path("C:/Windows/Fonts") / fn
            if p.exists():
                try:
                    f_font = ImageFont.truetype(str(p), 22 * scale)
                    break
                except Exception:
                    pass
        if not f_font:
            f_font = ImageFont.load_default()

        probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        pills_data = []
        flag_h = int(30 * scale)

        for c in chips[:6]:
            raw = str(c).strip()
            if not raw:
                continue

            # Detectar si hay bandera emoji o código de 2 letras
            clean_name = raw
            c_code = None

            # 1. Buscar código al inicio (ej: 'us Estados Unidos', 'CN China')
            m_code = re.match(r"^([A-Za-z]{2})\s+(.+)$", raw)
            if m_code and m_code.group(1).lower() in COUNTRY_CODES:
                c_code = COUNTRY_CODES[m_code.group(1).lower()]
                clean_name = m_code.group(2).strip()
            else:
                # 2. Buscar por nombre de país: SOLO palabra completa ("us" dentro
                # de "Museo" o "Discusión" no es EE.UU.). Antes este fallback por
                # substring pintaba banderas falsas en chips corrientes.
                low_raw = raw.lower()
                for k, code_val in COUNTRY_CODES.items():
                    m_flag = re.search(rf"\b{re.escape(k)}\b", low_raw)
                    if not m_flag:
                        continue
                    # Claves cortas solo como SIGLAS en mayúsculas: "Usa energía"
                    # es el verbo español, no Estados Unidos.
                    if len(k) <= 4 and not raw[m_flag.start():m_flag.end()].isupper():
                        continue
                    c_code = code_val
                    break
                # Nota: ya NO se recorta el prefijo de 2 letras aquí — el re.sub
                # anterior destruía palabras legítimas ("IA avances" → "avances")
                # en el caso en que ni siquiera hubo código de país detectado.

            flag_img = _get_flag_img(c_code, flag_h) if c_code else None
            txt_w = int(probe.textlength(clean_name, font=f_font))
            extra_w = (flag_img.width + int(8 * scale)) if flag_img else 0
            w = int(txt_w + extra_w + (pad_x * 2))
            pills_data.append((clean_name, flag_img, w))

        if not pills_data:
            return None

        total_w = sum(w for _, _, w in pills_data) + (len(pills_data) - 1) * gap
        margin = 16 * scale
        W = total_w + (margin * 2)
        H = pill_h + (margin * 2)

        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)

        cur_x = margin
        for name_txt, f_img, w in pills_data:
            rect = (cur_x, margin, cur_x + w, margin + pill_h)
            # Pastilla obsidian dark con borde suave
            d.rounded_rectangle(rect, radius=pill_h // 2, fill=(18, 18, 22, 245), outline=(255, 255, 255, 60), width=1 * scale)
            content_x = cur_x + pad_x
            if f_img:
                f_y = margin + ((pill_h - f_img.height) // 2)
                im.paste(f_img, (content_x, f_y), f_img)
                content_x += f_img.width + int(8 * scale)
            d.text((content_x, margin + (pill_h // 2)), name_txt, font=f_font, fill=(255, 255, 255, 255), anchor="lm")
            cur_x += w + gap

        # Sombra suave difusa
        shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(shadow)
        cur_x = margin
        for _, _, w in pills_data:
            s_draw.rounded_rectangle((cur_x, margin + 4, cur_x + w, margin + pill_h + 4), radius=pill_h // 2, fill=(0, 0, 0, 160))
            cur_x += w + gap
        shadow = shadow.filter(ImageFilter.GaussianBlur(6 * scale))

        comp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        comp.paste(shadow, (0, 0), shadow)
        comp.paste(im, (0, 0), im)

        final_w = W // scale
        final_h = H // scale
        comp = comp.resize((final_w, final_h), Image.LANCZOS)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        comp.save(out_path, "PNG")
        return out_path

    def _get_sfx_path(self, sfx_name: str) -> Optional[Path]:
        # El LLM puede emitir "sfx": null — sin este guard el AttributeError
        # ("NoneType no tiene .lower") abortaba el broadcast completo.
        if not sfx_name or not isinstance(sfx_name, str):
            return None
        _audio_dir = settings.BASE_DIR / "assets" / "audio"
        sfx_map = {
            "whoosh": _audio_dir / "whoosh.wav",
            "chime": _audio_dir / "chime.wav",
            "impact": _audio_dir / "impact.wav",
            "alert": _audio_dir / "alert.wav",
            "pop": _audio_dir / "pop.wav",
            "none": None,
        }
        return sfx_map.get(sfx_name.lower().strip())

    def _generate_scene_subtitles(
        self,
        speech: str,
        duration: float,
        scene_dir: Path,
        boundaries: Optional[List[tuple]] = None
    ) -> Optional[Path]:
        srt_path = scene_dir / "scene_subtitles.srt"
        srt_lines = []

        def _fmt_srt(t: float) -> str:
            h = int(t // 3600)
            m = int((t % 3600) // 60)
            s = int(t % 60)
            ms = int((t - int(t)) * 1000)
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

        def _chunk_words(text_str: str) -> List[str]:
            """Subdivide el texto en bloques concisos de 3 a 4 palabras para que nunca saturen la pantalla."""
            raw_w = text_str.split()
            if not raw_w:
                return []
            chunks = []
            cur = []
            for i, w in enumerate(raw_w):
                cur.append(w)
                remaining = len(raw_w) - (i + 1)
                has_punct = bool(re.search(r"[.,!?;:]", w))
                # Cortar si llegamos a 4 palabras, o a 3 palabras si hay puntuación o quedan palabras suficientes
                if len(cur) >= 4 or (len(cur) >= 3 and remaining != 1) or (has_punct and len(cur) >= 2 and remaining >= 2):
                    chunks.append(" ".join(cur))
                    cur = []
            if cur:
                if len(cur) <= 2 and chunks:
                    prev_words = chunks[-1].split()
                    if len(prev_words) <= 3:
                        chunks[-1] = chunks[-1] + " " + " ".join(cur)
                    else:
                        chunks.append(" ".join(cur))
                else:
                    chunks.append(" ".join(cur))
            return chunks

        # 1. Si tenemos timestamps precisos de Edge TTS por oración
        if boundaries and len(boundaries) > 0:
            idx = 1
            for st, en, text in boundaries:
                sentence_chunks = _chunk_words(text)
                if not sentence_chunks:
                    continue
                total_chars = sum(len(c) for c in sentence_chunks) or 1
                span = max(0.4, en - st)
                c_start = st
                for chunk_idx, chunk in enumerate(sentence_chunks):
                    weight = len(chunk) / total_chars
                    c_dur = span * weight
                    c_end = en if chunk_idx == len(sentence_chunks) - 1 else round(c_start + c_dur, 3)
                    clean_txt = chunk.strip().replace(":", "")
                    srt_lines.append(f"{idx}\n{_fmt_srt(c_start)} --> {_fmt_srt(c_end)}\n{clean_txt}\n")
                    idx += 1
                    c_start = c_end
            if srt_lines:
                srt_path.write_text("\n".join(srt_lines), encoding="utf-8")
                return srt_path

        # 2. Fallback ponderado por caracteres en fragmentos cortos de 3 a 4 palabras
        words = speech.split()
        if not words:
            return None
        sub_chunks = _chunk_words(speech)
        if not sub_chunks:
            return None

        start_lead = 0.12
        total_chars = sum(len(c) for c in sub_chunks) or 1
        active_speech_time = max(2.0, duration - 0.45)

        curr_t = start_lead
        for idx, chunk in enumerate(sub_chunks):
            chunk_weight = len(chunk) / total_chars
            chunk_dur = max(0.7, active_speech_time * chunk_weight)
            st = curr_t
            en = min(duration - 0.1, curr_t + chunk_dur)
            curr_t = en

            clean = chunk.strip().replace(":", "")
            srt_lines.append(f"{idx + 1}\n{_fmt_srt(st)} --> {_fmt_srt(en)}\n{clean}\n")

        srt_path.write_text("\n".join(srt_lines), encoding="utf-8")
        return srt_path
