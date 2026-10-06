import os
import shutil
import subprocess
import json
from pathlib import Path
from threading import Event
from typing import Dict, Any, Optional
from config.settings import settings
from process_runner import run_process

class FileManager:
    """Administrador del ciclo de vida de archivos, metadatos y limpieza de almacenamiento."""

    @staticmethod
    def get_media_metadata(file_path: Path, cancel_event: Optional[Event] = None) -> Dict[str, Any]:
        """Obtiene duración, resolución y framerate usando ffprobe."""
        if not file_path.exists():
            raise FileNotFoundError(f"El archivo {file_path} no existe.")

        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration:stream=width,height,r_frame_rate,codec_type",
            "-of", "json",
            str(file_path)
        ]
        
        try:
            result = run_process(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                 check=True, timeout=60, cancel_event=cancel_event)
            data = json.loads(result.stdout)
            
            duration = float(data.get("format", {}).get("duration", 0.0))
            video_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
            
            width = int(video_stream.get("width", 0)) if video_stream else 0
            height = int(video_stream.get("height", 0)) if video_stream else 0
            
            fps = 30.0
            if video_stream and "r_frame_rate" in video_stream:
                num, denom = video_stream["r_frame_rate"].split("/")
                fps = float(num) / float(denom) if float(denom) > 0 else 30.0
                
            return {
                "duration": duration,
                "width": width,
                "height": height,
                "fps": round(fps, 2)
            }
        except Exception as e:
            return {"duration": 0.0, "width": 0, "height": 0, "fps": 30.0, "error": str(e)}

    @staticmethod
    def create_analysis_proxy(source: Path, destination: Path,
                              cancel_event: Optional[Event] = None) -> Path:
        """Crea una copia liviana únicamente para el análisis remoto.

        El render final siempre parte del archivo original. Reducir el proxy a
        854 px y 12 fps conserva planos, texto visible y cambios de escena, y
        evita subir gigabytes a Gemini para decidir cortes y recursos.
        """
        if not source.exists():
            raise FileNotFoundError(f"El archivo de video no existe: {source}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ffmpeg", "-y", "-i", str(source),
            # H.264 exige dimensiones pares. La expresión fija 854 cuando se
            # reduce y conserva la anchura original par para videos pequeños.
            # `-2` calcula la altura par preservando el aspecto.
            "-vf", "scale=w='if(gte(iw,854),854,trunc(iw/2)*2)':h=-2,fps=12",
            "-c:v", "libx264", "-preset", "veryfast", "-b:v", "520k", "-maxrate", "700k", "-bufsize", "1400k",
            "-c:a", "aac", "-b:a", "64k", "-movflags", "+faststart", str(destination),
        ]
        run_process(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                    encoding="utf-8", errors="replace", check=True, timeout=1800,
                    cancel_event=cancel_event)
        if not destination.exists() or destination.stat().st_size == 0:
            raise RuntimeError("FFmpeg no generó la copia de análisis.")
        return destination

    @staticmethod
    def clean_temp_directory() -> int:
        """Elimina todos los archivos del directorio temporal y devuelve la cantidad eliminada."""
        count = 0
        if not settings.TEMP_DIR.exists():
            return count

        for item in settings.TEMP_DIR.iterdir():
            try:
                if item.is_file() or item.is_symlink():
                    item.unlink()
                    count += 1
                elif item.is_dir():
                    shutil.rmtree(item)
                    count += 1
            except Exception as e:
                print(f"[FileManager] Advertencia al eliminar {item}: {e}")
        return count
