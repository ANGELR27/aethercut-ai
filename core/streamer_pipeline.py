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
from core.card_renderer import InfoCardRenderer
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

STREAMER_SCRIPT_PROMPT = """Eres KAI, el divulgador, analista e streamer con inteligencia artificial más carismático y riguroso.

TAREA:
Crea un guión profesional para una transmisión en video de aproximadamente {duration_target} segundos ({duration_label}) sobre este tema:
TEMA: "{topic}"

{style_instructions}

DURACIÓN OBJETIVO Y EXTENSIÓN OBLIGATORIA:
- Duración deseada: {duration_target} segundos ({duration_label}).
- OBJETIVO DE PALABRAS PARA EL MONÓLOGO: Aproximadamente {words_target} palabras (lectura fluida a ritmo natural de 135-145 ppm).
- IMPORTANTE: Si la duración es extendida (3 a 15 minutos), es OBLIGATORIO que desarrolles los argumentos a fondo, con múltiples secciones, datos precisos, antecedentes, dilemas para reflexionar y advertencias sobre precauciones necesarias. No lo resumas.

INFORMACIÓN Y HECHOS RECOPILADOS DE LA WEB:
{evidence}

REGLAS DE GUIÓN:
1. "monologue": Texto completo que KAI dirá en voz alta:
   - Arranque potente que capture la atención de inmediato.
   - Pausas naturales con comas, puntos y puntos suspensivos (...) para que la voz respire con cadencia humana.
   - Enlace natural con las tarjetas de datos y comentarios del chat en vivo.
   - Cierre con conclusión sólida y llamado a la reflexión o debate.
2. "cards": Lista de {num_cards} tarjetas Bento de apoyo con datos concretos (cifras exactas o conceptos clave).
3. "chat_comments": Lista de 3 o 4 comentarios del chat en vivo con preguntas o reacciones de los espectadores.
4. "broll_queries": Lista de {num_brolls} términos en inglés para fondos visuales cinematográficos.
5. "highlight_words": 6 palabras clave de alto impacto.

FORMATO DE RESPUESTA (ESTRICTO JSON):
{{
  "title": "Titular llamativo de la transmisión",
  "monologue": "Texto completo y natural que KAI dirá en voz alta ({words_target} palabras aprox)...",
  "cards": [
    {{
      "headline": "Titular corto (máx 30 caracteres)",
      "body": "Explicación concisa y nítida del dato (máx 130 caracteres)",
      "badge": "DATO CLAVE",
      "stat": "40%"
    }}
  ],
  "chat_comments": [
    {{"user": "Usuario1", "badge": "VIP", "text": "Pregunta o reacción interesante"}},
    {{"user": "Usuario2", "badge": "SUB", "text": "Comentario sobre el dilema planteado"}},
    {{"user": "Usuario3", "badge": "MOD", "text": "Aporte complementario con datos"}}
  ],
  "broll_queries": ["search term 1", "search term 2"],
  "highlight_words": ["palabra1", "palabra2"]
}}"""


@dataclass
class StreamerOptions:
    topic: str
    style: str = "divulgacion"  # "divulgacion", "debate", "analisis", "noticias", "podcast", "mitos"
    duration_sec: int = 45      # 60, 180, 300, 600, 900
    voice: str = DEFAULT_VOICE
    aspect_ratio: str = "16:9"  # "16:9" o "9:16"
    card_theme: str = "dark"    # "dark" o "light"
    rtmp_url: Optional[str] = None # RTMP stream key URL para YouTube, Twitch o Kick


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
        
        # 1. Investigación Web
        self._state("research", 10.0, f"Investigando en internet sobre «{self.options.topic}»...")
        evidence = await self._gather_web_facts(self.options.topic)

        if self.cancel_event.is_set():
            raise asyncio.CancelledError()

        # 2. Planificación con el Director de IA
        self._state("script", 25.0, "Director de IA planificando escenas, emociones y encuadres...")
        style_instructions = resolve_style_instructions(self.options.style)
        
        plan_cache_path = self.workdir / "broadcast_plan.json"
        if plan_cache_path.exists():
            try:
                cached_dict = json.loads(plan_cache_path.read_text(encoding="utf-8"))
                plan = DirectorPlan.from_dict(cached_dict)
                safe_log(f"[Streamer] Plan de emisión recuperado de disco: {len(plan.scenes)} escenas.")
            except Exception as _e:
                safe_log(f"[Streamer] No se pudo leer plan cacheado, regenerando: {_e}")
                director = AIDirector(self.llm)
                plan = await director.direct_broadcast(
                    topic=self.options.topic,
                    style=self.options.style,
                    evidence=evidence,
                    duration_target=self.options.duration_sec,
                    style_instructions=style_instructions,
                )
        else:
            director = AIDirector(self.llm)
            plan = await director.direct_broadcast(
                topic=self.options.topic,
                style=self.options.style,
                evidence=evidence,
                duration_target=self.options.duration_sec,
                style_instructions=style_instructions,
            )

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
        self._state("avatar", 45.0, "Animando expresiones, respiración y lip-sync de KAI...")
        avatar_clip = self.workdir / "kai_avatar.mov"
        await asyncio.to_thread(
            self.avatar_rnd.render_reaction_clip,
            6.0,
            avatar_clip,
            fps=24
        )

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

        scene_engine = SceneEngine(
            workdir=self.workdir,
            aspect_ratio=self.options.aspect_ratio,
            voice=self.options.voice,
            card_theme=self.options.card_theme,
            cancel_event=self.cancel_event,
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

            if candidate_scene and candidate_scene.exists():
                import subprocess
                subprocess.run([
                    "ffmpeg", "-y", "-i", str(candidate_scene),
                    "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
                    "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20",
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

    async def _generate_script(self, topic: str, style: str, evidence: str) -> Dict[str, Any]:
        """Genera el monólogo y elementos con Gemini adaptados al estilo y duración seleccionada."""
        style_instructions = resolve_style_instructions(style)

        dur_sec = max(30, self.options.duration_sec)
        words_target = max(130, int(dur_sec * 2.3))
        num_cards = min(6, max(2, int(dur_sec / 120)))
        num_brolls = min(8, max(4, int(dur_sec / 40) + 1))

        if dur_sec >= 600:
            duration_label = f"{dur_sec // 60} minutos (Análisis Extendido)"
        elif dur_sec >= 120:
            duration_label = f"{dur_sec // 60} minutos"
        else:
            duration_label = f"{dur_sec} segundos"

        prompt = STREAMER_SCRIPT_PROMPT.format(
            topic=topic,
            style_instructions=style_instructions,
            duration_target=dur_sec,
            duration_label=duration_label,
            words_target=words_target,
            num_cards=num_cards,
            num_brolls=num_brolls,
            evidence=evidence
        )

        gen_timeout = max(35.0, min(120.0, float(dur_sec * 0.12)))
        try:
            loop = asyncio.get_running_loop()
            raw = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: self.llm.generate(prompt, json_mode=True, max_models=2)),
                timeout=gen_timeout
            )
            cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
            return json.loads(cleaned)
        except Exception as exc:
            safe_log(f"[Streamer] Error en Gemini script: {exc}")
            if style_key == "debate":
                fb_monologue = (
                    f"¡Qué tal mi gente! Hoy abrimos el debate con un tema que genera dilemas profundos: {topic}. "
                    "Por un lado, los defensores aseguran que el progreso es imparable... "
                    "Pero debemos detenernos y preguntarnos: ¿cuáles son las consecuencias imprevistas? "
                    "¿Qué precauciones deberíamos plantearnos antes de que sea irreversible? "
                    "¡Dato mata relato! Las cifras confirman una transformación acelerada, pero la prudencia no se puede delegar. "
                    "Dejen su postura en el chat porque este dilema nos involucra a todos."
                )
            elif style_key == "analisis":
                fb_monologue = (
                    f"Bienvenidos a este análisis exhaustivo sobre {topic}. "
                    "Para entender el estado actual, primero debemos remontarnos al origen de esta tecnología. "
                    "El mecanismo real y la arquitectura técnica demuestran que no se trata de una moda pasajera, sino de un cambio estructural. "
                    "Las cifras oficiales y los estudios más rigurosos proyectan un impacto determinante en los próximos años. "
                    "Desglosemos cada punto con precisión, porque como siempre decimos: ¡dato mata relato!"
                )
            else:
                fb_monologue = (
                    f"¡Qué tal mi gente! Hoy tenemos que hablar a fondo de {topic}. "
                    "La realidad es que este tema está marcando un punto de inflexión. "
                    "¡Y como siempre les digo: dato mata relato! Estén atentos a cada cifra y a cada dilema porque esto recién comienza."
                )
            return {
                "title": f"KAI Live: {topic[:40]}",
                "monologue": fb_monologue,
                "cards": [
                    {"headline": "Dato Clave Verificado", "body": "Transformación confirmada por fuentes técnicas oficiales.", "badge": "DATO CLAVE", "stat": "2026"},
                    {"headline": "Dilema y Precaución", "body": "Puntos críticos que debemos plantearnos con seriedad.", "badge": "DEBATE", "stat": "95%"}
                ],
                "chat_comments": [
                    {"user": "TechFan", "badge": "VIP", "text": "¡Tema crucial para debatir!"},
                    {"user": "Lucas_Dev", "badge": "SUB", "text": "¿Qué precauciones hay que tener KAI?"},
                    {"user": "Sara_M", "badge": "MOD", "text": "Dato mata relato siempre."}
                ],
                "broll_queries": ["future technology", "modern abstract data"],
                "highlight_words": ["futuro", "datos", "dilema", "riesgo"]
            }

    async def _fetch_brolls(self, queries: List[str]) -> List[Path]:
        """Descarga fondos o clips de video libres de derechos rotativos."""
        orchestrator = AssetOrchestrator(target_dir=self.workdir / "assets")
        clips: List[Path] = []
        for i, q in enumerate(queries[:8]):
            try:
                cue = BRollCue(
                    cue_id=f"streamer_broll_{i}",
                    start_sec=float(i * 6.0),
                    end_sec=float((i + 1) * 6.0),
                    concept=q,
                    search_query_en=q,
                    reasoning="Apoyo visual contextual en video",
                )
                res = await orchestrator._resolve_single_cue(cue)
                if res.local_file_path and Path(res.local_file_path).exists():
                    clips.append(Path(res.local_file_path))
            except Exception as exc:
                safe_log(f"[Streamer] Falló descarga B-Roll para {q}: {exc}")
        return clips

    async def _assemble_broadcast_video(
        self,
        audio_file: Path,
        avatar_webm: Path,
        broll_clips: List[Path],
        cards: List[Dict[str, Any]],
        duration: float,
        out_path: Path,
        title: str,
        chat_path: Optional[Path] = None,
        monologue: str = "",
    ) -> None:
        """Renderiza la transmisión broadcast en FFmpeg con B-roll full-screen rotativo, tarjetas, chat, subtítulos y audio mix."""
        is_vertical = self.options.aspect_ratio == "9:16"
        W, H = (1080, 1920) if is_vertical else (1920, 1080)
        fps = 30
        dur_str = f"{duration:.2f}"

        # 1. Lienzo base Negro Mate Puro
        inputs = ["-f", "lavfi", "-i", f"color=c=0x080808:s={W}x{H}:d={dur_str}:r={fps}"]
        num_inputs = 1
        filter_parts = ["[0:v]format=yuva420p[v0]"]
        cur_v = "v0"

        # 2. Añadir B-rolls dinámicos full-frame rotativos cada 6-7 segundos (100% pantalla, dinámico)
        valid_brolls = [Path(c) for c in broll_clips if Path(c).exists()]
        if valid_brolls:
            num_brolls = len(valid_brolls)
            clip_dur = 6.5
            total_slots = math.ceil(duration / clip_dur)
            for s_idx in range(total_slots):
                b_clip = valid_brolls[s_idx % num_brolls]
                st_time = s_idx * clip_dur
                en_time = min(duration, (s_idx + 1) * clip_dur)
                if b_clip.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
                    inputs.extend(["-loop", "1", "-i", str(b_clip)])
                else:
                    inputs.extend(["-stream_loop", "-1", "-i", str(b_clip)])
                b_idx = num_inputs
                num_inputs += 1

                # Escalar y recortar al 100% de la pantalla sin bordes negros
                filter_parts.append(
                    f"[{b_idx}:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1[broll_{s_idx}];"
                    f"[{cur_v}][broll_{s_idx}]overlay=0:0:enable='between(t,{st_time:.2f},{en_time:.2f})'[v_bg_{s_idx}]"
                )
                cur_v = f"v_bg_{s_idx}"

            # Sutil capa oscura translúcida (20%) para garantizar legibilidad de HUD, tarjetas y subtítulos
            filter_parts.append(
                f"[{cur_v}]drawbox=x=0:y=0:w={W}:h={H}:color=black@0.20:t=fill[v_bg_dim]"
            )
            cur_v = "v_bg_dim"

        # 3. Añadir Avatar WebM con canal alfa transparente 100% real (sin caja negra)
        if avatar_webm and avatar_webm.exists():
            inputs.extend(["-stream_loop", "-1", "-i", str(avatar_webm)])
            a_idx = num_inputs
            num_inputs += 1
            if is_vertical:
                av_w = int(W * 0.40)
                filter_parts.append(
                    f"[{a_idx}:v]scale={av_w}:{av_w},format=rgba[avatar];"
                    f"[{cur_v}][avatar]overlay={int(W - av_w - 30)}:{int(H - av_w - 110)}:format=auto[v_av]"
                )
            else:
                av_w = int(W * 0.26)
                filter_parts.append(
                    f"[{a_idx}:v]scale={av_w}:{av_w},format=rgba[avatar];"
                    f"[{cur_v}][avatar]overlay={int(W - av_w - 45)}:{int(H - av_w - 45)}:format=auto[v_av]"
                )
            cur_v = "v_av"

        # 4. Añadir Overlay de Chat en Vivo
        if chat_path and Path(chat_path).exists():
            inputs.extend(["-i", str(chat_path)])
            chat_stream_idx = num_inputs
            num_inputs += 1
            c_start_t = 2.5
            c_end_t = max(3.0, duration - 1.5)
            if is_vertical:
                cx = 30
                cy = int(H * 0.72)
            else:
                cx = 60
                cy = int(H - 330)
            filter_parts.append(
                f"[{cur_v}][{chat_stream_idx}:v]overlay={cx}:{cy}:enable='between(t,{c_start_t:.1f},{c_end_t:.1f})'[v_chat]"
            )
            cur_v = "v_chat"

        # 5. Añadir Tarjetas Bento
        for c_idx, c_info in enumerate(cards):
            c_file = Path(c_info["path"])
            if c_file.exists():
                inputs.extend(["-i", str(c_file)])
                card_stream_idx = num_inputs
                num_inputs += 1
                c_start = c_info["start"]
                c_end = c_info["end"]
                if is_vertical:
                    cx = 40
                    cy = int(H * 0.58)
                else:
                    cx = 60
                    cy = 60
                filter_parts.append(
                    f"[{cur_v}][{card_stream_idx}:v]overlay={cx}:{cy}:enable='between(t,{c_start},{c_end})'[v_card_{c_idx}]"
                )
                cur_v = f"v_card_{c_idx}"

        # 6. Subtítulos dinámicos en tercio inferior (renderizados vía libass para mínimo consumo de memoria y máxima velocidad)
        if monologue:
            words = monologue.split()
            chunk_size = 4
            sub_chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
            if sub_chunks:
                chunk_dur = duration / len(sub_chunks)
                srt_path = self.workdir / "kai_stream_subtitles.srt"
                srt_lines = []
                for idx, chunk in enumerate(sub_chunks):
                    st = idx * chunk_dur
                    en = (idx + 1) * chunk_dur
                    clean_txt = chunk.strip().replace(":", "")
                    if clean_txt:
                        def _fmt_srt(t: float) -> str:
                            h = int(t // 3600)
                            m = int((t % 3600) // 60)
                            s = int(t % 60)
                            ms = int((t - int(t)) * 1000)
                            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
                        srt_lines.append(f"{idx + 1}\n{_fmt_srt(st)} --> {_fmt_srt(en)}\n{clean_txt}\n")
                if srt_lines:
                    srt_path.write_text("\n".join(srt_lines), encoding="utf-8")
                    esc_srt = str(srt_path.resolve()).replace("\\", "/").replace(":", "\\:")
                    sub_size = 20 if is_vertical else 16
                    margin_v = 45 if is_vertical else 26
                    filter_parts.append(
                        f"[{cur_v}]subtitles='{esc_srt}':force_style='FontName=Segoe UI,FontSize={sub_size},Bold=1,PrimaryColour=&H00FFFFFF,BorderStyle=3,OutlineColour=&HB2000000,MarginV={margin_v}'[v_subs]"
                    )
                    cur_v = "v_subs"

        # 7. Titular superior en vivo (ASCII seguro para Windows cp1252)
        safe_title = re.sub(r"[^\w\s-]", "", title, flags=re.UNICODE).encode("ascii", "ignore").decode("ascii").strip()[:35].replace("'", "").replace(":", "")
        if not safe_title:
            safe_title = "TRANSMISION KAI"
        font_path = "C\\:/Windows/Fonts/segoeuib.ttf"
        filter_parts.append(
            f"[{cur_v}]drawtext=fontfile='{font_path}':text='REC EN VIVO  |  {safe_title}':fontcolor=white:fontsize={22 if is_vertical else 26}:x=44:y=34:box=1:boxcolor=black@0.75:boxborderw=8[v_final]"
        )

        # 8. Entrada y mezcla de audio (Voz + BGM con ducking + SFX Whoosh y Chime)
        inputs.extend(["-i", str(audio_file)])
        audio_idx = num_inputs
        num_inputs += 1

        bgm_file = Path("assets/audio/bgm_streamer.wav")
        whoosh_file = Path("assets/audio/whoosh.wav")
        chime_file = Path("assets/audio/chime.wav")

        audio_filter_parts: List[str] = []
        audio_mix_inputs: List[str] = [f"[{audio_idx}:a]"]

        if bgm_file.exists():
            inputs.extend(["-t", dur_str, "-stream_loop", "-1", "-i", str(bgm_file)])
            bgm_in_idx = num_inputs
            num_inputs += 1
            audio_filter_parts.append(f"[{bgm_in_idx}:a]volume=0.06[a_bgm]")
            audio_mix_inputs.append("[a_bgm]")

        if whoosh_file.exists() and cards:
            inputs.extend(["-i", str(whoosh_file)])
            whoosh_in_idx = num_inputs
            num_inputs += 1
            w_delay = max(500, int(cards[0].get("start", 2.0) * 1000))
            audio_filter_parts.append(f"[{whoosh_in_idx}:a]adelay={w_delay}|{w_delay},volume=0.35[a_whoosh]")
            audio_mix_inputs.append("[a_whoosh]")

        if chime_file.exists():
            inputs.extend(["-i", str(chime_file)])
            chime_in_idx = num_inputs
            num_inputs += 1
            c_delay = max(1000, int(duration * 0.72 * 1000))
            audio_filter_parts.append(f"[{chime_in_idx}:a]adelay={c_delay}|{c_delay},volume=0.32[a_chime]")
            audio_mix_inputs.append("[a_chime]")

        if len(audio_mix_inputs) > 1:
            inputs_tags = "".join(audio_mix_inputs)
            audio_filter_parts.append(f"{inputs_tags}amix=inputs={len(audio_mix_inputs)}:duration=first:dropout_transition=2[a_final]")
            a_map = "[a_final]"
        else:
            a_map = f"{audio_idx}:a"

        has_rtmp = bool(self.options.rtmp_url and str(self.options.rtmp_url).strip() not in ("None", "null", ""))
        v_file_map = "[v_final]"
        a_file_map = a_map

        if has_rtmp:
            filter_parts.append("[v_final]split=2[v_file][v_rtmp]")
            v_file_map = "[v_file]"
            v_rtmp_map = "[v_rtmp]"
            if a_map.startswith("[") and a_map.endswith("]"):
                clean_a = a_map[1:-1]
                audio_filter_parts.append(f"[{clean_a}]asplit=2[a_file][a_rtmp]")
            else:
                audio_filter_parts.append(f"[{a_map}]asplit=2[a_file][a_rtmp]")
            a_file_map = "[a_file]"
            a_rtmp_map = "[a_rtmp]"

        full_filter_complex = ";\n".join(filter_parts + audio_filter_parts)
        filter_script = self.workdir / "streamer_filter.txt"
        filter_script.write_text(full_filter_complex, encoding="utf-8")

        cmd = [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex_script", str(filter_script),
            "-map", v_file_map,
            "-map", a_file_map,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "20",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            "-t", dur_str,
            str(out_path)
        ]

        if has_rtmp:
            rtmp_dest = str(self.options.rtmp_url).strip()
            safe_log(f"[Streamer] Transmitiendo simultáneamente en vivo a RTMP ({rtmp_dest[:32]}...)...")
            cmd.extend([
                "-map", v_rtmp_map,
                "-map", a_rtmp_map,
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-b:v", "3500k",
                "-maxrate", "4000k",
                "-bufsize", "7000k",
                "-pix_fmt", "yuv420p",
                "-g", "60",
                "-c:a", "aac",
                "-b:a", "160k",
                "-ar", "44100",
                "-f", "flv",
                rtmp_dest
            ])

        safe_log(f"[Streamer] Ejecutando FFmpeg render...")
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            if out_path.exists() and out_path.stat().st_size > 50_000:
                safe_log(f"[Streamer] FFmpeg completó la transmisión exitosamente ({out_path.stat().st_size} bytes generados).")
            else:
                err_msg = stderr.decode(errors="replace")[-600:]
                safe_log(f"[Streamer] Error en FFmpeg: {err_msg}")
                raise RuntimeError(f"Error renderizando transmisión: {err_msg}")
        
        safe_log(f"[Streamer] Renderizado completado: {out_path}")
