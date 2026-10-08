import asyncio
import io
import json
import re
import subprocess
import sys
import threading
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import aiofiles
from fastapi import FastAPI, Body, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from config.settings import settings
from cancellation import CancellationRequested
from core.avatar_narrator import DEFAULT_VOICE
from core.llm import safe_log
from core.models import VideoEditingPlan
from core.pipeline import PipelineOptions, VideoPipeline
from core.project_store import ProjectStore, editor_snapshot
from core.render_engine import VideoRenderEngine
from core.streamer_pipeline import StreamerOptions, StreamerPipeline
from core.timeline import TimelineMapper
from utils.file_manager import FileManager

app = FastAPI(title="AetherCut AI Video Editor")

WEB_DIR = Path(__file__).resolve().parent / "web"
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"

ALLOWED_EXT = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
MAX_UPLOAD_MB = 2048


class NoCacheStaticFiles(StaticFiles):
    """Evita que el navegador sirva CSS/JS antiguos tras cambios de diseño."""
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        return response


app.mount("/static", NoCacheStaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/media", StaticFiles(directory=str(settings.OUTPUTS_DIR)), name="media")
app.mount("/storage", StaticFiles(directory=str(settings.STORAGE_DIR)), name="storage")
app.mount("/assets", StaticFiles(directory=str(Path(__file__).resolve().parent / "assets")), name="assets")

tasks_progress: Dict[str, Dict[str, Any]] = {}
task_cancel_events: Dict[str, threading.Event] = {}
task_pipelines: Dict[str, VideoPipeline] = {}
task_jobs: Dict[str, asyncio.Task] = {}
_state_lock = threading.RLock()
_render_lock = asyncio.Lock()  # un render FFmpeg a la vez: protege CPU/GPU y memoria


@app.on_event("startup")
async def recover_orphaned_inputs() -> None:
    """Convierte cargas de un servidor interrumpido en proyectos recuperables."""
    import time
    defaults = {"silence_threshold": 1.5, "broll": True, "cards": True, "captions": False, "shorts": True}
    if not settings.INPUTS_DIR.exists():
        return
    for source in settings.INPUTS_DIR.iterdir():
        if not source.is_file():
            continue
        match = re.match(r"^([a-f0-9]{8})_", source.name, re.I)
        if not match:
            continue
        # Solo recuperar archivos modificados en las últimas 24 horas
        if time.time() - source.stat().st_mtime > 86400:
            continue
        project = ProjectStore(match.group(1))
        if project.manifest_path.exists():
            continue
        project.create(source_file=source, original_name=source.name.split("_", 1)[-1], options=defaults)
        project.set_status("recovered", message="Carga conservada tras reiniciar el servidor.")


def friendly_error(exc: Exception) -> str:
    text = str(exc)
    for key in settings.GEMINI_API_KEY.split(","):
        if key.strip():
            text = text.replace(key.strip(), "[clave oculta]")
    low = text.lower()
    if "429" in text or "quota" in low or "resource_exhausted" in low:
        return "Gemini alcanzó un límite de cuota en los proyectos configurados. Revisa su uso en AI Studio e inténtalo cuando alguno vuelva a estar disponible."
    if "503" in text or "unavailable" in low:
        return "Los modelos de Gemini están saturados en este momento. Inténtalo de nuevo en un minuto."
    if "api key" in low or "401" in text or "unauthenticated" in low:
        return "La clave de Gemini no es válida. Revisa GEMINI_API_KEY en el archivo .env."
    if "ffmpeg" in low:
        return "FFmpeg falló al procesar el video. Prueba con otro archivo o formato (MP4 recomendado)."
    return text[:300]


def update_task_state(task_id: str, step: str, progress: float, message: str, **extra: Any) -> None:
    with _state_lock:
        state = tasks_progress.get(task_id)
        if state is not None:
            # Los latidos solo confirman que el worker continúa esperando una
            # operación externa. No son una acción nueva y no deben llenar la
            # actividad ni fingir una respuesta de Gemini.
            heartbeat = bool(extra.pop("heartbeat", False))
            if heartbeat:
                state.update({
                    "heartbeat_at": datetime.now(timezone.utc).isoformat(),
                    "waiting_seconds": int(extra.pop("waiting_seconds", 0)),
                    **extra,
                })
                return
            if state.get("cancel_requested") and step not in {"cancelling", "cancelled"}:
                step = "cancelling"
                progress = state.get("progress", progress)
                message = state.get("message", "Cancelación solicitada.")
            now = datetime.now(timezone.utc).isoformat()
            changed = step != state.get("step") or message != state.get("message")
            if step != state.get("step"):
                state["step_started_at"] = now
            state.update({"step": step, "progress": max(progress, state.get("progress", 0.0)),
                          "message": message, "updated_at": now, **extra})
            if changed:
                events = state.setdefault("events", [])
                events.append({"step": step, "progress": state["progress"], "message": message, "at": now})
                del events[:-80]
            try:
                # Persistir progreso activo en el almacén del proyecto para que la recarga de página no lo pierda
                p_store = ProjectStore(task_id)
                if p_store.manifest_path.exists():
                    doc = p_store.read()
                    doc["current_progress"] = {
                        "step": state.get("step"),
                        "progress": state.get("progress"),
                        "message": state.get("message"),
                        "completed": state.get("completed", False),
                        "error": state.get("error"),
                        "result": state.get("result"),
                        "file_name": state.get("file_name"),
                        "cancel_supported": state.get("cancel_supported", True),
                        "live_scenes": state.get("live_scenes"),
                        "events": state.get("events"),
                    }
                    p_store.write(doc)
            except Exception:
                pass


def cleanup_cancelled_task_files(task_id: str, input_file: Path) -> None:
    # El proyecto se conserva para poder revisar el material, las fuentes y la
    # línea de tiempo después de cancelar. Solo se limpian exportaciones
    # incompletas que pertenezcan a la tarea.
    for path in settings.OUTPUTS_DIR.glob(f"{task_id}_*"):
        if path.is_file():
            path.unlink(missing_ok=True)


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    async with aiofiles.open(TEMPLATES_DIR / "index.html", mode="r", encoding="utf-8") as f:
        return HTMLResponse(content=await f.read())


async def run_pipeline_task(task_id: str, input_file: Path, options: PipelineOptions) -> None:
    update_task_state(task_id, "init", 5.0, "Iniciando análisis del video...")
    cancel_event = task_cancel_events[task_id]
    project = ProjectStore(task_id)
    project.set_status("running")
    try:
        pipeline = VideoPipeline(
            task_id, input_file, options,
            on_state=lambda step, pct, msg, **kw: update_task_state(task_id, step, pct, msg, **kw),
            cancel_event=cancel_event,
            project_store=project,
            render_lock=_render_lock,
        )
        task_pipelines[task_id] = pipeline
        if cancel_event.is_set():
            raise CancellationRequested()
        result = await pipeline.run()
        if cancel_event.is_set():
            raise CancellationRequested()
        update_task_state(task_id, "done", 100.0, "Edición completada.", completed=True, result=result)
        project.set_status("done", result=result)
    except CancellationRequested:
        update_task_state(task_id, "cancelled", tasks_progress.get(task_id, {}).get("progress", 0.0),
                          "Edición cancelada.", completed=True, cancelled=True,
                          cancel_requested=False)
        cleanup_cancelled_task_files(task_id, input_file)
        project.set_status("cancelled")
    except Exception as exc:
        safe_log(f"[Pipeline] Error: {exc}")
        state = tasks_progress.get(task_id, {})
        update_task_state(task_id, "error", state.get("progress", 0.0), "La edición se detuvo.",
                          error=friendly_error(exc), failed_step=state.get("step"))
        project.set_status("error", error=friendly_error(exc))
    finally:
        task_pipelines.pop(task_id, None)
        task_cancel_events.pop(task_id, None)
        task_jobs.pop(task_id, None)

    # conserva solo las últimas 20 tareas en memoria
    for old in list(tasks_progress)[:-20]:
        tasks_progress.pop(old, None)


async def run_export_task(task_id: str) -> None:
    """Renderiza un proyecto guardado sin repetir Gemini ni búsquedas web."""
    acquired = False
    cancel_event = task_cancel_events[task_id]
    store = ProjectStore(task_id)
    try:
        if _render_lock.locked():
            update_task_state(task_id, "queued", 5.0, "En cola de render: esperando que termine la codificación actual...")
        await _render_lock.acquire()
        acquired = True
        document = store.read()
        source = Path(document.get("source_file") or "")
        if not source.exists():
            raise FileNotFoundError("No se encontró el video original para exportar.")
        plan = store.load_plan()
        duration = float(FileManager.get_media_metadata(source, cancel_event).get("duration") or 0)
        if duration <= 0:
            raise RuntimeError("No se pudo leer la duración del video original.")
        mapper = TimelineMapper.from_plan_segments(plan.timeline, duration)
        revision = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        output = settings.OUTPUTS_DIR / f"{task_id}_edit_{revision}.mp4"
        engine = VideoRenderEngine(fps=settings.DEFAULT_VIDEO_FPS, cancel_event=cancel_event)

        def progress(message: str, fraction: float) -> None:
            update_task_state(task_id, "render", 10.0 + 85.0 * fraction, message)

        # Preparar Avatar Copilot para las tarjetas si no existen aún
        from core.avatar_narrator import AvatarNarrator
        from core.avatar_renderer import AvatarRenderer
        narrator = AvatarNarrator()
        avatar_rnd = AvatarRenderer(badge_size=320)
        for card in plan.info_cards:
            if card.enabled and card.verdict in ("supported", "contradicted", "insufficient"):
                if not getattr(card, "avatar_video_path", None) or not Path(card.avatar_video_path).exists():
                    try:
                        if not card.avatar_spoken_text:
                            surrounding_context = ""
                            if plan.captions:
                                chunks = [
                                    c.text for c in plan.captions
                                    if (card.start_sec - 14.0) <= c.start_sec <= (card.start_sec + 4.0)
                                ]
                                surrounding_context = " ".join(chunks).strip()
                            card.avatar_spoken_text = await narrator.craft_dialogue_with_ai(
                                card, surrounding_context=surrounding_context
                            )
                        audio_file = store.workdir / f"{card.card_id}_voice.mp3"
                        _p, dur = await narrator.synthesize(card.avatar_spoken_text, audio_file)
                        card.avatar_audio_path = str(audio_file)
                        video_file = store.workdir / f"{card.card_id}_avatar.webm"
                        rendered = avatar_rnd.render_reaction_clip(dur + 0.5, video_file, audio_path=audio_file)
                        if rendered:
                            card.avatar_video_path = str(rendered)
                            card.avatar_enabled = True
                            card.display_duration_sec = max(card.display_duration_sec, dur + 1.0)
                    except Exception as exc:
                        safe_log(f"[Export] Avatar en reexportación: {exc}")

        update_task_state(task_id, "render", 8.0, "Reexportando el proyecto guardado con tus cambios.")
        loop = asyncio.get_running_loop()
        render_info = await loop.run_in_executor(
            None,
            lambda: engine.render(source, plan, mapper, store.workdir / "reexports" / revision, output,
                                  (lambda _cut: mapper.remap_captions(plan.captions)) if plan.captions else None,
                                  progress),
        )
        if cancel_event.is_set():
            raise CancellationRequested()
        result = dict(document.get("result") or {})
        result.update({
            "master_video_url": f"/media/{output.name}",
            "cards_shown": sum(1 for item in render_info["overlays"] if item["kind"] == "card"),
            "brolls_count": sum(1 for item in render_info["overlays"] if item["kind"] != "card"),
            "captions_count": render_info["captions"],
        })
        store.set_status("done", result=result)
        update_task_state(task_id, "done", 100.0, "Nueva versión exportada.", completed=True, result=result)
    except CancellationRequested:
        store.set_status("ready_for_export")
        update_task_state(task_id, "cancelled", tasks_progress.get(task_id, {}).get("progress", 0.0),
                          "Exportación cancelada.", completed=True, cancelled=True)
    except Exception as exc:
        safe_log(f"[Export] Error: {exc}")
        store.set_status("ready_for_export", error=friendly_error(exc))
        update_task_state(task_id, "error", tasks_progress.get(task_id, {}).get("progress", 0.0),
                          "La exportación se detuvo.", error=friendly_error(exc))
    finally:
        if acquired:
            _render_lock.release()
        task_cancel_events.pop(task_id, None)
        task_jobs.pop(task_id, None)


@app.post("/api/process-video")
async def process_video(
    video: UploadFile = File(...),
    silence_threshold: float = Form(1.5),
    enable_broll: bool = Form(True),
    enable_captions: bool = Form(True),
    enable_shorts: bool = Form(True),
    enable_cards: bool = Form(True),
):
    ext = Path(video.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail=f"Formato no soportado ({ext or 'sin extensión'}). Usa MP4, MOV, MKV o WEBM.")

    task_id = uuid.uuid4().hex[:8]
    clean = re.sub(r"[^a-zA-Z0-9_-]", "_", Path(video.filename).stem)[:60]
    saved = settings.INPUTS_DIR / f"{task_id}_{clean}{ext}"

    # Escritura por bloques: un video de cientos de MB no se carga entero en memoria.
    written, limit = 0, MAX_UPLOAD_MB * 1024 * 1024
    async with aiofiles.open(saved, "wb") as out:
        while chunk := await video.read(4 * 1024 * 1024):
            written += len(chunk)
            if written > limit:
                await out.close()
                saved.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail=f"El archivo supera {MAX_UPLOAD_MB} MB.")
            await out.write(chunk)

    now = datetime.now(timezone.utc).isoformat()
    tasks_progress[task_id] = {
        "step": "init", "progress": 5.0, "message": "Archivo recibido. Iniciando...",
        "completed": False, "error": None, "result": None, "cancel_supported": True,
        "file_name": Path(video.filename or "video").name,
        "created_at": now, "updated_at": now, "step_started_at": now,
        "events": [{"step": "init", "progress": 5.0, "message": "Archivo recibido. Iniciando...", "at": now}],
    }
    options = PipelineOptions(
        silence_threshold=max(0.8, min(3.0, silence_threshold)),
        broll=enable_broll, captions=enable_captions, shorts=enable_shorts, cards=enable_cards,
    )
    ProjectStore(task_id).create(
        source_file=saved,
        original_name=Path(video.filename or "video").name,
        options={
            "silence_threshold": options.silence_threshold,
            "broll": options.broll,
            "cards": options.cards,
            "captions": options.captions,
            "shorts": options.shorts,
        },
    )
    task_cancel_events[task_id] = threading.Event()
    task_jobs[task_id] = asyncio.create_task(run_pipeline_task(task_id, saved, options))
    return {"task_id": task_id, "project_id": task_id}


async def run_streamer_task(task_id: str, options: StreamerOptions) -> None:
    update_task_state(task_id, "research", 10.0, f"Investigando datos web sobre «{options.topic}»...")
    cancel_event = task_cancel_events[task_id]
    project = ProjectStore(task_id)
    project.set_status("running")
    try:
        pipeline = StreamerPipeline(
            task_id, options,
            on_state=lambda step, pct, msg, **kw: update_task_state(task_id, step, pct, msg, **kw),
            cancel_event=cancel_event,
            project_store=project,
            render_lock=_render_lock,
        )
        if cancel_event.is_set():
            raise CancellationRequested()
        result = await pipeline.run()
        if cancel_event.is_set():
            raise CancellationRequested()
        update_task_state(task_id, "done", 100.0, "¡Transmisión completada!", completed=True, result=result)
        project.set_status("done", result=result)
    except (CancellationRequested, asyncio.CancelledError):
        update_task_state(task_id, "cancelled", tasks_progress.get(task_id, {}).get("progress", 0.0),
                          "Transmisión cancelada.", completed=True, cancelled=True)
        project.set_status("cancelled")
    except Exception as exc:
        safe_log(f"[StreamerTask] Error: {exc}")
        state = tasks_progress.get(task_id, {})
        update_task_state(task_id, "error", state.get("progress", 0.0), "La transmisión se detuvo.",
                          error=friendly_error(exc), failed_step=state.get("step"))
        project.set_status("error", error=friendly_error(exc))
    finally:
        task_cancel_events.pop(task_id, None)
        task_jobs.pop(task_id, None)


@app.post("/api/streamer/create")
async def create_streamer_broadcast(payload: Dict[str, Any] = Body(...)):
    topic = str(payload.get("topic", "")).strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Debes indicar un tema para la transmisión.")
    style = str(payload.get("style", "divulgacion")).strip()
    duration_sec = int(payload.get("duration_sec", 45))
    aspect_ratio = str(payload.get("aspect_ratio", "16:9")).strip()
    card_theme = str(payload.get("card_theme", "dark")).strip()
    voice = str(payload.get("voice", DEFAULT_VOICE)).strip()
    raw_rtmp = payload.get("rtmp_url")
    rtmp_url = str(raw_rtmp).strip() if (raw_rtmp and str(raw_rtmp).strip() not in ("None", "null", "")) else None

    task_id = uuid.uuid4().hex[:8]
    now = datetime.now(timezone.utc).isoformat()
    tasks_progress[task_id] = {
        "step": "research", "progress": 10.0, "message": f"Investigando «{topic}» en la web...",
        "completed": False, "error": None, "result": None, "cancel_supported": True,
        "file_name": f"KAI Stream: {topic[:35]}",
        "created_at": now, "updated_at": now, "step_started_at": now,
        "events": [{"step": "research", "progress": 10.0, "message": f"Investigando «{topic}»...", "at": now}],
    }
    options = StreamerOptions(
        topic=topic,
        style=style,
        duration_sec=duration_sec,
        aspect_ratio=aspect_ratio,
        card_theme=card_theme,
        voice=voice,
        rtmp_url=rtmp_url,
    )
    store = ProjectStore(task_id)
    store.create(
        source_file=settings.OUTPUTS_DIR / f"{task_id}_master.mp4",
        original_name=f"KAI Stream: {topic}",
        options={"topic": topic, "style": style, "duration_sec": duration_sec, "mode": "streamer"}
    )
    task_cancel_events[task_id] = threading.Event()
    task_jobs[task_id] = asyncio.create_task(run_streamer_task(task_id, options))
    return {"task_id": task_id, "project_id": task_id}


@app.post("/api/projects/{task_id}/resume")
async def resume_project(task_id: str):
    """Reanuda un proyecto interrumpido (Streamer o Co-Piloto) sin perder escenas ya grabadas."""
    if task_id in task_jobs:
        raise HTTPException(status_code=409, detail="Este proyecto ya está procesándose.")
    store = ProjectStore(task_id)
    try:
        document = store.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="No se encontró el proyecto.")

    raw_options = document.get("options") or {}
    now = datetime.now(timezone.utc).isoformat()

    # Si es una transmisión de KAI Streamer
    if raw_options.get("mode") == "streamer" or (document.get("original_name") or "").startswith("KAI Stream"):
        topic = raw_options.get("topic") or (document.get("result") or {}).get("topic") or document.get("original_name", "").replace("KAI Stream: ", "")
        options = StreamerOptions(
            topic=topic,
            style=raw_options.get("style", "divulgacion"),
            duration_sec=int(raw_options.get("duration_sec", 45)),
            aspect_ratio=raw_options.get("aspect_ratio", "16:9"),
            card_theme=raw_options.get("card_theme", "dark"),
            voice=raw_options.get("voice", DEFAULT_VOICE),
            rtmp_url=raw_options.get("rtmp_url"),
        )
        tasks_progress[task_id] = {
            "step": "render", "progress": 50.0, "message": f"Reanudando transmisión de «{topic}»...",
            "completed": False, "error": None, "result": None, "cancel_supported": True,
            "file_name": document.get("original_name", f"KAI Stream {task_id}"),
            "created_at": document.get("created_at", now), "updated_at": now, "step_started_at": now,
            "events": [{"step": "render", "progress": 50.0, "message": "Reanudando transmisión desde escenas guardadas...", "at": now}],
        }
        task_cancel_events[task_id] = threading.Event()
        task_jobs[task_id] = asyncio.create_task(run_streamer_task(task_id, options))
        return {"task_id": task_id, "message": f"Transmisión «{topic}» reanudada con éxito."}

    # Si es video co-piloto
    source = Path(document.get("source_file") or "")
    if not source.exists():
        raise HTTPException(status_code=410, detail="No se encontró el video original para reanudar este proyecto.")
    options = PipelineOptions(
        silence_threshold=max(0.8, min(3.0, float(raw_options.get("silence_threshold", 1.5)))),
        broll=bool(raw_options.get("broll", True)), cards=bool(raw_options.get("cards", True)),
        captions=bool(raw_options.get("captions", False)), shorts=bool(raw_options.get("shorts", True)),
    )
    tasks_progress[task_id] = {
        "step": "queued", "progress": 5.0, "message": "Reanudando la carga conservada.",
        "completed": False, "error": None, "result": None, "cancel_supported": True,
        "file_name": document.get("original_name", source.name), "created_at": now,
        "updated_at": now, "step_started_at": now,
        "events": [{"step": "queued", "progress": 5.0, "message": "Reanudando la carga conservada.", "at": now}],
    }
    task_cancel_events[task_id] = threading.Event()
    task_jobs[task_id] = asyncio.create_task(run_pipeline_task(task_id, source, options))
    return {"task_id": task_id, "message": "El proyecto se reanudó con el archivo ya guardado."}


@app.get("/api/projects/{task_id}")
async def get_project(task_id: str):
    try:
        document = ProjectStore(task_id).read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="No se encontró el proyecto.")
    plan_data = document.get("plan")
    editor = editor_snapshot(VideoEditingPlan.model_validate(plan_data)) if plan_data else None

    # Asegurar compatibilidad de URLs del video editado
    if document.get("result") and isinstance(document["result"], dict):
        res = document["result"]
        if "media_url" in res and "master_video_url" not in res:
            res["master_video_url"] = res["media_url"]
        if "master_video_url" in res and "media_url" not in res:
            res["media_url"] = res["master_video_url"]

    # No se exponen rutas del equipo local a la interfaz.
    public = {key: value for key, value in document.items() if key not in {"source_file", "preview_file", "plan"}}
    return {"project": public, "editor": editor}


@app.get("/api/projects")
async def list_projects():
    projects = []
    for manifest in settings.PROJECTS_DIR.glob("*/project.json"):
        try:
            document = json.loads(manifest.read_text(encoding="utf-8"))
            pid = document.get("id")
            result = document.get("result") or {}
            
            # Detectar thumbnail si existe
            thumbnail_url = None
            thumb_path = settings.OUTPUTS_DIR / f"{pid}_thumbnail.jpg"
            if thumb_path.exists():
                thumbnail_url = f"/media/{pid}_thumbnail.jpg"
            else:
                # Comprobar b-roll o escena de trabajo si existe en storage/projects
                work_thumb = settings.PROJECTS_DIR / pid / "work" / "streamer_card_0.png"
                if work_thumb.exists():
                    thumbnail_url = f"/storage/projects/{pid}/work/streamer_card_0.png"
                else:
                    broll = next((settings.PROJECTS_DIR / pid / "work" / "assets").glob("*.jpg"), None) if (settings.PROJECTS_DIR / pid / "work" / "assets").exists() else None
                    if broll:
                        thumbnail_url = f"/storage/projects/{pid}/work/assets/{broll.name}"

            duration = result.get("duration") or 0.0
            topic = result.get("topic") or (document.get("options") or {}).get("topic") or ""

            projects.append({
                "id": pid,
                "name": document.get("original_name") or result.get("title") or "Video sin nombre",
                "status": document.get("status", "unknown"),
                "updated_at": document.get("updated_at"),
                "has_plan": bool(document.get("plan")),
                "has_result": bool(document.get("result")),
                "duration": duration,
                "topic": topic,
                "thumbnail_url": thumbnail_url,
                "master_video_url": result.get("master_video_url") or result.get("media_url")
            })
        except (OSError, json.JSONDecodeError):
            continue
    projects.sort(key=lambda project: project.get("updated_at") or "", reverse=True)
    return {"projects": projects[:50]}


@app.delete("/api/projects/{task_id}")
async def delete_project(task_id: str):
    """Elimina un proyecto y libera espacio en disco."""
    if task_id in task_jobs:
        raise HTTPException(status_code=409, detail="No se puede eliminar un proyecto en ejecución. Cancélalo primero.")
    store = ProjectStore(task_id)
    if not store.root.exists() and not store.manifest_path.exists():
        raise HTTPException(status_code=404, detail="No se encontró el proyecto.")
    report = store.delete(include_source=True, include_outputs=True)
    tasks_progress.pop(task_id, None)
    return {"message": "Proyecto eliminado.", "freed_mb": round(report["freed_bytes"] / 1024 / 1024, 2)}


@app.post("/api/cleanup")
async def trigger_storage_cleanup():
    """Limpia archivos temporales, duplicados de uploads antiguos y libera espacio en disco."""
    report = FileManager.cleanup_storage()
    return {"message": "Limpieza completada con éxito.", **report}


@app.get("/api/projects/{task_id}/preview")
async def get_project_preview(task_id: str):
    store = ProjectStore(task_id)
    try:
        document = store.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="No se encontró el proyecto.")
    
    path = Path(document.get("preview_file") or "")
    if not path.exists() or not path.is_file():
        src_path = Path(document.get("source_file") or "")
        if src_path.exists() and src_path.is_file():
            path = src_path
        else:
            master_file = settings.OUTPUTS_DIR / f"{task_id}_master.mp4"
            if master_file.exists():
                path = master_file
            else:
                res = document.get("result") or {}
                out_path = Path(res.get("output_file") or "")
                if out_path.exists() and out_path.is_file():
                    path = out_path
                else:
                    raise HTTPException(status_code=404, detail="La previsualización todavía no está lista.")

    title = document.get("original_name") or (document.get("result") or {}).get("title") or f"KAI_{task_id}"
    safe_title = re.sub(r"[^\w\s-]", "", title, flags=re.UNICODE).strip().replace(" ", "_")[:50] or f"KAI_{task_id}"
    filename = f"{safe_title}.mp4"

    return FileResponse(
        path=path,
        media_type="video/mp4",
        filename=filename,
        headers={"Content-Disposition": f'inline; filename="{filename}"'}
    )


@app.get("/api/projects/{task_id}/download")
async def download_project_master(task_id: str):
    """Descarga el video final con nombre descriptivo y extensión .mp4 garantizada."""
    store = ProjectStore(task_id)
    try:
        document = store.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="No se encontró el proyecto.")

    master_file = settings.OUTPUTS_DIR / f"{task_id}_master.mp4"
    if not master_file.exists():
        res = document.get("result") or {}
        candidate = Path(res.get("output_file") or "")
        if candidate.exists() and candidate.is_file():
            master_file = candidate
        else:
            prev = Path(document.get("preview_file") or "")
            if prev.exists() and prev.is_file():
                master_file = prev
            else:
                raise HTTPException(status_code=404, detail="El video master todavía no está generado.")

    title = document.get("original_name") or (document.get("result") or {}).get("title") or "KAI_Broadcast"
    safe_title = re.sub(r"[^\w\s-]", "", title, flags=re.UNICODE).strip().replace(" ", "_")[:50] or f"KAI_{task_id}"
    filename = f"{safe_title}.mp4"

    return FileResponse(
        path=master_file,
        media_type="video/mp4",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )





@app.get("/api/projects/{task_id}/materials-zip")
async def download_project_materials_zip(task_id: str):
    """Empaqueta y descarga todos los recursos del proyecto (video master, guión, audios, tarjetas, subtítulos) en un ZIP."""
    store = ProjectStore(task_id)
    try:
        document = store.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="No se encontró el proyecto.")

    title = document.get("original_name") or (document.get("result") or {}).get("title") or "KAI_Broadcast"
    safe_title = re.sub(r"[^\w\s-]", "", title, flags=re.UNICODE).strip().replace(" ", "_")[:45] or f"KAI_{task_id}"

    # Crear buffer ZIP en memoria o archivo temporal
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # 1. Video master si existe
        master_file = settings.OUTPUTS_DIR / f"{task_id}_master.mp4"
        if master_file.exists():
            zip_file.write(master_file, arcname=f"{safe_title}_Master_1080p.mp4")

        # 2. Archivo del proyecto manifest
        if store.manifest_path.exists():
            zip_file.write(store.manifest_path, arcname="proyecto_metadata.json")

        # 3. Todo el directorio de trabajo (escenas, voz, subtítulos, tarjetas)
        if store.workdir.exists():
            for f in store.workdir.rglob("*"):
                if f.is_file() and not f.name.endswith(".tmp"):
                    rel = f.relative_to(store.workdir)
                    zip_file.write(f, arcname=f"materiales/{rel}")

    zip_buffer.seek(0)
    zip_filename = f"{safe_title}_Materiales_Completos.zip"
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'}
    )


@app.post("/api/projects/{task_id}/open-folder")
async def open_project_folder(task_id: str):
    """Abre la carpeta del proyecto en el Explorador de Windows y resalta el archivo .mp4."""
    store = ProjectStore(task_id)
    master_file = settings.OUTPUTS_DIR / f"{task_id}_master.mp4"
    if not master_file.exists():
        try:
            document = store.read()
            res = document.get("result") or {}
            candidate = Path(res.get("output_file") or "")
            if candidate.exists():
                master_file = candidate
            else:
                prev = Path(document.get("preview_file") or "")
                if prev.exists():
                    master_file = prev
        except Exception:
            pass

    folder = store.workdir
    if not folder.exists():
        folder = store.root
    if not folder.exists():
        folder = settings.OUTPUTS_DIR

    try:
        if master_file.exists():
            # Abre el explorador seleccionando/resaltando directamente el video master
            subprocess.Popen(["explorer.exe", f"/select,{str(master_file.resolve())}"])
            return {"status": "ok", "path": str(master_file.parent), "file": str(master_file)}
        else:
            subprocess.Popen(["explorer.exe", str(folder.resolve())])
            return {"status": "ok", "path": str(folder)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo abrir el explorador: {exc}")


@app.post("/api/projects/{task_id}/save-to-downloads")
async def save_project_to_downloads(task_id: str):
    """Guarda una copia directa del archivo .mp4 en la carpeta Descargas del usuario de Windows."""
    import shutil
    store = ProjectStore(task_id)
    try:
        document = store.read()
    except Exception:
        document = {}

    master_file = settings.OUTPUTS_DIR / f"{task_id}_master.mp4"
    if not master_file.exists():
        res = document.get("result") or {}
        candidate = Path(res.get("output_file") or "")
        if candidate.exists() and candidate.is_file():
            master_file = candidate
        else:
            prev = Path(document.get("preview_file") or "")
            if prev.exists() and prev.is_file():
                master_file = prev
            else:
                raise HTTPException(status_code=404, detail="El archivo de video no está listo.")

    title = document.get("original_name") or (document.get("result") or {}).get("title") or "KAI_Broadcast"
    safe_title = re.sub(r"[^\w\s-]", "", title, flags=re.UNICODE).strip().replace(" ", "_")[:50] or f"KAI_{task_id}"
    filename = f"{safe_title}.mp4"

    # Carpeta Downloads del usuario
    downloads_dir = Path.home() / "Downloads"
    if not downloads_dir.exists():
        downloads_dir = Path.home()
    dest_path = downloads_dir / filename

    try:
        shutil.copy2(str(master_file), str(dest_path))
        # Abrir explorador seleccionando el archivo copiado en Downloads
        try:
            subprocess.Popen(["explorer.exe", f"/select,{str(dest_path.resolve())}"])
        except Exception:
            pass
        return {"status": "ok", "path": str(dest_path), "filename": filename}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo copiar a Descargas: {exc}")


@app.get("/api/projects/{task_id}/materials")
async def get_project_materials(task_id: str):
    """Devuelve el inventario completo de archivos generados por escena."""
    store = ProjectStore(task_id)
    try:
        document = store.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="No se encontró el proyecto.")

    result = document.get("result") or {}
    scenes_info = result.get("scenes") or []
    materials = {
        "master_video_url": f"/api/projects/{task_id}/download",
        "zip_url": f"/api/projects/{task_id}/materials-zip",
        "title": result.get("title") or document.get("original_name") or "Producción KAI",
        "scenes": scenes_info,
        "files": []
    }

    if store.workdir.exists():
        for f in store.workdir.rglob("*"):
            if f.is_file() and not f.name.endswith(".tmp"):
                rel = str(f.relative_to(store.workdir)).replace("\\", "/")
                materials["files"].append({
                    "name": f.name,
                    "rel_path": rel,
                    "size_kb": round(f.stat().st_size / 1024, 1),
                    "ext": f.suffix.lower()
                })

    return materials


@app.post("/api/projects/{task_id}/webhook")
async def dispatch_project_webhook(task_id: str, payload: Dict[str, Any] = Body(...)):
    """Despacha la información completa de la transmisión a un Webhook (Make, Zapier, Discord, Notion)."""
    import urllib.request
    webhook_url = str(payload.get("webhook_url", "")).strip()
    if not webhook_url or not webhook_url.startswith("http"):
        raise HTTPException(status_code=400, detail="URL de webhook inválida. Debe comenzar con http o https.")

    store = ProjectStore(task_id)
    try:
        document = store.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="No se encontró el proyecto.")

    res = document.get("result") or {}
    title = res.get("title") or document.get("original_name") or f"KAI Broadcast {task_id}"
    topic = res.get("topic") or document.get("options", {}).get("topic", "")
    
    thumb_path = settings.OUTPUTS_DIR / f"{task_id}_thumbnail.jpg"
    short_path = settings.OUTPUTS_DIR / f"{task_id}_short.mp4"
    master_path = settings.OUTPUTS_DIR / f"{task_id}_master.mp4"

    export_data = {
        "event": "broadcast_completed",
        "task_id": task_id,
        "title": title,
        "topic": topic,
        "duration_sec": res.get("duration", 0),
        "scenes_count": res.get("scenes_count", len(res.get("scenes", []))),
        "master_video_url": f"/media/{master_path.name}" if master_path.exists() else res.get("master_video_url"),
        "thumbnail_url": f"/media/{thumb_path.name}" if thumb_path.exists() else None,
        "short_video_url": f"/media/{short_path.name}" if short_path.exists() else None,
        "scenes": res.get("scenes", []),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(export_data).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "AetherCut-Studio/2.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            status_code = resp.getcode()
            return {"status": "ok", "http_status": status_code, "message": "Datos enviados exitosamente al Webhook."}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Error despachando webhook: {exc}")


@app.put("/api/projects/{task_id}/timeline")
async def update_project_timeline(task_id: str, payload: Dict[str, Any] = Body(...)):
    """Guarda ajustes editoriales sin perder la investigación ni los assets."""
    store = ProjectStore(task_id)
    try:
        plan = store.load_plan()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="No se encontró el proyecto.")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    card_updates = {str(item.get("id")): item for item in payload.get("cards", []) if item.get("id")}
    for card in plan.info_cards:
        update = card_updates.get(card.card_id)
        if not update:
            continue
        if "enabled" in update:
            card.enabled = bool(update["enabled"])
        if "start" in update:
            card.start_sec = max(0.0, float(update["start"]))
        if "duration" in update:
            card.display_duration_sec = max(4.5, min(12.0, float(update["duration"])))
        if update.get("position") in {"auto", "upper_left", "upper_right", "lower_left", "lower_right"}:
            card.screen_position = update["position"]
        if "avatar_spoken_text" in update and update["avatar_spoken_text"] != card.avatar_spoken_text:
            card.avatar_spoken_text = str(update["avatar_spoken_text"]).strip()
            card.avatar_audio_path = None
            card.avatar_video_path = None
        if "avatar_enabled" in update:
            card.avatar_enabled = bool(update["avatar_enabled"])

    broll_updates = {str(item.get("id")): item for item in payload.get("brolls", []) if item.get("id")}
    for cue in plan.b_rolls:
        update = broll_updates.get(cue.cue_id)
        if not update:
            continue
        if "enabled" in update:
            cue.enabled = bool(update["enabled"])
        if "start" in update:
            cue.start_sec = max(0.0, float(update["start"]))
        if "end" in update:
            cue.end_sec = max(cue.start_sec + 1.0, float(update["end"]))

    store.save_plan(plan, status="ready_for_export")
    state = tasks_progress.get(task_id)
    if state is not None:
        update_task_state(task_id, state.get("step", "done"), state.get("progress", 100.0),
                          "Cambios del editor guardados.", editor=editor_snapshot(plan))
    return {"editor": editor_snapshot(plan), "message": "Cambios guardados. Puedes conservar el proyecto o exportar una nueva versión."}


@app.post("/api/projects/{task_id}/export")
async def export_project(task_id: str):
    """Exporta una nueva versión a partir de las decisiones ya guardadas."""
    if task_id in task_jobs:
        raise HTTPException(status_code=409, detail="Este proyecto ya está procesándose.")
    store = ProjectStore(task_id)
    try:
        document = store.read()
        store.load_plan()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="No se encontró el proyecto.")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if not Path(document.get("source_file") or "").exists():
        raise HTTPException(status_code=410, detail="No se encontró el video original para exportar.")
    now = datetime.now(timezone.utc).isoformat()
    tasks_progress[task_id] = {
        "step": "queued", "progress": 5.0, "message": "Nueva exportación en cola.",
        "completed": False, "error": None, "result": None, "cancel_supported": True,
        "file_name": document.get("original_name", "video"), "created_at": now,
        "updated_at": now, "step_started_at": now,
        "events": [{"step": "queued", "progress": 5.0, "message": "Nueva exportación en cola.", "at": now}],
    }
    task_cancel_events[task_id] = threading.Event()
    task_jobs[task_id] = asyncio.create_task(run_export_task(task_id))
    return {"task_id": task_id, "message": "Se inició una nueva exportación sin repetir el análisis."}


@app.post("/api/cancel-task/{task_id}")
async def cancel_task(task_id: str):
    with _state_lock:
        state = tasks_progress.get(task_id)
        if not state:
            raise HTTPException(status_code=404, detail="No se encontró la tarea.")
        if state.get("completed") or state.get("error") or state.get("cancelled"):
            return {"status": "finished", "message": "La tarea ya terminó."}
        if state.get("cancel_requested"):
            return {"status": "cancelling", "message": "La cancelación ya está solicitada."}
        state["cancelled_step"] = state.get("step")
        state["cancel_requested"] = True
    cancel_event = task_cancel_events.get(task_id)
    if cancel_event is not None:
        cancel_event.set()

    job = task_jobs.get(task_id)
    if job and not job.done():
        job.cancel()

    update_task_state(task_id, "cancelled", state.get("progress", 0.0),
                      "Transmisión cancelada.", completed=True, cancelled=True,
                      cancel_requested=True, cancelled_step=state.get("cancelled_step"))
    return {"status": "cancelled", "message": "Proceso cancelado inmediatamente."}


@app.get("/api/stream-progress/{task_id}")
async def stream_progress(task_id: str):
    async def events():
        while True:
            state = tasks_progress.get(task_id)
            if not state:
                # Si la tarea no está en memoria, verificar si existe un proyecto guardado completado
                try:
                    doc = ProjectStore(task_id).read()
                    if "current_progress" in doc and doc["current_progress"]:
                        cp = doc["current_progress"]
                        yield f"data: {json.dumps(cp, default=str)}\n\n"
                        if cp.get("completed") or cp.get("error"):
                            break
                        await asyncio.sleep(1)
                        continue
                    elif doc.get("status") == "done":
                        done_state = {
                            "step": "done",
                            "progress": 100.0,
                            "message": "¡Transmisión completada!",
                            "completed": True,
                            "file_name": doc.get("original_name") or f"KAI Stream {task_id}",
                            "result": doc.get("result"),
                        }
                        yield f"data: {json.dumps(done_state, default=str)}\n\n"
                        break
                    elif doc.get("status") == "error":
                        yield f"data: {json.dumps({'error': doc.get('message', 'Error en el proyecto')})}\n\n"
                        break
                except Exception:
                    pass
                yield f"data: {json.dumps({'error': 'Tarea no encontrada'})}\n\n"
                break
            yield f"data: {json.dumps(state, default=str)}\n\n"
            if state.get("completed") or state.get("error"):
                break
            await asyncio.sleep(1)

    return StreamingResponse(events(), media_type="text/event-stream")


@app.get("/api/progress/{task_id}")
async def get_task_progress(task_id: str):
    state = tasks_progress.get(task_id)
    if not state:
        try:
            doc = ProjectStore(task_id).read()
            if doc.get("status") == "done":
                return {
                    "step": "done",
                    "progress": 100.0,
                    "message": "¡Transmisión completada!",
                    "completed": True,
                    "file_name": doc.get("original_name") or f"KAI Stream {task_id}",
                    "result": doc.get("result"),
                }
        except Exception:
            pass
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return state


@app.get("/api/trending-topics")
async def get_trending_topics():
    """Devuelve temas y noticias en tendencia reales extraídos de la web (ciencia, polémicas, descubrimientos, virales)."""
    import random
    
    # Categorías variadas y potentes para mantener contenido fresco en cada consulta
    CATEGORIES = [
        ("descubrimientos", ["descubrimiento cientifico reciente", "arqueologia hallazgo historia", "espacio astronomia universo"]),
        ("polemicas", ["polemica debate viral redes", "polemica tecnologia inteligencia artificial", "noticias controversia actual"]),
        ("noticias", ["noticias del mundo actualidad", "ultimas noticias internacionales", "ciencia tecnologia futuro"]),
        ("virales", ["tendencias virales hoy", "video viral impacto redes", "curiosidades del mundo ciencia"]),
    ]
    
    try:
        from ddgs import DDGS
        topics: List[Dict[str, str]] = []
        seen_titles = set()
        
        # Seleccionar consultas aleatorias de diferentes categorías en cada refresco
        selected_queries = []
        for cat_name, queries in CATEGORIES:
            selected_queries.append((cat_name, random.choice(queries)))
        random.shuffle(selected_queries)

        def _fetch_multi_news():
            results = []
            with DDGS() as ddgs:
                for cat, q in selected_queries:
                    try:
                        for item in ddgs.news(q, max_results=3):
                            results.append((cat, item))
                    except Exception:
                        continue
            return results

        news_items = await asyncio.to_thread(_fetch_multi_news)
        
        cat_emojis = {
            "descubrimientos": "🔬",
            "polemicas": "🔥",
            "noticias": "🌍",
            "virales": "⚡",
        }

        for cat, n in news_items:
            t = (n.get("title") or "").strip()
            if t and len(t) > 12:
                # Limpiar sufijos de fuentes (ej: "- El País", "| BBC News")
                clean = re.sub(r"\s*[-|–]\s*[A-Za-z0-9\.\sáéíóúÁÉÍÓÚ]+$", "", t).strip()
                clean = re.sub(r"^[A-Za-z0-9\.\s]+:\s*", "", clean).strip()
                if clean and len(clean) > 10 and clean.lower() not in seen_titles:
                    seen_titles.add(clean.lower())
                    topics.append({
                        "title": clean,
                        "category": cat,
                        "emoji": cat_emojis.get(cat, "✨")
                    })
            if len(topics) >= 8:
                break

        if topics:
            return {"topics": topics}
    except Exception as exc:
        safe_log(f"[Trending] Fallback en noticias: {exc}")

    # Fallback diverso y categorizado por si no hay conexión de red externa
    FALLBACK_TOPICS = [
        {"title": "Misión Europa Clipper y Océanos en el Sistema Solar", "category": "descubrimientos", "emoji": "🚀"},
        {"title": "Debate Ético y Regulación Global sobre la IA Autónoma", "category": "polemicas", "emoji": "🔥"},
        {"title": "Nuevo Hallazgo Arqueológico Desafía la Historia de la Humanidad", "category": "descubrimientos", "emoji": "🏺"},
        {"title": "Baterías Cuánticas y la Revolución de la Energía Limpia", "category": "noticias", "emoji": "⚡"},
        {"title": "El Misterio de las Señales Cósmicas Rápidas Detectadas en el Espacio", "category": "descubrimientos", "emoji": "🔭"},
        {"title": "Polémica Viral: La Transformación del Mercado Laboral con Robótica", "category": "polemicas", "emoji": "🤖"},
        {"title": "Terapias Genéticas CRISPR Curan Enfermedades Hereditarias", "category": "noticias", "emoji": "🧬"},
        {"title": "Diez Curiosidades Ocultas de la Naturaleza que Desafían la Ciencia", "category": "virales", "emoji": "🌍"},
    ]
    random.shuffle(FALLBACK_TOPICS)
    return {"topics": FALLBACK_TOPICS}


@app.post("/api/cleanup")
async def cleanup_storage_endpoint():
    """Limpia de forma segura los archivos temporales intermedios de render (.mov pesados, etc.) sin borrar videos master."""
    import os
    freed_bytes = 0
    deleted_files = 0
    try:
        # 1. Limpiar .mov intermedios pesados en carpetas work de proyectos
        for p in settings.PROJECTS_DIR.glob("*"):
            w = p / "work"
            if w.exists():
                for root, dirs, files in os.walk(w):
                    for f in files:
                        if f.endswith(".mov") or (f.endswith(".png") and f.startswith("f_")):
                            fp = os.path.join(root, f)
                            try:
                                sz = os.path.getsize(fp)
                                os.remove(fp)
                                freed_bytes += sz
                                deleted_files += 1
                            except Exception:
                                pass
        # 2. Limpiar archivos temporales en raíz del proyecto
        for f in Path(".").glob("temp_*.mp4"):
            try:
                sz = f.stat().st_size
                f.unlink()
                freed_bytes += sz
                deleted_files += 1
            except Exception:
                pass
    except Exception as exc:
        safe_log(f"[Cleanup] Error parcial: {exc}")

    freed_mb = round(freed_bytes / (1024 * 1024), 2)
    freed_gb = round(freed_bytes / (1024 * 1024 * 1024), 2)
    return {
        "status": "ok",
        "freed_mb": freed_mb,
        "freed_gb": freed_gb,
        "deleted_files": deleted_files,
    }


if __name__ == "__main__":
    import uvicorn
    safe_log("[Server] AetherCut AI en http://127.0.0.1:8000")
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)
