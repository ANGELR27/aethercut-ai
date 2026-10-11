"""
Motion Graphics Engine (HyperFrames, Remotion & Native WebM/SVG Adapter)
Genera capas cinéticas sutiles de microelementos (partículas de luz ambiental,
esquineros geométricos finos, marcadores técnicos y destellos fugaces) diseñados por GLM-5.3.
"""

import json
import logging
import math
import random
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("aethercut.motion_engine")


class MotionGraphicsEngine:
    def __init__(self, web_renderer=None, is_vertical: bool = False):
        self.web_renderer = web_renderer
        self.is_vertical = is_vertical
        self.W = 1080 if is_vertical else 1920
        self.H = 1920 if is_vertical else 1080

    def build_composition_html(
        self,
        motion_spec: Dict[str, Any],
        duration: float,
        palette_color: str = "#ff9436",
    ) -> str:
        """
        Genera la composición HTML5/SVG/CSS determinista con microelementos sutiles.
        Mantiene despejado el centro y la esquina inferior derecha.
        """
        particles_cfg = motion_spec.get("particles", {})
        p_count = min(24, max(8, int(particles_cfg.get("count", 16))))
        p_color = particles_cfg.get("color", palette_color)
        geo_accents = motion_spec.get("geometric_accents", [])
        fleeting = motion_spec.get("fleeting_accents", [])

        # Generar posiciones aleatorias deterministas para las partículas en zonas periféricas seguras
        random.seed(int(duration * 100) + len(str(motion_spec)))
        particles_html = []
        for i in range(p_count):
            # Zonas periféricas: top bar (y: 60-180), left bar (x: 40-280), right bar (x: W-320 a W-40)
            zone = random.choice(["top", "left", "right", "bottom_left"])
            if zone == "top":
                x = random.randint(120, self.W - 120)
                y = random.randint(70, 200)
            elif zone == "left":
                x = random.randint(60, 260)
                y = random.randint(180, self.H - 220)
            elif zone == "right":
                x = random.randint(self.W - 280, self.W - 70)
                y = random.randint(120, int(self.H * 0.55))  # evitar tapar avatar PIP
            else:
                x = random.randint(80, int(self.W * 0.40))
                y = random.randint(self.H - 240, self.H - 80)

            size = random.uniform(3.5, 6.5)
            opac = random.uniform(0.18, 0.42)
            dur_anim = random.uniform(2.8, 4.5)
            delay = random.uniform(0.0, 2.0)
            drift_y = random.choice([-16, -24, 18])
            drift_x = random.choice([-8, 8, 12, -12])

            particles_html.append(
                f'<div class="p-dot" style="width:{size:.1f}px;height:{size:.1f}px;'
                f'left:{x}px;top:{y}px;--opac:{opac:.2f};--dy:{drift_y}px;--dx:{drift_x}px;'
                f'animation: pDrift {dur_anim:.2f}s ease-in-out {delay:.2f}s infinite alternate;"></div>'
            )

        # Generar esquineros y marcadores HUD finos
        geo_html = []
        for g in geo_accents:
            g_type = g.get("type", "")
            g_col = g.get("color", palette_color)
            if g_type == "corner_brackets":
                geo_html.append(f"""
                <div class="hud-bracket b-tl" style="border-color:{g_col};"></div>
                <div class="hud-bracket b-tr" style="border-color:{g_col};"></div>
                <div class="hud-bracket b-bl" style="border-color:{g_col};"></div>
                """)
            elif g_type == "tech_marker":
                txt = g.get("text", "REC // SYS")
                geo_html.append(f"""
                <div class="hud-marker" style="color:{g_col};">
                  <span class="m-dot" style="background:{g_col};"></span>
                  <span>{txt}</span>
                </div>
                """)

        # Elementos fugaces
        fleeting_html = []
        for fl in fleeting:
            st = float(fl.get("start_sec", 4.0))
            fdur = float(fl.get("duration_sec", 2.0))
            fcol = fl.get("color", palette_color)
            fleeting_html.append(f"""
            <div class="fleeting-accent" style="border-color:{fcol};animation: fleetingAnim {fdur:.2f}s ease-out {st:.2f}s forwards;">
              <div class="f-pulse" style="background:{fcol};box-shadow:0 0 16px {fcol};"></div>
            </div>
            """)

        html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width={self.W}, height={self.H}">
  <style>
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    html, body {{
      width: {self.W}px; height: {self.H}px;
      background: transparent;
      overflow: hidden;
      font-family: 'Space Grotesk', -apple-system, sans-serif;
    }}
    .p-dot {{
      position: absolute;
      border-radius: 50%;
      background: {p_color};
      box-shadow: 0 0 10px {p_color};
      pointer-events: none;
    }}
    @keyframes pDrift {{
      0% {{ transform: translate(0, 0) scale(0.9); opacity: calc(var(--opac) * 0.6); }}
      100% {{ transform: translate(var(--dx), var(--dy)) scale(1.15); opacity: var(--opac); }}
    }}
    .hud-bracket {{
      position: absolute;
      width: 32px; height: 32px;
      pointer-events: none;
      opacity: 0.40;
      animation: bracketPulse 3.5s ease-in-out infinite alternate;
    }}
    .b-tl {{ top: 44px; left: 44px; border-top: 1.5px solid; border-left: 1.5px solid; }}
    .b-tr {{ top: 44px; right: 44px; border-top: 1.5px solid; border-right: 1.5px solid; }}
    .b-bl {{ bottom: 44px; left: 44px; border-bottom: 1.5px solid; border-left: 1.5px solid; }}
    @keyframes bracketPulse {{
      from {{ opacity: 0.25; transform: scale(0.98); }}
      to {{ opacity: 0.50; transform: scale(1.02); }}
    }}
    .hud-marker {{
      position: absolute;
      top: 50px; left: 88px;
      display: inline-flex; align-items: center; gap: 8px;
      font-size: 11px; font-weight: 700; letter-spacing: 0.20em;
      opacity: 0.35; pointer-events: none;
    }}
    .m-dot {{
      width: 5px; height: 5px; border-radius: 50%;
      box-shadow: 0 0 6px currentColor;
    }}
    .fleeting-accent {{
      position: absolute;
      top: 35%; left: 15%;
      width: 80px; height: 2px;
      background: linear-gradient(90deg, transparent, currentColor, transparent);
      opacity: 0; pointer-events: none;
    }}
    @keyframes fleetingAnim {{
      0% {{ opacity: 0; transform: scaleX(0.2) translateX(-20px); }}
      30% {{ opacity: 0.65; transform: scaleX(1.0) translateX(0); }}
      80% {{ opacity: 0.50; transform: scaleX(1.1) translateX(15px); }}
      100% {{ opacity: 0; transform: scaleX(0.8) translateX(25px); }}
    }}
  </style>
</head>
<body data-duration="{duration:.1f}" data-fps="25">
  {"".join(geo_html)}
  {"".join(particles_html)}
  {"".join(fleeting_html)}
</body>
</html>"""
        return html

    async def render_scene_motion_overlay(
        self,
        motion_spec: Dict[str, Any],
        duration: float,
        scene_dir: Path,
        scene_id: int = 0,
    ) -> Optional[Path]:
        """
        Renderiza la capa de motion graphics como PNG/WebM transparente de alta definición.
        Devuelve la ruta al archivo para componer en FFmpeg o None.
        """
        try:
            scene_dir = Path(scene_dir)
            out_png = scene_dir / f"motion_layer_{scene_id}.png"
            html_text = self.build_composition_html(motion_spec, duration)

            # Usar WebCardRenderer / Chromium para generar el overlay transparente nativo
            if self.web_renderer:
                try:
                    p = await self.web_renderer.export_html_screenshot(
                        html_content=html_text,
                        out_path=out_png,
                        width=self.W,
                        height=self.H,
                        transparent=True,
                    )
                    if p and p.exists() and p.stat().st_size > 1000:
                        return p
                except Exception as _we:
                    logger.debug(f"[MotionEngine] WebRenderer async export fallback: {_we}")

                        # Renderizado nativo Headless Chromium / Edge con transparencia 100% garantizada
            html_file = scene_dir / f"motion_layer_{scene_id}.html"
            html_file.write_text(html_text, encoding="utf-8")
            
            from core.web_card_renderer import _get_browser_bin
            browser_bin = _get_browser_bin()
            args = [
                browser_bin,
                "--headless",
                "--disable-gpu",
                "--no-sandbox",
                "--hide-scrollbars",
                "--default-background-color=00000000",
                f"--screenshot={out_png.resolve()}",
                f"--window-size={self.W},{self.H}",
                html_file.resolve().as_uri(),
            ]
            subprocess.run(args, capture_output=True, check=True, timeout=15)

            if out_png.exists() and out_png.stat().st_size > 1000:
                logger.info(f"[MotionEngine] Capa de microelementos generada: {out_png}")
                return out_png

        except Exception as exc:
            logger.warning(f"[MotionEngine] Error renderizando motion overlay: {exc}")

        return None
