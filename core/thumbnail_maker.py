"""Generador de Miniaturas para YouTube de Alta Retención y CTR Pro.
Diseño cinematográfico con tipografía de alto impacto, gradientes obsidian/neón,
badges broadcast llamativos y recortes de alta fidelidad.
"""

from __future__ import annotations

import os
import re
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List

from PIL import Image, ImageDraw, ImageFont, ImageFilter
from config.settings import settings
from core.llm import safe_log


def _get_font(names: List[str], size: int) -> ImageFont.ImageFont:
    """Busca fuentes de alta fidelidad en Windows Fonts o fallback."""
    for fn in names:
        p = Path("C:/Windows/Fonts") / fn
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size)
            except Exception:
                pass
    return ImageFont.load_default()


class YouTubeThumbnailMaker:
    """Motor de portadas de YouTube de alta conversión (1280x720)."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or settings.OUTPUTS_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        title: str,
        badge_text: str = "🔴 BROADCAST URGENTE",
        subtitle: Optional[str] = None,
        project_id: Optional[str] = None,
        style: str = "cyber_amber",
    ) -> Dict[str, Any]:
        """
        Genera una miniatura 1280x720 optimizada para retención visual en YouTube.
        """
        W, H = 1280, 720
        thumb_id = f"thumb_{project_id or uuid.uuid4().hex[:8]}"
        out_file = self.output_dir / f"{thumb_id}.jpg"

        # 1. Base background
        bg_img = None
        if project_id:
            # Intentar rescatar algún fotograma o tarjeta del proyecto
            proj_dir = settings.PROJECTS_DIR / project_id
            candidates = [
                proj_dir / "work" / "streamer_card_0.png",
                proj_dir / "work" / "scene_1" / "scene_thumb.jpg",
                proj_dir / "work" / "scene_0" / "scene_thumb.jpg",
            ]
            # También buscar en storage/outputs
            candidates.extend(list(settings.OUTPUTS_DIR.glob(f"*{project_id}*card*.png")))
            candidates.extend(list(settings.OUTPUTS_DIR.glob(f"*{project_id}*.jpg")))
            for c in candidates:
                if c.exists() and c != out_file:
                    try:
                        bg_img = Image.open(c).convert("RGB")
                        break
                    except Exception:
                        pass

        if not bg_img:
            # Fallback a fondo de estudio o gradiente abstracto
            studio_ref = Path("assets/streamer_studio_room.jpg")
            if studio_ref.exists():
                try:
                    bg_img = Image.open(studio_ref).convert("RGB")
                except Exception:
                    bg_img = None

        if bg_img:
            # Escalar y recortar al centro exacto
            bg_w, bg_h = bg_img.size
            ratio = max(W / bg_w, H / bg_h)
            new_w, new_h = int(bg_w * ratio), int(bg_h * ratio)
            bg_resized = bg_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            x0 = (new_w - W) // 2
            y0 = (new_h - H) // 2
            canvas = bg_resized.crop((x0, y0, x0 + W, y0 + H))
            # Desenfoque cinematográfico sutil de fondo
            canvas = canvas.filter(ImageFilter.GaussianBlur(3))
        else:
            # Crear gradiente obsidian deep space
            canvas = Image.new("RGB", (W, H), (10, 11, 16))
            grad_draw = ImageDraw.Draw(canvas)
            for y in range(H):
                factor = y / H
                r = int(12 + factor * 14)
                g = int(14 + factor * 8)
                b = int(24 + factor * 26)
                grad_draw.line([(0, y), (W, y)], fill=(r, g, b))

        # 2. Velo y viñeta lateral (para que el texto a la izquierda sea 100% legible)
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        o_draw = ImageDraw.Draw(overlay)
        # Sombra profunda en lado izquierdo (0 a 860px)
        for x in range(880):
            alpha = int(240 * (1 - (x / 880) ** 1.6))
            o_draw.line([(x, 0), (x, H)], fill=(5, 6, 10, alpha))
        # Viñeta en los bordes
        o_draw.rectangle([0, 0, W, H], outline=(0, 240, 255, 30), width=4)
        canvas.paste(overlay, (0, 0), overlay)

        draw = ImageDraw.Draw(canvas)

        # 3. Tipografía ultra-impactante
        f_badge = _get_font(["segoeuib.ttf", "arialbd.ttf"], 22)
        f_headline = _get_font(["impact.ttf", "segoeuib.ttf", "arialbd.ttf"], 68)
        f_sub = _get_font(["segoeuib.ttf", "arialbd.ttf"], 30)

        # 4. Badge Superior "🔴 BROADCAST URGENTE"
        badge_clean = badge_text.upper().strip()
        bw = int(draw.textlength(badge_clean, font=f_badge)) + 40
        bh = 46
        bx, by = 60, 60

        # Fondo del badge con color llamativo (Rojo broadcast o Ámbar advertencia)
        badge_bg = (239, 68, 68) if ("URGENTE" in badge_clean or "ALERTA" in badge_clean or "PELIGRO" in badge_clean) else (245, 158, 11)
        draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=8, fill=badge_bg)
        draw.text((bx + 20, by + 10), badge_clean, font=f_badge, fill=(255, 255, 255))

        # 5. Titular de alta retención (2 o 3 líneas grandes)
        # Limpiar palabras
        words = title.replace("\n", " ").split()
        lines: List[str] = []
        curr = ""
        for w in words:
            cand = (curr + " " + w).strip()
            if len(cand) <= 18:
                curr = cand
            else:
                if curr:
                    lines.append(curr)
                curr = w
        if curr:
            lines.append(curr)
        lines = lines[:4]  # Máximo 4 líneas gigantes

        ty = 135
        # Colores dinámicos por línea: línea 1 blanco, línea 2 amarillo/cian llamativo
        line_colors = [
            (255, 255, 255),
            (254, 240, 138),  # Amarillo neón
            (56, 189, 248),   # Cian
            (255, 255, 255),
        ]

        for idx, line in enumerate(lines):
            line_txt = line.upper()
            # Sombra de texto 3D profunda
            for sx, sy in [(3, 3), (4, 4), (5, 5)]:
                draw.text((60 + sx, ty + sy), line_txt, font=f_headline, fill=(0, 0, 0))
            col = line_colors[idx % len(line_colors)]
            draw.text((60, ty), line_txt, font=f_headline, fill=col)
            ty += 78

        # 6. Subtítulo o gancho inferior
        if subtitle:
            sub_clean = subtitle.strip()
            sub_y = min(H - 90, ty + 15)
            draw.text((64, sub_y + 2), sub_clean, font=f_sub, fill=(0, 0, 0))
            draw.text((60, sub_y), sub_clean, font=f_sub, fill=(203, 213, 225))

        # 7. Detalles visuales tecnológicos (HUD Brackets & Tech lines)
        # Línea de acento neón inferior
        draw.line([(60, H - 40), (480, H - 40)], fill=(56, 189, 248), width=4)
        draw.text((500, H - 48), "4K ULTRA HD • 60 FPS", font=_get_font(["segoeui.ttf"], 18), fill=(148, 163, 184))

        # Guardar en alta calidad
        canvas.save(out_file, "JPEG", quality=95)
        safe_log(f"[ThumbnailMaker] Miniatura generada con éxito: {out_file.name}")

        return {
            "thumbnail_id": thumb_id,
            "filename": out_file.name,
            "url": f"/media/{out_file.name}",
            "path": str(out_file),
            "title": title,
            "badge": badge_clean,
        }
