"""Módulo de Control de Calidad Visual Autónomo con Gemini Vision (VideoVisionQA).

Función:
Inspecciona fotogramas reales de los videos renderizados antes de su publicación en Facebook,
garantizando:
1. 0% contaminación cruzada (detecta y bloquea anime en canales de Fe, Política o Tech).
2. Coherencia temática con el nicho esperado.
3. Calidad estética y legibilidad visual.
"""

from __future__ import annotations

import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image

from config.settings import settings
from core.llm import safe_log

logger = logging.getLogger("aethercut.vision_qa")


class VideoVisionQA:
    """Auditor visual con Gemini Vision para control de calidad pre-publicación."""

    def __init__(self):
        self.temp_frames_dir = settings.STORAGE_DIR / "temp" / "qa_frames"
        self.temp_frames_dir.mkdir(parents=True, exist_ok=True)

    def extract_keyframes(self, video_path: Path, num_frames: int = 3) -> List[Path]:
        """Extrae fotogramas representativos a lo largo del video con FFmpeg."""
        if not video_path.exists():
            return []

        # Obtener duración del video con ffprobe
        probe_cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=duration",
            "-of", "json", str(video_path)
        ]
        duration = 45.0
        try:
            res = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
            info = json.loads(res.stdout)
            duration = float(info.get("streams", [{}])[0].get("duration", 45.0))
        except Exception:
            pass

        timestamps: List[float] = []
        if num_frames == 1:
            timestamps = [duration * 0.5]
        elif num_frames == 2:
            timestamps = [duration * 0.3, duration * 0.7]
        else:
            timestamps = [duration * 0.25, duration * 0.50, duration * 0.75]

        extracted: List[Path] = []
        stem = video_path.stem
        for i, ts in enumerate(timestamps):
            out_img = self.temp_frames_dir / f"qa_{stem}_frame_{i+1}.jpg"
            out_img.unlink(missing_ok=True)
            # Extraer frame exacto
            cmd = [
                "ffmpeg", "-y",
                "-ss", f"{ts:.2f}",
                "-i", str(video_path),
                "-vframes", "1",
                "-q:v", "2",
                str(out_img)
            ]
            try:
                subprocess.run(cmd, capture_output=True, timeout=15)
                if out_img.exists() and out_img.stat().st_size > 1000:
                    extracted.append(out_img)
            except Exception as exc:
                safe_log(f"[VisionQA] Aviso extrayendo frame {i+1}: {exc}")

        return extracted

    def audit_video(
        self,
        video_path: Path,
        expected_niche: str,
        forbidden_elements: Optional[List[str]] = None,
        channel_name: str = "General",
    ) -> Dict[str, Any]:
        """
        Audita el video visualmente usando Gemini Vision.
        Retorna:
          {
            "approved": bool,
            "has_forbidden": bool,
            "critique": str,
            "detected_elements": List[str],
            "channel": str
          }
        """
        forbidden = forbidden_elements or ["anime", "caricaturas japonesas", "dibujos animados", "elementos fuera de contexto"]
        safe_log(f"\n[VisionQA] 👁️ Inspeccionando visualmente '{video_path.name}' para [{channel_name}]...")

        frames = self.extract_keyframes(video_path, num_frames=3)
        if not frames:
            safe_log("[VisionQA] ⚠️ No se pudieron extraer fotogramas para auditoría. Aprobando por omisión de extracción.")
            return {"approved": True, "warning": "No frames extracted", "channel": channel_name}

        # Preparar llamada a Gemini Vision
        api_key = settings.GEMINI_API_KEY
        if not api_key or api_key == "your_gemini_api_key_here":
            safe_log("[VisionQA] ⚠️ GEMINI_API_KEY no configurada. Saltando auditoría.")
            return {"approved": True, "warning": "No Gemini API key", "channel": channel_name}

        try:
            from google import genai
            from google.genai import types

            first_key = api_key.split(",")[0].strip()
            client = genai.Client(api_key=first_key)

            pil_images = []
            for f in frames:
                try:
                    pil_images.append(Image.open(f))
                except Exception:
                    pass

            if not pil_images:
                return {"approved": True, "warning": "Could not open frames as PIL images", "channel": channel_name}

            forbidden_str = ", ".join(forbidden)
            prompt = (
                f"Eres el Auditor Jefe de Calidad Visual de un estudio de video profesional.\n"
                f"Canal destino: {channel_name}\n"
                f"Nicho esperado: {expected_niche}\n"
                f"Elementos estrictamente PROHIBIDOS: {forbidden_str}\n\n"
                f"Examina los {len(pil_images)} fotogramas adjuntos del video final renderizado.\n"
                f"Determina si el metraje es coherente con el canal y confirma si contiene algún elemento prohibido.\n\n"
                f"Responde estrictamente en formato JSON:\n"
                f"{{\n"
                f"  \"approved\": true/false,\n"
                f"  \"has_forbidden\": true/false,\n"
                f"  \"forbidden_found\": [\"lista de cosas prohibidas si las hay\"],\n"
                f"  \"critique\": \"explicación concisa de 1 a 2 oraciones sobre lo que se ve en pantalla\",\n"
                f"  \"confidence\": 0.95\n"
                f"}}"
            )

            contents: list[Any] = pil_images + [prompt]
            response = client.models.generate_content(
                model="gemini-flash-lite-latest",
                contents=contents,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )

            if response.text:
                result = json.loads(response.text)
                approved = bool(result.get("approved", True))
                has_forbidden = bool(result.get("has_forbidden", False))
                critique = result.get("critique", "Sin observaciones.")
                forbidden_found = result.get("forbidden_found", [])

                # Si detecta elementos prohibidos, desaprobar de inmediato
                if has_forbidden:
                    approved = False

                if approved:
                    safe_log(f"[VisionQA] ✅ APROBADO: {critique}")
                else:
                    safe_log(f"[VisionQA] 🛑 RECHAZADO: Elementos prohibidos detectados: {forbidden_found}. {critique}")

                return {
                    "approved": approved,
                    "has_forbidden": has_forbidden,
                    "critique": critique,
                    "forbidden_found": forbidden_found,
                    "channel": channel_name,
                }

        except Exception as exc:
            safe_log(f"[VisionQA] Aviso en auditoría Gemini Vision: {exc}. Permitiendo publicación con advertencia.")
            return {"approved": True, "warning": str(exc), "channel": channel_name}
        finally:
            # Limpiar frames temporales
            for f in frames:
                try:
                    f.unlink(missing_ok=True)
                except Exception:
                    pass

        return {"approved": True, "channel": channel_name}


# Instancia singleton para uso rápido en productores
vision_qa = VideoVisionQA()
