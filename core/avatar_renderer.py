"""Renderizador visual del Avatar Copiloto IA (KAI) con dinámicas humanas.

Genera clips de video transparentes (.webm con canal alfa yuva420p) con:
1. Lip-sync reactivo al volumen real de la voz (análisis RMS del audio).
2. Parpadeo ocular natural cada 2.5 - 3 segundos (blink).
3. Micro-movimiento corporal de respiración y habla (sway/bobbing orgánico).
4. Anillo de audio HUD neón que pulsa según la energía de la voz.
"""

from __future__ import annotations

import math
import shutil
import subprocess
import wave
from pathlib import Path
from typing import List, Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont

DEFAULT_AVATAR_DIR = Path("assets/avatars/kai")
FONT_DIR = Path("C:/Windows/Fonts")


def _get_font(names: list[str], size: int) -> ImageFont.FreeTypeFont:
    for name in names:
        p = FONT_DIR / name
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


class AvatarRenderer:
    """Genera animaciones fluidas y orgánicas del avatar sincronizadas con la voz."""

    def __init__(self, avatar_dir: Optional[Path] = None, badge_size: int = 340):
        self.avatar_dir = avatar_dir or DEFAULT_AVATAR_DIR
        self.size = badge_size

        self.idle_path = self.avatar_dir / "idle.jpg"
        self.talk_path = self.avatar_dir / "talking.jpg"
        self.point_path = self.avatar_dir / "pointing.jpg"
        self.blink_path = self.avatar_dir / "blink.jpg"

        self.idle_img = self._load_img(self.idle_path)
        self.talk_img = self._load_img(self.talk_path)
        self.point_img = self._load_img(self.point_path)
        self.blink_img = self._load_img(self.blink_path, fallback=self.idle_img)

    def _load_img(self, path: Path, fallback: Optional[Image.Image] = None) -> Image.Image:
        if path.exists():
            return Image.open(path).convert("RGBA")
        if fallback:
            return fallback.copy()
        canvas = Image.new("RGBA", (self.size, self.size), (24, 30, 48, 255))
        d = ImageDraw.Draw(canvas)
        d.ellipse((20, 20, self.size - 20, self.size - 20), fill=(56, 189, 248, 200))
        return canvas

    @staticmethod
    def _extract_audio_envelope(audio_path: Optional[Path], fps: int, total_frames: int) -> List[float]:
        """Calcula la curva de energía acústica RMS por fotograma para Lip-Sync reactivo."""
        if not audio_path or not Path(audio_path).exists():
            return []
        wav_tmp = audio_path.with_suffix(".tmp.wav")
        try:
            cmd = [
                "ffmpeg", "-y", "-i", str(audio_path),
                "-ar", "16000", "-ac", "1", "-f", "wav", str(wav_tmp)
            ]
            subprocess.run(cmd, capture_output=True, timeout=10)
            if not wav_tmp.exists():
                return []
            with wave.open(str(wav_tmp), "rb") as wf:
                raw = wf.readframes(wf.getnframes())
            samples = np.frombuffer(raw, dtype=np.int16)
            if len(samples) == 0:
                return []
            chunk_len = max(1, 16000 // fps)
            rms_list: List[float] = []
            for i in range(0, len(samples), chunk_len):
                chunk = samples[i:i + chunk_len]
                if len(chunk):
                    rms_list.append(float(np.sqrt(np.mean(chunk.astype(float) ** 2))))
            if not rms_list:
                return []
            max_rms = max(rms_list) + 1e-5
            # Normalizar entre 0.0 y 1.0 con umbral de sensibilidad
            norm = [min(1.0, r / (max_rms * 0.72)) for r in rms_list]
            # Ajustar longitud exacta a total_frames
            if len(norm) < total_frames:
                norm.extend([0.0] * (total_frames - len(norm)))
            return norm[:total_frames]
        except Exception as exc:
            print(f"[AvatarRenderer] No se pudo extraer envolvente de audio: {exc}")
            return []
        finally:
            wav_tmp.unlink(missing_ok=True)

    def render_reaction_clip(
        self,
        duration_sec: float,
        out_path: Path,
        audio_path: Optional[Path] = None,
        fps: int = 24
    ) -> Optional[Path]:
        """Crea un clip WebM transparente con gestos dinámicos y Lip-Sync realista."""
        dur = max(1.5, float(duration_sec))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        temp_dir = out_path.parent / f"_avatar_tmp_{out_path.stem}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        size = self.size
        total_frames = max(1, int(dur * fps))
        intro_frames = int(min(0.45, dur * 0.15) * fps)
        outro_frames = int(min(0.5, dur * 0.15) * fps)

        # 1. Extraer energía real del audio para sincronía labial
        envelope = self._extract_audio_envelope(audio_path, fps, total_frames)

        # Máscara circular
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((6, 6, size - 6, size - 6), fill=255)

        # Pre-redimensionar imágenes base
        img_idle = self.idle_img.resize((size, size), Image.Resampling.LANCZOS)
        img_talk = self.talk_img.resize((size, size), Image.Resampling.LANCZOS)
        img_point = self.point_img.resize((size, size), Image.Resampling.LANCZOS)
        img_blink = self.blink_img.resize((size, size), Image.Resampling.LANCZOS)

        f_tag = _get_font(["segoeuib.ttf", "arialbd.ttf"], 13)

        try:
            for i in range(total_frames):
                # Determinar parpadeo natural (3 fotogramas cada ~2.8 segundos)
                blink_cycle = int(fps * 2.8)
                is_blinking = (i % blink_cycle) in (20, 21, 22)

                # Selección del fotograma según la fase y la energía del habla
                if i < intro_frames:
                    current_img = img_point
                    energy = 0.5
                elif i >= total_frames - outro_frames:
                    current_img = img_idle
                    energy = 0.0
                elif is_blinking:
                    current_img = img_blink
                    energy = envelope[i] if envelope else 0.2
                elif envelope:
                    energy = envelope[i]
                    if energy > 0.32:
                        current_img = img_talk
                    elif energy > 0.13:
                        current_img = img_point
                    else:
                        current_img = img_idle
                else:
                    # Alternancia orgánica si no hay audio procesado
                    cycle = (i // 3) % 4
                    current_img = img_talk if cycle in (0, 2) else (img_point if cycle == 1 else img_idle)
                    energy = 0.4

                # Micro-movimiento humano de respiración y gesticulación (sway/bobbing)
                sway_y = int(math.sin(i / (fps * 0.45)) * 3.5)
                sway_x = int(math.cos(i / (fps * 0.8)) * 1.5)

                canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
                # Pegar con desplazamiento orgánico suave dentro de la máscara
                canvas.paste(current_img, (sway_x, sway_y), mask)
                d = ImageDraw.Draw(canvas)

                # Anillo de pulso neón reactivo a la energía de la voz
                alpha_cyan = int(170 + 80 * energy)
                d.ellipse((4, 4, size - 4, size - 4), outline=(56, 189, 248, alpha_cyan), width=3)
                d.ellipse((8, 8, size - 8, size - 8), outline=(99, 102, 241, int(100 + 60 * energy)), width=1)

                # Insignia KAI COPILOT
                tag_w = 120
                tag_h = 24
                tx = (size - tag_w) // 2
                ty = size - 34
                d.rounded_rectangle(
                    (tx, ty, tx + tag_w, ty + tag_h),
                    radius=12,
                    fill=(10, 14, 22, 230),
                    outline=(56, 189, 248, 190),
                    width=1,
                )
                d.text(
                    (size // 2, ty + 12),
                    "⚡ KAI COPILOT",
                    font=f_tag,
                    fill=(255, 255, 255, 255),
                    anchor="mm",
                )

                canvas.save(temp_dir / f"f_{i:04d}.png")

            cmd = [
                "ffmpeg", "-y",
                "-framerate", str(fps),
                "-i", str(temp_dir / "f_%04d.png"),
                "-c:v", "libvpx-vp9",
                "-pix_fmt", "yuva420p",
                "-b:v", "0",
                "-crf", "25",
                str(out_path),
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if res.returncode == 0 and out_path.exists():
                return out_path
            print(f"[AvatarRenderer] Falló codificación WebM: {res.stderr[-400:]}")
            return None
        except Exception as exc:
            print(f"[AvatarRenderer] Error renderizando avatar: {exc}")
            return None
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
