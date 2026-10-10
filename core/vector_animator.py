"""Motor Canonico de Animacion Vectorial v2 (Vector Motion Graphics Engine).

AetherCut Studio Signature Pro v2:
- Graficos de barras con grow animation ease-out cubico.
- Red neuronal pulsante con señales viajando por conexiones.
- Ondas sinusoidales multi-capa (espectro de audio / datos).
- Personaje animado con cinematica mejorada (respiracion, parpadeo).
- Fondo atmosferico con glow suave.
- Full HD 1080p a 24fps nativo para FFmpeg.
"""

from __future__ import annotations

import math
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageFilter


C_BG     = (8, 9, 13, 255)
C_BLUE   = (56, 189, 248, 255)
C_GREEN  = (52, 211, 153, 255)
C_AMBER  = (251, 191, 36, 255)
C_WHITE  = (255, 255, 255, 255)
C_MUTED  = (148, 163, 184, 220)
C_PANEL  = (16, 22, 34, 240)
C_BORDER = (56, 189, 248, 100)


def _ease_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


class VectorAnimator:
    """Generador de graficos y animaciones vectoriales de estudio profesional v2."""

    def __init__(self, width: int = 1920, height: int = 1080, fps: int = 24):
        self.W = width
        self.H = height
        self.fps = fps
        self._fonts: Dict[str, ImageFont.FreeTypeFont] = {}
        font_specs = [
            ("bold_xl", "segoeuib.ttf", 52),
            ("bold_lg", "segoeuib.ttf", 36),
            ("bold_md", "segoeuib.ttf", 22),
            ("bold_sm", "segoeuib.ttf", 15),
            ("reg_md",  "segoeui.ttf",  20),
            ("reg_sm",  "segoeui.ttf",  14),
            ("tag",     "segoeuib.ttf", 12),
        ]
        for name, fname, size in font_specs:
            p = Path(f"C:/Windows/Fonts/{fname}")
            if p.exists():
                try:
                    self._fonts[name] = ImageFont.truetype(str(p), size)
                except Exception:
                    pass
        fallback = ImageFont.load_default()
        for k in ("bold_xl", "bold_lg", "bold_md", "bold_sm", "reg_md", "reg_sm", "tag"):
            if k not in self._fonts:
                self._fonts[k] = fallback

    def _f(self, key: str):
        return self._fonts.get(key, ImageFont.load_default())

    def _background(self) -> Image.Image:
        bg = Image.new("RGBA", (self.W, self.H), C_BG)
        glow = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse((-200, 300, 900, 1300), fill=(14, 28, 54, 80))
        glow = glow.filter(ImageFilter.GaussianBlur(180))
        bg.paste(glow, (0, 0), glow)
        glow2 = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        ImageDraw.Draw(glow2).ellipse((1300, -200, 2200, 700), fill=(255, 255, 255, 8))
        glow2 = glow2.filter(ImageFilter.GaussianBlur(200))
        bg.paste(glow2, (0, 0), glow2)
        return bg

    def _badge(self, d: ImageDraw.Draw, x: int, y: int, text: str) -> None:
        tw = int(d.textlength(text, font=self._f("tag"))) + 24
        d.rounded_rectangle((x, y - 5, x + tw, y + 19), radius=12,
                             fill=(255, 255, 255, 12), outline=C_BORDER, width=1)
        d.ellipse((x + 8, y + 4, x + 14, y + 10), fill=C_BLUE)
        d.text((x + 20, y + 7), text, font=self._f("tag"),
               fill=(255, 255, 255, 220), anchor="lm")

    def _bar_chart(self, d: ImageDraw.Draw, t: float,
                   x0: int, y0: int, bars: list,
                   chart_w: int = 480, chart_h: int = 280,
                   title: str = "ANALISIS") -> None:
        d.rounded_rectangle((x0 - 16, y0 - 44, x0 + chart_w + 16, y0 + chart_h + 16),
                             radius=16, fill=C_PANEL, outline=C_BORDER, width=1)
        d.text((x0, y0 - 32), title, font=self._f("bold_sm"), fill=C_BLUE, anchor="lm")
        n = len(bars)
        if not n:
            return
        bar_w = (chart_w - (n - 1) * 10) // n
        anim = min(1.0, t / 0.8)
        for i, (label, val, color_hex) in enumerate(bars):
            bx = x0 + i * (bar_w + 10)
            max_h = chart_h - 32
            cur_h = int(max_h * val * _ease_out(anim))
            by_top = y0 + chart_h - 16 - cur_h
            by_bot = y0 + chart_h - 16
            try:
                r = int(color_hex[1:3], 16)
                g = int(color_hex[3:5], 16)
                b = int(color_hex[5:7], 16)
                fill = (r, g, b, 230)
                shadow = (r, g, b, 55)
            except Exception:
                fill = C_BLUE
                shadow = (56, 189, 248, 55)
            if cur_h > 2:
                d.rounded_rectangle((bx - 3, by_top - 3, bx + bar_w + 3, by_bot + 3),
                                     radius=6, fill=shadow)
                d.rounded_rectangle((bx, by_top, bx + bar_w, by_bot), radius=6, fill=fill)
                d.rectangle((bx + 2, by_top + 2, bx + bar_w - 2, by_top + 5),
                             fill=(255, 255, 255, 65))
            d.text((bx + bar_w // 2, by_top - 8), f"{int(val * 100)}%",
                   font=self._f("tag"), fill=C_WHITE, anchor="mb")
            d.text((bx + bar_w // 2, by_bot + 8), label[:8],
                   font=self._f("tag"), fill=C_MUTED, anchor="mt")

    def _neural_net(self, d: ImageDraw.Draw, t: float,
                    cx: int, cy: int, layers: list, radius: int = 360) -> None:
        gap = radius * 2 // max(len(layers) - 1, 1)
        nodes: List[List[Tuple[int, int]]] = []
        for li, n in enumerate(layers):
            lx = cx - radius + li * gap
            ygap = 80 if n < 5 else 60
            y0 = cy - (n - 1) * ygap // 2
            nodes.append([(lx, y0 + ni * ygap) for ni in range(n)])
        for li in range(len(nodes) - 1):
            for n1 in nodes[li]:
                for n2 in nodes[li + 1]:
                    d.line([n1, n2], fill=(56, 189, 248, 18), width=1)
                    pulse = (t * 0.6 + (n1[0] + n2[1]) * 0.003) % 1.0
                    px = int(n1[0] + (n2[0] - n1[0]) * pulse)
                    py = int(n1[1] + (n2[1] - n1[1]) * pulse)
                    d.ellipse((px - 4, py - 4, px + 4, py + 4), fill=(56, 189, 248, 190))
        for li, layer in enumerate(nodes):
            for ni, (nx, ny) in enumerate(layer):
                p = math.sin(t * 2.5 + li * 1.1 + ni * 0.7) * 0.5 + 0.5
                nr = int(8 + p * 5)
                active = abs(hash((li, ni, int(t * 2)))) % 4 == 0
                color = C_GREEN if active else (56, 189, 248, int(180 + p * 75))
                d.ellipse((nx - nr, ny - nr, nx + nr, ny + nr),
                          fill=color, outline=(255, 255, 255, 55), width=1)

    def _wave(self, d: ImageDraw.Draw, t: float,
              yc: int, x0: int, x1: int,
              amp: int = 30, freq: float = 0.04,
              color: tuple = (56, 189, 248, 80),
              phase: float = 0.0) -> None:
        pts = []
        for x in range(x0, x1, 3):
            y = yc + int(amp * math.sin(freq * (x - x0) + t * 3.5 + phase))
            pts.append((x, y))
        if len(pts) > 1:
            d.line(pts, fill=color, width=2)

    def _info_cards(self, d: ImageDraw.Draw, t: float,
                    x: int, y: int, cards: list, stagger: float = 0.18) -> None:
        for i, card in enumerate(cards[:4]):
            a = _ease_out(min(1.0, max(0.0, t - i * stagger) / 0.4))
            if a < 0.02:
                continue
            cy = y + i * 130
            d.rounded_rectangle((x, cy, x + 380, cy + 110), radius=16,
                                 fill=(*C_PANEL[:3], int(240 * a)),
                                 outline=(*C_BORDER[:3], int(140 * a)), width=1)
            accent = (52, 211, 153) if i % 2 == 0 else (56, 189, 248)
            d.ellipse((x + 16, cy + 20, x + 26, cy + 30), fill=(*accent, int(255 * a)))
            d.text((x + 36, cy + 24), card.get("title", "")[:24],
                   font=self._f("bold_sm"), fill=(*C_WHITE[:3], int(255 * a)), anchor="lm")
            d.text((x + 16, cy + 54), card.get("desc", "")[:38],
                   font=self._f("reg_sm"), fill=(*C_MUTED[:3], int(255 * a)), anchor="lm")
            stat = card.get("stat", "")[:12]
            if stat:
                d.text((x + 362, cy + 24), stat,
                       font=self._f("bold_md"), fill=(*C_AMBER[:3], int(255 * a)), anchor="rm")

    def _character(self, d: ImageDraw.Draw, t: float,
                   cx: int, floor_y: int, action: str = "analyzing") -> None:
        breath = math.sin(t * 3.2) * 4
        tt = int(490 + breath)
        tb = int(635 + breath)
        d.ellipse((cx - 80, floor_y - 10, cx + 80, floor_y + 10), fill=(0, 0, 0, 100))
        d.rounded_rectangle((cx - 44, tt, cx + 44, tb), radius=18,
                             fill=(22, 32, 52, 255), outline=(56, 189, 248, 155), width=2)
        d.line([(cx - 8, tt + 10), (cx, tt + 40), (cx + 8, tt + 10)],
               fill=(56, 189, 248, 115), width=2)
        neck_y = tt - 14
        d.line([(cx, tt), (cx, neck_y)], fill=(215, 185, 165, 255), width=11)
        hcy = neck_y - 36
        d.ellipse((cx - 32, hcy - 32, cx + 32, hcy + 32), fill=(225, 195, 175, 255))
        d.arc((cx - 32, hcy - 36, cx + 32, hcy + 32), start=180, end=360,
              fill=(28, 35, 50, 255), width=11)
        for ex in (cx - 12, cx + 12):
            blink = abs(math.sin(t * 0.3 + ex)) > 0.97
            eh = 2 if blink else 5
            d.ellipse((ex - 4, hcy - 6 - eh, ex + 4, hcy - 6 + eh), fill=(35, 40, 55, 255))
        d.line([(cx - 18, tb), (cx - 18, floor_y)], fill=(15, 20, 34, 255), width=16)
        d.line([(cx + 18, tb), (cx + 18, floor_y)], fill=(15, 20, 34, 255), width=16)
        for sx in (cx - 30, cx + 12):
            d.rounded_rectangle((sx, floor_y - 10, sx + 36, floor_y), radius=5,
                                 fill=(38, 48, 68, 255))
        if action == "analyzing":
            arm_y = int(math.sin(t * 1.8) * 8)
            d.line([(cx - 40, tt + 18), (cx - 80, tt + 50 + arm_y)],
                   fill=(22, 32, 52, 255), width=14)
            d.ellipse((cx - 90, tt + 44 + arm_y, cx - 72, tt + 62 + arm_y),
                      fill=(215, 185, 165, 255))
            d.line([(cx + 40, tt + 18), (cx + 58, tt + 60)],
                   fill=(22, 32, 52, 255), width=14)
        elif action == "presenting":
            ang = math.sin(t * 1.2) * 0.15
            ax = int(math.cos(-0.5 + ang) * 85)
            ay = int(math.sin(-0.5 + ang) * 85)
            d.line([(cx + 40, tt + 18), (cx + 40 + ax, tt + 18 + ay)],
                   fill=(22, 32, 52, 255), width=14)
            d.ellipse((cx + 40 + ax - 8, tt + 18 + ay - 8,
                       cx + 40 + ax + 8, tt + 18 + ay + 8), fill=(215, 185, 165, 255))
        else:
            d.line([(cx - 40, tt + 18), (cx - 50, tt + 70)],
                   fill=(22, 32, 52, 255), width=14)
            d.line([(cx + 40, tt + 18), (cx + 50, tt + 70)],
                   fill=(22, 32, 52, 255), width=14)

    def render_character_action_clip(
        self,
        headline: str,
        action_name: str,
        cards_info: list,
        duration_sec: float,
        out_mp4: Path,
        scene_type: str = "analyzing",
    ) -> Path:
        """Renderiza escena animada completa: personaje + graficos + red neuronal."""
        out_mp4.parent.mkdir(parents=True, exist_ok=True)
        total_frames = max(1, int(self.fps * duration_sec))
        tmp = out_mp4.parent / f"_vframes_{out_mp4.stem}"
        tmp.mkdir(parents=True, exist_ok=True)

        show_bars   = scene_type in ("analyzing", "data", "chart", "stats")
        show_neural = scene_type in ("ai", "neural", "tech", "mixed")
        show_wave   = scene_type in ("audio", "wave", "podcast", "mixed")

        bar_colors = ["#38bdf8", "#34d399", "#fbbf24", "#f87171", "#a78bfa"]
        bars: List[Tuple[str, float, str]] = []
        for i, c in enumerate(cards_info[:5]):
            raw = c.get("stat", f"{60 + i * 8}%")
            try:
                v = float(raw.replace("%", "").replace("x", "").strip()) / 100.0
                v = max(0.1, min(1.0, v))
            except Exception:
                v = 0.5 + i * 0.08
            bars.append((c.get("title", f"K{i+1}")[:6], v, bar_colors[i % len(bar_colors)]))

        bg = self._background()

        for f in range(total_frames):
            t = f / self.fps
            im = bg.copy()
            d = ImageDraw.Draw(im)

            if show_wave:
                for wv in range(4):
                    self._wave(d, t,
                               yc=self.H // 2 + wv * 60 - 90,
                               x0=0, x1=self.W,
                               amp=20 + wv * 8,
                               freq=0.015 + wv * 0.005,
                               color=(56, 189, 248, 28 + wv * 10),
                               phase=wv * 0.8)

            if show_neural:
                self._neural_net(d, t, cx=int(self.W * 0.65),
                                 cy=int(self.H * 0.5),
                                 layers=[3, 5, 4, 3, 2], radius=320)

            self._character(d, t, cx=int(self.W * 0.32), floor_y=780,
                             action=scene_type if scene_type in ("analyzing", "presenting") else "analyzing")

            if show_bars and bars:
                self._bar_chart(d, t, x0=int(self.W * 0.52), y0=280,
                                bars=bars, chart_w=460, chart_h=260, title="ANALISIS")

            self._info_cards(d, t, x=int(self.W * 0.62), y=560, cards=cards_info[:3])

            self._badge(d, 100, 90, f"ESTUDIO // {scene_type.upper()}")
            d.text((100, 126), headline.upper()[:48],
                   font=self._f("bold_xl"), fill=C_WHITE)
            d.text((100, 190), action_name[:70],
                   font=self._f("reg_md"), fill=C_MUTED)

            hud_a = int(200 + math.sin(t * 4) * 55)
            d.rounded_rectangle((100, 230, 310, 262), radius=14,
                                 fill=(239, 68, 68, 38), outline=(239, 68, 68, hud_a), width=1)
            d.ellipse((114, 240, 124, 250), fill=(239, 68, 68, hud_a))
            d.text((130, 246), "EN ANALISIS",
                   font=self._f("tag"), fill=(255, 255, 255, hud_a), anchor="lm")

            im.convert("RGB").save(tmp / f"f_{f:04d}.png")

        subprocess.run([
            "ffmpeg", "-y",
            "-framerate", str(self.fps),
            "-i", str(tmp / "f_%04d.png"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-preset", "fast", "-crf", "18",
            str(out_mp4)
        ], check=True, capture_output=True)

        for png in tmp.glob("*.png"):
            try:
                png.unlink()
            except Exception:
                pass
        try:
            tmp.rmdir()
        except Exception:
            pass

        return out_mp4

    def render_data_wave_clip(
        self,
        title: str,
        stats: list,
        duration_sec: float,
        out_mp4: Path,
    ) -> Path:
        """Clip de espectro de onda de datos para escenas de audio o analisis."""
        out_mp4.parent.mkdir(parents=True, exist_ok=True)
        total_frames = max(1, int(self.fps * duration_sec))
        tmp = out_mp4.parent / f"_wframes_{out_mp4.stem}"
        tmp.mkdir(parents=True, exist_ok=True)
        bg = self._background()

        wave_cfg = [
            (self.H // 2 - 80, 50, 0.025, C_BLUE,  0.0),
            (self.H // 2,       35, 0.018, C_GREEN, 1.2),
            (self.H // 2 + 80,  25, 0.032, C_AMBER, 2.5),
        ]

        for f in range(total_frames):
            t = f / self.fps
            im = bg.copy()
            d = ImageDraw.Draw(im)

            for yc, amp, freq, color, phase in wave_cfg:
                self._wave(d, t, yc, 80, self.W - 80, amp=amp, freq=freq,
                           color=color, phase=phase)

            bar_n = 48
            seg = (self.W - 160) // bar_n
            for bi in range(bar_n):
                bx = 80 + bi * seg
                bh = int(abs(math.sin(t * 3 + bi * 0.4)) * 140 + 20)
                ba = int(180 + math.sin(t * 2 + bi * 0.3) * 60)
                fr = bi / bar_n
                rc = int(56 + (248 - 56) * fr)
                gc = int(189 * (1 - fr))
                bc = int(248 * (1 - fr) + 36 * fr)
                d.rectangle((bx, self.H // 2 - bh // 2, bx + 10, self.H // 2 + bh // 2),
                             fill=(rc, gc, bc, ba))

            self._badge(d, 100, 80, "DATOS // ANALISIS")
            d.text((100, 116), title.upper()[:50], font=self._f("bold_lg"), fill=C_WHITE)

            for si, (label, val) in enumerate(stats[:4]):
                sx = 120 + si * 260
                sy = self.H - 160
                d.rounded_rectangle((sx - 10, sy - 10, sx + 220, sy + 70),
                                     radius=14, fill=C_PANEL, outline=C_BORDER, width=1)
                d.text((sx + 100, sy + 4), f"{int(val * 100)}%",
                       font=self._f("bold_lg"), fill=C_AMBER, anchor="mt")
                d.text((sx + 100, sy + 50), label[:18],
                       font=self._f("reg_sm"), fill=C_MUTED, anchor="mt")

            im.convert("RGB").save(tmp / f"f_{f:04d}.png")

        subprocess.run([
            "ffmpeg", "-y",
            "-framerate", str(self.fps),
            "-i", str(tmp / "f_%04d.png"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-preset", "fast", "-crf", "18",
            str(out_mp4)
        ], check=True, capture_output=True)

        for png in tmp.glob("*.png"):
            try:
                png.unlink()
            except Exception:
                pass
        try:
            tmp.rmdir()
        except Exception:
            pass

        return out_mp4
