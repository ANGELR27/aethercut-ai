"""
WebCardRenderer - Motor de Renderizado Gráfico Basado en Web (HTML5/CSS3/SVG + Headless Chromium).
Produce tarjetas Bento cuadradas y rectangulares de estándar profesional 2026.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any


HTML_FONTS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
"""


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


class WebCardRenderer:
    """Renderizador moderno de tarjetas estilo Bento Square & Pro HUD."""

    def __init__(self, browser_bin: Optional[str] = None):
        self.browser_bin = browser_bin or _get_browser_bin()

    def generate_html(
        self,
        headline: str,
        stat_value: str = "95%",
        stat_label: str = "Métrica Clave",
        body: str = "",
        badge: str = "Dato Verificado",
        source: str = "Registro Oficial 2026",
        style: str = "obsidian_bento",
    ) -> str:
        """Genera el HTML5 + CSS de alta gama para la tarjeta seleccionada."""

        # Sanitizar textos
        headline = headline.replace("<", "&lt;").replace(">", "&gt;")
        stat_value = stat_value.replace("<", "&lt;").replace(">", "&gt;")
        stat_label = stat_label.replace("<", "&lt;").replace(">", "&gt;")
        body = body.replace("<", "&lt;").replace(">", "&gt;")
        badge = badge.replace("<", "&lt;").replace(">", "&gt;")
        source = source.replace("<", "&lt;").replace(">", "&gt;")

        if style in ("quote", "cita"):
            return self.generate_quote_html(
                quote_text=body or headline,
                highlight_words=stat_value if (stat_value and stat_value not in ("95%", "DATO CLAVE")) else "",
                author=headline,
                badge=badge or "ÉNFASIS CLAVE",
            )
        if style in ("flag", "pais", "entidad"):
            # Detectar país y código ISO oficial
            c_code = "us"
            low_h = (headline + " " + body).lower()
            if any(k in low_h for k in ["china", "pekin", "pekín"]):
                c_code = "cn"
            elif any(k in low_h for k in ["rusia", "moscu", "moscú"]):
                c_code = "ru"
            elif any(k in low_h for k in ["ucrania", "kiev"]):
                c_code = "ua"
            elif any(k in low_h for k in ["europa", "unión europea", "ue"]):
                c_code = "eu"
            elif any(k in low_h for k in ["taiwan", "taiwán"]):
                c_code = "tw"
            elif any(k in low_h for k in ["españa", "espana", "madrid"]):
                c_code = "es"
            elif any(k in low_h for k in ["méxico", "mexico"]):
                c_code = "mx"
            elif any(k in low_h for k in ["israel", "jerusalén", "tel aviv"]):
                c_code = "il"
            elif any(k in low_h for k in ["turquía", "turquia", "ankara"]):
                c_code = "tr"
            elif any(k in low_h for k in ["otan", "nato"]):
                c_code = "un"

            return self.generate_entity_flag_html(
                country_name=headline,
                country_code=c_code,
                role_label=badge or "ANÁLISIS ESTRATÉGICO",
                metric_stat=stat_value or "DATOS CLAVE",
                detail=body,
            )

        if style == "tactical_amber":
            # Estilo 2: Táctico Ámbar / Cuadrado HUD
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
    font-family: 'Plus Jakarta Sans', sans-serif;
  }}
  .card {{
    width: 600px;
    background: linear-gradient(145deg, rgba(9, 10, 13, 0.98) 0%, rgba(4, 5, 7, 0.99) 100%);
    border: 1px solid rgba(255, 255, 255, 0.09);
    box-shadow: 0 32px 80px rgba(0, 0, 0, 0.95), 0 0 40px rgba(12, 24, 48, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 26px;
    color: #f8fafc;
    position: relative;
  }}
  .corner-tl {{ position: absolute; top: 4px; left: 4px; width: 10px; height: 10px; border-top: 2px solid #f59e0b; border-left: 2px solid #f59e0b; }}
  .corner-br {{ position: absolute; bottom: 4px; right: 4px; width: 10px; height: 10px; border-bottom: 2px solid #f59e0b; border-right: 2px solid #f59e0b; }}
  .top-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 18px;
    border-bottom: 1px solid rgba(255,255,255,0.08);
    padding-bottom: 12px;
  }}
  .badge {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 700;
    color: #f59e0b;
    letter-spacing: 1px;
    display: flex;
    align-items: center;
    gap: 8px;
    text-transform: uppercase;
  }}
  .dot {{ width: 8px; height: 8px; border-radius: 50%; background: #f59e0b; box-shadow: 0 0 10px #f59e0b; }}
  .source {{ font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #64748b; }}
  .split-metric {{
    display: flex;
    align-items: stretch;
    gap: 24px;
    margin-bottom: 20px;
    background: rgba(0, 0, 0, 0.45);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 20px 24px;
  }}
  .metric-badge-box {{
    display: flex;
    flex-direction: column;
    justify-content: center;
    min-width: 150px;
    max-width: 220px;
    padding-right: 22px;
    border-right: 1px solid rgba(255, 255, 255, 0.12);
  }}
  .stat-val {{
    font-family: 'Outfit', sans-serif;
    font-size: 34px;
    font-weight: 800;
    line-height: 1.1;
    color: #fbbf24;
    text-shadow: 0 0 20px rgba(245, 158, 11, 0.35);
    letter-spacing: -0.5px;
  }}
  .stat-lbl {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-top: 6px;
    font-weight: 600;
  }}
  .metric-info {{
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
  }}
  .metric-info h3 {{
    font-family: 'Outfit', sans-serif;
    font-size: 22px;
    color: #ffffff;
    font-weight: 700;
    line-height: 1.25;
    margin-bottom: 6px;
  }}
  .metric-info p {{
    font-size: 14px;
    color: #cbd5e1;
    line-height: 1.5;
  }}
  .footer-row {{
    display: flex;
    justify-content: space-between;
    font-size: 11px;
    color: #94a3b8;
    font-family: 'JetBrains Mono', monospace;
    margin-top: 10px;
  }}
</style>
</head>
<body>
  <div class="card">
    <div class="corner-tl"></div>
    <div class="corner-br"></div>
    <div class="top-row">
      <div class="badge"><span class="dot"></span>{badge}</div>
      <div class="source">{source}</div>
    </div>
    <div class="split-metric">
      <div class="metric-badge-box">
        <div class="stat-val">{stat_value}</div>
        <div class="stat-lbl">{stat_label}</div>
      </div>
      <div class="metric-info">
        <h3>{headline}</h3>
        <p>{body}</p>
      </div>
    </div>
    <div class="footer-row">
      <span>REF: EVIDENCIA ARQUEOLÓGICA & TÉCNICA</span>
      <span>ESTATUS: AUDITADO</span>
    </div>
  </div>
</body>
</html>"""

        elif style == "square_emerald":
            # Estilo 3: Cuadrado Compacto 1:1
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
    font-family: 'Plus Jakarta Sans', sans-serif;
  }}
  .card {{
    width: 440px;
    height: 440px;
    background: linear-gradient(160deg, rgba(9, 10, 13, 0.98) 0%, rgba(4, 5, 7, 0.99) 100%);
    border: 1px solid rgba(255, 255, 255, 0.09);
    box-shadow: 0 32px 80px rgba(0, 0, 0, 0.95), 0 0 40px rgba(12, 24, 48, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 30px;
    color: #f8fafc;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    position: relative;
    overflow: hidden;
  }}
  .card::after {{
    content: '';
    position: absolute;
    bottom: -60px; right: -60px;
    width: 180px; height: 180px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(16, 185, 129, 0.25) 0%, transparent 70%);
    pointer-events: none;
  }}
  .sq-badge {{
    align-self: flex-start;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    border-radius: 6px;
    background: rgba(16, 185, 129, 0.12);
    border: 1px solid rgba(16, 185, 129, 0.35);
    color: #34d399;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 700;
  }}
  .sq-big-stat {{
    font-family: 'Outfit', sans-serif;
    font-size: 60px;
    font-weight: 800;
    line-height: 1;
    color: #ffffff;
    letter-spacing: -1.5px;
    margin: 14px 0 4px;
  }}
  .sq-stat-lbl {{
    font-size: 13px;
    color: #34d399;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
  }}
  .sq-title {{
    font-family: 'Outfit', sans-serif;
    font-size: 22px;
    font-weight: 700;
    color: #ffffff;
    line-height: 1.25;
    margin-bottom: 8px;
  }}
  .sq-desc {{
    font-size: 13px;
    color: #94a3b8;
    line-height: 1.45;
  }}
  .sq-footer {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    padding-top: 14px;
    font-size: 11px;
    color: #64748b;
  }}
</style>
</head>
<body>
  <div class="card">
    <div>
      <div class="sq-badge">● {badge}</div>
      <div class="sq-big-stat">{stat_value}</div>
      <div class="sq-stat-lbl">{stat_label}</div>
    </div>
    <div>
      <div class="sq-title">{headline}</div>
      <div class="sq-desc">{body}</div>
    </div>
    <div class="sq-footer">
      <span>{source}</span>
      <span>✓ Certificado</span>
    </div>
  </div>
</body>
</html>"""

        else:
            # Estilo 1 por defecto: Obsidian Bento Pro (Rectangular Cuadrado Moderno)
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
    font-family: 'Plus Jakarta Sans', sans-serif;
  }}
  .card {{
    width: 580px;
    background: linear-gradient(145deg, rgba(9, 10, 13, 0.98) 0%, rgba(4, 5, 7, 0.99) 100%);
    border: 1px solid rgba(255, 255, 255, 0.09);
    box-shadow: 0 32px 80px rgba(0, 0, 0, 0.95), 0 0 40px rgba(12, 24, 48, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 28px;
    color: #f8fafc;
    position: relative;
    overflow: hidden;
  }}
  .card::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #38bdf8, #818cf8, transparent);
  }}
  .top-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
  }}
  .badge {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 12px;
    border-radius: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
    background: rgba(56, 189, 248, 0.12);
    border: 1px solid rgba(56, 189, 248, 0.35);
    color: #38bdf8;
    text-transform: uppercase;
  }}
  .badge-dot {{
    width: 6px; height: 6px; border-radius: 50%; background: #38bdf8; box-shadow: 0 0 8px #38bdf8;
  }}
  .source-tag {{
    font-size: 11px;
    color: #94a3b8;
    display: flex;
    align-items: center;
    gap: 4px;
  }}
  .metric-box {{
    background: rgba(2, 6, 23, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 18px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  .metric-val {{
    font-family: 'Outfit', sans-serif;
    font-size: 38px;
    font-weight: 800;
    color: #38bdf8;
    line-height: 1;
    letter-spacing: -0.5px;
  }}
  .metric-label {{
    font-size: 12px;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-top: 4px;
    font-weight: 600;
  }}
  .chart-bars {{
    display: flex;
    align-items: flex-end;
    gap: 5px;
    height: 44px;
  }}
  .c-bar {{
    width: 8px;
    border-radius: 2px;
    background: rgba(56, 189, 248, 0.25);
  }}
  .c-bar.active {{
    background: linear-gradient(180deg, #38bdf8, #0284c7);
    box-shadow: 0 0 10px rgba(56, 189, 248, 0.5);
  }}
  .headline {{
    font-family: 'Outfit', sans-serif;
    font-size: 22px;
    font-weight: 700;
    line-height: 1.25;
    color: #ffffff;
    margin-bottom: 10px;
  }}
  .body-text {{
    font-size: 13.5px;
    line-height: 1.5;
    color: #cbd5e1;
  }}
</style>
</head>
<body>
  <div class="card">
    <div class="top-row">
      <div class="badge"><span class="badge-dot"></span>{badge}</div>
      <div class="source-tag">{source}</div>
    </div>
    <div class="metric-box">
      <div>
        <div class="metric-val">{stat_value}</div>
        <div class="metric-label">{stat_label}</div>
      </div>
      <div class="chart-bars">
        <div class="c-bar" style="height: 35%;"></div>
        <div class="c-bar" style="height: 50%;"></div>
        <div class="c-bar" style="height: 65%;"></div>
        <div class="c-bar" style="height: 80%;"></div>
        <div class="c-bar active" style="height: 95%;"></div>
      </div>
    </div>
    <div class="headline">{headline}</div>
    <div class="body-text">{body}</div>
  </div>
</body>
</html>"""

    def generate_quote_html(
        self,
        quote_text: str,
        highlight_words: str = "",
        author: str = "Afirmación Destacada",
        badge: str = "ÉNFASIS CLAVE",
    ) -> str:
        """Tarjeta grande referencial para énfasis en frases (Kinetic Impact Quote)."""
        safe_q = quote_text.replace("<", "&lt;").replace(">", "&gt;")
        if highlight_words and highlight_words.lower() in safe_q.lower():
            # Resaltar la palabra o frase con glow
            import re
            pattern = re.compile(re.escape(highlight_words), re.IGNORECASE)
            safe_q = pattern.sub(f'<span class="hl">{highlight_words}</span>', safe_q)

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
    font-family: 'Plus Jakarta Sans', sans-serif;
  }}
  .quote-card {{
    width: 660px;
    background: linear-gradient(145deg, rgba(9, 10, 13, 0.98) 0%, rgba(4, 5, 7, 0.99) 100%);
    border: 1px solid rgba(255, 255, 255, 0.09);
    border-left: 4px solid #38bdf8;
    box-shadow: 0 32px 80px rgba(0, 0, 0, 0.95), 0 0 40px rgba(12, 24, 48, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    padding: 30px 34px;
    color: #f8fafc;
    position: relative;
  }}
  .quote-mark {{
    position: absolute;
    top: 16px; right: 24px;
    font-family: 'Outfit', sans-serif;
    font-size: 80px;
    line-height: 1;
    color: rgba(56, 189, 248, 0.12);
    user-select: none;
  }}
  .q-badge {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 12px;
    border-radius: 4px;
    background: rgba(56, 189, 248, 0.15);
    border: 1px solid rgba(56, 189, 248, 0.35);
    color: #38bdf8;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    margin-bottom: 16px;
  }}
  .q-text {{
    font-family: 'Outfit', sans-serif;
    font-size: 26px;
    font-weight: 700;
    line-height: 1.35;
    color: #ffffff;
    margin-bottom: 20px;
    letter-spacing: -0.3px;
  }}
  .hl {{
    color: #38bdf8;
    text-shadow: 0 0 16px rgba(56, 189, 248, 0.6);
  }}
  .q-footer {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    padding-top: 14px;
    font-size: 12px;
    color: #94a3b8;
    font-family: 'JetBrains Mono', monospace;
  }}
  .q-author {{
    color: #e2e8f0;
    font-weight: 600;
  }}
</style>
</head>
<body>
  <div class="quote-card">
    <div class="quote-mark">“</div>
    <div class="q-badge">● {badge}</div>
    <div class="q-text">«{safe_q}»</div>
    <div class="q-footer">
      <span class="q-author">— {author}</span>
      <span>DECLARACIÓN VERIFICADA</span>
    </div>
  </div>
</body>
</html>"""

    def generate_entity_flag_html(
        self,
        country_name: str,
        country_code: str = "us",
        role_label: str = "ANÁLISIS ESTRATÉGICO",
        metric_stat: str = "DATOS CLAVE",
        detail: str = "Evaluación geopolítica y balance operativo en tiempo real.",
        flag_emoji: str = "",
    ) -> str:
        """Tarjeta de entidad geopolítica o país con bandera oficial de alta definición y métrica destacada (sin emojis)."""
        c_clean = country_name.replace("<", "&lt;").replace(">", "&gt;")
        code_clean = (country_code or "us").lower().strip()
        role_clean = role_label.replace("<", "&lt;").replace(">", "&gt;")
        stat_clean = metric_stat.replace("<", "&lt;").replace(">", "&gt;")
        det_clean = detail.replace("<", "&lt;").replace(">", "&gt;")

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
    font-family: 'Plus Jakarta Sans', sans-serif;
  }}
  /* Floating HUD container — NO enclosing background card */
  .floating-entity {{
    width: 680px;
    padding: 12px 18px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    position: relative;
  }}
  .floating-meta-row {{
    display: flex;
    align-items: center;
    gap: 10px;
  }}
  .floating-role-badge {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 12px;
    border-radius: 4px;
    background: rgba(8, 9, 12, 0.92);
    border: 1px solid rgba(255, 255, 255, 0.12);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.85), 0 0 20px rgba(12, 24, 48, 0.4);
    color: #38bdf8;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
  }}
  .floating-stat-pill {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 700;
    color: #f59e0b;
    background: rgba(8, 9, 12, 0.92);
    padding: 5px 12px;
    border-radius: 4px;
    border: 1px solid rgba(255, 255, 255, 0.12);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.85), 0 0 20px rgba(12, 24, 48, 0.3);
    letter-spacing: 0.5px;
  }}
  .floating-identity-row {{
    display: flex;
    align-items: center;
    gap: 20px;
  }}
  .floating-flag-box {{
    width: 68px;
    height: 46px;
    border-radius: 6px;
    overflow: hidden;
    box-shadow: 0 16px 36px rgba(0, 0, 0, 0.95), 0 0 24px rgba(12, 24, 48, 0.5);
    border: 1.5px solid rgba(255, 255, 255, 0.20);
    background: #08090c;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }}
  .floating-flag-img {{
    width: 100%;
    height: 100%;
    object-fit: cover;
  }}
  .floating-name-col {{
    display: flex;
    flex-direction: column;
    gap: 3px;
  }}
  .floating-country-title {{
    font-family: 'Outfit', sans-serif;
    font-size: 38px;
    font-weight: 800;
    color: #ffffff;
    line-height: 1.05;
    letter-spacing: -0.6px;
    text-shadow: 0 4px 25px rgba(0, 0, 0, 0.98), 0 1px 4px rgba(0, 0, 0, 0.9);
  }}
  .floating-iso-badge {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 700;
    color: rgba(255, 255, 255, 0.65);
    letter-spacing: 1.5px;
    text-transform: uppercase;
    text-shadow: 0 2px 10px rgba(0, 0, 0, 0.95);
  }}
  .floating-detail-text {{
    font-size: 15px;
    line-height: 1.55;
    color: #e2e8f0;
    text-shadow: 0 3px 18px rgba(0, 0, 0, 0.98), 0 1px 3px rgba(0, 0, 0, 0.9);
    max-width: 640px;
    padding-left: 2px;
  }}
</style>
</head>
<body>
  <div class="floating-entity">
    <div class="floating-meta-row">
      <div class="floating-role-badge">● {role_clean}</div>
      <div class="floating-stat-pill">{stat_clean}</div>
    </div>
    <div class="floating-identity-row">
      <div class="floating-flag-box">
        <img class="floating-flag-img" src="https://flagcdn.com/w160/{code_clean}.png" alt="{code_clean}" onerror="this.style.display='none'" />
      </div>
      <div class="floating-name-col">
        <div class="floating-country-title">{c_clean}</div>
        <div class="floating-iso-badge">{code_clean.upper()} // ENTIDAD RECONOCIDA</div>
      </div>
    </div>
    <div class="floating-detail-text">{det_clean}</div>
  </div>
</body>
</html>"""

    def generate_popup_html(
        self,
        text: str,
        tag_label: str = "CLAVE",
        kind: str = "fact",
    ) -> str:
        """Micro Pop-up HUD reactivo estilo pastilla moderna."""
        kind_colors = {
            "stat": ("#f59e0b", "rgba(245, 158, 11, 0.15)", "rgba(245, 158, 11, 0.35)"),
            "fact": ("#38bdf8", "rgba(56, 189, 248, 0.15)", "rgba(56, 189, 248, 0.35)"),
            "alert": ("#f43f5e", "rgba(244, 63, 94, 0.15)", "rgba(244, 63, 94, 0.35)"),
            "quote": ("#10b981", "rgba(16, 185, 129, 0.15)", "rgba(16, 185, 129, 0.35)"),
        }
        accent, bg, border = kind_colors.get(kind.lower(), kind_colors["fact"])

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
    font-family: 'Plus Jakarta Sans', sans-serif;
  }}
  .pill {{
    display: inline-flex;
    align-items: center;
    gap: 14px;
    background: rgba(9, 10, 13, 0.96);
    border: 1px solid rgba(255, 255, 255, 0.10);
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.92), 0 0 30px rgba(12, 24, 48, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.08);
    border-radius: 999px;
    padding: 10px 24px;
    color: #ffffff;
  }}
  .badge {{
    display: flex;
    align-items: center;
    gap: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 700;
    color: {accent};
    letter-spacing: 1px;
    padding: 4px 10px;
    border-radius: 999px;
    background: {bg};
    border: 1px solid {border};
  }}
  .dot {{
    width: 6px; height: 6px; border-radius: 50%; background: {accent}; box-shadow: 0 0 8px {accent};
  }}
  .divider {{
    width: 1px; height: 18px; background: rgba(255, 255, 255, 0.15);
  }}
  .text {{
    font-size: 15px;
    font-weight: 600;
    color: #f8fafc;
    white-space: nowrap;
    letter-spacing: -0.2px;
  }}
</style>
</head>
<body>
  <div class="pill">
    <div class="badge"><span class="dot"></span>{tag_label}</div>
    <div class="divider"></div>
    <div class="text">{text}</div>
  </div>
</body>
</html>"""

    def generate_lower_third_html(
        self,
        title: str,
        subtitle: str,
        tag: str = "INFORME ESPECIAL",
    ) -> str:
        """Rótulo Broadcast Lower Third panorámico de alta fidelidad."""
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
    font-family: 'Plus Jakarta Sans', sans-serif;
  }}
  .lt-container {{
    width: 780px;
    background: linear-gradient(90deg, rgba(9, 10, 13, 0.98) 0%, rgba(9, 10, 13, 0.88) 75%, transparent 100%);
    border-left: 4px solid #38bdf8;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    box-shadow: 0 24px 60px rgba(0, 0, 0, 0.92), 0 0 35px rgba(12, 24, 48, 0.35);
    border-radius: 0 10px 10px 0;
    padding: 16px 26px;
    color: #ffffff;
    position: relative;
  }}
  .lt-tag {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 700;
    color: #38bdf8;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-bottom: 4px;
    display: flex;
    align-items: center;
    gap: 6px;
  }}
  .lt-title {{
    font-family: 'Outfit', sans-serif;
    font-size: 24px;
    font-weight: 800;
    color: #ffffff;
    line-height: 1.2;
    margin-bottom: 4px;
  }}
  .lt-sub {{
    font-size: 13.5px;
    color: #cbd5e1;
    font-weight: 500;
  }}
</style>
</head>
<body>
  <div class="lt-container">
    <div class="lt-tag">● {tag}</div>
    <div class="lt-title">{title}</div>
    <div class="lt-sub">{subtitle}</div>
  </div>
</body>
</html>"""


    def render_to_image(
        self,
        headline: str,
        out_png: Path,
        stat_value: str = "95%",
        stat_label: str = "Tasa de Precisión",
        body: str = "",
        badge: str = "Dato Verificado",
        source: str = "Registro Oficial 2026",
        style: str = "obsidian_bento",
    ) -> Path:
        """Renderiza la tarjeta a un archivo PNG con fondo transparente utilizando Headless Chromium."""
        out_png = Path(out_png)
        out_png.parent.mkdir(parents=True, exist_ok=True)
        html_file = out_png.with_suffix(".html")

        html_content = self.generate_html(
            headline=headline,
            stat_value=stat_value,
            stat_label=stat_label,
            body=body,
            badge=badge,
            source=source,
            style=style,
        )
        html_file.write_text(html_content, encoding="utf-8")

        file_uri = html_file.resolve().as_uri()

        # Configurar dimensiones de captura según el estilo
        win_size = "900,600" if style != "square_emerald" else "700,700"

        args = [
            self.browser_bin,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--hide-scrollbars",
            "--default-background-color=00000000",
            f"--screenshot={out_png.resolve()}",
            f"--window-size={win_size}",
            file_uri,
        ]

        subprocess.run(args, capture_output=True, check=True, timeout=15)

        # Auto-recorte inteligente para ajustar los bordes transparentes conservando la sombra suave
        try:
            from PIL import Image
            im = Image.open(out_png)
            bbox = im.getbbox()
            if bbox:
                pad = 14
                b = (max(0, bbox[0]-pad), max(0, bbox[1]-pad), min(im.width, bbox[2]+pad), min(im.height, bbox[3]+pad))
                cropped = im.crop(b)
                cropped.save(out_png)
        except Exception:
            pass

        return out_png

    def render_quote_to_image(
        self,
        quote_text: str,
        out_png: Path,
        highlight_words: str = "",
        author: str = "Afirmación Destacada",
        badge: str = "ÉNFASIS CLAVE",
    ) -> Path:
        """Renderiza una tarjeta de énfasis en frase / cita cinética."""
        out_png = Path(out_png)
        out_png.parent.mkdir(parents=True, exist_ok=True)
        html_file = out_png.with_suffix(".html")
        html_content = self.generate_quote_html(quote_text, highlight_words, author, badge)
        html_file.write_text(html_content, encoding="utf-8")
        file_uri = html_file.resolve().as_uri()

        args = [
            self.browser_bin,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--hide-scrollbars",
            "--default-background-color=00000000",
            f"--screenshot={out_png.resolve()}",
            "--window-size=1000,600",
            file_uri,
        ]
        subprocess.run(args, capture_output=True, check=True, timeout=15)
        self._crop_transparent(out_png)
        return out_png

    def render_entity_flag_to_image(
        self,
        country_name: str,
        out_png: Path,
        country_code: str = "us",
        role_label: str = "ANÁLISIS ESTRATÉGICO",
        metric_stat: str = "DATOS CLAVE",
        detail: str = "Evaluación geopolítica y balance operativo en tiempo real.",
        flag_emoji: str = "",
    ) -> Path:
        """Renderiza una tarjeta táctica de país o entidad geopolítica con bandera (sin emojis)."""
        out_png = Path(out_png)
        out_png.parent.mkdir(parents=True, exist_ok=True)
        html_file = out_png.with_suffix(".html")
        html_content = self.generate_entity_flag_html(
            country_name=country_name,
            country_code=country_code,
            role_label=role_label,
            metric_stat=metric_stat,
            detail=detail,
            flag_emoji=flag_emoji,
        )
        html_file.write_text(html_content, encoding="utf-8")
        file_uri = html_file.resolve().as_uri()

        args = [
            self.browser_bin,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--hide-scrollbars",
            "--default-background-color=00000000",
            f"--screenshot={out_png.resolve()}",
            "--window-size=900,500",
            file_uri,
        ]
        subprocess.run(args, capture_output=True, check=True, timeout=15)
        self._crop_transparent(out_png)
        return out_png

    def render_popup_to_image(
        self,
        text: str,
        out_png: Path,
        tag_label: str = "CLAVE",
        kind: str = "fact",
    ) -> Path:
        """Renderiza un micro Pop-up HUD reactivo estilo pastilla moderna."""
        out_png = Path(out_png)
        out_png.parent.mkdir(parents=True, exist_ok=True)
        html_file = out_png.with_suffix(".html")
        html_content = self.generate_popup_html(text, tag_label, kind)
        html_file.write_text(html_content, encoding="utf-8")
        file_uri = html_file.resolve().as_uri()

        args = [
            self.browser_bin,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--hide-scrollbars",
            "--default-background-color=00000000",
            f"--screenshot={out_png.resolve()}",
            "--window-size=800,300",
            file_uri,
        ]
        subprocess.run(args, capture_output=True, check=True, timeout=15)
        self._crop_transparent(out_png)
        return out_png

    def render_lower_third_to_image(
        self,
        title: str,
        subtitle: str,
        out_png: Path,
        tag: str = "INFORME ESPECIAL",
    ) -> Path:
        """Renderiza un rótulo broadcast panorámico de alta gama."""
        out_png = Path(out_png)
        out_png.parent.mkdir(parents=True, exist_ok=True)
        html_file = out_png.with_suffix(".html")
        html_content = self.generate_lower_third_html(title, subtitle, tag)
        html_file.write_text(html_content, encoding="utf-8")
        file_uri = html_file.resolve().as_uri()

        args = [
            self.browser_bin,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--hide-scrollbars",
            "--default-background-color=00000000",
            f"--screenshot={out_png.resolve()}",
            "--window-size=1100,400",
            file_uri,
        ]
        subprocess.run(args, capture_output=True, check=True, timeout=15)
        self._crop_transparent(out_png)
        return out_png

    def generate_chips_html(self, chips: list) -> str:
        """Fila horizontal de chips Glassmorphism con banderas y datos de referencia."""
        import re
        COUNTRY_CODES = {
            "estados unidos": "us", "ee.uu": "us", "eeuu": "us", "usa": "us", "us": "us",
            "china": "cn", "cn": "cn", "rusia": "ru", "ru": "ru", "ucrania": "ua", "ua": "ua",
            "alemania": "de", "francia": "fr", "reino unido": "gb", "uk": "gb", "españa": "es",
            "japón": "jp", "japon": "jp", "corea": "kr", "taiwan": "tw", "taiwán": "tw",
        }

        chips_html = []
        for c in chips[:5]:
            raw = str(c).strip()
            if not raw:
                continue
            clean = raw
            c_code = None
            m = re.match(r"^([A-Za-z]{2})\s+(.+)$", raw)
            if m and m.group(1).lower() in COUNTRY_CODES:
                c_code = COUNTRY_CODES[m.group(1).lower()]
                clean = m.group(2).strip()
            else:
                low = raw.lower()
                for k, code in COUNTRY_CODES.items():
                    if k in low:
                        c_code = code
                        break

            if c_code:
                flag_markup = f'<img src="https://flagcdn.com/w80/{c_code}.png" class="flag-thumb" alt="{c_code}">'
            else:
                flag_markup = '<span class="chip-dot"></span>'

            chips_html.append(f"""
              <div class="glass-chip">
                {flag_markup}
                <span class="chip-text">{clean}</span>
              </div>
            """)

        joined = "".join(chips_html)
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
    font-family: 'Plus Jakarta Sans', sans-serif;
  }}
  .chips-track {{
    display: inline-flex;
    align-items: center;
    gap: 12px;
    padding: 10px;
  }}
  .glass-chip {{
    display: inline-flex;
    align-items: center;
    gap: 10px;
    background: rgba(9, 10, 13, 0.96);
    border: 1px solid rgba(255, 255, 255, 0.10);
    box-shadow: 0 16px 40px rgba(0, 0, 0, 0.90), 0 0 25px rgba(12, 24, 48, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.08);
    border-radius: 999px;
    padding: 8px 18px;
    color: #f8fafc;
  }}
  .flag-thumb {{
    width: 22px;
    height: 15px;
    border-radius: 3px;
    object-fit: cover;
    box-shadow: 0 2px 6px rgba(0,0,0,0.4);
  }}
  .chip-dot {{
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #38bdf8;
    box-shadow: 0 0 8px #38bdf8;
  }}
  .chip-text {{
    font-size: 14px;
    font-weight: 600;
    letter-spacing: -0.2px;
    white-space: nowrap;
  }}
</style>
</head>
<body>
  <div class="chips-track">
    {joined}
  </div>
</body>
</html>"""

    def render_chips_to_image(self, chips: list, out_png: Path) -> Path:
        """Renderiza una fila de chips moderna con banderas e indicadores de luz."""
        out_png = Path(out_png)
        out_png.parent.mkdir(parents=True, exist_ok=True)
        html_file = out_png.with_suffix(".html")
        html_content = self.generate_chips_html(chips)
        html_file.write_text(html_content, encoding="utf-8")
        file_uri = html_file.resolve().as_uri()

        args = [
            self.browser_bin,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--hide-scrollbars",
            "--default-background-color=00000000",
            f"--screenshot={out_png.resolve()}",
            "--window-size=1200,300",
            file_uri,
        ]
        subprocess.run(args, capture_output=True, check=True, timeout=15)
        self._crop_transparent(out_png)
        return out_png

    def generate_ranking_number_html(
        self,
        number: str = "03",
        title: str = "Puesto Destacado",
        subtitle: str = "Análisis e Impacto Clave",
        badge: str = "TOP RANKING",
    ) -> str:
        """Diseño cinematográfico para hitos de cuenta regresiva (Top 10, Puestos, Cifras de Impacto)."""
        num_clean = number.replace("<", "&lt;").replace(">", "&gt;")
        tit_clean = title.replace("<", "&lt;").replace(">", "&gt;")
        sub_clean = subtitle.replace("<", "&lt;").replace(">", "&gt;")
        bdg_clean = badge.replace("<", "&lt;").replace(">", "&gt;")

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
    font-family: 'Plus Jakarta Sans', sans-serif;
  }}
  .ranking-card {{
    width: 660px;
    background: linear-gradient(145deg, rgba(9, 10, 13, 0.98) 0%, rgba(4, 5, 7, 0.99) 100%);
    border: 1px solid rgba(255, 255, 255, 0.10);
    box-shadow: 0 32px 80px rgba(0, 0, 0, 0.95), 0 0 45px rgba(12, 24, 48, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 30px 36px;
    color: #ffffff;
    display: flex;
    align-items: center;
    gap: 30px;
    position: relative;
    overflow: hidden;
  }}
  .ranking-card::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; width: 140px;
    height: 2px;
    background: linear-gradient(90deg, #38bdf8, transparent);
  }}
  .number-box {{
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-width: 120px;
    height: 120px;
    background: rgba(14, 18, 26, 0.85);
    border: 1px solid rgba(56, 189, 248, 0.25);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.6), inset 0 0 20px rgba(56, 189, 248, 0.06);
    border-radius: 12px;
    position: relative;
  }}
  .big-number {{
    font-family: 'Outfit', sans-serif;
    font-size: 76px;
    font-weight: 800;
    line-height: 1;
    background: linear-gradient(180deg, #ffffff 30%, #38bdf8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    filter: drop-shadow(0 4px 14px rgba(56, 189, 248, 0.35));
    letter-spacing: -2px;
  }}
  .info-content {{
    flex: 1;
  }}
  .rank-badge {{
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 4px 11px;
    border-radius: 4px;
    background: rgba(56, 189, 248, 0.08);
    border: 1px solid rgba(56, 189, 248, 0.25);
    color: #38bdf8;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10.5px;
    font-weight: 700;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    margin-bottom: 10px;
  }}
  .rank-badge svg {{ flex-shrink: 0; }}
  .rank-title {{
    font-family: 'Outfit', sans-serif;
    font-size: 26px;
    font-weight: 800;
    color: #f1f5f9;
    line-height: 1.2;
    letter-spacing: -0.4px;
    margin-bottom: 7px;
  }}
  .rank-sub {{
    font-size: 13.5px;
    color: #94a3b8;
    line-height: 1.45;
  }}
</style>
</head>
<body>
  <div class="ranking-card">
    <div class="number-box">
      <div class="big-number">{num_clean}</div>
    </div>
    <div class="info-content">
      <div class="rank-badge">
        <svg width="10" height="10" viewBox="0 0 10 10" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="5" cy="5" r="3" fill="#38bdf8"/><circle cx="5" cy="5" r="4.5" stroke="#38bdf8" stroke-opacity="0.5"/></svg>
        <span>{bdg_clean}</span>
      </div>
      <div class="rank-title">{tit_clean}</div>
      <div class="rank-sub">{sub_clean}</div>
    </div>
  </div>
</body>
</html>"""

    def render_ranking_number_to_image(
        self,
        number: str,
        title: str,
        out_png: Path,
        subtitle: str = "Análisis e Impacto Clave",
        badge: str = "TOP RANKING",
    ) -> Path:
        """Renderiza una tarjeta de hito de cuenta regresiva (Puesto / Número de Top)."""
        out_png = Path(out_png)
        out_png.parent.mkdir(parents=True, exist_ok=True)
        html_file = out_png.with_suffix(".html")
        html_content = self.generate_ranking_number_html(number, title, subtitle, badge)
        html_file.write_text(html_content, encoding="utf-8")
        file_uri = html_file.resolve().as_uri()

        args = [
            self.browser_bin,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--hide-scrollbars",
            "--default-background-color=00000000",
            f"--screenshot={out_png.resolve()}",
            "--window-size=1100,500",
            file_uri,
        ]
        subprocess.run(args, capture_output=True, check=True, timeout=15)
        self._crop_transparent(out_png)
        return out_png

    def generate_free_kinetic_text_html(
        self,
        main_title: str,
        number: str = "",
        tag: str = "",
        subtitle: str = "",
        highlight: str = "",
        accent_color: str = "#38bdf8",
    ) -> str:
        """
        Texto libre cinematográfico flotante (Kinetic Typography):
        - CERO cajas, CERO fondos, CERO tarjetas.
        - Tipografía de escala cinematográfica con sombreado multicapa para máxima legibilidad.
        - Soporta números gigantes de ranking (03), hitos numerados (1. 2. 3.), etiquetas tácticas y palabras clave con resplandor.
        """
        import re
        t_clean = main_title.replace("<", "&lt;").replace(">", "&gt;")
        n_clean = number.replace("<", "&lt;").replace(">", "&gt;") if number else ""
        tag_clean = tag.replace("<", "&lt;").replace(">", "&gt;") if tag else ""
        sub_clean = subtitle.replace("<", "&lt;").replace(">", "&gt;") if subtitle else ""

        if highlight and highlight.lower() in t_clean.lower():
            pat = re.compile(re.escape(highlight), re.IGNORECASE)
            t_formatted = pat.sub(f'<span class="hl">{highlight}</span>', t_clean)
        else:
            t_formatted = t_clean

        tag_markup = f'<div class="free-tag">● {tag_clean}</div>' if tag_clean else ""
        num_markup = f'<div class="free-num">{n_clean}</div>' if n_clean else ""
        sub_markup = f'<div class="free-sub">{sub_clean}</div>' if sub_clean else ""

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
    font-family: 'Plus Jakarta Sans', sans-serif;
  }}
  .free-wrap {{
    text-align: center;
    max-width: 1400px;
    padding: 30px;
  }}
  .free-tag {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 16px;
    font-weight: 800;
    letter-spacing: 4px;
    color: {accent_color};
    text-shadow: 0 0 20px {accent_color}, 0 2px 10px rgba(0,0,0,0.9);
    text-transform: uppercase;
    margin-bottom: 8px;
    display: inline-block;
  }}
  .free-num {{
    font-family: 'Outfit', sans-serif;
    font-size: 136px;
    font-weight: 900;
    line-height: 0.92;
    background: linear-gradient(180deg, #ffffff 10%, {accent_color} 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    filter: drop-shadow(0 15px 40px rgba(0,0,0,0.95)) drop-shadow(0 0 35px {accent_color}66);
    letter-spacing: -4px;
    margin-bottom: 8px;
  }}
  .free-title {{
    font-family: 'Outfit', sans-serif;
    font-size: 70px;
    font-weight: 800;
    line-height: 1.08;
    color: #ffffff;
    text-shadow: 0 8px 45px rgba(0,0,0,0.95), 0 3px 12px rgba(0,0,0,0.85);
    letter-spacing: -1.2px;
    text-transform: uppercase;
  }}
  .hl {{
    color: {accent_color};
    text-shadow: 0 0 35px {accent_color}, 0 4px 30px rgba(0,0,0,0.9);
  }}
  .free-sub {{
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 24px;
    font-weight: 700;
    color: #ffffff;
    text-shadow: 0 4px 20px rgba(0, 0, 0, 0.95), 0 2px 8px rgba(0, 0, 0, 0.9);
    margin-top: 14px;
    letter-spacing: 0.4px;
  }}
</style>
</head>
<body>
  <div class="free-wrap">
    {tag_markup}
    {num_markup}
    <div class="free-title">{t_formatted}</div>
    {sub_markup}
  </div>
</body>
</html>"""

    def render_free_kinetic_text_to_image(
        self,
        main_title: str,
        out_png: Path,
        number: str = "",
        tag: str = "",
        subtitle: str = "",
        highlight: str = "",
        accent_color: str = "#38bdf8",
    ) -> Path:
        """Renderiza texto libre cinematográfico animable (sin card, 100% transparente)."""
        out_png = Path(out_png)
        out_png.parent.mkdir(parents=True, exist_ok=True)
        html_file = out_png.with_suffix(".html")
        html_content = self.generate_free_kinetic_text_html(
            main_title=main_title,
            number=number,
            tag=tag,
            subtitle=subtitle,
            highlight=highlight,
            accent_color=accent_color,
        )
        html_file.write_text(html_content, encoding="utf-8")
        file_uri = html_file.resolve().as_uri()

        args = [
            self.browser_bin,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--hide-scrollbars",
            "--default-background-color=00000000",
            f"--screenshot={out_png.resolve()}",
            "--window-size=1600,900",
            file_uri,
        ]
        subprocess.run(args, capture_output=True, check=True, timeout=15)
        self._crop_transparent(out_png)
        return out_png

    def generate_document_citation_html(
        self,
        source_name: str,
        title: str,
        excerpt: str,
        highlighted_phrase: str = "",
        date_str: str = "REGISTRO OFICIAL",
        badge: str = "EVIDENCIA DOCUMENTAL",
    ) -> str:
        """Efecto de recorte de documento oficial / noticia con resaltador fluorescente estilo Vox / Johnny Harris."""
        import re
        s_clean = source_name.replace("<", "&lt;").replace(">", "&gt;")
        t_clean = title.replace("<", "&lt;").replace(">", "&gt;")
        e_clean = excerpt.replace("<", "&lt;").replace(">", "&gt;")
        d_clean = date_str.replace("<", "&lt;").replace(">", "&gt;")
        b_clean = badge.replace("<", "&lt;").replace(">", "&gt;")

        if highlighted_phrase and highlighted_phrase.lower() in e_clean.lower():
            pat = re.compile(re.escape(highlighted_phrase), re.IGNORECASE)
            e_formatted = pat.sub(f'<mark class="highlighter">{highlighted_phrase}</mark>', e_clean)
        else:
            e_formatted = e_clean

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
    font-family: 'Plus Jakarta Sans', sans-serif;
  }}
  .doc-card {{
    width: 760px;
    background: linear-gradient(145deg, rgba(9, 10, 13, 0.97) 0%, rgba(4, 5, 7, 0.99) 100%);
    border: 1px solid rgba(255, 255, 255, 0.10);
    box-shadow: 0 32px 80px rgba(0, 0, 0, 0.95), 0 0 45px rgba(12, 24, 48, 0.40), inset 0 1px 0 rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 34px 40px;
    color: #f1f5f9;
    position: relative;
    overflow: hidden;
  }}
  /* Comilla tipográfica de lujo en marca de agua */
  .doc-card::after {{
    content: '“';
    position: absolute;
    bottom: -35px;
    right: 25px;
    font-family: 'Outfit', serif;
    font-size: 160px;
    font-weight: 900;
    line-height: 1;
    color: rgba(255, 255, 255, 0.035);
    pointer-events: none;
  }}
  .doc-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 16px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    margin-bottom: 22px;
  }}
  .source-tag {{
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    font-weight: 600;
    color: #94a3b8;
    letter-spacing: 2px;
    text-transform: uppercase;
  }}
  .source-dot {{
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #38bdf8;
    box-shadow: 0 0 8px #38bdf8;
  }}
  .date-tag {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: #64748b;
    letter-spacing: 1px;
    text-transform: uppercase;
  }}
  .doc-title {{
    font-family: 'Outfit', sans-serif;
    font-size: 26px;
    font-weight: 700;
    line-height: 1.25;
    color: #ffffff;
    letter-spacing: -0.4px;
    margin-bottom: 20px;
  }}
  .doc-quote-wrap {{
    position: relative;
    padding-left: 20px;
    border-left: 2px solid rgba(255, 255, 255, 0.16);
  }}
  .doc-body {{
    font-size: 18px;
    line-height: 1.68;
    color: #cbd5e1;
    font-weight: 400;
  }}
  /* Resaltador sutil estilo papelería editorial de lujo */
  .highlighter {{
    background: linear-gradient(180deg, transparent 40%, rgba(234, 179, 8, 0.28) 40%, rgba(234, 179, 8, 0.32) 92%, transparent 92%);
    color: #ffffff;
    font-weight: 600;
    padding: 0 4px;
    border-radius: 2px;
    border-bottom: 1.5px solid rgba(250, 204, 21, 0.65);
  }}
  .doc-footer {{
    margin-top: 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 12px;
    color: #64748b;
    font-family: 'JetBrains Mono', monospace;
  }}
</style>
</head>
<body>
  <div class="doc-card">
    <div class="doc-header">
      <div class="source-tag">
        <span class="source-dot"></span>
        <span>{s_clean}</span>
      </div>
      <div class="date-tag">{d_clean}</div>
    </div>
    <div class="doc-title">{t_clean}</div>
    <div class="doc-quote-wrap">
      <div class="doc-body">“{e_formatted}”</div>
    </div>
    <div class="doc-footer">
      <span>● DOCUMENTO DE ARCHIVO VERIFICADO</span>
      <span>{b_clean}</span>
    </div>
  </div>
</body>
</html>"""

    def render_document_citation_to_image(
        self,
        source_name: str,
        title: str,
        excerpt: str,
        out_png: Path,
        highlighted_phrase: str = "",
        date_str: str = "REGISTRO OFICIAL",
        badge: str = "EVIDENCIA DOCUMENTAL",
    ) -> Path:
        """Renderiza una cita documental oficial con texto resaltado fluorescente."""
        out_png = Path(out_png)
        out_png.parent.mkdir(parents=True, exist_ok=True)
        html_file = out_png.with_suffix(".html")
        html_content = self.generate_document_citation_html(
            source_name=source_name,
            title=title,
            excerpt=excerpt,
            highlighted_phrase=highlighted_phrase,
            date_str=date_str,
            badge=badge,
        )
        html_file.write_text(html_content, encoding="utf-8")
        file_uri = html_file.resolve().as_uri()

        args = [
            self.browser_bin,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--hide-scrollbars",
            "--default-background-color=00000000",
            f"--screenshot={out_png.resolve()}",
            "--window-size=1200,600",
            file_uri,
        ]
        subprocess.run(args, capture_output=True, check=True, timeout=15)
        self._crop_transparent(out_png)
        return out_png

    def generate_split_versus_html(
        self,
        left_name: str,
        left_stat: str,
        right_name: str,
        right_stat: str,
        left_sub: str = "",
        right_sub: str = "",
        badge: str = "COMPARATIVA DIRECTA",
    ) -> str:
        """Diseño cinemático Versus / Comparativa doble con divisor láser de neón."""
        l_n = left_name.replace("<", "&lt;").replace(">", "&gt;")
        l_s = left_stat.replace("<", "&lt;").replace(">", "&gt;")
        r_n = right_name.replace("<", "&lt;").replace(">", "&gt;")
        r_s = right_stat.replace("<", "&lt;").replace(">", "&gt;")
        l_sb = left_sub.replace("<", "&lt;").replace(">", "&gt;")
        r_sb = right_sub.replace("<", "&lt;").replace(">", "&gt;")
        b_c = badge.replace("<", "&lt;").replace(">", "&gt;")

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
    font-family: 'Plus Jakarta Sans', sans-serif;
  }}
  .vs-wrap {{
    width: 780px;
    background: linear-gradient(145deg, rgba(9, 10, 13, 0.98) 0%, rgba(4, 5, 7, 0.99) 100%);
    border: 1px solid rgba(255, 255, 255, 0.10);
    box-shadow: 0 32px 80px rgba(0, 0, 0, 0.95), 0 0 45px rgba(12, 24, 48, 0.40), inset 0 1px 0 rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 28px 36px;
    color: #ffffff;
    position: relative;
    overflow: hidden;
  }}
  .vs-badge {{
    text-align: center;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 2px;
    color: #38bdf8;
    margin-bottom: 20px;
    text-transform: uppercase;
  }}
  .vs-columns {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: relative;
  }}
  .vs-divider {{
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 0 16px;
  }}
  .divider-line {{
    width: 1px;
    height: 40px;
    background: rgba(255, 255, 255, 0.2);
  }}
  .vs-pill {{
    background: linear-gradient(135deg, #ef4444, #f59e0b);
    color: #ffffff;
    font-family: 'Outfit', sans-serif;
    font-weight: 900;
    font-size: 14px;
    padding: 6px 12px;
    border-radius: 999px;
    box-shadow: 0 0 20px rgba(239, 68, 68, 0.6);
    letter-spacing: 1px;
  }}
  .col-side {{
    flex: 1;
    text-align: center;
  }}
  .col-name {{
    font-family: 'Outfit', sans-serif;
    font-size: 22px;
    font-weight: 800;
    color: #ffffff;
    margin-bottom: 8px;
    text-transform: uppercase;
  }}
  .col-stat-left {{
    font-family: 'Outfit', sans-serif;
    font-size: 52px;
    font-weight: 900;
    line-height: 1;
    color: #38bdf8;
    filter: drop-shadow(0 0 20px rgba(56, 189, 248, 0.5));
    margin-bottom: 8px;
  }}
  .col-stat-right {{
    font-family: 'Outfit', sans-serif;
    font-size: 52px;
    font-weight: 900;
    line-height: 1;
    color: #f59e0b;
    filter: drop-shadow(0 0 20px rgba(245, 158, 11, 0.5));
    margin-bottom: 8px;
  }}
  .col-sub {{
    font-size: 13px;
    color: #94a3b8;
    line-height: 1.4;
  }}
</style>
</head>
<body>
  <div class="vs-wrap">
    <div class="vs-badge">● {b_c}</div>
    <div class="vs-columns">
      <div class="col-side">
        <div class="col-name">{l_n}</div>
        <div class="col-stat-left">{l_s}</div>
        <div class="col-sub">{l_sb}</div>
      </div>
      <div class="vs-divider">
        <div class="divider-line"></div>
        <div class="vs-pill">VS</div>
        <div class="divider-line"></div>
      </div>
      <div class="col-side">
        <div class="col-name">{r_n}</div>
        <div class="col-stat-right">{r_s}</div>
        <div class="col-sub">{r_sb}</div>
      </div>
    </div>
  </div>
</body>
</html>"""

    def render_split_versus_to_image(
        self,
        left_name: str,
        left_stat: str,
        right_name: str,
        right_stat: str,
        out_png: Path,
        left_sub: str = "",
        right_sub: str = "",
        badge: str = "COMPARATIVA DIRECTA",
    ) -> Path:
        """Renderiza una tarjeta Versus / Comparativa doble de dos entidades."""
        out_png = Path(out_png)
        out_png.parent.mkdir(parents=True, exist_ok=True)
        html_file = out_png.with_suffix(".html")
        html_content = self.generate_split_versus_html(
            left_name=left_name,
            left_stat=left_stat,
            right_name=right_name,
            right_stat=right_stat,
            left_sub=left_sub,
            right_sub=right_sub,
            badge=badge,
        )
        html_file.write_text(html_content, encoding="utf-8")
        file_uri = html_file.resolve().as_uri()

        args = [
            self.browser_bin,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--hide-scrollbars",
            "--default-background-color=00000000",
            f"--screenshot={out_png.resolve()}",
            "--window-size=1200,500",
            file_uri,
        ]
        subprocess.run(args, capture_output=True, check=True, timeout=15)
        self._crop_transparent(out_png)
        return out_png

    def generate_chapter_tracker_html(
        self,
        chapters: list,
        current_index: int = 0,
    ) -> str:
        """Barra superior discreta de seguimiento de capítulos / temas (Chapter Progress Tracker)."""
        svg_check = '<svg width="12" height="10" viewBox="0 0 12 10" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M1 5L4.2 8.5L11 1.5" stroke="#38bdf8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
        pills_html = []
        for idx, ch in enumerate(chapters):
            ch_clean = str(ch).replace("<", "&lt;").replace(">", "&gt;")
            if idx == current_index:
                pills_html.append(f'<div class="ch-pill active"><span class="pulse-dot"></span><span>{ch_clean}</span></div>')
            elif idx < current_index:
                pills_html.append(f'<div class="ch-pill past"><span class="check-icon">{svg_check}</span><span>{ch_clean}</span></div>')
            else:
                pills_html.append(f'<div class="ch-pill future"><span>{ch_clean}</span></div>')

        joined = '<div class="divider-line"></div>'.join(pills_html)

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
    font-family: 'Plus Jakarta Sans', sans-serif;
  }}
  .tracker-bar {{
    display: inline-flex;
    align-items: center;
    gap: 16px;
    background: linear-gradient(145deg, rgba(9, 10, 13, 0.96) 0%, rgba(4, 5, 7, 0.98) 100%);
    border: 1px solid rgba(255, 255, 255, 0.10);
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.9), inset 0 1px 0 rgba(255, 255, 255, 0.08);
    border-radius: 999px;
    padding: 9px 26px;
    color: #ffffff;
  }}
  .ch-pill {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 14.5px;
    font-weight: 600;
    letter-spacing: 0.3px;
    white-space: nowrap;
  }}
  .ch-pill.active {{
    color: #38bdf8;
    font-weight: 800;
    font-size: 15px;
    text-shadow: 0 0 14px rgba(56, 189, 248, 0.5);
  }}
  .ch-pill.past {{
    color: #cbd5e1;
    font-weight: 500;
  }}
  .check-icon {{
    display: inline-flex;
    align-items: center;
  }}
  .ch-pill.future {{
    color: #64748b;
    font-weight: 500;
  }}
  .pulse-dot {{
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #38bdf8;
    box-shadow: 0 0 10px #38bdf8;
  }}
  .divider-line {{
    width: 14px;
    height: 1px;
    background: rgba(255, 255, 255, 0.15);
  }}
</style>
</head>
<body>
  <div class="tracker-bar">
    {joined}
  </div>
</body>
</html>"""

    def render_chapter_tracker_to_image(
        self,
        chapters: list,
        current_index: int,
        out_png: Path,
    ) -> Path:
        """Renderiza una barra de seguimiento de capítulos translúcida superior."""
        out_png = Path(out_png)
        out_png.parent.mkdir(parents=True, exist_ok=True)
        html_file = out_png.with_suffix(".html")
        html_content = self.generate_chapter_tracker_html(chapters, current_index)
        html_file.write_text(html_content, encoding="utf-8")
        file_uri = html_file.resolve().as_uri()

        args = [
            self.browser_bin,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--hide-scrollbars",
            "--default-background-color=00000000",
            f"--screenshot={out_png.resolve()}",
            "--window-size=1600,200",
            file_uri,
        ]
        subprocess.run(args, capture_output=True, check=True, timeout=15)
        self._crop_transparent(out_png)
        return out_png

    def generate_geointel_map_html(
        self,
        location_title: str,
        country_name: str,
        sat_b64: str = "",
        target_x: int = 560,
        target_y: int = 280,
        coordinates_str: str = "39.702° N, 44.299° E",
        notes: str = "Análisis topográfico y geológico en tiempo real.",
        badge: str = "SAT RECON // ORBITAL FEED",
        accent_color: str = "#38bdf8",
        lat: float = 39.702,
        lon: float = 44.299,
        zoom: float = 7.2,
        pitch: float = 38.0,
        bearing: float = -14.0,
        maplibre_js_uri: str = "",
        maplibre_css_uri: str = "",
    ) -> str:
        """Mapa satelital hiperrealista con MapLibre GL JS (WebGL 3D orbital) y HUD de telemetría estilo Bloomberg/Reuters."""
        loc_clean = location_title.replace("<", "&lt;").replace(">", "&gt;")
        c_clean = country_name.replace("<", "&lt;").replace(">", "&gt;")
        coord_clean = coordinates_str.replace("<", "&lt;").replace(">", "&gt;")
        n_clean = notes.replace("<", "&lt;").replace(">", "&gt;")
        b_clean = badge.replace("<", "&lt;").replace(">", "&gt;")

        js_src = maplibre_js_uri or "https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.js"
        css_src = maplibre_css_uri or "https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css"

        # SVG icon defs — profesionales y sin emojis
        svg_pin = '<svg width="11" height="13" viewBox="0 0 12 14" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M6 0C3.24 0 1 2.24 1 5c0 3.75 5 9 5 9s5-5.25 5-9c0-2.76-2.24-5-5-5Zm0 6.75A1.75 1.75 0 1 1 6 3.25a1.75 1.75 0 0 1 0 3.5Z" fill="currentColor"/></svg>'
        svg_target = '<svg width="10" height="10" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="6" cy="6" r="5" stroke="currentColor" stroke-width="1.5"/><circle cx="6" cy="6" r="2" fill="currentColor"/></svg>'

        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
{HTML_FONTS}
<link rel="stylesheet" href="{css_src}" />
<script src="{js_src}"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: transparent;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
  }}
  .map-card {{
    width: 960px;
    height: 540px;
    position: relative;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid rgba(255,255,255,0.16);
    box-shadow: 0 36px 90px rgba(0,0,0,0.92);
    background: #06090e;
    font-family: 'Plus Jakarta Sans', sans-serif;
  }}
  #map {{
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
  }}
  /* Subtle vignette around map edges for depth without obscuring center */
  .vignette-overlay {{
    position: absolute;
    inset: 0;
    box-shadow: inset 0 0 90px rgba(0, 0, 0, 0.65);
    pointer-events: none;
    z-index: 2;
  }}
  /* Subtle cartographic grid markers */
  .grid-overlay {{
    position: absolute;
    inset: 0;
    background-image: 
      radial-gradient(rgba(255, 255, 255, 0.15) 1px, transparent 1px);
    background-size: 80px 80px;
    pointer-events: none;
    z-index: 3;
    opacity: 0.4;
  }}
  /* Top-left North compass */
  .north-badge {{
    position: absolute;
    top: 20px; left: 24px;
    display: flex;
    align-items: center;
    gap: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 700;
    color: #e2e8f0;
    background: rgba(10, 16, 26, 0.78);
    border: 1px solid rgba(255, 255, 255, 0.12);
    padding: 6px 10px;
    border-radius: 4px;
    backdrop-filter: blur(10px);
    z-index: 10;
    letter-spacing: 1px;
  }}
  /* Top-right telemetry live pill */
  .top-pill {{
    position: absolute;
    top: 20px; right: 24px;
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10.5px;
    font-weight: 700;
    color: #f1f5f9;
    background: rgba(10, 16, 26, 0.78);
    border: 1px solid rgba(255, 255, 255, 0.12);
    padding: 6px 12px;
    border-radius: 4px;
    backdrop-filter: blur(10px);
    z-index: 10;
    letter-spacing: 1.2px;
    text-transform: uppercase;
  }}
  .live-dot {{
    width: 6px; height: 6px;
    border-radius: 50%;
    background: #10b981;
    box-shadow: 0 0 8px #10b981;
  }}
  .pill-sep {{ color: rgba(255, 255, 255, 0.25); }}
  .pill-dim {{ color: {accent_color}; font-weight: 600; }}

  /* Floating Editorial Chyron (bottom-left) */
  .chyron-card {{
    position: absolute;
    bottom: 24px; left: 24px;
    width: 370px;
    background: rgba(8, 14, 24, 0.86);
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-left: 3.5px solid {accent_color};
    border-radius: 6px;
    padding: 18px 20px;
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.85);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    z-index: 10;
  }}
  .chyron-tag {{
    display: flex;
    align-items: center;
    gap: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.8px;
    color: {accent_color};
    text-transform: uppercase;
    margin-bottom: 8px;
  }}
  .chyron-title {{
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 20px;
    font-weight: 700;
    color: #f8fafc;
    line-height: 1.25;
    margin-bottom: 8px;
    letter-spacing: -0.2px;
  }}
  .chyron-desc {{
    font-size: 12px;
    color: #94a3b8;
    line-height: 1.5;
    margin-bottom: 14px;
  }}
  .telemetry-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    padding-top: 10px;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    font-family: 'JetBrains Mono', monospace;
  }}
  .tele-item {{
    display: flex;
    flex-direction: column;
    gap: 2px;
  }}
  .tele-label {{
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1.2px;
    color: rgba(255, 255, 255, 0.38);
    text-transform: uppercase;
  }}
  .tele-val {{
    font-size: 10.5px;
    font-weight: 600;
    color: #e2e8f0;
    letter-spacing: 0.3px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}

  /* Cartographic scale bar (bottom-right) */
  .scale-bar {{
    position: absolute;
    bottom: 24px; right: 24px;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 4px;
    z-index: 10;
    font-family: 'JetBrains Mono', monospace;
    font-size: 9.5px;
    color: rgba(255,255,255,0.7);
    letter-spacing: 1.2px;
    background: rgba(10, 16, 26, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.1);
    padding: 6px 10px;
    border-radius: 4px;
    backdrop-filter: blur(8px);
  }}
  .scale-ticks {{
    width: 60px;
    height: 3px;
    border-left: 1.5px solid {accent_color};
    border-right: 1.5px solid {accent_color};
    border-bottom: 1.5px solid {accent_color};
  }}

  /* Minimal precision corner brackets */
  .corner {{
    position: absolute;
    width: 14px; height: 14px;
    border-color: rgba(255, 255, 255, 0.25);
    border-style: solid;
    z-index: 12;
  }}
  .corner-tl {{ top: 10px; left: 10px; border-width: 1.5px 0 0 1.5px; }}
  .corner-tr {{ top: 10px; right: 10px; border-width: 1.5px 1.5px 0 0; }}
  .corner-bl {{ bottom: 10px; left: 10px; border-width: 0 0 1.5px 1.5px; }}
  .corner-br {{ bottom: 10px; right: 10px; border-width: 0 1.5px 1.5px 0; }}

  /* Documentary Cartographic Reticle Marker with Johnny Harris / Vox Leader Line */
  .reticle-container {{
    position: relative;
    width: 32px;
    height: 32px;
    pointer-events: none;
  }}
  .reticle-ring {{
    position: absolute;
    top: 0; left: 0;
    width: 32px; height: 32px;
    border-radius: 50%;
    border: 1.5px solid {accent_color};
    background: rgba(56, 189, 248, 0.12);
    box-shadow: 0 0 16px rgba(56, 189, 248, 0.35);
  }}
  .reticle-core {{
    position: absolute;
    top: 13px; left: 13px;
    width: 6px; height: 6px;
    border-radius: 50%;
    background: #ffffff;
    box-shadow: 0 0 6px #ffffff, 0 0 10px {accent_color};
  }}
  .reticle-tick-top {{
    position: absolute;
    top: -6px; left: 15px;
    width: 2px; height: 6px;
    background: {accent_color};
  }}
  .reticle-tick-bottom {{
    position: absolute;
    bottom: -6px; left: 15px;
    width: 2px; height: 6px;
    background: {accent_color};
  }}
  .reticle-tick-left {{
    position: absolute;
    top: 15px; left: -6px;
    width: 6px; height: 2px;
    background: {accent_color};
  }}
  .reticle-tick-right {{
    position: absolute;
    top: 15px; right: -6px;
    width: 6px; height: 2px;
    background: {accent_color};
  }}
  /* 45-degree Leader line callout */
  .leader-svg {{
    position: absolute;
    top: -36px;
    left: 20px;
    width: 140px;
    height: 48px;
    overflow: visible;
  }}
  .leader-badge {{
    position: absolute;
    top: -46px;
    left: 76px;
    display: flex;
    align-items: center;
    gap: 5px;
    background: rgba(10, 16, 26, 0.88);
    border: 1px solid rgba(255, 255, 255, 0.16);
    border-radius: 3px;
    padding: 3px 8px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 9.5px;
    font-weight: 700;
    letter-spacing: 0.8px;
    color: #f1f5f9;
    white-space: nowrap;
    backdrop-filter: blur(8px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.6);
  }}
</style>
</head>
<body>
  <div class="map-card">
    <div id="map"></div>
    <div class="vignette-overlay"></div>
    <div class="grid-overlay"></div>

    <div class="corner corner-tl"></div>
    <div class="corner corner-tr"></div>
    <div class="corner corner-bl"></div>
    <div class="corner corner-br"></div>

    <div class="north-badge">
      <svg width="9" height="13" viewBox="0 0 10 14" fill="none">
        <path d="M5 0L10 14L5 10L0 14L5 0Z" fill="{accent_color}"/>
      </svg>
      <span>N</span>
    </div>

    <div class="top-pill">
      <div class="live-dot"></div>
      <span>{b_clean}</span>
      <span class="pill-sep">|</span>
      <span class="pill-dim">WGS-84</span>
    </div>

    <div class="chyron-card">
      <div class="chyron-tag">
        {svg_pin}
        <span>{c_clean}</span>
      </div>
      <div class="chyron-title">{loc_clean}</div>
      <div class="chyron-desc">{n_clean}</div>
      <div class="telemetry-grid">
        <div class="tele-item">
          <span class="tele-label">COORDENADAS</span>
          <span class="tele-val">{coord_clean}</span>
        </div>
        <div class="tele-item">
          <span class="tele-label">SENSOR ÓPTICO</span>
          <span class="tele-val">ESRI ORBITAL 0.5M</span>
        </div>
      </div>
    </div>

    <div class="scale-bar">
      <div class="scale-ticks"></div>
      <span>50 KM</span>
    </div>
  </div>

  <script>
    const map = new maplibregl.Map({{
      container: 'map',
      style: {{
        version: 8,
        sources: {{
          'esri-satellite': {{
            'type': 'raster',
            'tiles': ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}'],
            'tileSize': 256
          }}
        }},
        layers: [{{
          id: 'satellite-layer',
          type: 'raster',
          source: 'esri-satellite'
        }}]
      }},
      center: [{lon}, {lat}],
      zoom: {zoom},
      pitch: {pitch},
      bearing: {bearing},
      interactive: false,
      attributionControl: false
    }});

    const el = document.createElement('div');
    el.className = 'reticle-container';
    el.innerHTML = `
      <div class="reticle-ring"></div>
      <div class="reticle-core"></div>
      <div class="reticle-tick-top"></div>
      <div class="reticle-tick-bottom"></div>
      <div class="reticle-tick-left"></div>
      <div class="reticle-tick-right"></div>
      <svg class="leader-svg" viewBox="0 0 140 48" fill="none">
        <polyline points="0,40 36,4 120,4" stroke="{accent_color}" stroke-width="1.2" stroke-dasharray="2 2"/>
        <circle cx="0" cy="40" r="2" fill="{accent_color}"/>
      </svg>
      <div class="leader-badge">
        {svg_target}
        <span>OBJETIVO</span>
      </div>
    `;

    new maplibregl.Marker({{ element: el, anchor: 'center' }})
      .setLngLat([{lon}, {lat}])
      .addTo(map);
  </script>
</body>
</html>"""

    def render_geointel_map_to_image(
        self,
        location_title: str,
        country_name: str,
        out_png: Path,
        coordinates_str: str = "",
        notes: str = "Análisis topográfico y teledetección en tiempo real.",
        badge: str = "SAT RECON // ORBITAL FEED",
        accent_color: str = "#38bdf8",
        **kwargs,
    ) -> Path:
        """Renderiza un mapa satelital hiperrealista con MapLibre GL JS (WebGL 3D orbital) y HUD de telemetría."""
        import urllib.request
        from pathlib import Path

        out_png = Path(out_png)
        out_png.parent.mkdir(parents=True, exist_ok=True)

        # Base de datos global ampliada de coordenadas y metadatos
        GEO_COORDS = {
            "turquía": (39.702, 44.299, 7.2, "39.702° N, 44.299° E", "MONTE ARARAT / MESETA DE ARMENIA"),
            "turquia": (39.702, 44.299, 7.2, "39.702° N, 44.299° E", "MONTE ARARAT / MESETA DE ARMENIA"),
            "ararat": (39.702, 44.299, 7.2, "39.702° N, 44.299° E", "MONTE ARARAT / FORMACIÓN DURUPINAR"),
            "colombia": (4.609, -74.081, 6.8, "4.609° N, 74.081° W", "BOGOTÁ D.C. / CORDILLERA ORIENTAL"),
            "bogotá": (4.609, -74.081, 7.2, "4.609° N, 74.081° W", "BOGOTÁ D.C. / SABANA DE BOGOTÁ"),
            "bogota": (4.609, -74.081, 7.2, "4.609° N, 74.081° W", "BOGOTÁ D.C. / SABANA DE BOGOTÁ"),
            "estados unidos": (38.907, -77.036, 6.8, "38.907° N, 77.036° W", "WASHINGTON D.C. / REGIÓN CAPITAL"),
            "ee.uu": (38.907, -77.036, 6.8, "38.907° N, 77.036° W", "WASHINGTON D.C. / REGIÓN CAPITAL"),
            "eeuu": (38.907, -77.036, 6.8, "38.907° N, 77.036° W", "WASHINGTON D.C. / REGIÓN CAPITAL"),
            "usa": (38.907, -77.036, 6.8, "38.907° N, 77.036° W", "WASHINGTON D.C. / REGIÓN CAPITAL"),
            "china": (39.904, 116.407, 6.8, "39.904° N, 116.407° E", "BEIJING / CUENCA DE HEBEI"),
            "rusia": (55.755, 37.617, 6.8, "55.755° N, 37.617° E", "MOSCÚ / LLANURA EUROPEA"),
            "ucrania": (50.450, 30.523, 6.8, "50.450° N, 30.523° E", "KIEV / CUENCA DEL DNIEPER"),
            "israel": (31.768, 35.213, 8.0, "31.768° N, 35.213° E", "JERUSALÉN / VALLE DEL JORDÁN"),
            "argentina": (-34.603, -58.381, 6.8, "34.603° S, 58.381° W", "BUENOS AIRES / REGIÓN PAMPEANA"),
            "españa": (40.416, -3.703, 6.8, "40.416° N, 3.703° W", "MADRID / MESETA CENTRAL"),
            "espana": (40.416, -3.703, 6.8, "40.416° N, 3.703° W", "MADRID / MESETA CENTRAL"),
            "méxico": (19.432, -99.133, 6.8, "19.432° N, 99.133° W", "VALLE DE MÉXICO"),
            "mexico": (19.432, -99.133, 6.8, "19.432° N, 99.133° W", "VALLE DE MÉXICO"),
            "chile": (-33.448, -70.669, 6.8, "33.448° S, 70.669° W", "SANTIAGO / VALLE CENTRAL"),
            "brasil": (-15.797, -47.864, 6.5, "15.797° S, 47.864° W", "BRASILIA / PLANALTO CENTRAL"),
            "egipto": (30.044, 31.235, 7.2, "30.044° N, 31.235° E", "EL CAIRO / DELTA DEL NILO"),
            "japón": (35.676, 139.650, 7.0, "35.676° N, 139.650° E", "TOKIO / LLANURA DE KANTO"),
            "japon": (35.676, 139.650, 7.0, "35.676° N, 139.650° E", "TOKIO / LLANURA DE KANTO"),
        }

        c_key = country_name.lower().strip()
        l_key = location_title.lower().strip()
        matched = GEO_COORDS.get(c_key) or GEO_COORDS.get(l_key)
        if not matched:
            for k, val in GEO_COORDS.items():
                if k in c_key or k in l_key:
                    matched = val
                    break
        if not matched:
            matched = (39.702, 44.299, 7.2, "39.702° N, 44.299° E", "ZONA DE INVESTIGACIÓN")

        lat, lon, zoom, default_coords, default_reg = matched
        coords_display = (
            coordinates_str
            if coordinates_str and len(coordinates_str) > 5 and "COORDENADAS" not in coordinates_str
            else default_coords
        )

        # Cache local de MapLibre GL JS para carga instantánea
        cache_dir = Path("storage/cache/maplibre").resolve()
        cache_dir.mkdir(parents=True, exist_ok=True)
        js_path = cache_dir / "maplibre-gl.js"
        css_path = cache_dir / "maplibre-gl.css"

        if not js_path.exists():
            try:
                urllib.request.urlretrieve("https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.js", js_path)
            except Exception:
                pass

        if not css_path.exists():
            try:
                urllib.request.urlretrieve("https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css", css_path)
            except Exception:
                pass

        js_uri = js_path.as_uri() if js_path.exists() else ""
        css_uri = css_path.as_uri() if css_path.exists() else ""

        html_file = out_png.with_suffix(".html")
        html_content = self.generate_geointel_map_html(
            location_title=location_title,
            country_name=country_name if country_name and "ZONA" not in country_name else default_reg,
            coordinates_str=coords_display,
            notes=notes,
            badge=badge,
            accent_color=accent_color,
            lat=lat,
            lon=lon,
            zoom=zoom,
            pitch=38.0,
            bearing=-14.0,
            maplibre_js_uri=js_uri,
            maplibre_css_uri=css_uri,
        )
        html_file.write_text(html_content, encoding="utf-8")
        file_uri = html_file.resolve().as_uri()

        args = [
            self.browser_bin,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--hide-scrollbars",
            "--default-background-color=00000000",
            "--virtual-time-budget=6000",
            f"--screenshot={out_png.resolve()}",
            "--window-size=1200,750",
            file_uri,
        ]
        subprocess.run(args, capture_output=True, check=True, timeout=25)
        self._crop_transparent(out_png)
        return out_png

    @staticmethod
    def _crop_transparent(png_path: Path):
        try:
            from PIL import Image
            im = Image.open(png_path)
            bbox = im.getbbox()
            if bbox:
                pad = 12
                b = (max(0, bbox[0]-pad), max(0, bbox[1]-pad), min(im.width, bbox[2]+pad), min(im.height, bbox[3]+pad))
                im.crop(b).save(png_path)
        except Exception:
            pass
