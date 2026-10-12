"""
Visual Templates Library (AetherCut Pro Design System)
Colección completa de componentes gráficos, distintivos virales, tarjetas técnicas
y ayudas visuales cinéticas estilo Orange Noir y variantes profesionales.
"""

from __future__ import annotations

import base64
import logging
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("aethercut.visual_templates")

HTML_FONTS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800;900&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700;800&family=Playfair+Display:ital,wght@0,600;0,700;1,600;1,700&family=Space+Grotesk:wght@500;700;800&display=swap" rel="stylesheet">
"""

# Paletas de color firma con enfoque "Orange Noir" y variantes
THEME_PALETTES = {
    "orange_noir": {
        "bg": "rgba(12, 13, 18, 0.88)",
        "card_bg": "#0c0d12",
        "border": "rgba(255, 148, 54, 0.40)",
        "accent": "#ff9436",
        "accent_gradient": "linear-gradient(135deg, #ff9436 0%, #ff5500 100%)",
        "text": "#ffffff",
        "text_sub": "#cbd5e1",
        "glow": "rgba(255, 148, 54, 0.35)",
        "badge_border": "3px solid rgba(255, 148, 54, 0.90)",
        "pill_bg": "rgba(255, 148, 54, 0.14)",
        "grid_dot": "rgba(255, 148, 54, 0.16)",
    },
    "frosted_white": {
        "bg": "rgba(20, 22, 30, 0.50)",
        "card_bg": "rgba(18, 20, 28, 0.65)",
        "border": "rgba(255, 255, 255, 0.85)",
        "accent": "#ffffff",
        "accent_gradient": "linear-gradient(135deg, #ffffff 0%, #e2e8f0 100%)",
        "text": "#ffffff",
        "text_sub": "#94a3b8",
        "glow": "rgba(255, 255, 255, 0.20)",
        "badge_border": "3.5px solid rgba(255, 255, 255, 0.95)",
        "pill_bg": "rgba(255, 255, 255, 0.15)",
        "grid_dot": "rgba(255, 255, 255, 0.14)",
    },
    "emerald_matrix": {
        "bg": "rgba(10, 18, 14, 0.90)",
        "card_bg": "#0a130e",
        "border": "rgba(0, 245, 160, 0.45)",
        "accent": "#00f5a0",
        "accent_gradient": "linear-gradient(135deg, #00f5a0 0%, #00bb77 100%)",
        "text": "#ffffff",
        "text_sub": "#a7f3d0",
        "glow": "rgba(0, 245, 160, 0.30)",
        "badge_border": "3px solid rgba(0, 245, 160, 0.90)",
        "pill_bg": "rgba(0, 245, 160, 0.15)",
        "grid_dot": "rgba(0, 245, 160, 0.18)",
    },
    "crimson_hazard": {
        "bg": "rgba(20, 10, 12, 0.92)",
        "card_bg": "#140a0e",
        "border": "rgba(255, 51, 102, 0.50)",
        "accent": "#ff3366",
        "accent_gradient": "linear-gradient(135deg, #ff3366 0%, #cc0033 100%)",
        "text": "#ffffff",
        "text_sub": "#fecdd3",
        "glow": "rgba(255, 51, 102, 0.35)",
        "badge_border": "3px solid rgba(255, 51, 102, 0.95)",
        "pill_bg": "rgba(255, 51, 102, 0.16)",
        "grid_dot": "rgba(255, 51, 102, 0.20)",
    },
    "cyber_cyan": {
        "bg": "rgba(8, 16, 24, 0.90)",
        "card_bg": "#09121a",
        "border": "rgba(0, 229, 255, 0.45)",
        "accent": "#00e5ff",
        "accent_gradient": "linear-gradient(135deg, #00e5ff 0%, #0077ff 100%)",
        "text": "#ffffff",
        "text_sub": "#bae6fd",
        "glow": "rgba(0, 229, 255, 0.30)",
        "badge_border": "3px solid rgba(0, 229, 255, 0.90)",
        "pill_bg": "rgba(0, 229, 255, 0.15)",
        "grid_dot": "rgba(0, 229, 255, 0.18)",
    },
    "royal_gold": {
        "bg": "rgba(18, 14, 8, 0.90)",
        "card_bg": "#141009",
        "border": "rgba(255, 183, 3, 0.45)",
        "accent": "#ffb703",
        "accent_gradient": "linear-gradient(135deg, #ffb703 0%, #fb8500 100%)",
        "text": "#ffffff",
        "text_sub": "#fde68a",
        "glow": "rgba(255, 183, 3, 0.35)",
        "badge_border": "3px solid rgba(255, 183, 3, 0.90)",
        "pill_bg": "rgba(255, 183, 3, 0.15)",
        "grid_dot": "rgba(255, 183, 3, 0.18)",
    },
}


def _get_browser_bin() -> str:
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return "chrome"


class VisualTemplatesLibrary:
    """Librería y motor de plantillas visuales cinéticas de alta gama."""

    def __init__(self, browser_bin: Optional[str] = None):
        self.browser_bin = browser_bin or _get_browser_bin()

    def get_palette(self, variant: str = "orange_noir") -> Dict[str, str]:
        var_key = (variant or "orange_noir").lower().strip()
        return THEME_PALETTES.get(var_key, THEME_PALETTES["orange_noir"])

    @staticmethod
    def _crop_transparent(png_path: Path):
        try:
            from PIL import Image
            im = Image.open(png_path)
            bbox = im.getbbox()
            if bbox:
                pad = 16
                b = (
                    max(0, bbox[0] - pad),
                    max(0, bbox[1] - pad),
                    min(im.width, bbox[2] + pad),
                    min(im.height, bbox[3] + pad),
                )
                im.crop(b).save(png_path)
        except Exception:
            pass

    # =========================================================================
    # 1. PLANTILLA: VERDICT BADGE (Distintivo / Sello Inclinado)
    # =========================================================================
    def build_verdict_badge_html(
        self,
        headline: str,
        icon: str = "✓",
        variant: str = "orange_noir",
        tilt_deg: float = -3.5,
        subtitle: str = "",
    ) -> str:
        p = self.get_palette(variant)
        clean_headline = (headline or "Verificado").strip()
        clean_icon = (icon or "✓").strip()
        sub_html = f'<div class="badge-sub">{subtitle}</div>' if subtitle else ""

        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
{HTML_FONTS}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: transparent;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    overflow: hidden;
  }}
  .badge-wrap {{
    display: inline-flex;
    flex-direction: column;
    align-items: center;
    transform: rotate({tilt_deg:.1f}deg);
  }}
  .badge-stamp {{
    display: inline-flex;
    align-items: center;
    gap: 18px;
    padding: 18px 44px;
    border: {p['badge_border']};
    border-radius: 24px;
    background: {p['bg']};
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    box-shadow: 0 24px 50px rgba(0, 0, 0, 0.55), 0 0 30px {p['glow']}, inset 0 1px 1px rgba(255, 255, 255, 0.35);
    color: {p['text']};
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 56px;
    font-weight: 700;
    letter-spacing: -0.5px;
    text-shadow: 0 3px 14px rgba(0, 0, 0, 0.65);
    white-space: nowrap;
  }}
  .badge-icon {{
    font-size: 46px;
    font-weight: 900;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    color: {p['accent']};
    display: inline-flex;
    align-items: center;
    justify-content: center;
    line-height: 1;
    filter: drop-shadow(0 0 8px {p['glow']});
  }}
  .badge-sub {{
    margin-top: 10px;
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 18px;
    font-weight: 600;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: {p['text_sub']};
    background: rgba(0, 0, 0, 0.50);
    padding: 4px 16px;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.10);
  }}
</style>
</head>
<body>
  <div class="badge-wrap">
    <div class="badge-stamp">
      <span class="badge-icon">{clean_icon}</span>
      <span>{clean_headline}</span>
    </div>
    {sub_html}
  </div>
</body>
</html>"""

    # =========================================================================
    # 2. PLANTILLA: TECH HEADER CARD (Tarjeta Técnica Superior)
    # =========================================================================
    def build_tech_header_card_html(
        self,
        title: str,
        subtitle: str = "",
        author: str = "",
        repo_or_tag: str = "",
        variant: str = "orange_noir",
    ) -> str:
        p = self.get_palette(variant)
        clean_title = (title or "tech-specification").strip()

        clean_sub = subtitle.strip()
        if not author and not repo_or_tag and "·" in clean_sub:
            parts = [x.strip() for x in clean_sub.split("·", 1)]
            author = parts[0][4:].strip() if parts[0].lower().startswith("por ") else parts[0]
            repo_or_tag = parts[1]
        elif not author and clean_sub:
            author = clean_sub

        meta_parts = []
        if author:
            meta_parts.append(f'<span>por <span class="tech-author">{author}</span></span>')
        if repo_or_tag:
            if meta_parts:
                meta_parts.append('<span class="tech-sep">·</span>')
            meta_parts.append(f'<span class="tech-repo">{repo_or_tag}</span>')
        meta_html = "".join(meta_parts) if meta_parts else f'<span>{clean_sub or "verified-engine"}</span>'

        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
{HTML_FONTS}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: transparent;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    overflow: hidden;
  }}
  .tech-card {{
    position: relative;
    width: 720px;
    padding: 34px 44px;
    border-radius: 22px;
    background: {p['card_bg']};
    background-image: radial-gradient({p['grid_dot']} 1.2px, transparent 1.2px);
    background-size: 18px 18px;
    border: 1.5px solid {p['border']};
    box-shadow: 0 28px 60px rgba(0, 0, 0, 0.65), 0 0 25px {p['glow']}, inset 0 1px 0 rgba(255, 255, 255, 0.12);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    gap: 10px;
  }}
  .tech-tag-indicator {{
    position: absolute;
    top: -12px;
    left: 40px;
    background: {p['accent_gradient']};
    color: #000000;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    padding: 3px 12px;
    border-radius: 8px;
    box-shadow: 0 4px 12px {p['glow']};
  }}
  .tech-title {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 50px;
    font-weight: 800;
    color: {p['text']};
    letter-spacing: -1.2px;
    line-height: 1.15;
    text-shadow: 0 3px 12px rgba(0, 0, 0, 0.60);
    word-break: break-word;
  }}
  .tech-meta {{
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 20px;
    font-weight: 500;
    color: {p['text_sub']};
    letter-spacing: -0.2px;
    display: flex;
    align-items: center;
    gap: 10px;
  }}
  .tech-author {{
    color: {p['accent']};
    font-weight: 700;
  }}
  .tech-sep {{
    color: rgba(255, 255, 255, 0.30);
  }}
  .tech-repo {{
    color: #e2e8f0;
    font-family: 'JetBrains Mono', monospace;
    font-size: 18px;
  }}
</style>
</head>
<body>
  <div class="tech-card">
    <div class="tech-tag-indicator">SYS // SPEC</div>
    <div class="tech-title">{clean_title}</div>
    <div class="tech-meta">
      {meta_html}
    </div>
  </div>
</body>
</html>"""

    # =========================================================================
    # 3. PLANTILLA: STAT COUNTER CARD (Cifra de Impacto / Métrica Clave)
    # =========================================================================
    def build_stat_counter_html(
        self,
        stat_value: str,
        stat_label: str,
        headline: str = "",
        tag: str = "MÉTRICA CLAVE",
        trend_text: str = "+42% Récord",
        variant: str = "orange_noir",
    ) -> str:
        p = self.get_palette(variant)
        clean_stat = (stat_value or "99.8%").strip()
        clean_lbl = (stat_label or "Efectividad Verificada").strip()
        clean_hl = headline.strip()

        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
{HTML_FONTS}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: transparent;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    overflow: hidden;
  }}
  .stat-card {{
    position: relative;
    width: 680px;
    padding: 36px 44px;
    border-radius: 24px;
    background: {p['card_bg']};
    border: 1.5px solid {p['border']};
    box-shadow: 0 24px 60px rgba(0, 0, 0, 0.65), 0 0 30px {p['glow']}, inset 0 1px 0 rgba(255, 255, 255, 0.15);
    display: flex;
    flex-direction: column;
    gap: 14px;
  }}
  .top-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  .stat-badge {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 5px 14px;
    border-radius: 10px;
    background: {p['pill_bg']};
    border: 1px solid {p['border']};
    color: {p['accent']};
    font-family: 'Space Grotesk', sans-serif;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }}
  .dot-pulse {{
    width: 7px; height: 7px;
    border-radius: 50%;
    background: {p['accent']};
    box-shadow: 0 0 10px {p['accent']};
  }}
  .trend-pill {{
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 14px;
    font-weight: 700;
    color: #10b981;
    background: rgba(16, 185, 129, 0.12);
    padding: 4px 12px;
    border-radius: 8px;
    border: 1px solid rgba(16, 185, 129, 0.25);
  }}
  .headline-txt {{
    font-family: 'Outfit', sans-serif;
    font-size: 26px;
    font-weight: 700;
    color: {p['text']};
    line-height: 1.25;
  }}
  .number-row {{
    display: flex;
    align-items: baseline;
    gap: 16px;
  }}
  .stat-number {{
    font-family: 'Outfit', sans-serif;
    font-size: 78px;
    font-weight: 900;
    background: {p['accent_gradient']};
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 1;
    letter-spacing: -2px;
    filter: drop-shadow(0 4px 16px {p['glow']});
  }}
  .stat-unit {{
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 22px;
    font-weight: 600;
    color: {p['text_sub']};
  }}
  .meter-bar {{
    width: 100%;
    height: 6px;
    background: rgba(255, 255, 255, 0.10);
    border-radius: 4px;
    overflow: hidden;
    position: relative;
    margin-top: 4px;
  }}
  .meter-fill {{
    height: 100%;
    width: 78%;
    background: {p['accent_gradient']};
    box-shadow: 0 0 12px {p['accent']};
    border-radius: 4px;
  }}
</style>
</head>
<body>
  <div class="stat-card">
    <div class="top-row">
      <div class="stat-badge"><span class="dot-pulse"></span><span>{tag}</span></div>
      <div class="trend-pill">▲ {trend_text}</div>
    </div>
    {f'<div class="headline-txt">{clean_hl}</div>' if clean_hl else ''}
    <div class="number-row">
      <div class="stat-number">{clean_stat}</div>
      <div class="stat-unit">{clean_lbl}</div>
    </div>
    <div class="meter-bar">
      <div class="meter-fill"></div>
    </div>
  </div>
</body>
</html>"""

    # =========================================================================
    # 4. PLANTILLA: VERSUS SPLIT (Comparativa Dual)
    # =========================================================================
    def build_versus_split_html(
        self,
        side_a: str,
        side_b: str,
        stat_a: str = "",
        stat_b: str = "",
        tag: str = "COMPARATIVA DIRECTA",
        variant: str = "orange_noir",
    ) -> str:
        p = self.get_palette(variant)

        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
{HTML_FONTS}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: transparent;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    overflow: hidden;
  }}
  .versus-container {{
    position: relative;
    width: 760px;
    display: flex;
    border-radius: 26px;
    background: {p['card_bg']};
    border: 1.5px solid {p['border']};
    box-shadow: 0 30px 70px rgba(0, 0, 0, 0.70), 0 0 30px {p['glow']};
    overflow: hidden;
  }}
  .versus-side {{
    flex: 1;
    padding: 38px 30px;
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: 8px;
  }}
  .side-left {{
    background: rgba(255, 255, 255, 0.02);
    border-right: 1px dashed rgba(255, 255, 255, 0.12);
  }}
  .side-right {{
    background: rgba(255, 148, 54, 0.04);
  }}
  .side-name {{
    font-family: 'Outfit', sans-serif;
    font-size: 32px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: -0.5px;
  }}
  .side-stat {{
    font-family: 'Outfit', sans-serif;
    font-size: 44px;
    font-weight: 900;
    color: {p['accent']};
    filter: drop-shadow(0 2px 10px {p['glow']});
  }}
  .side-label {{
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 15px;
    font-weight: 600;
    color: {p['text_sub']};
  }}
  .vs-badge {{
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 54px;
    height: 54px;
    border-radius: 50%;
    background: {p['accent_gradient']};
    box-shadow: 0 0 20px {p['glow']}, 0 4px 12px rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'Outfit', sans-serif;
    font-weight: 900;
    font-size: 20px;
    color: #000000;
    z-index: 10;
  }}
  .vs-tag-header {{
    position: absolute;
    top: -12px;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(0, 0, 0, 0.85);
    border: 1px solid {p['border']};
    padding: 3px 16px;
    border-radius: 8px;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.18em;
    color: {p['accent']};
    text-transform: uppercase;
  }}
</style>
</head>
<body>
  <div class="versus-container">
    <div class="vs-tag-header">{tag}</div>
    <div class="vs-badge">VS</div>
    <div class="versus-side side-left">
      <div class="side-name">{side_a}</div>
      {f'<div class="side-stat">{stat_a}</div>' if stat_a else ''}
      <div class="side-label">Referencia Base</div>
    </div>
    <div class="versus-side side-right">
      <div class="side-name">{side_b}</div>
      {f'<div class="side-stat">{stat_b}</div>' if stat_b else ''}
      <div class="side-label">Resultado Final</div>
    </div>
  </div>
</body>
</html>"""

    # =========================================================================
    # 5. PLANTILLA: QUOTE & EVIDENCE (Cita Resaltada Vox Style)
    # =========================================================================
    def build_quote_evidence_html(
        self,
        quote_text: str,
        source: str = "Registro Oficial",
        highlight_phrase: str = "",
        variant: str = "orange_noir",
    ) -> str:
        p = self.get_palette(variant)
        clean_quote = (quote_text or "La evidencia documental confirma el hallazgo.").strip()

        # Si se especifica highlight_phrase, rodear con tag de resaltador fosforescente
        if highlight_phrase and highlight_phrase in clean_quote:
            clean_quote = clean_quote.replace(
                highlight_phrase,
                f'<span class="highlighter">{highlight_phrase}</span>',
            )

        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
{HTML_FONTS}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: transparent;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    overflow: hidden;
  }}
  .quote-card {{
    position: relative;
    width: 740px;
    padding: 42px 46px;
    border-radius: 24px;
    background: {p['card_bg']};
    border: 1.5px solid {p['border']};
    box-shadow: 0 28px 65px rgba(0, 0, 0, 0.70), 0 0 25px {p['glow']}, inset 0 1px 0 rgba(255, 255, 255, 0.14);
    display: flex;
    flex-direction: column;
    gap: 18px;
  }}
  .quote-icon {{
    position: absolute;
    top: 26px;
    right: 36px;
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 90px;
    line-height: 0.6;
    color: {p['accent']};
    opacity: 0.25;
  }}
  .source-header {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: {p['accent']};
  }}
  .quote-body {{
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 32px;
    font-weight: 600;
    font-style: italic;
    color: #ffffff;
    line-height: 1.35;
    letter-spacing: -0.2px;
  }}
  .highlighter {{
    background: rgba(255, 148, 54, 0.35);
    color: #ffffff;
    padding: 2px 8px;
    border-radius: 4px;
    box-shadow: 0 0 12px rgba(255, 148, 54, 0.40);
  }}
  .source-footer {{
    display: flex;
    align-items: center;
    gap: 10px;
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 17px;
    font-weight: 600;
    color: {p['text_sub']};
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    padding-top: 14px;
  }}
  .verified-badge {{
    color: #10b981;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 13px;
    font-weight: 700;
    background: rgba(16, 185, 129, 0.12);
    padding: 3px 10px;
    border-radius: 6px;
  }}
</style>
</head>
<body>
  <div class="quote-card">
    <div class="quote-icon">“</div>
    <div class="source-header">EVIDENCIA DOCUMENTAL</div>
    <div class="quote-body">“{clean_quote}”</div>
    <div class="source-footer">
      <span>Fuente: <strong>{source}</strong></span>
      <span class="verified-badge">✓ Verificado</span>
    </div>
  </div>
</body>
</html>"""

    # =========================================================================
    # 6. PLANTILLA: STEP BADGE (Fase / Paso / Hito)
    # =========================================================================
    def build_step_badge_html(
        self,
        step_number: str,
        step_title: str,
        subtitle: str = "",
        variant: str = "orange_noir",
    ) -> str:
        p = self.get_palette(variant)
        clean_num = str(step_number or "01").zfill(2)
        clean_title = (step_title or "Paso Clave").strip()
        sub_html = f'<div class="step-sub">{subtitle}</div>' if subtitle else ""

        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
{HTML_FONTS}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: transparent;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    overflow: hidden;
  }}
  .step-pill {{
    display: inline-flex;
    align-items: center;
    gap: 22px;
    padding: 16px 36px 16px 20px;
    border-radius: 24px;
    background: {p['card_bg']};
    border: 1.5px solid {p['border']};
    box-shadow: 0 24px 50px rgba(0, 0, 0, 0.65), 0 0 25px {p['glow']}, inset 0 1px 0 rgba(255, 255, 255, 0.15);
  }}
  .step-num-circle {{
    width: 60px;
    height: 60px;
    border-radius: 18px;
    background: {p['accent_gradient']};
    box-shadow: 0 0 16px {p['glow']};
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'Outfit', sans-serif;
    font-size: 32px;
    font-weight: 900;
    color: #000000;
  }}
  .step-texts {{
    display: flex;
    flex-direction: column;
    gap: 3px;
  }}
  .step-title {{
    font-family: 'Outfit', sans-serif;
    font-size: 38px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: -0.5px;
    line-height: 1.1;
  }}
  .step-sub {{
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 17px;
    font-weight: 600;
    color: {p['text_sub']};
  }}
</style>
</head>
<body>
  <div class="step-pill">
    <div class="step-num-circle">{clean_num}</div>
    <div class="step-texts">
      <div class="step-title">{clean_title}</div>
      {sub_html}
    </div>
  </div>
</body>
</html>"""

    # =========================================================================
    # 7. PLANTILLA: ALERT BANNER (Alerta Crítica / Warning HUD)
    # =========================================================================
    def build_alert_banner_html(
        self,
        headline: str,
        body: str = "",
        tag: str = "ADVERTENCIA CRÍTICA",
        variant: str = "crimson_hazard",
    ) -> str:
        p = self.get_palette(variant)
        clean_hl = (headline or "PUNTO DE QUIEBRE").strip()
        body_html = f'<div class="alert-body">{body}</div>' if body else ""

        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
{HTML_FONTS}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: transparent;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    overflow: hidden;
  }}
  .alert-banner {{
    width: 720px;
    padding: 32px 40px;
    border-radius: 22px;
    background: {p['card_bg']};
    border: 2px solid {p['border']};
    box-shadow: 0 24px 60px rgba(0, 0, 0, 0.70), 0 0 35px {p['glow']}, inset 0 1px 0 rgba(255, 255, 255, 0.15);
    display: flex;
    align-items: flex-start;
    gap: 22px;
  }}
  .alert-icon-box {{
    width: 54px;
    height: 54px;
    border-radius: 14px;
    background: {p['pill_bg']};
    border: 1.5px solid {p['border']};
    display: flex;
    align-items: center;
    justify-content: center;
    color: {p['accent']};
    font-size: 28px;
    flex-shrink: 0;
    box-shadow: 0 0 16px {p['glow']};
  }}
  .alert-content {{
    display: flex;
    flex-direction: column;
    gap: 6px;
  }}
  .alert-tag {{
    font-family: 'Space Grotesk', sans-serif;
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 0.18em;
    color: {p['accent']};
    text-transform: uppercase;
  }}
  .alert-title {{
    font-family: 'Outfit', sans-serif;
    font-size: 34px;
    font-weight: 800;
    color: #ffffff;
    line-height: 1.15;
    letter-spacing: -0.5px;
  }}
  .alert-body {{
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 18px;
    font-weight: 500;
    color: {p['text_sub']};
    line-height: 1.35;
    margin-top: 4px;
  }}
</style>
</head>
<body>
  <div class="alert-banner">
    <div class="alert-icon-box">⚠️</div>
    <div class="alert-content">
      <div class="alert-tag">⚡ {tag}</div>
      <div class="alert-title">{clean_hl}</div>
      {body_html}
    </div>
  </div>
</body>
</html>"""

    # =========================================================================
    # 8. PLANTILLA: SOURCE CHIP (Pastilla de Fuente / Atribución)
    # =========================================================================
    def build_source_chip_html(
        self,
        source_name: str,
        tag: str = "FUENTE OFICIAL",
        variant: str = "orange_noir",
    ) -> str:
        p = self.get_palette(variant)
        clean_src = (source_name or "Registro Internacional").strip()

        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
{HTML_FONTS}
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: transparent;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    overflow: hidden;
  }}
  .source-chip {{
    display: inline-flex;
    align-items: center;
    gap: 14px;
    padding: 12px 28px;
    border-radius: 18px;
    background: {p['card_bg']};
    border: 1px solid {p['border']};
    box-shadow: 0 16px 40px rgba(0, 0, 0, 0.55), 0 0 18px {p['glow']};
  }}
  .chip-tag {{
    font-family: 'Space Grotesk', sans-serif;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.16em;
    color: {p['accent']};
    text-transform: uppercase;
    background: {p['pill_bg']};
    padding: 3px 10px;
    border-radius: 6px;
  }}
  .chip-title {{
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 20px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: -0.2px;
  }}
  .chip-icon {{
    color: {p['accent']};
    font-size: 18px;
  }}
</style>
</head>
<body>
  <div class="source-chip">
    <span class="chip-icon">🛡️</span>
    <span class="chip-tag">{tag}</span>
    <span class="chip-title">{clean_src}</span>
  </div>
</body>
</html>"""

    # =========================================================================
    # MÉTODO MAESTRO DE RENDERIZADO A PNG
    # =========================================================================
    def render_template_to_image(
        self,
        template_name: str,
        out_png: Path,
        params: Optional[Dict[str, Any]] = None,
        variant: str = "orange_noir",
    ) -> Optional[Path]:
        """Renderiza cualquier plantilla a PNG transparente mediante Headless Chromium."""
        params = params or {}
        tmpl = (template_name or "verdict_badge").lower().strip()

        # Generar HTML correspondiente
        if tmpl in ("verdict_badge", "badge", "stamp"):
            html = self.build_verdict_badge_html(
                headline=params.get("headline") or params.get("title") or "Verificado",
                icon=params.get("icon", "✓"),
                variant=variant,
                tilt_deg=float(params.get("tilt_deg", -3.5)),
                subtitle=params.get("subtitle", ""),
            )
        elif tmpl in ("tech_card", "tech_header", "code_spec"):
            html = self.build_tech_header_card_html(
                title=params.get("title") or params.get("headline") or "tech-specification",
                subtitle=params.get("subtitle", ""),
                author=params.get("author", ""),
                repo_or_tag=params.get("repo_or_tag", ""),
                variant=variant,
            )
        elif tmpl in ("stat_counter", "stat_card", "metric"):
            html = self.build_stat_counter_html(
                stat_value=params.get("stat_value") or params.get("stat") or "8.2B",
                stat_label=params.get("stat_label") or params.get("label") or "Total",
                headline=params.get("headline", ""),
                tag=params.get("tag", "MÉTRICA CLAVE"),
                trend_text=params.get("trend_text", "+42% Récord"),
                variant=variant,
            )
        elif tmpl in ("versus_split", "versus", "vs"):
            html = self.build_versus_split_html(
                side_a=params.get("side_a") or params.get("headline") or "Entidad A",
                side_b=params.get("side_b") or params.get("body") or "Entidad B",
                stat_a=params.get("stat_a", ""),
                stat_b=params.get("stat_b", ""),
                tag=params.get("tag", "COMPARATIVA DIRECTA"),
                variant=variant,
            )
        elif tmpl in ("quote_evidence", "quote", "citation"):
            html = self.build_quote_evidence_html(
                quote_text=params.get("quote_text") or params.get("body") or params.get("headline") or "Cita oficial",
                source=params.get("source", "Registro Oficial"),
                highlight_phrase=params.get("highlight_phrase", ""),
                variant=variant,
            )
        elif tmpl in ("step_badge", "step", "phase"):
            html = self.build_step_badge_html(
                step_number=params.get("step_number") or params.get("number") or "01",
                step_title=params.get("step_title") or params.get("title") or params.get("headline") or "Paso Clave",
                subtitle=params.get("subtitle", ""),
                variant=variant,
            )
        elif tmpl in ("alert_banner", "alert", "warning"):
            html = self.build_alert_banner_html(
                headline=params.get("headline") or params.get("title") or "PUNTO CRÍTICO",
                body=params.get("body", ""),
                tag=params.get("tag", "ADVERTENCIA CRÍTICA"),
                variant=variant,
            )
        elif tmpl in ("source_chip", "chip", "source"):
            html = self.build_source_chip_html(
                source_name=params.get("source_name") or params.get("source") or params.get("headline") or "Registro Oficial",
                tag=params.get("tag", "FUENTE OFICIAL"),
                variant=variant,
            )
        else:
            # Fallback a verdict badge
            html = self.build_verdict_badge_html(
                headline=params.get("headline", "Dato Verificado"),
                variant=variant,
            )

        try:
            out_png = Path(out_png)
            out_png.parent.mkdir(parents=True, exist_ok=True)
            html_file = out_png.with_suffix(".html")
            html_file.write_text(html, encoding="utf-8")
            file_uri = html_file.resolve().as_uri()

            args = [
                self.browser_bin,
                "--headless",
                "--disable-gpu",
                "--no-sandbox",
                "--hide-scrollbars",
                "--default-background-color=00000000",
                f"--screenshot={out_png.resolve()}",
                "--window-size=1080,1920",
                file_uri,
            ]
            subprocess.run(args, capture_output=True, check=True, timeout=15)
            self._crop_transparent(out_png)
            if out_png.exists() and out_png.stat().st_size > 500:
                return out_png
        except Exception as exc:
            logger.warning(f"Error renderizando template '{tmpl}': {exc}")
        return None

    # Catálogo introspectivo para el frontend y director
    @staticmethod
    def get_catalog() -> Dict[str, Any]:
        return {
            "themes": list(THEME_PALETTES.keys()),
            "templates": [
                {
                    "id": "verdict_badge",
                    "name": "Distintivo / Sello de Veredicto",
                    "description": "Píldora viral inclinada con borde brillante, ícono de verificación y tipografía serif editorial.",
                    "sfx": "pop",
                    "animation": "spring_bounce",
                    "default_variant": "orange_noir",
                    "sample_params": {"headline": "ganó Opus", "icon": "✓", "tilt_deg": -3.5},
                },
                {
                    "id": "tech_card",
                    "name": "Tarjeta Técnica de Cabecera",
                    "description": "Tarjeta flotante superior en dark slate con micro-matriz de puntos y tipografía mono.",
                    "sfx": "whoosh",
                    "animation": "top_slide_settle",
                    "default_variant": "orange_noir",
                    "sample_params": {"title": "find-skills", "subtitle": "por Vercel · vercel-labs/skills"},
                },
                {
                    "id": "stat_counter",
                    "name": "Métrica Clave / Cifra de Impacto",
                    "description": "Tarjeta Bento con número gigante en gradiente, medidor de barra y tendencia.",
                    "sfx": "chime",
                    "animation": "elastic_scale_pop",
                    "default_variant": "orange_noir",
                    "sample_params": {"stat_value": "+340%", "stat_label": "Crecimiento IA", "headline": "Récord Histórico"},
                },
                {
                    "id": "versus_split",
                    "name": "Comparativa Versus Dual",
                    "description": "Contenedor dividido lado A vs lado B con distintivo central circular VS en naranja eléctrico.",
                    "sfx": "impact",
                    "animation": "convergence_pop",
                    "default_variant": "orange_noir",
                    "sample_params": {"side_a": "Humano", "side_b": "IA Autónoma", "stat_a": "4h 20m", "stat_b": "12s"},
                },
                {
                    "id": "quote_evidence",
                    "name": "Cita y Evidencia Documental (Vox Style)",
                    "description": "Tarjeta periodística con comillas tipográficas gigantes y texto resaltado fluorescente.",
                    "sfx": "whoosh",
                    "animation": "smooth_rise",
                    "default_variant": "orange_noir",
                    "sample_params": {"quote_text": "Los datos demuestran un cambio irreversible en el fondo oceánico.", "source": "NOAA Research 2026"},
                },
                {
                    "id": "step_badge",
                    "name": "Insignia de Fase / Paso a Paso",
                    "description": "Píldora moderna con círculo numérico en naranja neón y titular de fase.",
                    "sfx": "pop",
                    "animation": "slide_in_left",
                    "default_variant": "orange_noir",
                    "sample_params": {"step_number": "01", "step_title": "Detección Acústica", "subtitle": "Frecuencia Ultra Baja"},
                },
                {
                    "id": "alert_banner",
                    "name": "Banner de Alerta Táctica HUD",
                    "description": "Banner de advertencia con ícono de peligro, bordes carmesí/ámbar y micro-etiqueta superior.",
                    "sfx": "alert",
                    "animation": "flash_impact",
                    "default_variant": "crimson_hazard",
                    "sample_params": {"headline": "CONTRADICCIÓN DETECTADA", "body": "La señal no coincide con actividad biológica conocida."},
                },
                {
                    "id": "source_chip",
                    "name": "Pastilla de Fuente Verificada",
                    "description": "Micro-chip discreto con escudo y atribución oficial para esquinas.",
                    "sfx": "pop",
                    "animation": "corner_pop",
                    "default_variant": "orange_noir",
                    "sample_params": {"source_name": "Laboratorio Acústico del Pacífico", "tag": "FUENTE OFICIAL"},
                },
            ]
        }
