"""Renderizador visual del Avatar Copiloto IA (KAI).

Genera clips de video transparentes (.webm con canal alfa yuva420p) con
animación reactiva (gestos de habla, señalamiento de tarjeta, parpadeo y
anillo de audio HUD neón) sincronizados con la narración de Microsoft Neural TTS.
"""

from __future__ import annotations

import math
import shutil
import subprocess
from pathlib import Path
from typing import Optional

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
    """Genera animaciones de alta calidad del avatar para composiciones con FFmpeg."""

    def __init__(self, avatar_dir: Optional[Path] = None, badge_size: int = 340):
        self.avatar_dir = avatar_dir or DEFAULT_AVATAR_DIR
        self.size = badge_size

        self.idle_path = self.avatar_dir / "idle.jpg"
        self.talk_path = self.avatar_dir / "talking.jpg"
        self.point_path = self.avatar_dir / "pointing.jpg"

        # Cargar imágenes base o placeholders si no existen
        self.idle_img = self._load_img(self.idle_path)
        self.talk_img = self._load_img(self.talk_path)
        self.point_img = self._load_img(self.point_path)

    def _load_img(self, path: Path) -> Image.Image:
        if path.exists():
            return Image.open(path).convert("RGBA")
        # Fallback estilizado si no existe
        canvas = Image.new("RGBA", (self.size, self.size), (24, 30, 48, 255))
        d = ImageDraw.Draw(canvas)
        d.ellipse((20, 20, self.size - 20, self.size - 20), fill=(56, 189, 248, 200))
        return canvas

    def render_reaction_clip(self, duration_sec: float, out_path: Path, fps: int = 24) -> Optional[Path]:
        """Crea un clip de video transparente WebM (VP9 + alfa) con gestos dinámicos."""
        dur = max(1.5, float(duration_sec))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        temp_dir = out_path.parent / f"_avatar_tmp_{out_path.stem}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        size = self.size
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((6, 6, size - 6, size - 6), fill=255)

        total_frames = max(1, int(dur * fps))
        intro_frames = int(min(0.4, dur * 0.15) * fps)
        outro_frames = int(min(0.5, dur * 0.15) * fps)
        speaking_frames = max(1, total_frames - intro_frames - outro_frames)

        # Patrón de gesticulación sincronizado (boca y poses)
        states = [self.point_img] * intro_frames
        speech_cycle = (
            [self.talk_img] * 3
            + [self.idle_img] * 2
            + [self.talk_img] * 4
            + [self.point_img] * 2
            + [self.idle_img] * 2
        )
        while len(states) < intro_frames + speaking_frames:
            states.extend(speech_cycle)
        states = states[:intro_frames + speaking_frames]
        states.extend([self.point_img] * (total_frames - len(states)))

        f_tag = _get_font(["segoeuib.ttf", "arialbd.ttf"], 13)

        try:
            for i in range(total_frames):
                raw_img = states[i].resize((size, size), Image.Resampling.LANCZOS)
                canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
                canvas.paste(raw_img, (0, 0), mask)
                d = ImageDraw.Draw(canvas)

                # Anillo de pulso neon reactivo
                pulse = math.sin(i / 2.5)
                alpha_cyan = int(200 + 55 * pulse)
                d.ellipse((4, 4, size - 4, size - 4), outline=(56, 189, 248, alpha_cyan), width=3)
                d.ellipse((8, 8, size - 8, size - 8), outline=(99, 102, 241, 140), width=1)

                # Insignia flotante inferior KAI COPILOT
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
