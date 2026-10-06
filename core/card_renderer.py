"""Módulo de renderizado de tarjetas gráficas (Info Cards) de alto impacto visual.

Diseño profesional oscuro, sólido, limpio y de máximo contraste:
- Contenedor oscuro sólido con sutil glassmorfismo y borde de 1px.
- Una sola etiqueta/badge clara y legible (sin saturación de píldoras).
- Tipografía grande y nítida en blanco puro y slate brillante para máxima legibilidad.
- Para tarjetas con imagen: foto limpia con sutil difuminado en el borde inferior.
- Para tarjetas de solo info: tarjeta compacta, sólida y elegante sin espacios vacíos.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from core.models import InfoCard

FONT_DIR = Path("C:/Windows/Fonts")

# Paleta para badges e indicadores
BADGE_PALETTE = {
    "green": ((16, 185, 129, 45), (52, 211, 153, 220), (52, 211, 153, 255)),
    "red": ((239, 68, 68, 45), (248, 113, 113, 220), (248, 113, 113, 255)),
    "amber": ((245, 158, 11, 45), (251, 191, 36, 220), (251, 191, 36, 255)),
    "cyan": ((14, 165, 233, 45), (56, 189, 248, 220), (56, 189, 248, 255)),
    "purple": ((147, 51, 234, 45), (192, 132, 252, 220), (192, 132, 252, 255)),
    "slate": ((71, 85, 105, 45), (148, 163, 184, 220), (226, 232, 240, 255)),
}

KIND_LABELS = {
    "ley": ("LEY CONFIRMADA", "cyan"),
    "normativa": ("NORMATIVA OFICIAL", "cyan"),
    "articulo": ("ARTÍCULO LEGAL", "cyan"),
    "cifra": ("ESTADÍSTICA", "amber"),
    "estadistica": ("ESTADÍSTICA", "amber"),
    "fecha": ("CRONOLOGÍA", "purple"),
    "persona": ("PERFIL", "purple"),
    "lugar": ("UBICACIÓN", "cyan"),
    "organizacion": ("INSTITUCIÓN", "cyan"),
    "organización": ("INSTITUCIÓN", "cyan"),
    "hardware": ("ESPECIFICACIÓN", "slate"),
    "concepto": ("CONCEPTO CLAVE", "purple"),
    "dato": ("DATO VERIFICADO", "green"),
    "confirmacion": ("CONFIRMADO", "green"),
    "confirmación": ("CONFIRMADO", "green"),
}


def _font(names: List[str], size: int) -> ImageFont.FreeTypeFont:
    for name in names:
        path = FONT_DIR / name
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except Exception:
                pass
    return ImageFont.load_default()


class InfoCardRenderer:
    """
    Renderizador de tarjetas broadcast limpias, oscuras y de máximo contraste.
    """

    def __init__(self, frame_w: int, frame_h: int):
        portrait = frame_h > frame_w
        self.card_w = int(frame_w * (0.84 if portrait else 0.32))
        self.card_w = max(self.card_w, 420)
        self.s = self.card_w / 640.0

    def _px(self, v: float) -> int:
        return max(1, int(round(v * self.s)))

    @staticmethod
    def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int, max_lines: int) -> List[str]:
        words = (text or "").split()
        lines = []
        cur = ""
        for w in words:
            trial = f"{cur} {w}".strip()
            if draw.textlength(trial, font=font) <= max_w:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            lines[-1] = lines[-1].rstrip(" .,;:") + "…"
        return lines

    def _cover(self, img: Image.Image, w: int, h: int) -> Image.Image:
        img = img.convert("RGB")
        ratio = max(w / img.width, h / img.height)
        img = img.resize((int(img.width * ratio) + 1, int(img.height * ratio) + 1), Image.LANCZOS)
        left = (img.width - w) // 2
        top = (img.height - h) // 3
        return img.crop((left, top, left + w, top + h))

    def _get_single_badge(self, card: InfoCard) -> Tuple[str, str]:
        verdict = (card.verdict or "").lower()
        if verdict == "contradicted":
            return ("CORRECCIÓN OFICIAL", "red")
        if verdict == "insufficient":
            return ("EN REVISIÓN", "amber")

        if card.stat_value:
            return (f"DATO CLAVE: {card.stat_value[:18]}", "amber")

        kind = (card.kind or "dato").lower()
        if kind in KIND_LABELS:
            return KIND_LABELS[kind]

        return ("VERIFICADO", "green")

    def _render_solid_dark_card(
        self,
        headline: str,
        body: str,
        badge_text: str,
        badge_color: str = "green",
        image_path: Optional[str] = None,
        source_domain: str = "Registro oficial",
        out_path: Optional[Path] = None,
    ) -> Path:
        """Renderiza una tarjeta profesional sólida, oscura y limpia."""
        w = self.card_w
        pad_x = self._px(28)
        inner_w = w - 2 * pad_x
        radius = self._px(22)

        f_badge = _font(["segoeuib.ttf", "arialbd.ttf"], self._px(13))
        f_title = _font(["segoeuib.ttf", "arialbd.ttf"], self._px(28))
        f_body = _font(["segoeuib.ttf", "segoeui.ttf", "arialbd.ttf"], self._px(20))
        f_src = _font(["segoeuib.ttf", "arialbd.ttf"], self._px(13))

        probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        title_lines = self._wrap(probe, headline, f_title, inner_w, 2)
        body_lines = self._wrap(probe, body, f_body, inner_w, 4)

        title_lh = f_title.size + self._px(6)
        body_lh = f_body.size + self._px(8)
        badge_h = self._px(28)

        has_photo = bool(image_path and Path(image_path).exists())
        photo_h = self._px(160) if has_photo else 0

        if has_photo:
            h = (
                photo_h
                + self._px(16)
                + badge_h
                + self._px(12)
                + (len(title_lines) * title_lh)
                + self._px(10)
                + (len(body_lines) * body_lh)
                + self._px(16)
                + f_src.size
                + self._px(24)
            )
        else:
            h = (
                self._px(24)
                + badge_h
                + self._px(12)
                + (len(title_lines) * title_lh)
                + self._px(10)
                + (len(body_lines) * body_lh)
                + self._px(16)
                + f_src.size
                + self._px(24)
            )

        ss = 2
        W, H = w * ss, h * ss
        # Fondo oscuro profesional sólido de máxima legibilidad
        card = Image.new("RGBA", (W, H), (14, 19, 32, 248))

        if has_photo:
            try:
                raw_photo = Image.open(image_path).convert("RGB")
                photo = self._cover(raw_photo, W, photo_h * ss).convert("RGBA")

                # Difuminado muy sutil solo en el último 22% del borde inferior
                fade_start = int(photo_h * ss * 0.78)
                fade_len = max(1, (photo_h * ss) - fade_start)
                mask = Image.new("L", (W, photo_h * ss), 255)
                m_data = []
                for py in range(photo_h * ss):
                    if py < fade_start:
                        a = 255
                    else:
                        t = (py - fade_start) / fade_len
                        a = int(255 * (1.0 - t))
                    m_data.extend([a] * W)
                mask.putdata(m_data)
                card.paste(photo, (0, 0), mask)
            except Exception as exc:
                print(f"[CardRenderer] Error cargando foto {image_path}: {exc}")
                has_photo = False

        d = ImageDraw.Draw(card)
        y = (photo_h + self._px(16)) * ss if has_photo else self._px(24) * ss

        # Badge único y limpio con punto luminoso
        bg_col, border_col, text_col = BADGE_PALETTE.get(badge_color, BADGE_PALETTE["green"])
        text_w = int(d.textlength(badge_text, font=f_badge))
        bw = text_w + self._px(34) * ss
        d.rounded_rectangle(
            (pad_x * ss, y, pad_x * ss + bw, y + badge_h * ss),
            radius=(badge_h * ss) // 2,
            fill=bg_col,
            outline=border_col,
            width=ss,
        )
        dot_cx = pad_x * ss + self._px(12) * ss
        dot_cy = y + (badge_h * ss) // 2
        dot_r = self._px(4) * ss
        d.ellipse((dot_cx - dot_r, dot_cy - dot_r, dot_cx + dot_r, dot_cy + dot_r), fill=text_col)
        d.text((pad_x * ss + self._px(24) * ss, dot_cy), badge_text, font=f_badge, fill=text_col, anchor="lm")
        y += (badge_h + self._px(14)) * ss

        # Titular en blanco puro bold
        for line in title_lines:
            d.text((pad_x * ss, y), line, font=f_title, fill=(255, 255, 255, 255))
            y += title_lh * ss
        y += self._px(8) * ss

        # Cuerpo en slate brillante ultra-legible
        for line in body_lines:
            d.text((pad_x * ss, y), line, font=f_body, fill=(241, 245, 249, 255))
            y += body_lh * ss
        y += self._px(14) * ss

        # Pie de fuente limpio
        d.text((pad_x * ss, y), f"Fuente: {source_domain}", font=f_src, fill=(148, 163, 184, 255))

        # Redimensionado para máxima nitidez
        card = card.resize((w, h), Image.LANCZOS)

        # Máscara de esquinas redondeadas
        c_mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(c_mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=255)

        # Sombra suave que despega la tarjeta del video
        margin = self._px(18)
        shadow = Image.new("RGBA", (w + 2 * margin, h + 2 * margin), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(shadow)
        s_draw.rounded_rectangle(
            (margin, margin + self._px(4), margin + w, margin + h + self._px(4)),
            radius=radius,
            fill=(0, 0, 0, 115),
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(self._px(10)))

        final_img = Image.new("RGBA", (w + 2 * margin, h + 2 * margin), (0, 0, 0, 0))
        final_img.paste(shadow, (0, 0), shadow)
        final_img.paste(card, (margin, margin), c_mask)

        # Borde sutil de cristal de 1px
        b_layer = Image.new("RGBA", (w + 2 * margin, h + 2 * margin), (0, 0, 0, 0))
        ImageDraw.Draw(b_layer).rounded_rectangle(
            (margin, margin, margin + w - 1, margin + h - 1),
            radius=radius,
            outline=(255, 255, 255, 45),
            width=1,
        )
        final_img = Image.alpha_composite(final_img, b_layer)

        target_out = out_path or Path("card_output.png")
        target_out.parent.mkdir(parents=True, exist_ok=True)
        final_img.save(target_out, "PNG")
        return target_out

    def render(self, card: InfoCard, out_path: Path) -> str:
        """Renderiza la tarjeta con el diseño profesional oscuro."""
        domain = card.sources[0].domain if card.sources else "Registro oficial"
        badge_text, badge_color = self._get_single_badge(card)

        # 1. Contradicción / Corrección
        if card.verdict == "contradicted":
            if getattr(card, "is_myth", False):
                return self._render_myth_cards(card, out_path)
            headline = card.headline
            correction_text = card.correction or card.corrected_value or card.note
            body = f"Afirmación: «{card.claim}»\n\nDato real confirmado: {correction_text}"
            return str(self._render_solid_dark_card(
                headline=headline,
                body=body,
                badge_text="CORRECCIÓN OFICIAL",
                badge_color="red",
                image_path=card.image_path,
                source_domain=card.correction_source or domain,
                out_path=out_path,
            ))

        # 2. Insuficiente evidencia
        if card.verdict == "insufficient":
            headline = card.headline
            body = card.note or "No se encontraron registros ni evidencia oficial concluyente que respalden esta afirmación."
            return str(self._render_solid_dark_card(
                headline=headline,
                body=body,
                badge_text="EN REVISIÓN",
                badge_color="amber",
                image_path=card.image_path,
                source_domain=domain,
                out_path=out_path,
            ))

        # 3. Estadística / Cifra
        if card.stat_value:
            headline = card.headline
            body = f"Cifra confirmada: {card.stat_value}. {card.body or card.claim}"
            return str(self._render_solid_dark_card(
                headline=headline,
                body=body,
                badge_text=f"DATO CLAVE: {card.stat_value[:18]}",
                badge_color="amber",
                image_path=card.image_path,
                source_domain=domain,
                out_path=out_path,
            ))

        # 4. Referencia o Apoyo visual estándar
        headline = card.headline
        body = card.body or card.claim
        return str(self._render_solid_dark_card(
            headline=headline,
            body=body,
            badge_text=badge_text,
            badge_color=badge_color,
            image_path=card.image_path,
            source_domain=domain,
            out_path=out_path,
        ))

    def render_photo_frame(self, image_path: str, label: str, out_path: Path) -> Optional[Path]:
        """Foto real enmarcada en el formato sólido oscuro con badge de apoyo visual."""
        try:
            return self._render_solid_dark_card(
                headline=label.strip(),
                body="Apoyo visual contextual integrado para ilustrar el argumento expuesto.",
                badge_text="APOYO VISUAL",
                badge_color="green",
                image_path=image_path,
                source_domain="Registro visual",
                out_path=out_path,
            )
        except Exception as exc:
            print(f"[CardRenderer] No se pudo enmarcar la foto: {exc}")
            return None

    def _render_myth_cards(self, card: InfoCard, out_path: Path) -> str:
        """Renderiza dos tarjetas: MITO y REALIDAD."""
        path_mito = out_path.with_name(f"{out_path.stem}_mito.png")
        path_real = out_path.with_name(f"{out_path.stem}_real.png")
        domain = card.correction_source or (card.sources[0].domain if card.sources else "Registro oficial")

        self._render_solid_dark_card(
            headline="Mito Popular",
            body=f"«{card.claim}»",
            badge_text="MITO POPULAR",
            badge_color="amber",
            image_path=card.image_path,
            source_domain=domain,
            out_path=path_mito,
        )

        self._render_solid_dark_card(
            headline=card.headline or "Realidad Verificada",
            body=card.correction or card.corrected_value or card.body,
            badge_text="REALIDAD CONFIRMADA",
            badge_color="green",
            image_path=card.image_path,
            source_domain=domain,
            out_path=path_real,
        )

        return f"{path_mito}|{path_real}"

    def render_all(self, cards: List[InfoCard], workdir: Path) -> List[InfoCard]:
        for card in cards:
            if not card.enabled or card.verdict not in ("supported", "contradicted", "insufficient"):
                continue
            try:
                card.card_path = str(self.render(card, workdir / f"{card.card_id}_card.png"))
            except Exception as exc:
                print(f"[CardRenderer] Error dibujando {card.card_id}: {exc}")
        return cards
