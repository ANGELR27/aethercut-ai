"""Módulo de renderizado de tarjetas gráficas (Info Cards) de alto impacto visual.

Estilo Pinterest / Modern Bento Glassmorphism:
- Diseño compacto, elegante y sin espacios vacíos.
- Soporte para tema Oscuro (Obsidian Glass) y Claro (Porcelain Snow Glass).
- Formato Bento horizontal para tarjetas con foto: miniatura redondeada a la izquierda,
  tipografía grande, nítida y de alto contraste a la derecha.
- Formato Floating Widget para datos de solo texto: altura auto-ajustada al contenido,
  micro-badge con indicador luminoso y pie de fuente verificado.
- Sombra difusa multicapa (ambient drop shadow) y sutil reflejo de cristal superior (rim highlight).
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from core.models import InfoCard

FONT_DIR = Path("C:/Windows/Fonts")

# Paletas calibradas para micro-badges en estilo Negro Mate con Blanco puro (Zero azul, Zero morado)
BADGE_THEMES = {
    "white": {
        "dark": {"bg": (22, 22, 22, 255), "border": (255, 255, 255, 75), "text": (255, 255, 255, 255), "pip": (255, 255, 255, 255)},
        "light": {"bg": (245, 245, 245, 255), "border": (210, 210, 210, 255), "text": (15, 15, 15, 255), "pip": (15, 15, 15, 255)},
    },
    "green": {
        "dark": {"bg": (22, 22, 22, 255), "border": (255, 255, 255, 60), "text": (255, 255, 255, 255), "pip": (52, 211, 153, 255)},
        "light": {"bg": (241, 245, 249, 255), "border": (226, 232, 240, 255), "text": (15, 23, 42, 255), "pip": (16, 185, 129, 255)},
    },
    "amber": {
        "dark": {"bg": (22, 22, 22, 255), "border": (255, 255, 255, 60), "text": (255, 255, 255, 255), "pip": (251, 191, 36, 255)},
        "light": {"bg": (241, 245, 249, 255), "border": (226, 232, 240, 255), "text": (15, 23, 42, 255), "pip": (245, 158, 11, 255)},
    },
    "red": {
        "dark": {"bg": (22, 22, 22, 255), "border": (255, 255, 255, 60), "text": (255, 255, 255, 255), "pip": (248, 113, 113, 255)},
        "light": {"bg": (241, 245, 249, 255), "border": (226, 232, 240, 255), "text": (15, 23, 42, 255), "pip": (239, 68, 68, 255)},
    },
    "cyan": {
        "dark": {"bg": (22, 22, 22, 255), "border": (255, 255, 255, 75), "text": (255, 255, 255, 255), "pip": (255, 255, 255, 255)},
        "light": {"bg": (241, 245, 249, 255), "border": (226, 232, 240, 255), "text": (15, 23, 42, 255), "pip": (6, 182, 212, 255)},
    },
    "purple": {
        "dark": {"bg": (22, 22, 22, 255), "border": (255, 255, 255, 75), "text": (255, 255, 255, 255), "pip": (255, 255, 255, 255)},
        "light": {"bg": (241, 245, 249, 255), "border": (226, 232, 240, 255), "text": (15, 23, 42, 255), "pip": (168, 85, 247, 255)},
    },
}

KIND_LABELS = {
    "ley": ("NORMATIVA LEGAL", "white"),
    "normativa": ("NORMATIVA OFICIAL", "white"),
    "articulo": ("ARTÍCULO LEGAL", "white"),
    "cifra": ("ESTADÍSTICA", "white"),
    "estadistica": ("ESTADÍSTICA", "white"),
    "fecha": ("CRONOLOGÍA", "white"),
    "persona": ("PERFIL", "white"),
    "lugar": ("UBICACIÓN", "white"),
    "organizacion": ("INSTITUCIÓN", "white"),
    "organización": ("INSTITUCIÓN", "white"),
    "hardware": ("ESPECIFICACIÓN", "white"),
    "concepto": ("CONCEPTO CLAVE", "white"),
    "complemento": ("REFUERZO CLAVE", "white"),
    "refuerzo": ("REFUERZO CLAVE", "white"),
    "dato_extra": ("DATO EXTRA", "white"),
    "impacto": ("ESTUDIO DE IMPACTO", "white"),
    "contexto": ("CONTEXTO GLOBAL", "white"),
    "dato": ("DATO VERIFICADO", "white"),
    "confirmacion": ("CONFIRMADO", "white"),
    "confirmación": ("CONFIRMADO", "white"),
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
    Renderizador de tarjetas estilo Pinterest / Bento Glassmorphism.
    """

    def __init__(self, frame_w: int, frame_h: int, theme: str = "dark"):
        self.frame_w = frame_w
        self.frame_h = frame_h
        self.theme = theme if theme in ("dark", "light") else "dark"
        self.portrait = frame_h > frame_w

    @staticmethod
    def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int, max_lines: int) -> List[str]:
        lines: List[str] = []
        for p in (text or "").split("\n"):
            p = p.strip()
            if not p:
                continue
            words = p.split()
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

        return ("DATO CONFIRMADO", "green")

    def _render_pinterest_glass_card(
        self,
        headline: str,
        body: str,
        badge_text: str,
        badge_tone: str = "white",
        image_path: Optional[str] = None,
        source_domain: str = "Registro oficial",
        out_path: Optional[Path] = None,
    ) -> Path:
        """
        Renderiza la tarjeta con estética Pinterest Glassmorphism compacta y elegante.
        """
        scale = 2  # Super-sampling para máxima nitidez

        # Fuentes calibradas
        f_badge = _font(["segoeuib.ttf", "arialbd.ttf"], 11 * scale)
        f_title = _font(["segoeuib.ttf", "arialbd.ttf"], 19 * scale)
        f_body = _font(["segoeui.ttf", "arial.ttf"], 14 * scale)
        f_src = _font(["segoeuib.ttf", "segoeui.ttf"], 11 * scale)

        # Paleta según tema
        if self.theme == "dark":
            # Negro mate puro (Strictly R=G=B, Zero azul, Zero morado) con blanco puro de alto contraste
            bg_card_top = (14, 14, 14, 252)
            bg_card_bot = (7, 7, 7, 254)
            border_top = (255, 255, 255, 60)
            title_color = (255, 255, 255, 255)
            body_color = (245, 245, 245, 255)
            src_color = (175, 175, 175, 245)
            shadow_color = (0, 0, 0, 180)
        else:
            bg_card_top = (255, 255, 255, 248)
            bg_card_bot = (245, 247, 250, 252)
            border_top = (255, 255, 255, 230)
            title_color = (15, 23, 42, 255)
            body_color = (51, 65, 85, 255)
            src_color = (100, 116, 139, 230)
            shadow_color = (15, 23, 42, 50)

        bcfg = BADGE_THEMES.get(badge_tone, BADGE_THEMES["white"])[self.theme]
        badge_bg = bcfg["bg"]
        badge_border = bcfg["border"]
        badge_txt_col = bcfg["text"]
        pip_col = bcfg["pip"]

        has_photo = bool(image_path and Path(image_path).exists())

        # Dimensiones compactas y ergonómicas
        card_w = 480 if not has_photo else 560
        if self.portrait:
            card_w = min(card_w, int(self.frame_w * 0.88))

        pad_x = 22
        pad_y = 20
        radius = 18

        # Layout horizontal si hay foto (Bento split)
        photo_w = 150 if has_photo else 0
        photo_gap = 18 if has_photo else 0

        text_avail_w = card_w - (pad_x * 2) - photo_w - photo_gap

        probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        title_lines = self._wrap(probe, headline, f_title, text_avail_w * scale, max_lines=2)
        body_lines = self._wrap(probe, body, f_body, text_avail_w * scale, max_lines=4)

        title_lh = int(24 * scale)
        body_lh = int(19 * scale)
        badge_h = int(22 * scale)

        content_h_px = (
            badge_h
            + int(10 * scale)
            + (len(title_lines) * title_lh)
            + int(6 * scale)
            + (len(body_lines) * body_lh)
            + int(10 * scale)
            + int(14 * scale)
        )
        content_h = content_h_px // scale

        if has_photo:
            photo_h = max(content_h, 115)
            card_h = max(content_h + (pad_y * 2), photo_h + (pad_y * 2))
        else:
            card_h = content_h + (pad_y * 2)

        W = card_w * scale
        H = card_h * scale
        R = radius * scale

        # 1. Gradiente translúcido
        card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        c_draw = ImageDraw.Draw(card)
        for y in range(H):
            t = y / max(1, H - 1)
            r = int(bg_card_top[0] * (1 - t) + bg_card_bot[0] * t)
            g = int(bg_card_top[1] * (1 - t) + bg_card_bot[1] * t)
            b = int(bg_card_top[2] * (1 - t) + bg_card_bot[2] * t)
            a = int(bg_card_top[3] * (1 - t) + bg_card_bot[3] * t)
            c_draw.line([(0, y), (W, y)], fill=(r, g, b, a))

        # 2. Máscara redondeada
        round_mask = Image.new("L", (W, H), 0)
        ImageDraw.Draw(round_mask).rounded_rectangle((0, 0, W - 1, H - 1), radius=R, fill=255)
        card_masked = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        card_masked.paste(card, (0, 0), round_mask)
        d = ImageDraw.Draw(card_masked)

        # 3. Foto a la izquierda si existe
        text_start_x = (pad_x + photo_w + photo_gap) * scale if has_photo else pad_x * scale
        if has_photo:
            pw = photo_w * scale
            ph = (card_h - (pad_y * 2)) * scale
            px_pos = pad_x * scale
            py_pos = pad_y * scale
            pr = 12 * scale

            try:
                raw = Image.open(image_path).convert("RGB")
                ratio = max(pw / raw.width, ph / raw.height)
                resized = raw.resize((int(raw.width * ratio) + 1, int(raw.height * ratio) + 1), Image.LANCZOS)
                left = (resized.width - pw) // 2
                top = (resized.height - ph) // 2
                cropped = resized.crop((left, top, left + pw, top + ph)).convert("RGBA")

                pmask = Image.new("L", (pw, ph), 0)
                ImageDraw.Draw(pmask).rounded_rectangle((0, 0, pw - 1, ph - 1), radius=pr, fill=255)
                card_masked.paste(cropped, (px_pos, py_pos), pmask)

                # Borde sutil a la miniatura
                d.rounded_rectangle(
                    (px_pos, py_pos, px_pos + pw - 1, py_pos + ph - 1),
                    radius=pr,
                    outline=(255, 255, 255, 50) if self.theme == "dark" else (0, 0, 0, 25),
                    width=1 * scale,
                )
            except Exception as exc:
                print(f"[CardRenderer] Error procesando imagen {image_path}: {exc}")

        # 4. Texto
        cur_y = pad_y * scale

        # Micro-badge estilo Pinterest
        b_text = badge_text.upper()
        tw = d.textlength(b_text, font=f_badge)
        b_w = int(tw + (24 * scale))
        b_rect = (text_start_x, cur_y, text_start_x + b_w, cur_y + badge_h)
        d.rounded_rectangle(b_rect, radius=badge_h // 2, fill=badge_bg, outline=badge_border, width=1 * scale)

        # Indicador luminoso
        dot_r = 3 * scale
        dot_cx = text_start_x + (8 * scale)
        dot_cy = cur_y + (badge_h // 2)
        d.ellipse((dot_cx - dot_r, dot_cy - dot_r, dot_cx + dot_r, dot_cy + dot_r), fill=pip_col)

        # Etiqueta de badge
        d.text((text_start_x + (16 * scale), dot_cy), b_text, font=f_badge, fill=badge_txt_col, anchor="lm")
        cur_y += badge_h + int(10 * scale)

        # Titular Bold nítido
        for line in title_lines:
            d.text((text_start_x, cur_y), line, font=f_title, fill=title_color)
            cur_y += title_lh
        cur_y += int(6 * scale)

        # Cuerpo
        for line in body_lines:
            d.text((text_start_x, cur_y), line, font=f_body, fill=body_color)
            cur_y += body_lh
        cur_y += int(10 * scale)

        # Fuente
        src_text = f"Fuente: {source_domain}"
        d.text((text_start_x, cur_y), src_text, font=f_src, fill=src_color)

        # Downscale con Lanczos
        card_final = card_masked.resize((card_w, card_h), Image.LANCZOS)

        # 5. Sombra difusa multicapa (ambient drop shadow)
        margin = 24
        shadow = Image.new("RGBA", (card_w + 2 * margin, card_h + 2 * margin), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(shadow)
        s_draw.rounded_rectangle(
            (margin, margin + 6, margin + card_w, margin + card_h + 6),
            radius=radius,
            fill=shadow_color,
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(12))

        # Compuesto final
        out_img = Image.new("RGBA", (card_w + 2 * margin, card_h + 2 * margin), (0, 0, 0, 0))
        out_img.paste(shadow, (0, 0), shadow)
        out_img.paste(card_final, (margin, margin), card_final)

        # Borde de cristal con luz superior
        border_img = Image.new("RGBA", (card_w + 2 * margin, card_h + 2 * margin), (0, 0, 0, 0))
        b_draw = ImageDraw.Draw(border_img)
        b_draw.rounded_rectangle(
            (margin, margin, margin + card_w - 1, margin + card_h - 1),
            radius=radius,
            outline=border_top,
            width=1,
        )
        out_img = Image.alpha_composite(out_img, border_img)

        target_out = out_path or Path("card_output.png")
        target_out.parent.mkdir(parents=True, exist_ok=True)
        out_img.save(target_out, "PNG")
        return target_out

    def render(self, card: InfoCard, out_path: Path) -> str:
        """Renderiza la tarjeta con el diseño Pinterest Bento Glassmorphism."""
        domain = card.sources[0].domain if card.sources else "Registro oficial"
        badge_text, badge_tone = self._get_single_badge(card)

        # 1. Contradicción / Corrección
        if card.verdict == "contradicted":
            if getattr(card, "is_myth", False):
                return self._render_myth_cards(card, out_path)
            headline = card.headline
            correction_text = card.correction or card.corrected_value or card.note
            body = f"Afirmación: «{card.claim}»\n\nDato real confirmado: {correction_text}"
            return str(self._render_pinterest_glass_card(
                headline=headline,
                body=body,
                badge_text="CORRECCIÓN OFICIAL",
                badge_tone="red",
                image_path=card.image_path,
                source_domain=card.correction_source or domain,
                out_path=out_path,
            ))

        # 2. Insuficiente evidencia
        if card.verdict == "insufficient":
            headline = card.headline
            body = card.note or "No se encontraron registros ni evidencia oficial concluyente que respalden esta afirmación."
            return str(self._render_pinterest_glass_card(
                headline=headline,
                body=body,
                badge_text="EN REVISIÓN",
                badge_tone="amber",
                image_path=card.image_path,
                source_domain=domain,
                out_path=out_path,
            ))

        # 3. Estadística / Cifra
        if card.stat_value:
            headline = card.headline
            body = f"Cifra confirmada: {card.stat_value}. {card.body or card.claim}"
            return str(self._render_pinterest_glass_card(
                headline=headline,
                body=body,
                badge_text=f"DATO CLAVE: {card.stat_value[:18]}",
                badge_tone="amber",
                image_path=card.image_path,
                source_domain=domain,
                out_path=out_path,
            ))

        # 4. Referencia o Apoyo visual estándar
        headline = card.headline
        body = card.body or card.claim
        return str(self._render_pinterest_glass_card(
            headline=headline,
            body=body,
            badge_text=badge_text,
            badge_tone=badge_tone,
            image_path=card.image_path,
            source_domain=domain,
            out_path=out_path,
        ))

    def render_photo_frame(self, image_path: str, label: str, out_path: Path) -> Optional[Path]:
        """Foto contextual enmarcada en formato Bento con badge de apoyo visual."""
        try:
            return self._render_pinterest_glass_card(
                headline=label.strip(),
                body="Apoyo visual contextual integrado para ilustrar el argumento expuesto.",
                badge_text="APOYO VISUAL",
                badge_tone="green",
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

        self._render_pinterest_glass_card(
            headline="Mito Popular",
            body=f"«{card.claim}»",
            badge_text="MITO POPULAR",
            badge_tone="amber",
            image_path=card.image_path,
            source_domain=domain,
            out_path=path_mito,
        )

        self._render_pinterest_glass_card(
            headline=card.headline or "Realidad Verificada",
            body=card.correction or card.corrected_value or card.body,
            badge_text="REALIDAD CONFIRMADA",
            badge_tone="green",
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
