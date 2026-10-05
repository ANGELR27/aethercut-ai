import asyncio
import json
import re
import sys
import uuid
from pathlib import Path
from typing import Any, Dict

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import aiofiles
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from config.settings import settings
from core.llm import safe_log
from core.pipeline import PipelineOptions, VideoPipeline

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
_pipeline_lock = asyncio.Lock()  # un render a la vez: MoviePy/FFmpeg saturan CPU y RAM


def friendly_error(exc: Exception) -> str:
    text = str(exc)
    low = text.lower()
    if "429" in text or "quota" in low or "resource_exhausted" in low:
        return "Gemini alcanzó su límite de uso gratuito. Espera unos minutos e inténtalo de nuevo."
    if "503" in text or "unavailable" in low:
        return "Los modelos de Gemini están saturados en este momento. Inténtalo de nuevo en un minuto."
    if "api key" in low or "401" in text or "unauthenticated" in low:
        return "La clave de Gemini no es válida. Revisa GEMINI_API_KEY en el archivo .env."
    if "ffmpeg" in low:
        return "FFmpeg falló al procesar el video. Prueba con otro archivo o formato (MP4 recomendado)."
    return text[:300]


def update_task_state(task_id: str, step: str, progress: float, message: str, **extra: Any) -> None:
    state = tasks_progress.get(task_id)
    if state is not None:
        state.update({"step": step, "progress": progress, "message": message, **extra})


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    async with aiofiles.open(TEMPLATES_DIR / "index.html", mode="r", encoding="utf-8") as f:
        return HTMLResponse(content=await f.read())


async def run_pipeline_task(task_id: str, input_file: Path, options: PipelineOptions) -> None:
    update_task_state(task_id, "queued", 5.0, "En cola...")
    async with _pipeline_lock:
        try:
            pipeline = VideoPipeline(
                task_id, input_file, options,
                on_state=lambda step, pct, msg, **kw: update_task_state(task_id, step, pct, msg, **kw),
            )
            result = await pipeline.run()
            update_task_state(task_id, "done", 100.0, "Edición completada.", completed=True, result=result)
        except Exception as exc:
            safe_log(f"[Pipeline] Error: {exc}")
            update_task_state(task_id, "error", 0.0, "Error", error=friendly_error(exc))

    # conserva solo las últimas 20 tareas en memoria
    for old in list(tasks_progress)[:-20]:
        tasks_progress.pop(old, None)


@app.post("/api/process-video")
async def process_video(
    background_tasks: BackgroundTasks,
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

    tasks_progress[task_id] = {
        "step": "init", "progress": 5.0, "message": "Archivo recibido. Iniciando...",
        "completed": False, "error": None, "result": None,
    }
    options = PipelineOptions(
        silence_threshold=max(0.8, min(3.0, silence_threshold)),
        broll=enable_broll, captions=enable_captions, shorts=enable_shorts, cards=enable_cards,
    )
    background_tasks.add_task(run_pipeline_task, task_id, saved, options)
    return {"task_id": task_id}


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
            await asyncio.sleep(0.5)

    return StreamingResponse(events(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    safe_log("[Server] AetherCut AI en http://127.0.0.1:8000")
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)
