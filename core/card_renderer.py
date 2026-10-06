import re
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from core.models import InfoCard

FONT_DIR = Path("C:/Windows/Fonts")

# Paleta premium Nate Gentile / Platzi (True Glassmorphism)
BG = (10, 10, 14, 160)           # Transparente oscuro (Glass)
BG_ALT = (18, 18, 24, 180)       # Contenedores secundarios translúcidos
BORDER = (80, 85, 100, 180)      # Borde más visible para efecto cristal
BORDER_ACCENT = (99, 102, 241, 220) # Indigo sutil Nate Gentile
TXT = (255, 255, 255, 255)       # Blanco puro
MUTED = (190, 195, 210, 255)     # Gris texto explicativo brillante
DIM = (120, 130, 140, 255)       # Metadatos
GREEN = (52, 211, 153, 255)      # Esmeralda / Verificado
CHIP_BG = (16, 185, 129, 60)
BLUE_ACCENT = (56, 189, 248, 255) # Cyan Platzi
AMBER = (251, 191, 36, 255)      # Ámbar destacados

KIND_LABELS = {
    "ley": "LEY / NORMATIVA",
    "cifra": "ESTADÍSTICA / DATO",
    "fecha": "CRONOLOGÍA",
    "persona": "PERFIL / BIOGRAFÍA",
    "lugar": "UBICACIÓN",
    "organizacion": "INSTITUCIÓN",
    "organización": "INSTITUCIÓN",
    "hardware": "ESPECIFICACIÓN TÉCNICA",
    "concepto": "GLOSARIO / CONCEPTO",
    "dato": "REFERENCIA VERIFICADA",
}


def _font(names: List[str], size: int) -> ImageFont.FreeTypeFont:
    for name in names:
        path = FONT_DIR / name
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


class InfoCardRenderer:
    """
    Renderizador de tarjetas gráficas premium estilo Platzi y Nate Gentile:
    - Reference Callouts: Foto real, etiqueta verificada, titular y resumen.
    - Browser Mockup: Marco tipo navegador con botones macOS, barra de dirección y titular de prensa/wiki.
    - Stat Highlight: Métrica gigante destacada (+78%, USD 50M) con barra de contexto.
    - Tech Spec: Ficha técnica con borde de acento e ícono.
    """

    def __init__(self, frame_w: int, frame_h: int):
        portrait = frame_h > frame_w
        # Escala adecuada para que sea muy legible en 1080p sin tapar el centro de la pantalla
        self.card_w = int(frame_w * (0.86 if portrait else 0.34))
        self.card_w = max(self.card_w, 380)
        self.s = self.card_w / 640.0

    def _px(self, v: float) -> int:
        return max(1, int(round(v * self.s)))

    @staticmethod
    def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int, max_lines: int) -> List[str]:
        words, lines, cur = text.split(), [], ""
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
        left, top = (img.width - w) // 2, (img.height - h) // 3
        return img.crop((left, top, left + w, top + h))

    def render(self, card: InfoCard, out_path: Path) -> str:
        """Elige el diseño según card_style o tipo de dato."""
        if card.verdict == "contradicted":
            if getattr(card, "is_myth", False):
                return self._render_myth_cards(card, out_path)
            return str(self._render_correction_card(card, out_path))
        if card.verdict == "insufficient":
            return str(self._render_unverifiable_card(card, out_path))
            
        style = (getattr(card, "card_style", None) or "reference").lower()
        kind = (card.kind or "").lower()
        if style == "mockup_browser" or kind in ("ley", "articulo", "noticia"):
            return str(self._render_browser_mockup(card, out_path))
        if (style == "stat_highlight" or kind == "cifra") and self._stat_text(card):
            return str(self._render_stat_highlight(card, out_path))
        return str(self._render_reference_callout(card, out_path))

    @staticmethod
    def _stat_text(card: InfoCard) -> str:
        if card.stat_value:
            return card.stat_value
        m = re.search(r"([+\-]?(?:US\$|\$|USD\s?)?\d[\d.,]*\s?%?)", card.body or "")
        return m.group(1).strip() if m else ""

    def render_photo_frame(self, image_path: str, label: str, out_path: Path) -> Optional[Path]:
        """Foto real enmarcada como tarjeta flotante (para B-Roll de imagen), con chip del concepto."""
        try:
            pad = self._px(12)
            w = int(self.card_w * 1.05)
            photo_w = w - 2 * pad
            photo_h = int(photo_w * 9 / 16)
            f_chip = _font(["segoeuib.ttf", "arialbd.ttf"], self._px(17))
            chip_h = self._px(34)
            h = pad + photo_h + self._px(10) + chip_h + pad

            ss = 2
            canvas = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
            ImageDraw.Draw(canvas).rounded_rectangle(
                (0, 0, w * ss - 1, h * ss - 1), radius=self._px(22) * ss, fill=BG, outline=BORDER, width=2 * ss)
            canvas = canvas.resize((w, h), Image.LANCZOS)
            d = ImageDraw.Draw(canvas)

            photo = self._cover(Image.open(image_path), photo_w, photo_h).convert("RGBA")
            mask = Image.new("L", photo.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, photo_w - 1, photo_h - 1), radius=self._px(14), fill=255)
            canvas.paste(photo, (pad, pad), mask)

            y = pad + photo_h + self._px(10)
            text = label.strip()[:48]
            d.ellipse((pad + self._px(4), y + chip_h // 2 - self._px(5), pad + self._px(14), y + chip_h // 2 + self._px(5)), fill=BLUE_ACCENT)
            d.text((pad + self._px(24), y + chip_h // 2), text, font=f_chip, fill=TXT, anchor="lm")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            canvas.save(out_path, "PNG")
            return out_path
        except Exception as exc:
            print(f"[CardRenderer] No se pudo enmarcar la foto: {exc}")
            return None

    # ---------------------------------------------------------
    # 1. Estilo Reference Callout (Nate Gentile / Platzi estándar)
    # ---------------------------------------------------------
    def _render_reference_callout(self, card: InfoCard, out_path: Path) -> Path:
        pad = self._px(22)
        inner_w = self.card_w - 2 * pad

        f_chip = _font(["segoeuib.ttf", "arialbd.ttf"], self._px(14))
        f_title = _font(["segoeuib.ttf", "arialbd.ttf"], self._px(28))
        f_body = _font(["segoeui.ttf", "arial.ttf"], self._px(19))
        f_src = _font(["segoeui.ttf", "arial.ttf"], self._px(15))

        probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        title_lines = self._wrap(probe, card.headline, f_title, inner_w, 2)
        body_lines = self._wrap(probe, card.body or card.claim, f_body, inner_w, 4)

        has_photo = bool(card.image_path and Path(card.image_path).exists())
        photo_h = self._px(230) if has_photo else 0
        chip_h = self._px(28)
        title_lh = f_title.size + self._px(6)
        body_lh = f_body.size + self._px(7)

        h = pad
        if photo_h:
            h += photo_h + self._px(14)
        h += chip_h + self._px(12)
        h += len(title_lines) * title_lh + self._px(8)
        h += len(body_lines) * body_lh + self._px(14)
        h += self._px(1) + self._px(12) + f_src.size + pad

        # Supermuestreo 2x
        ss = 2
        W, H = self.card_w * ss, h * ss
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(canvas)
        radius = self._px(24) * ss

        # Fondo translúcido con gradiente de borde
        d.rounded_rectangle((0, 0, W - 1, H - 1), radius=radius, fill=BG, outline=BORDER, width=2 * ss)
        # Glow superior sutil
        d.line((radius, 1, W - radius, 1), fill=BORDER_ACCENT, width=3 * ss)

        canvas = canvas.resize((self.card_w, h), Image.LANCZOS)
        d = ImageDraw.Draw(canvas)

        y = pad
        if photo_h:
            try:
                photo = self._cover(Image.open(card.image_path), inner_w, photo_h).convert("RGBA")
                mask = Image.new("L", photo.size, 0)
                ImageDraw.Draw(mask).rounded_rectangle(
                    (0, 0, photo.width - 1, photo.height - 1), radius=self._px(16), fill=255
                )
                canvas.paste(photo, (pad, y), mask)
            except Exception as exc:
                print(f"[CardRenderer] Foto falló: {exc}")
            y += photo_h + self._px(14)

        # Chips
        chip_w = int(d.textlength("VERIFICADO", font=f_chip)) + self._px(36)
        d.rounded_rectangle((pad, y, pad + chip_w, y + chip_h), radius=chip_h // 2, fill=CHIP_BG, outline=(52, 211, 153, 90))
        cy = y + chip_h // 2
        d.ellipse((pad + self._px(11), cy - self._px(4), pad + self._px(19), cy + self._px(4)), fill=GREEN)
        d.text((pad + self._px(26), cy), "VERIFICADO", font=f_chip, fill=GREEN, anchor="lm")

        kind_text = KIND_LABELS.get((card.kind or "dato").lower(), "REFERENCIA")
        d.text((self.card_w - pad, cy), kind_text, font=f_chip, fill=DIM, anchor="rm")
        y += chip_h + self._px(12)

        for line in title_lines:
            d.text((pad, y), line, font=f_title, fill=TXT)
            y += title_lh
        y += self._px(6)

        for line in body_lines:
            d.text((pad, y), line, font=f_body, fill=MUTED)
            y += body_lh
        y += self._px(14)

        d.line((pad, y, self.card_w - pad, y), fill=BORDER, width=max(1, self._px(1)))
        y += self._px(12)
        domain = card.sources[0].domain if card.sources else "Fuente oficial"
        extra = f" (+{len(card.sources) - 1} fuentes)" if len(card.sources) > 1 else ""
        d.text((pad, y), f"Fuente: {domain}{extra}", font=f_src, fill=DIM)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(out_path, "PNG")
        return out_path

    # ---------------------------------------------------------
    # 2. Estilo Mockup Browser (Nate Gentile: ventana de artículo)
    # ---------------------------------------------------------
    def _render_browser_mockup(self, card: InfoCard, out_path: Path) -> Path:
        pad = self._px(20)
        inner_w = self.card_w - 2 * pad

        f_url = _font(["segoeui.ttf", "arial.ttf"], self._px(14))
        f_title = _font(["segoeuib.ttf", "arialbd.ttf"], self._px(26))
        f_body = _font(["segoeui.ttf", "arial.ttf"], self._px(18))
        f_src = _font(["segoeui.ttf", "arial.ttf"], self._px(14))

        probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        title_lines = self._wrap(probe, card.headline, f_title, inner_w, 2)
        body_lines = self._wrap(probe, card.body or card.claim, f_body, inner_w, 4)

        has_photo = bool(card.image_path and Path(card.image_path).exists())
        photo_h = self._px(190) if has_photo else 0
        header_bar_h = self._px(36)
        title_lh = f_title.size + self._px(5)
        body_lh = f_body.size + self._px(6)

        h = header_bar_h + pad
        if photo_h:
            h += photo_h + self._px(14)
        h += len(title_lines) * title_lh + self._px(8)
        h += len(body_lines) * body_lh + self._px(14)
        h += self._px(1) + self._px(10) + f_src.size + pad

        ss = 2
        W, H = self.card_w * ss, h * ss
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(canvas)
        radius = self._px(22) * ss

        d.rounded_rectangle((0, 0, W - 1, H - 1), radius=radius, fill=BG, outline=BORDER, width=2 * ss)
        canvas = canvas.resize((self.card_w, h), Image.LANCZOS)
        d = ImageDraw.Draw(canvas)

        # Barra estilo navegador macOS
        d.rounded_rectangle((0, 0, self.card_w, header_bar_h), radius=0, fill=BG_ALT)
        d.line((0, header_bar_h, self.card_w, header_bar_h), fill=BORDER, width=1)

        # 3 botones macOS (rojo, amarillo, verde)
        dot_r = self._px(5)
        cy = header_bar_h // 2
        d.ellipse((pad, cy - dot_r, pad + 2 * dot_r, cy + dot_r), fill=(239, 68, 68, 255))
        d.ellipse((pad + self._px(16), cy - dot_r, pad + self._px(16) + 2 * dot_r, cy + dot_r), fill=(245, 158, 11, 255))
        d.ellipse((pad + self._px(32), cy - dot_r, pad + self._px(32) + 2 * dot_r, cy + dot_r), fill=(16, 185, 129, 255))

        # Barra de dirección URL en el mockup
        bar_x = pad + self._px(52)
        bar_w = self.card_w - bar_x - pad
        d.rounded_rectangle((bar_x, self._px(6), bar_x + bar_w, header_bar_h - self._px(6)), radius=self._px(6), fill=(30, 30, 38, 255))
        domain = card.sources[0].domain if card.sources else "es.wikipedia.org"
        d.text((bar_x + self._px(12), cy), f"https://{domain}/doc", font=f_url, fill=MUTED, anchor="lm")

        y = header_bar_h + pad
        if photo_h:
            try:
                photo = self._cover(Image.open(card.image_path), inner_w, photo_h).convert("RGBA")
                mask = Image.new("L", photo.size, 0)
                ImageDraw.Draw(mask).rounded_rectangle(
                    (0, 0, photo.width - 1, photo.height - 1), radius=self._px(12), fill=255
                )
                canvas.paste(photo, (pad, y), mask)
            except Exception as exc:
                print(f"[CardRenderer] Foto mockup falló: {exc}")
            y += photo_h + self._px(14)

        for line in title_lines:
            d.text((pad, y), line, font=f_title, fill=TXT)
            y += title_lh
        y += self._px(6)

        for line in body_lines:
            d.text((pad, y), line, font=f_body, fill=MUTED)
            y += body_lh
        y += self._px(14)

        d.line((pad, y, self.card_w - pad, y), fill=BORDER, width=max(1, self._px(1)))
        y += self._px(10)
        d.text((pad, y), f"Referencia confirmada • {domain}", font=f_src, fill=BLUE_ACCENT)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(out_path, "PNG")
        return out_path

    # ---------------------------------------------------------
    # 3. Estilo Stat / Cifra Gigante (Platzi: números impactantes)
    # ---------------------------------------------------------
    def _render_stat_highlight(self, card: InfoCard, out_path: Path) -> Path:
        pad = self._px(22)
        inner_w = self.card_w - 2 * pad

        f_chip = _font(["segoeuib.ttf", "arialbd.ttf"], self._px(14))
        f_num = _font(["segoeuib.ttf", "arialbd.ttf"], self._px(46)) # Número gigante
        f_title = _font(["segoeuib.ttf", "arialbd.ttf"], self._px(24))
        f_body = _font(["segoeui.ttf", "arial.ttf"], self._px(18))
        f_src = _font(["segoeui.ttf", "arial.ttf"], self._px(14))

        # Intentar extraer la cifra destacada o usar la primera palabra clave
        stat_text = self._stat_text(card) or "DATO"

        probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        body_lines = self._wrap(probe, card.body or card.claim, f_body, inner_w, 3)

        num_lh = f_num.size + self._px(8)
        body_lh = f_body.size + self._px(6)
        chip_h = self._px(28)

        h = pad + chip_h + self._px(12) + num_lh + self._px(6) + f_title.size + self._px(12)
        h += len(body_lines) * body_lh + self._px(16) + self._px(1) + self._px(12) + f_src.size + pad

        ss = 2
        W, H = self.card_w * ss, h * ss
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(canvas)
        radius = self._px(24) * ss

        d.rounded_rectangle((0, 0, W - 1, H - 1), radius=radius, fill=BG, outline=BORDER, width=2 * ss)
        # Línea de acento verde/cyan brillante a la izquierda estilo dashboard Platzi
        d.line((1, radius, 1, H - radius), fill=BLUE_ACCENT, width=6 * ss)

        canvas = canvas.resize((self.card_w, h), Image.LANCZOS)
        d = ImageDraw.Draw(canvas)

        y = pad
        # Chip
        d.rounded_rectangle((pad, y, pad + self._px(130), y + chip_h), radius=chip_h // 2, fill=(56, 189, 248, 30), outline=(56, 189, 248, 100))
        d.text((pad + self._px(65), y + chip_h // 2), "MÉTRICA / DATO", font=f_chip, fill=BLUE_ACCENT, anchor="mm")
        y += chip_h + self._px(12)

        # Cifra gigante
        d.text((pad, y), stat_text, font=f_num, fill=AMBER)
        y += num_lh

        # Titular del dato
        d.text((pad, y), card.headline, font=f_title, fill=TXT)
        y += f_title.size + self._px(12)

        for line in body_lines:
            d.text((pad, y), line, font=f_body, fill=MUTED)
            y += body_lh
        y += self._px(14)

        d.line((pad, y, self.card_w - pad, y), fill=BORDER, width=max(1, self._px(1)))
        y += self._px(12)
        domain = card.sources[0].domain if card.sources else "Dato verificado"
        d.text((pad, y), f"Fuente: {domain} • Registro verificado", font=f_src, fill=DIM)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(out_path, "PNG")
        return out_path

    # ---------------------------------------------------------
    # 4. Estilo Correction / Dato Errado
    # ---------------------------------------------------------
    def _render_correction_card(self, card: InfoCard, out_path: Path) -> Path:
        pad = self._px(22)
        inner_w = self.card_w - 2 * pad

        f_chip = _font(["segoeuib.ttf", "arialbd.ttf"], self._px(14))
        f_title = _font(["segoeuib.ttf", "arialbd.ttf"], self._px(26))
        f_claim = _font(["segoeui.ttf", "arial.ttf"], self._px(16))
        f_body = _font(["segoeui.ttf", "arial.ttf"], self._px(18))
        f_src = _font(["segoeui.ttf", "arial.ttf"], self._px(14))

        probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        title_lines = self._wrap(probe, card.corrected_value or card.headline, f_title, inner_w, 2)
        claim_lines = self._wrap(probe, f"Dijo: \"{card.claim}\"", f_claim, inner_w, 2)
        body_lines = self._wrap(probe, card.correction, f_body, inner_w, 4)

        chip_h = self._px(28)
        title_lh = f_title.size + self._px(6)
        claim_lh = f_claim.size + self._px(4)
        body_lh = f_body.size + self._px(6)

        h = pad + chip_h + self._px(12)
        h += len(title_lines) * title_lh + self._px(8)
        h += len(claim_lines) * claim_lh + self._px(12)
        h += len(body_lines) * body_lh + self._px(14)
        h += self._px(1) + self._px(12) + f_src.size + pad

        ss = 2
        W, H = self.card_w * ss, h * ss
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(canvas)
        radius = self._px(24) * ss

        # Red styling for correction
        d.rounded_rectangle((0, 0, W - 1, H - 1), radius=radius, fill=(24, 12, 12, 180), outline=(220, 38, 38, 200), width=2 * ss)
        d.line((1, radius, 1, H - radius), fill=(239, 68, 68, 255), width=6 * ss)

        canvas = canvas.resize((self.card_w, h), Image.LANCZOS)
        d = ImageDraw.Draw(canvas)

        y = pad
        # Chip DATO ERRADO
        d.rounded_rectangle((pad, y, pad + self._px(145), y + chip_h), radius=chip_h // 2, fill=(239, 68, 68, 40), outline=(239, 68, 68, 120))
        d.ellipse((pad + self._px(11), y + chip_h // 2 - self._px(4), pad + self._px(19), y + chip_h // 2 + self._px(4)), fill=(239, 68, 68, 255))
        d.text((pad + self._px(26), y + chip_h // 2), "DATO ERRADO", font=f_chip, fill=(239, 68, 68, 255), anchor="lm")
        y += chip_h + self._px(12)

        # Title (Corrected Value)
        for line in title_lines:
            d.text((pad, y), line, font=f_title, fill=TXT)
            y += title_lh
        y += self._px(6)
        
        # What they said (Claim)
        for line in claim_lines:
            d.text((pad, y), line, font=f_claim, fill=(156, 163, 175, 255))
            d.line((pad, y + claim_lh // 2, pad + d.textlength(line, font=f_claim), y + claim_lh // 2), fill=(156, 163, 175, 255), width=1) # Strikethrough
            y += claim_lh
        y += self._px(12)

        # Correction text
        for line in body_lines:
            d.text((pad, y), line, font=f_body, fill=TXT)
            y += body_lh
        y += self._px(14)

        d.line((pad, y, self.card_w - pad, y), fill=(239, 68, 68, 100), width=max(1, self._px(1)))
        y += self._px(12)
        domain = card.correction_source or (card.sources[0].domain if card.sources else "Dato verificado")
        d.text((pad, y), f"Corrección verificada: {domain}", font=f_src, fill=(239, 68, 68, 255))

        out_path.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(out_path, "PNG")
        return out_path

    # ---------------------------------------------------------
    # 5. Estilo Unverifiable / Información no verificable
    # ---------------------------------------------------------
    def _render_unverifiable_card(self, card: InfoCard, out_path: Path) -> Path:
        pad = self._px(22)
        inner_w = self.card_w - 2 * pad

        f_chip = _font(["segoeuib.ttf", "arialbd.ttf"], self._px(14))
        f_title = _font(["segoeuib.ttf", "arialbd.ttf"], self._px(26))
        f_body = _font(["segoeui.ttf", "arial.ttf"], self._px(18))

        probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        title_lines = self._wrap(probe, card.headline, f_title, inner_w, 2)
        body_lines = self._wrap(probe, card.body or "No se pudo verificar esta información con fuentes confiables.", f_body, inner_w, 4)

        chip_h = self._px(28)
        title_lh = f_title.size + self._px(6)
        body_lh = f_body.size + self._px(6)

        h = pad + chip_h + self._px(12)
        h += len(title_lines) * title_lh + self._px(8)
        h += len(body_lines) * body_lh + self._px(14)
        h += pad

        ss = 2
        W, H = self.card_w * ss, h * ss
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(canvas)
        radius = self._px(24) * ss

        # Gray/Orange styling for unverifiable
        d.rounded_rectangle((0, 0, W - 1, H - 1), radius=radius, fill=(24, 24, 28, 180), outline=(156, 163, 175, 200), width=2 * ss)
        d.line((1, radius, 1, H - radius), fill=(245, 158, 11, 255), width=6 * ss)

        canvas = canvas.resize((self.card_w, h), Image.LANCZOS)
        d = ImageDraw.Draw(canvas)

        y = pad
        # Chip NO VERIFICABLE
        d.rounded_rectangle((pad, y, pad + self._px(160), y + chip_h), radius=chip_h // 2, fill=(245, 158, 11, 40), outline=(245, 158, 11, 120))
        d.ellipse((pad + self._px(11), y + chip_h // 2 - self._px(4), pad + self._px(19), y + chip_h // 2 + self._px(4)), fill=(245, 158, 11, 255))
        d.text((pad + self._px(26), y + chip_h // 2), "NO VERIFICABLE", font=f_chip, fill=(251, 191, 36, 255), anchor="lm")
        y += chip_h + self._px(12)

        # Title
        for line in title_lines:
            d.text((pad, y), line, font=f_title, fill=TXT)
            y += title_lh
        y += self._px(6)
        
        # Body text
        for line in body_lines:
            d.text((pad, y), line, font=f_body, fill=MUTED)
            y += body_lh

        out_path.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(out_path, "PNG")
        return out_path

    # ---------------------------------------------------------
    # 6. Estilo Mito vs Realidad (Gamificado)
    # ---------------------------------------------------------
    def _render_myth_cards(self, card: InfoCard, out_path: Path) -> str:
        # Renderiza dos tarjetas: la primera "MITO" (naranja/roja) y la segunda "REALIDAD" (verde/azul).
        # Devuelve las rutas separadas por "|".
        path_mito = out_path.with_name(f"{out_path.stem}_mito.png")
        path_real = out_path.with_name(f"{out_path.stem}_real.png")
        
        pad = self._px(22)
        inner_w = self.card_w - 2 * pad
        
        f_chip = _font(["segoeuib.ttf", "arialbd.ttf"], self._px(16))
        f_title = _font(["segoeuib.ttf", "arialbd.ttf"], self._px(28))
        f_body = _font(["segoeui.ttf", "arial.ttf"], self._px(20))
        
        probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        mito_lines = self._wrap(probe, f"\"{card.claim}\"", f_title, inner_w, 4)
        real_lines = self._wrap(probe, card.correction or card.corrected_value, f_body, inner_w, 5)
        
        chip_h = self._px(32)
        title_lh = f_title.size + self._px(6)
        body_lh = f_body.size + self._px(6)
        
        # Tarjeta 1: MITO
        h_mito = pad + chip_h + self._px(14) + len(mito_lines) * title_lh + pad
        ss = 2
        W, H_mito = self.card_w * ss, h_mito * ss
        cv_mito = Image.new("RGBA", (W, H_mito), (0, 0, 0, 0))
        d_m = ImageDraw.Draw(cv_mito)
        d_m.rounded_rectangle((0, 0, W - 1, H_mito - 1), radius=self._px(24) * ss, fill=(24, 12, 12, 180), outline=(245, 158, 11, 200), width=2 * ss)
        cv_mito = cv_mito.resize((self.card_w, h_mito), Image.LANCZOS)
        d_m = ImageDraw.Draw(cv_mito)
        
        y = pad
        d_m.rounded_rectangle((pad, y, pad + self._px(90), y + chip_h), radius=chip_h // 2, fill=(245, 158, 11, 40), outline=(245, 158, 11, 150))
        d_m.text((pad + self._px(45), y + chip_h // 2), "MITO", font=f_chip, fill=(251, 191, 36, 255), anchor="mm")
        y += chip_h + self._px(14)
        for line in mito_lines:
            d_m.text((pad, y), line, font=f_title, fill=TXT)
            y += title_lh
        cv_mito.save(path_mito, "PNG")
        
        # Tarjeta 2: REALIDAD
        h_real = pad + chip_h + self._px(14) + len(real_lines) * body_lh + self._px(12) + pad
        W, H_real = self.card_w * ss, h_real * ss
        cv_real = Image.new("RGBA", (W, H_real), (0, 0, 0, 0))
        d_r = ImageDraw.Draw(cv_real)
        d_r.rounded_rectangle((0, 0, W - 1, H_real - 1), radius=self._px(24) * ss, fill=(12, 24, 18, 180), outline=(16, 185, 129, 200), width=2 * ss)
        cv_real = cv_real.resize((self.card_w, h_real), Image.LANCZOS)
        d_r = ImageDraw.Draw(cv_real)
        
        y = pad
        d_r.rounded_rectangle((pad, y, pad + self._px(140), y + chip_h), radius=chip_h // 2, fill=(16, 185, 129, 40), outline=(16, 185, 129, 150))
        d_r.text((pad + self._px(70), y + chip_h // 2), "REALIDAD", font=f_chip, fill=(52, 211, 153, 255), anchor="mm")
        y += chip_h + self._px(14)
        for line in real_lines:
            d_r.text((pad, y), line, font=f_body, fill=TXT)
            y += body_lh
        d_r.line((pad, y, self.card_w - pad, y), fill=(16, 185, 129, 100), width=1)
        y += self._px(12)
        domain = card.correction_source or (card.sources[0].domain if card.sources else "Web")
        f_src = _font(["segoeui.ttf", "arial.ttf"], self._px(14))
        d_r.text((pad, y), f"Fuente: {domain}", font=f_src, fill=(52, 211, 153, 255))
        
        cv_real.save(path_real, "PNG")
        
        return f"{path_mito}|{path_real}"

    def render_all(self, cards: List[InfoCard], workdir: Path) -> List[InfoCard]:
        for card in cards:
            # Cuando una afirmación no logra verificarse, también se muestra la
            # advertencia para no dar una certeza que las fuentes no respaldan.
            if not card.enabled or card.verdict not in ("supported", "contradicted", "insufficient"):
                continue
            try:
                card.card_path = str(self.render(card, workdir / f"{card.card_id}_card.png"))
            except Exception as exc:
                print(f"[CardRenderer] Error dibujando {card.card_id}: {exc}")
        return cards
