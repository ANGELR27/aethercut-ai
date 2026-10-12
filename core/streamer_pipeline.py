"""Motor autónomo de transmisión broadcast con KAI (Modo Libre / KAI Streamer).

Genera videos de divulgación o noticias 100% de forma autónoma:
1. Investigación web en tiempo real (noticias, datos verificados, cifras clave).
2. Redacción de guión de alto impacto con Gemini (humor, chispa, datos de peso).
3. Síntesis de voz neural de alta calidad (edge-tts).
4. Animación del presentador KAI (lip-sync reactivo, parpadeo, HUD interactivo).
5. B-rolls cinematográficos de apoyo y tarjetas estilo Pinterest Bento Glassmorphism.
6. Ensamble broadcast en alta definición (1080p o Short vertical 9:16).
"""

from __future__ import annotations

import asyncio
import json
import math
import re
import shutil
import subprocess
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from config.settings import settings
from core.orchestrator import AssetOrchestrator
from core.avatar_narrator import AvatarNarrator, DEFAULT_VOICE
from core.avatar_renderer import AvatarRenderer
from core.director import AIDirector, DirectorBroadcastPlan, DirectorScene
from core.llm import LLMClient, safe_log
from core.models import ActionType, BRollCue, CaptionItem, InfoCard, SourceRef, TimelineSegment, VideoEditingPlan
from core.project_store import ProjectStore
from core.scene_engine import SceneEngine

STYLE_PROMPTS: Dict[str, str] = {
    "divulgacion": """ESTILO DE COMUNICACIÓN: DIVULGACIÓN CIENTÍFICA & TECH
- Tono: Fresco, dinámico, chispeante, con analogías cotidianas y humor inteligente ("¡Dato mata relato!").
- Enfoque: Descomponer conceptos técnicos o científicos complejos en ideas claras, entretenidas y con cifras contundentes.""",

    "debate": """ESTILO DE COMUNICACIÓN: DEBATE, DILEMAS ÉTICOS Y PREGUNTAS A LA MESA
- Tono: Crítico, reflexivo, prudente e intelectualmente provocador.
- Misión: Dejar dilemas profundos y preguntas abiertas sobre la mesa:
  * "¿Hasta qué punto debemos permitir esto?", "¿Quién gana y quién asume los riesgos?", "¿Qué precauciones debemos plantearnos antes de que sea tarde?".
  * Llama a tener cuidado con el optimismo ciego, contrasta al menos dos posturas opuestas con datos duros y pide al chat/audiencia que compartan su postura.""",

    "analisis": """ESTILO DE COMUNICACIÓN: ANÁLISIS PROFUNDO & VIDEOENSAYO
- Tono: Riguroso, ordenado, pedagógico y exhaustivo.
- Estructura paso a paso:
  1. Origen histórico y contexto del problema.
  2. Mecanismo técnico real y cómo funciona en la práctica.
  3. Cifras económicas, impacto social comprobado y actores clave.
  4. Escenarios futuros y ramificaciones a mediano y largo plazo.""",

    "noticias": """ESTILO DE COMUNICACIÓN: NOTICIERO BROADCAST & BREAKING NEWS
- Tono: Periodístico, urgente, directo y de alto impacto.
- Estructura: Titular de impacto en los primeros segundos, citas de fuentes oficiales o declaraciones clave, análisis rápido de causas y consecuencias inmediatas.""",

    "podcast": """ESTILO DE COMUNICACIÓN: PÓDCAST & CHARLA STREAMER CERCANA
- Tono: Conversacional, íntimo, reflexivo y pausado ("Charla de café con KAI").
- Estilo oral: Pausas pensativas con puntos suspensivos (...), reflexiones sinceras en primera persona, interacción directa con comentarios del chat y anécdotas.""",

    "mitos": """ESTILO DE COMUNICACIÓN: MITOS AL DESCUBIERTO (DESMINTIENDO CREENCIAS POPULARES)
- Tono: Frontal, desafiante y desmitificador.
- Estructura: "¿Qué es lo que casi todo el mundo cree erróneamente?" vs "¿Qué dice la evidencia y la ciencia real?". Desarma falacias populares con datos incontestables.""",

    "directo": """ESTILO DE COMUNICACIÓN: DIRECTO, AL GRANO & SIN RODEOS
- Tono: Contundente, directo al punto, enérgico y sin filtro ni rodeos innecesarios.
- Estructura: Va directo a los hechos sin introducciones largas. Lenguaje franco, claro y certero que dice las cosas como son.""",

    "humor": """ESTILO DE COMUNICACIÓN: HUMORÍSTICO, JUGUETÓN & ENTRETENIDO
- Tono: Divertido, ocurrente, con comentarios cómicos, remates ingeniosos y comparaciones exageradas o chistosas.
- Dinámica: Mantiene al público sonriendo y enganchado, intercalando bromas inteligentes sobre los personajes o situaciones sin perder el hilo.""",

    "sarcastico": """ESTILO DE COMUNICACIÓN: SARCÁSTICO, IRÓNICO & ÁCIDO
- Tono: Mordaz, con fina ironía, cinismo elegante y sarcasmo punzante ("Vaya sorpresa, quién se lo hubiera imaginado...").
- Dinámica: Señala contradicciones obvias, hipocresías o absurdos con frases afiladas y ceja levantada.""",

    "storytelling": """ESTILO DE COMUNICACIÓN: STORYTELLING & RELATOS INMERSIVOS
- Tono: Cinematográfico, envolvente, con tensión narrativa y suspenso ("Todo comenzó un martes que parecía normal...").
- Estructura: Planteamiento, giro dramático, clímax y resolución moral o impactante. Pinta escenas vívidas con palabras.""",

    "top_ranking": """ESTILO DE COMUNICACIÓN: TOP & RANKING DINÁMICO
- Tono: Competitivo, de cuenta regresiva emocionante (ej. Puesto 10 al Puesto 1).
- Estructura: Cada posición tiene nombre claro, motivo del puesto, datos o cifras específicas que justifican su lugar, y sorpresa para el podio.""",

    "reaccion": """ESTILO DE COMUNICACIÓN: REACCIÓN & ANÁLISIS EN VIVO (MÓDULO A)
- Tono: Espontáneo, atento, crítico y analítico.
- Dinámica: Presenta el clip o noticia, reacciona genuinamente y aporta análisis propio sustancial. No se limita a narrar lo que ya se ve; descubre detalles que el espectador pasó por alto.""",

    "review": """ESTILO DE COMUNICACIÓN: REVIEW, PRUEBA & COMPARATIVA (MÓDULO E)
- Tono: Imparcial, técnico, transparente y orientado a resolver la duda del consumidor.
- Estructura: Problema a resolver, criterios de evaluación, ventajas, desventajas, limitaciones reales y recomendación final honesta.""",

    "gaming": """ESTILO DE COMUNICACIÓN: GAMING, GAMEPLAY & DESAFÍO (MÓDULO F)
- Tono: Enérgico, inmersivo, competitivo y emocionante.
- Estructura: Objetivo claro, reglas del desafío, obstáculos inesperados, decisiones bajo presión y desenlace épico.""",

    "tutorial": """ESTILO DE COMUNICACIÓN: TUTORIAL & GUÍA EDUCATIVA (MÓDULO H)
- Tono: Didáctico, claro, paciente y práctico.
- Estructura: Resultado prometido, requisitos previos, pasos secuenciales comprobables, errores comunes a evitar y demostración de éxito verificable.""",

    "biografia": """ESTILO DE COMUNICACIÓN: BIOGRAFÍA, HISTORIAS & CASOS REALES (MÓDULO G)
- Tono: Documental, humano, reflexivo y riguroso.
- Estructura: Contexto y protagonistas, decisiones críticas documentadas, consecuencias históricas y legado perdurable sin inventar hechos.""",

    "misterio": """ESTILO DE COMUNICACIÓN: MISTERIOS, ENIGMAS & INVESTIGACIÓN (MÓDULO C)
- Tono: Intrigante, analítico, atmosférico y basado en evidencias.
- Estructura: Incógnita inicial, pistas progresivas, contraste de hipótesis rivales y revelación de lo que la ciencia y la historia pueden confirmar.""",

    "shorts": """ESTILO DE COMUNICACIÓN: SHORT VIRAL VERTICAL (MÓDULO K)
- Tono: Dinámico, directo, ultracompacto y visual.
- Estructura: Gancho visual instantáneo en el segundo 1, una sola idea contundente desarrollada al grano y remate satisfactorio sin relleno.""",

    "hibrido": """ESTILO DE COMUNICACIÓN: COMBO MULTI-ESTILO (DIRECTO + HUMOR + SARCASMO + NARRATIVA)
- Tono: Una mezcla explosiva y súper entretenida: arranca directo al grano, mete comentarios sarcásticos y cómicos, y relata los hechos con tensión inmersiva."""
}

def resolve_style_instructions(style_raw: str) -> str:
    """Resuelve las instrucciones de estilo, permitiendo estilos individuales o combinaciones separadas por coma/signo más."""
    if not style_raw:
        return STYLE_PROMPTS["divulgacion"]
    tokens = [t.strip().lower() for t in style_raw.replace("+", ",").replace("&", ",").split(",") if t.strip()]
    matched = []
    for tok in tokens:
        for k, v in STYLE_PROMPTS.items():
            if tok == k or tok in k:
                if v not in matched:
                    matched.append(v)
                break
    if not matched:
        return STYLE_PROMPTS.get(style_raw.lower().strip(), STYLE_PROMPTS["divulgacion"])
    return "\n\n---\n\n".join(matched)

@dataclass
class StreamerOptions:
    topic: str
    style: str = "divulgacion"  # "divulgacion", "debate", "analisis", "noticias", "podcast", "mitos"
    duration_sec: int = 45      # 60, 180, 300, 600, 900
    voice: str = DEFAULT_VOICE
    aspect_ratio: str = "16:9"  # "16:9" o "9:16"
    card_theme: str = "dark"    # "dark" o "light"
    rtmp_url: Optional[str] = None # RTMP stream key URL para YouTube, Twitch o Kick
    # --- Opciones definidas en el compositor (todas con default retrocompatible) ---
    sub_style: str = "classic"     # classic, outline, viral, neon, minimal, cinema
    subs_enabled: bool = True
    visual_mode: str = "mixed"     # mixed | svg (animaciones vectoriales propias) | stock (b-roll)
    enable_broll: bool = True
    enable_cards: bool = True
    extra_notes: str = ""          # Indicaciones libres del usuario para el director
    flash_audit: bool = True       # Auditoría editorial con GLM-5.3-flash
    # === MODO ANÁLISIS DE CASO ===
    # URL de un video/caso concreto (YouTube u otro sitio soportado por yt-dlp):
    # KAI descarga el video, extrae fotogramas REALES, los analiza con Gemini y
    # el director los usa como fondos — análisis visual de un caso específico.
    source_video_url: Optional[str] = None
    # === PARÁMETROS DE PRODUCCIÓN PROFESIONAL (nuevos) ===
    audio_normalize: bool = True   # Normalización loudnorm EBU R128 (-16 LUFS broadcast)
    color_grade: str = "cinema"    # raw | cinema | broadcast | neon | warm | cool
    fps: int = 30                  # 24 (cine) | 30 (web/YT) | 60 (gaming)
    crf: int = 18                  # Calidad H.264: 16=máxima, 18=alta, 20=buena, 23=media
    bgm_volume: float = 0.06       # Volumen de música de fondo (0.0 = sin BGM, 0.12 = notable)
    intro_style: str = "kai"       # none | kai | minimal | broadcast
    outro_enabled: bool = True     # Agregar segmento de cierre con pantalla de like/sub
    bgm_track: str = "default"     # default | tension | upbeat | ambient | silent
    auto_publish: bool = False     # Publicar automáticamente en YouTube al finalizar renderizado


def build_creative_hints(options: "StreamerOptions") -> str:
    """Traduce las opciones del compositor a instrucciones para el AI Director."""
    hints = []
    mode = (options.visual_mode or "mixed").lower()
    if mode == "svg":
        hints.append("PRIORIZA B-Roll de video real cinemático y tarjetas Bento informativas en movimiento.")
    elif mode == "stock":
        hints.append("PRIORIZA B-Roll de video real (video_reaction); usa vector_motion solo si es imprescindible.")
    if not options.enable_broll:
        hints.append("NO uses escenas 'video_reaction' con B-Roll de stock.")
    if not options.enable_cards:
        hints.append("NO uses escenas 'card_focus' (tarjetas Bento); apoya los datos con la voz y los gráficos vectoriales.")
    if (options.extra_notes or "").strip():
        hints.append(f"INDICACIONES DEL USUARIO (obligatorias): {options.extra_notes.strip()[:600]}")
    if not hints:
        return ""
    return "\n\nPREFERENCIAS DE PRODUCCIÓN:\n- " + "\n- ".join(hints)


class StreamerPipeline:
    """Ejecuta el ciclo de vida completo de una transmisión autónoma de KAI."""

    def __init__(
        self,
        task_id: str,
        options: StreamerOptions,
        on_state: Callable[[str, float, str, Dict[str, Any]], None],
        cancel_event: Optional[threading.Event] = None,
        project_store: Optional[ProjectStore] = None,
        render_lock: Optional[asyncio.Lock] = None,
    ):
        self.task_id = task_id
        self.options = options
        self.on_state = on_state
        self.cancel_event = cancel_event or threading.Event()
        self.project_store = project_store or ProjectStore(task_id)
        self.render_lock = render_lock or asyncio.Lock()
        self.workdir = self.project_store.workdir
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.llm = LLMClient()
        self.narrator = AvatarNarrator(voice=options.voice)
        self.avatar_rnd = AvatarRenderer(badge_size=360)

    def _state(self, step: str, progress: float, message: str, **extra: Any) -> None:
        self.on_state(step, progress, message, **extra)
        if self.project_store:
            self.project_store.set_status(step, message=message)

    async def run(self) -> Dict[str, Any]:
        """Ejecuta la transmisión completa y genera el video final."""
        safe_log(f"[Streamer] Iniciando transmisión autónoma para: «{self.options.topic}»")
        
        plan_cache_path = self.workdir / "broadcast_plan.json"
        is_resumed_plan = False
        plan = None
        if plan_cache_path.exists():
            try:
                cached_dict = json.loads(plan_cache_path.read_text(encoding="utf-8"))
                plan = DirectorBroadcastPlan.from_dict(cached_dict)
                is_resumed_plan = True
                safe_log(f"[Streamer] Plan de emisión recuperado de disco: {len(plan.scenes)} escenas.")
            except Exception as _e:
                safe_log(f"[Streamer] No se pudo leer plan cacheado, regenerando: {_e}")

        # 0. MODO ANÁLISIS DE CASO: descargar el video fuente, extraer fotogramas
        # REALES y analizarlos con Gemini ANTES de dirigir. Los frames quedan en
        # workdir/case_frames para que scene_engine los use como fondos.
        case_frames: List[Dict[str, Any]] = []
        source_url = str(getattr(self.options, "source_video_url", "") or "").strip()
        if source_url and source_url.lower() not in ("none", "null"):
            case_frames = await self._prepare_case_media(source_url)

        if not plan:
            # 1. Investigación Web
            self._state("research", 10.0, f"Investigando en internet sobre «{self.options.topic}»...")
            evidence = await self._gather_web_facts(self.options.topic)

            if self.cancel_event.is_set():
                raise asyncio.CancelledError()

            # 2. Planificación con el Director de IA
            self._state("script", 25.0, "Director de IA planificando escenas, emociones y encuadres...")
            style_instructions = resolve_style_instructions(self.options.style) + build_creative_hints(self.options)
            director = AIDirector(self.llm)
            plan = await director.direct_broadcast(
                topic=self.options.topic,
                style=self.options.style,
                evidence=evidence,
                duration_target=self.options.duration_sec,
                style_instructions=style_instructions,
                case_frames=case_frames,
            )

        # Auditoría editorial y optimización de escenas con GLM-5.3-flash (solo para producciones nuevas)
        if not is_resumed_plan:
            try:
                from core.review_critic import FlashContentReviewer
                reviewer = FlashContentReviewer()
                if reviewer.available and getattr(self.options, "flash_audit", True):
                    self._state("script", 32.0, "⚡ GLM-5.3-flash auditando guión, locución y recursos visuales...")
                    plan_dict = reviewer.review_and_optimize_plan(plan.to_dict(), self.options.topic)
                    plan = DirectorBroadcastPlan.from_dict(plan_dict)
            except Exception as _rev_err:
                safe_log(f"[Streamer] Aviso en auditoría GLM-5.3-flash: {_rev_err}")

        # Guardar plan en workdir y en project_store inmediatamente
        try:
            (self.workdir / "broadcast_plan.json").write_text(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
            if self.project_store:
                self.project_store.save_plan(plan.to_dict())
        except Exception as _e:
            safe_log(f"[Streamer] Aviso al guardar plan: {_e}")

        if self.cancel_event.is_set():
            raise asyncio.CancelledError()

        # 3. Renderizado del Avatar Animado (Loop dinámico fluido con transparencia alfa perfecta)
        avatar_clip = self.workdir / "kai_avatar.mov"
        if not (avatar_clip.exists() and avatar_clip.stat().st_size > 50000):
            self._state("avatar", 45.0, "Animando expresiones, respiración y lip-sync de KAI...")
            await asyncio.to_thread(
                self.avatar_rnd.render_reaction_clip,
                6.0,
                avatar_clip,
                fps=24
            )
        else:
            safe_log("[Streamer] Reusando loop dinámico de avatar KAI existente.")

        if self.cancel_event.is_set():
            raise asyncio.CancelledError()

        # 4. Motor de Escenas: Modulación emocional, composición reactiva y masterización
        scenes_preview_data = [
            {
                "scene_id": sc.scene_id,
                "name": sc.name,
                "type": sc.type,
                "emotion": sc.emotion,
                "camera": sc.camera,
                "duration_est": round(sc.duration_est, 1),
                "headline": sc.card.headline if sc.card else "",
                "stat": sc.card.stat if sc.card else "",
                "thumb_url": f"/storage/projects/{self.task_id}/work/scene_{sc.scene_id}/scene_thumb.jpg",
                "card_url": f"/storage/projects/{self.task_id}/work/scene_{sc.scene_id}/card_{sc.scene_id}.png",
            }
            for sc in plan.scenes
        ]
        self._state("render", 60.0, f"Scene Engine dirigiendo y grabando {len(plan.scenes)} escenas...", live_scenes=scenes_preview_data)
        output_file = settings.OUTPUTS_DIR / f"{self.task_id}_master.mp4"

        # Director de Estilos: definir paleta y tipografía automáticamente según el tono del tema
        from core.ai_remotion_generator import AIStyleDirector
        style_director = AIStyleDirector(self.llm)
        theme_spec = style_director.determine_style(
            topic=self.options.topic,
            style_mode=self.options.style,
            extra_notes=getattr(self.options, "extra_notes", ""),
        )
        safe_log(f"[StyleDirector] 🎨 Paleta seleccionada: {theme_spec['name']} ({theme_spec['primary']} / {theme_spec['accent']}) | Tipografía/Subtítulos: {theme_spec['sub_style']}")

        scene_engine = SceneEngine(
            workdir=self.workdir,
            aspect_ratio=self.options.aspect_ratio,
            voice=self.options.voice,
            card_theme=self.options.card_theme,
            cancel_event=self.cancel_event,
            sub_style=self.options.sub_style,
            subs_enabled=self.options.subs_enabled,
            fps=getattr(self.options, 'fps', 30),
            crf=getattr(self.options, 'crf', 18),
            audio_normalize=getattr(self.options, 'audio_normalize', True),
            color_grade=getattr(self.options, 'color_grade', 'cinema'),
            bgm_volume=getattr(self.options, 'bgm_volume', 0.06),
            bgm_track=getattr(self.options, 'bgm_track', 'default'),
            style_spec=theme_spec,
        )

        def scene_progress(pct: float, msg: str):
            self._state("render", pct, msg, live_scenes=scenes_preview_data)

        async with self.render_lock:
            await scene_engine.assemble_broadcast(
                plan=plan,
                avatar_clip=avatar_clip,
                output_file=output_file,
                progress_cb=scene_progress,
            )

        # 5. Generar YouTube Cover Thumbnail (1280x720) y Short 9:16 Viral automáticamente
        thumb_output = settings.OUTPUTS_DIR / f"{self.task_id}_thumbnail.jpg"
        short_output = settings.OUTPUTS_DIR / f"{self.task_id}_short.mp4"
        try:
            # 5a. Crear YouTube Thumbnail de alta conversión
            from PIL import Image, ImageDraw, ImageFont, ImageFilter
            base_bg = None
            for sc in plan.scenes:
                sc_thumb = self.workdir / f"scene_{sc.scene_id}" / "scene_thumb.jpg"
                if sc_thumb.exists():
                    base_bg = sc_thumb
                    break
            
            tb_im = Image.open(base_bg) if (base_bg and base_bg.exists()) else Image.open("assets/streamer_studio_room.jpg")
            tb_im = tb_im.resize((1280, 720), Image.Resampling.LANCZOS)
            tb_draw = ImageDraw.Draw(tb_im)
            
            # Velo oscuro con viñeta para contraste cinematográfico
            overlay_grad = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
            og_draw = ImageDraw.Draw(overlay_grad)
            og_draw.rectangle([0, 0, 800, 720], fill=(5, 8, 14, 210))
            tb_im.paste(overlay_grad, (0, 0), overlay_grad)
            tb_draw = ImageDraw.Draw(tb_im)

            # Titular épico en alto contraste
            f_title = None
            f_badge = None
            for fn in ["segoeuib.ttf", "arialbd.ttf"]:
                p = Path("C:/Windows/Fonts") / fn
                if p.exists():
                    try:
                        f_title = ImageFont.truetype(str(p), 48)
                        f_badge = ImageFont.truetype(str(p), 20)
                        break
                    except Exception:
                        pass
            if not f_title:
                f_title = ImageFont.load_default()
                f_badge = ImageFont.load_default()

            # Pastilla superior
            tb_draw.rounded_rectangle((50, 60, 240, 98), radius=8, fill=(239, 68, 68, 240))
            tb_draw.text((70, 68), "🔴 BROADCAST", font=f_badge, fill=(255, 255, 255))

            # Dividir título en 3 líneas
            words = (plan.title or self.options.topic).split()
            lines = []
            curr = ""
            for w in words:
                cand = (curr + " " + w).strip()
                if len(cand) <= 24:
                    curr = cand
                else:
                    if curr: lines.append(curr)
                    curr = w
            if curr: lines.append(curr)

            y_txt = 130
            for idx_l, line_str in enumerate(lines[:3]):
                col = (255, 255, 255) if idx_l == 0 else ((56, 189, 248) if idx_l == 1 else (251, 191, 36))
                tb_draw.text((50, y_txt), line_str.upper(), font=f_title, fill=col)
                y_txt += 62

            # Badge de dato clave si existe
            best_stat = next((sc.card.stat for sc in plan.scenes if sc.card and sc.card.stat), None)
            if best_stat:
                tb_draw.rounded_rectangle((50, 560, 380, 640), radius=14, fill=(15, 23, 42, 230), outline=(56, 189, 248), width=2)
                tb_draw.text((70, 574), f"★ {best_stat}", font=f_title, fill=(56, 189, 248))

            tb_im.save(thumb_output, "JPEG", quality=95)

            # 5b. Generar Short 9:16 vertical re-encuadrado a partir de la escena 2 o 3 (12-25s)
            candidate_scene = None
            for sc in plan.scenes:
                sc_f = self.workdir / f"scene_{sc.scene_id}" / f"scene_{sc.scene_id}.mp4"
                if sc_f.exists() and sc.type in ("card_focus", "video_reaction"):
                    candidate_scene = sc_f
                    break
            if not candidate_scene and plan.scenes:
                candidate_scene = self.workdir / "scene_1" / "scene_1.mp4"

                import subprocess
                subprocess.run([
                    "ffmpeg", "-y", "-i", str(candidate_scene),
                    "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
                    "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20",
                    "-threads", "2",
                    "-max_muxing_queue_size", "1024",
                    "-c:a", "aac", "-b:a", "192k", str(short_output)
                ], capture_output=True, timeout=30)
        except Exception as exc:
            safe_log(f"[StreamerPipeline] Generación de thumbnail/short opcional: {exc}")

        # 6. Broadcast RTMP opcional si el usuario proporcionó URL / clave
        if self.options.rtmp_url and str(self.options.rtmp_url).strip() not in ("None", "null", ""):
            rtmp_dest = str(self.options.rtmp_url).strip()
            self._state("render", 95.0, f"Emitiendo en vivo por RTMP a {rtmp_dest[:22]}...")
            asyncio.create_task(self._stream_to_rtmp(output_file, rtmp_dest))

        # Construir y guardar plan en ProjectStore
        edit_plan = VideoEditingPlan(
            video_summary=plan.title,
            total_original_duration_sec=plan.total_est_duration,
            timeline=[TimelineSegment(start_sec=0.0, end_sec=plan.total_est_duration, action=ActionType.KEEP)],
            info_cards=[],
            b_rolls=[],
            captions=[],
        )
        self.project_store.save_plan(edit_plan)

        media_url = f"/media/{output_file.name}"
        result_payload = {
            "output_file": str(output_file),
            "media_url": media_url,
            "master_video_url": media_url,
            "title": plan.title,
            "duration": plan.total_est_duration,
            "topic": self.options.topic,
            "style": self.options.style,
            "scenes_count": len(plan.scenes),
            "scenes": [
                {
                    "id": sc.scene_id,
                    "name": sc.name,
                    "type": sc.type,
                    "emotion": sc.emotion,
                    "camera": sc.camera,
                }
                for sc in plan.scenes
            ],
            "cards_shown": sum(1 for sc in plan.scenes if sc.card is not None),
            "brolls_count": len(plan.scenes),
            "silences_cut_count": 0,
            "time_saved_sec": 0.0,
            "thumbnail_url": f"/media/{thumb_output.name}" if thumb_output.exists() else None,
            "short_video_url": f"/media/{short_output.name}" if short_output.exists() else None,
        }

        # 7. Publicación automática desatendida o preparación autónoma multi-canal
        if getattr(self.options, 'auto_publish', False) or getattr(settings, 'AUTO_PUBLISH', False):
            try:
                from core.publish_studio import PublishStudio
                from core.channel_manager import ChannelManager
                import core.youtube_oauth as yt
                
                studio = PublishStudio(self.task_id)
                classification = ChannelManager.classify_content(self.options.topic)
                target_ch = classification.get("channel") or {}
                meta = studio.generate_metadata()
                
                safe_log(f"[AutoPublish] 🎯 Canal clasificado: {target_ch.get('name')} (Confianza: {classification.get('confidence', 0):.0%})")
                
                if yt.is_connected():
                    self._state("publish", 98.0, f"Publicando automáticamente en YouTube ({target_ch.get('name')})...")
                    upload_res = yt.upload_video(
                        video_path=output_file,
                        title=meta["title"],
                        description=meta["description"],
                        tags=meta["tags"],
                        category_id=str(target_ch.get("category_id", "28")),
                    )
                    if thumb_output.exists():
                        yt.set_thumbnail(upload_res["video_id"], thumb_output)
                    result_payload["youtube_upload"] = upload_res
                    safe_log(f"[AutoPublish] 🚀 ¡Video publicado en YouTube con éxito! {upload_res.get('video_url')}")
                else:
                    result_payload["auto_publish_prepared"] = {
                        "channel": target_ch,
                        "metadata": meta,
                        "status": "ready_for_assisted",
                    }
                    safe_log(f"[AutoPublish] 🧭 Paquete SEO y miniatura preparados para publicación asistida en {target_ch.get('name')}")
            except Exception as _ap_err:
                safe_log(f"[AutoPublish] No se pudo completar subida desatendida: {_ap_err}")

        self.project_store.set_status("done", result=result_payload, preview_file=str(output_file))
        self._state("done", 100.0, "¡Transmisión de KAI masterizada exitosamente!", result=result_payload)
        return result_payload

    async def _stream_to_rtmp(self, video_file: Path, rtmp_url: str) -> None:
        """Emite en tiempo real el archivo final hacia YouTube, Twitch o Kick."""
        try:
            cmd = [
                "ffmpeg", "-re",
                "-i", str(video_file),
                "-c", "copy",
                "-f", "flv",
                rtmp_url,
            ]
            proc = await asyncio.create_subprocess_exec(*cmd)
            await proc.wait()
        except Exception as exc:
            safe_log(f"[StreamerPipeline] Error en emisión RTMP: {exc}")

    async def _gather_web_facts(self, topic: str) -> str:
        """Busca noticias y datos reales con DuckDuckGo."""
        try:
            from ddgs import DDGS
            def search_ddg():
                with DDGS() as ddgs:
                    return list(ddgs.text(topic, region="es-es", max_results=5))
            results = await asyncio.wait_for(asyncio.to_thread(search_ddg), timeout=10.0)
            if results:
                lines = [f"- {r.get('title', '')}: {r.get('body', '')[:220]}" for r in results if r.get('body')]
                return "\n".join(lines[:4])
        except Exception as exc:
            safe_log(f"[Streamer] Búsqueda de soporte falló: {exc}")
        return "Noticia relevante y debate actual sobre el tema en tendencia."

    # ------------------------------------------------------------------
    # MODO ANÁLISIS DE CASO: video fuente real → fotogramas → Gemini
    # ------------------------------------------------------------------

    async def _prepare_case_media(self, source_url: str) -> List[Dict[str, Any]]:
        """Descarga el video del caso, extrae fotogramas reales y los describe.

        Devuelve [{"index": int, "desc": str}, ...] para el director. Es
        tolerante a fallos: si algo falla, la transmisión continúa en modo
        normal (sin fotogramas), con un log claro del motivo.
        """
        frames_dir = self.workdir / "case_frames"
        frames_dir.mkdir(parents=True, exist_ok=True)
        existing = sorted(frames_dir.glob("frame_*.jpg"))
        try:
            if not existing:
                self._state("case_media", 6.0, "Descargando el video del caso para análisis visual...")
                video_file = self.workdir / "case_source.%(ext)s"
                final_video = None

                def do_download():
                    import yt_dlp
                    opts = {
                        "format": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]/best",
                        "outtmpl": str(video_file),
                        "quiet": True,
                        "no_warnings": True,
                        "noplaylist": True,
                        "noprogress": True,
                        "socket_timeout": 20,
                        "extractor_args": {"youtube": {"player_client": ["android", "ios"]}},
                        "postprocessor_args": {"ffmpeg": ["-threads", "2"]},
                    }
                    for c_cand in [settings.STORAGE_DIR / "cookies.txt", settings.BASE_DIR / "cookies.txt", settings.BASE_DIR / "assets" / "cookies.txt"]:
                        if c_cand.is_file() and c_cand.stat().st_size > 10:
                            opts["cookiefile"] = str(c_cand.resolve())
                            safe_log(f"[Streamer] 🍪 Usando archivo de cookies: {c_cand.name}")
                            break
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        ydl.download([source_url])

                await asyncio.wait_for(asyncio.to_thread(do_download), timeout=180)
                candidates = [p for p in self.workdir.glob("case_source.*") if p.suffix.lower() in (".mp4", ".mkv", ".webm", ".mov")]
                if not candidates:
                    safe_log("[Streamer] Caso: la descarga no produjo un archivo de video.")
                    return []
                final_video = candidates[0]

                if self.cancel_event.is_set():
                    raise asyncio.CancelledError()

                # Extraer fotogramas repartidos por TODA la duración (máx 12, min 3)
                self._state("case_media", 8.0, "Extrayendo fotogramas clave del video del caso...")
                def probe_duration():
                    import subprocess
                    r = subprocess.run(
                        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                         "-of", "default=noprint_wrappers=1:nokey=1", str(final_video)],
                        capture_output=True, text=True, timeout=20)
                    return float(r.stdout.strip() or 0)
                try:
                    dur = await asyncio.wait_for(asyncio.to_thread(probe_duration), timeout=25)
                except Exception:
                    dur = 60.0
                num = max(3, min(12, int(dur // 8) or 3))
                fps_expr = f"{num}/{max(1.0, dur):.3f}"
                import subprocess

                def extract_frames():
                    subprocess.run([
                        "ffmpeg", "-y", "-i", str(final_video),
                        "-vf", f"fps={fps_expr},scale=1280:-2",
                        "-frames:v", str(num), "-q:v", "3",
                        str(frames_dir / "frame_%02d.jpg"),
                    ], capture_output=True, timeout=180)

                await asyncio.wait_for(asyncio.to_thread(extract_frames), timeout=200)
                existing = sorted(frames_dir.glob("frame_*.jpg"))

            if not existing:
                return []

            # Análisis visual con Gemini (multimodal): describir cada fotograma.
            self._state("case_media", 9.0, f"Gemini analizando {len(existing)} fotogramas reales del caso...")
            frames_info: List[Dict[str, Any]] = []
            try:
                from google.genai import types as gtypes

                def analyze():
                    parts = []
                    for i, frame in enumerate(existing[:8]):
                        data = frame.read_bytes()
                        parts.append(gtypes.Part.from_bytes(data=data, mime_type="image/jpeg"))
                    parts.append(
                        "Estos son fotogramas (EN ORDEN, índice 0 a N) de un video real. "
                        "Para cada fotograma describe en español qué se ve (máx 25 palabras), "
                        "destacando lo visualmente llamativo o revelador para un análisis. "
                        'Responde SOLO JSON: {"frames": [{"index": 0, "desc": "..."}, ...]}'
                    )
                    return self.llm.generate(parts, json_mode=True, max_models=2)

                raw = await asyncio.wait_for(asyncio.to_thread(analyze), timeout=120)
                parsed = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
                for item in parsed.get("frames", []):
                    if isinstance(item, dict) and isinstance(item.get("index"), int):
                        frames_info.append({"index": item["index"], "desc": str(item.get("desc", ""))[:220]})
            except Exception as ana_exc:
                safe_log(f"[Streamer] Análisis Gemini de fotogramas falló: {ana_exc}")

            # Si Gemini no describió, registrar los frames con descripción vacía:
            # igual sirven como fondos (el director puede anclarlos por orden).
            if not frames_info:
                frames_info = [{"index": i, "desc": ""} for i in range(len(existing))]
            safe_log(f"[Streamer] Caso listo: {len(frames_info)} fotogramas reales disponibles para el director.")
            return frames_info

        except asyncio.CancelledError:
            raise
        except Exception as exc:
            safe_log(f"[Streamer] Modo análisis de caso degradado ({exc}): continuando sin fotogramas.")
            return []

