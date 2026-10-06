"""Módulo de renderizado de tarjetas gráficas (Info Cards) de alto impacto visual.

Inspirado en el diseño limpio y moderno de tarjetas UI con transición suave (gradient fade)
entre la imagen y los textos, micro-badges tipo píldora flotante con indicadores vectoriales,
y tipografía bold de máximo contraste y legibilidad broadcast sobre cualquier video.
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from core.models import InfoCard

FONT_DIR = Path("C:/Windows/Fonts")

# Paleta para badges e indicadores
PALETTE = {
    "green": (52, 211, 153, 255),    # Esmeralda neón / Verificado
    "cyan": (56, 189, 248, 255),     # Cyan eléctrico
    "amber": (251, 191, 36, 255),    # Ámbar / Alerta
    "red": (248, 113, 113, 255),     # Rojo suave / Corrección
    "purple": (168, 85, 247, 255),   # Violeta / Concepto
    "slate": (148, 163, 184, 255),   # Pizarra neutra
}

KIND_LABELS = {
    "ley": ("LEY / NORMATIVA", "cyan"),
    "normativa": ("LEY / NORMATIVA", "cyan"),
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
    "dato": ("DATO CLAVE", "cyan"),
    "confirmacion": ("CONFIRMADO", "green"),
    "confirmación": ("CONFIRMADO", "green"),
    "tip": ("TIP PRO", "amber"),
    "advertencia": ("ALERTA", "red"),
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
    Renderizador de tarjetas gráficas modernas y limpias:
    - Cabecera con imagen (o aura mesh) con transición suave (gradient fade) hacia el fondo blanco.
    - Badges flotantes tipo píldora oscura con indicadores luminosos (verde, cyan, ámbar, violeta).
    - Titular bold limpio y de gran contraste (charcoal / dark slate).
    - Párrafo explicativo con interlineado generoso.
    - Pie de fuentes minimalista sin botones de acción.
    - Sombra ambiental suave y borde sutil de 1px para destacar sobre cualquier escena de video.
    """

    def __init__(self, frame_w: int, frame_h: int):
        portrait = frame_h > frame_w
        # Escala adecuada para que sea muy legible sin tapar excesivamente la pantalla
        self.card_w = int(frame_w * (0.84 if portrait else 0.35))
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

    def _build_badges(self, card: InfoCard) -> List[Tuple[str, str]]:
        badges: List[Tuple[str, str]] = []

        verdict = (card.verdict or "").lower()
        if verdict == "contradicted":
            badges.append(("CORRECCIÓN", "red"))
        elif verdict == "supported":
            badges.append(("VERIFICADO", "green"))
        elif verdict == "insufficient":
            badges.append(("EN REVISIÓN", "amber"))

        kind = (card.kind or "dato").lower()
        if kind in KIND_LABELS:
            badges.append(KIND_LABELS[kind])

        if card.stat_value:
            badges.append((card.stat_value[:18], "amber"))
        elif card.sources and card.sources[0].domain:
            badges.append((card.sources[0].domain[:20], "slate"))

        # Limitar a máximo 4 badges para no saturar la cabecera
        return badges[:4]

    def _render_modern_card(
        self,
        headline: str,
        body: str,
        badges: List[Tuple[str, str]],
        image_path: Optional[str] = None,
        source_domain: str = "Registro oficial",
        highlight_color: Optional[Tuple[int, int, int]] = None,
        out_path: Optional[Path] = None,
    ) -> Path:
        """Renderiza la tarjeta con el diseño exacto: imagen + gradient fade + píldoras + textos."""
        w = self.card_w
        pad_x = self._px(30)
        inner_w = w - 2 * pad_x
        radius = self._px(28)

        f_badge = _font(["segoeuib.ttf", "arialbd.ttf"], self._px(13))
        f_title = _font(["segoeuib.ttf", "arialbd.ttf"], self._px(30))
        f_body = _font(["segoeui.ttf", "arial.ttf"], self._px(19))
        f_src = _font(["segoeuib.ttf", "arialbd.ttf"], self._px(13))

        probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        title_lines = self._wrap(probe, headline, f_title, inner_w, 2)
        body_lines = self._wrap(probe, body, f_body, inner_w, 4)

        title_lh = f_title.size + self._px(6)
        body_lh = f_body.size + self._px(8)

        has_photo = bool(image_path and Path(image_path).exists())
        photo_h = self._px(250) if has_photo else self._px(170)

        text_section_h = (
            (len(title_lines) * title_lh)
            + self._px(10)
            + (len(body_lines) * body_lh)
            + self._px(20)
            + f_src.size
            + self._px(34)
        )
        total_h = photo_h + text_section_h

        ss = 2
        W, H = w * ss, total_h * ss
        card = Image.new("RGBA", (W, H), (255, 255, 255, 255))

        # 1. Cabecera superior: Foto o Mesh gradient
        if has_photo:
            try:
                raw_photo = Image.open(image_path).convert("RGB")
                photo = self._cover(raw_photo, W, photo_h * ss).convert("RGBA")
            except Exception as exc:
                print(f"[CardRenderer] Error cargando imagen {image_path}: {exc}")
                has_photo = False

        if not has_photo:
            photo = Image.new("RGBA", (W, photo_h * ss), (15, 23, 42, 255))
            p_draw = ImageDraw.Draw(photo)
            for row in range(photo_h * ss):
                ratio = row / (photo_h * ss)
                r = int(18 + 24 * ratio)
                g = int(28 + 36 * ratio)
                b = int(48 + 68 * ratio)
                p_draw.line((0, row, W, row), fill=(r, g, b, 255))

        # 2. Máscara de transición suave (Smoothstep gradient fade) hacia el blanco
        mask = Image.new("L", (W, photo_h * ss), 255)
        fade_start = int(photo_h * ss * 0.38)
        fade_len = max(1, (photo_h * ss) - fade_start)
        m_data = []
        for y in range(photo_h * ss):
            if y < fade_start:
                a = 255
            else:
                t = (y - fade_start) / fade_len
                s = 3 * (t ** 2) - 2 * (t ** 3)
                a = int(255 * (1.0 - s))
            m_data.extend([a] * W)
        mask.putdata(m_data)

        card.paste(photo, (0, 0), mask)

        # 3. Badges flotantes estilo píldora oscura con punto luminoso
        d = ImageDraw.Draw(card)
        bx = pad_x * ss
        by = self._px(18) * ss
        badge_h = self._px(28) * ss
        dot_r = self._px(4) * ss

        for b_text, b_color in badges:
            text_w = int(d.textlength(b_text, font=f_badge))
            bw = text_w + self._px(36) * ss
            if bx + bw > (W - pad_x * ss):
                bx = pad_x * ss
                by += badge_h + self._px(8) * ss

            # Píldora con fondo de cristal oscuro y borde translúcido
            d.rounded_rectangle(
                (bx, by, bx + bw, by + badge_h),
                radius=badge_h // 2,
                fill=(15, 23, 42, 210),
                outline=(255, 255, 255, 55),
                width=ss,
            )

            # Punto vector luminoso
            accent_col = PALETTE.get(b_color, PALETTE["cyan"])
            dot_cx = bx + self._px(14) * ss
            dot_cy = by + badge_h // 2
            d.ellipse((dot_cx - dot_r, dot_cy - dot_r, dot_cx + dot_r, dot_cy + dot_r), fill=accent_col)

            # Texto de la píldora
            d.text((bx + self._px(25) * ss, dot_cy), b_text, font=f_badge, fill=(255, 255, 255, 255), anchor="lm")
            bx += bw + self._px(8) * ss

        # 4. Sección de texto (Titular y Cuerpo)
        ty = (photo_h + self._px(12)) * ss
        title_color = highlight_color or (15, 23, 42, 255)
        for line in title_lines:
            d.text((pad_x * ss, ty), line, font=f_title, fill=title_color)
            ty += title_lh * ss
        ty += self._px(8) * ss

        for line in body_lines:
            d.text((pad_x * ss, ty), line, font=f_body, fill=(51, 65, 85, 255))
            ty += body_lh * ss
        ty += self._px(16) * ss

        # 5. Pie de metadatos (limpio, sin botones)
        foot_text = f"Fuente oficial • {source_domain}"
        dot_fy = ty + (f_src.size // 2) * ss
        d.ellipse(
            (pad_x * ss, dot_fy - self._px(3) * ss, pad_x * ss + self._px(6) * ss, dot_fy + self._px(3) * ss),
            fill=(100, 116, 139, 255),
        )
        d.text((pad_x * ss + self._px(14) * ss, ty), foot_text, font=f_src, fill=(100, 116, 139, 255), anchor="lt")

        # 6. Redimensionar para antialiasing de precisión
        card = card.resize((w, total_h), Image.LANCZOS)

        # 7. Máscara de esquinas redondeadas
        card_mask = Image.new("L", (w, total_h), 0)
        ImageDraw.Draw(card_mask).rounded_rectangle((0, 0, w - 1, total_h - 1), radius=radius, fill=255)

        # 8. Sombra suave para despegar la tarjeta del video
        margin = self._px(28)
        shadow = Image.new("RGBA", (w + 2 * margin, total_h + 2 * margin), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(shadow)
        s_draw.rounded_rectangle(
            (margin, margin + self._px(6), margin + w, margin + total_h + self._px(6)),
            radius=radius,
            fill=(0, 0, 0, 75),
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(self._px(14)))

        final_img = Image.new("RGBA", (w + 2 * margin, total_h + 2 * margin), (0, 0, 0, 0))
        final_img.paste(shadow, (0, 0), shadow)
        final_img.paste(card, (margin, margin), card_mask)

        # 9. Borde sutil de 1px para nitidez máxima
        border_layer = Image.new("RGBA", (w + 2 * margin, total_h + 2 * margin), (0, 0, 0, 0))
        b_draw = ImageDraw.Draw(border_layer)
        b_draw.rounded_rectangle(
            (margin, margin, margin + w - 1, margin + total_h - 1),
            radius=radius,
            outline=(226, 232, 240, 220),
            width=1,
        )
        final_img = Image.alpha_composite(final_img, border_layer)

        target_out = out_path or Path("card_output.png")
        target_out.parent.mkdir(parents=True, exist_ok=True)
        final_img.save(target_out, "PNG")
        return target_out

    def render(self, card: InfoCard, out_path: Path) -> str:
        """Elige los contenidos y genera la tarjeta con el diseño moderno unificado."""
        domain = card.sources[0].domain if card.sources else "Registro oficial"
        badges = self._build_badges(card)

        # 1. Contradicción / Dato Errado
        if card.verdict == "contradicted":
            if getattr(card, "is_myth", False):
                return self._render_myth_cards(card, out_path)
            headline = card.headline
            body = (
                f"Afirmación en video: «{card.claim}»\n\n"
                f"Dato real verificado: {card.correction or card.corrected_value or card.note}"
            )
            return str(self._render_modern_card(
                headline=headline,
                body=body,
                badges=[("CORRECCIÓN", "red"), ("DATO OFICIAL", "green")] + badges[1:],
                image_path=card.image_path,
                source_domain=card.correction_source or domain,
                out_path=out_path,
            ))

        # 2. Información insuficiente / Alerta
        if card.verdict == "insufficient":
            headline = card.headline
            body = card.note or "No se encontraron registros ni evidencia oficial concluyente que respalden esta afirmación."
            return str(self._render_modern_card(
                headline=headline,
                body=body,
                badges=[("EN REVISIÓN", "amber"), ("SIN REGISTRO", "slate")] + badges[1:],
                image_path=card.image_path,
                source_domain=domain,
                out_path=out_path,
            ))

        # 3. Métrica destacada / Estadística
        style = (getattr(card, "card_style", None) or "reference").lower()
        if (style == "stat_highlight" or card.kind == "cifra") and card.stat_value:
            headline = card.headline
            body = f"Cifra confirmada: {card.stat_value}. {card.body or card.claim}"
            return str(self._render_modern_card(
                headline=headline,
                body=body,
                badges=[("ESTADÍSTICA", "amber"), (card.stat_value[:18], "cyan")] + badges[1:],
                image_path=card.image_path,
                source_domain=domain,
                out_path=out_path,
            ))

        # 4. Referencia estándar (con foto o sin foto)
        headline = card.headline
        body = card.body or card.claim
        return str(self._render_modern_card(
            headline=headline,
            body=body,
            badges=badges,
            image_path=card.image_path,
            source_domain=domain,
            out_path=out_path,
        ))

    def render_photo_frame(self, image_path: str, label: str, out_path: Path) -> Optional[Path]:
        """Foto real enmarcada con el nuevo diseño flotante y badge del concepto."""
        try:
            return self._render_modern_card(
                headline=label.strip(),
                body="Apoyo visual contextual integrado para ilustrar el argumento expuesto.",
                badges=[("APOYO VISUAL", "cyan"), ("FOTO REAL", "green")],
                image_path=image_path,
                source_domain="Registro visual",
                out_path=out_path,
            )
        except Exception as exc:
            print(f"[CardRenderer] No se pudo enmarcar la foto: {exc}")
            return None

    def _render_myth_cards(self, card: InfoCard, out_path: Path) -> str:
        """Renderiza dos tarjetas: la primera 'MITO' y la segunda 'REALIDAD'."""
        path_mito = out_path.with_name(f"{out_path.stem}_mito.png")
        path_real = out_path.with_name(f"{out_path.stem}_real.png")

        domain = card.correction_source or (card.sources[0].domain if card.sources else "Registro oficial")

        # Tarjeta 1: MITO
        self._render_modern_card(
            headline="Mito Popular",
            body=f"«{card.claim}»",
            badges=[("MITO", "red"), ("EN REVISIÓN", "amber")],
            image_path=card.image_path,
            source_domain=domain,
            out_path=path_mito,
        )

        # Tarjeta 2: REALIDAD
        self._render_modern_card(
            headline=card.headline or "Realidad Verificada",
            body=card.correction or card.corrected_value or card.body,
            badges=[("REALIDAD", "green"), ("DATO OFICIAL", "cyan")],
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
