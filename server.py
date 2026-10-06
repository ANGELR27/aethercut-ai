import asyncio
import json
import re
import sys
import threading
import uuid
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
from core.llm import safe_log
from core.models import VideoEditingPlan
from core.pipeline import PipelineOptions, VideoPipeline
from core.project_store import ProjectStore, editor_snapshot
from core.render_engine import VideoRenderEngine
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
                            card.avatar_spoken_text = narrator.craft_dialogue(card)
                        audio_file = store.workdir / f"{card.card_id}_voice.mp3"
                        _p, dur = await narrator.synthesize(card.avatar_spoken_text, audio_file)
                        card.avatar_audio_path = str(audio_file)
                        video_file = store.workdir / f"{card.card_id}_avatar.webm"
                        rendered = avatar_rnd.render_reaction_clip(dur + 0.4, video_file, audio_path=audio_file)
                        if rendered:
                            card.avatar_video_path = str(rendered)
                            card.avatar_enabled = True
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


@app.post("/api/projects/{task_id}/resume")
async def resume_project(task_id: str):
    """Reanuda una carga conservada sin volver a transferir el archivo desde el navegador."""
    if task_id in task_jobs:
        raise HTTPException(status_code=409, detail="Este proyecto ya está procesándose.")
    store = ProjectStore(task_id)
    try:
        document = store.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="No se encontró el proyecto.")
    source = Path(document.get("source_file") or "")
    if not source.exists():
        raise HTTPException(status_code=410, detail="No se encontró el video original para reanudar este proyecto.")
    raw_options = document.get("options") or {}
    options = PipelineOptions(
        silence_threshold=max(0.8, min(3.0, float(raw_options.get("silence_threshold", 1.5)))),
        broll=bool(raw_options.get("broll", True)), cards=bool(raw_options.get("cards", True)),
        captions=bool(raw_options.get("captions", False)), shorts=bool(raw_options.get("shorts", True)),
    )
    now = datetime.now(timezone.utc).isoformat()
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
    # No se exponen rutas del equipo local a la interfaz.
    public = {key: value for key, value in document.items() if key not in {"source_file", "preview_file", "plan"}}
    return {"project": public, "editor": editor}


@app.get("/api/projects")
async def list_projects():
    projects = []
    for manifest in settings.PROJECTS_DIR.glob("*/project.json"):
        try:
            document = json.loads(manifest.read_text(encoding="utf-8"))
            projects.append({
                "id": document.get("id"), "name": document.get("original_name", "Video sin nombre"),
                "status": document.get("status", "unknown"), "updated_at": document.get("updated_at"),
                "has_plan": bool(document.get("plan")), "has_result": bool(document.get("result")),
            })
        except (OSError, json.JSONDecodeError):
            continue
    projects.sort(key=lambda project: project.get("updated_at") or "", reverse=True)
    return {"projects": projects[:20]}


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
    try:
        document = ProjectStore(task_id).read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="No se encontró el proyecto.")
    path = Path(document.get("preview_file") or "")
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="La previsualización todavía no está lista.")
    return FileResponse(path, media_type="video/mp4", filename=f"{task_id}_preview.mp4")


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
    if cancel_event is None:
        raise HTTPException(status_code=409, detail="No se puede cancelar esta tarea en el servidor actual.")
    cancel_event.set()
    update_task_state(task_id, "cancelling", state.get("progress", 0.0),
                      "Cancelación solicitada. Esperando que termine la operación actual de forma segura.",
                      cancel_requested=True, cancelled_step=state.get("cancelled_step"))
    return {"status": "cancelling", "message": "La cancelación se aplicará al terminar la operación actual."}


@app.get("/api/stream-progress/{task_id}")
async def stream_progress(task_id: str):
    async def events():
        while True:
            state = tasks_progress.get(task_id)
            if not state:
                yield f"data: {json.dumps({'error': 'Tarea no encontrada'})}\n\n"
                break
            yield f"data: {json.dumps(state, default=str)}\n\n"
            if state.get("completed") or state.get("error"):
                break
            await asyncio.sleep(1)

    return StreamingResponse(events(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    safe_log("[Server] AetherCut AI en http://127.0.0.1:8000")
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)
