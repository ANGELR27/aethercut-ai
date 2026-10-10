import base64
import subprocess
from pathlib import Path
from core.web_card_renderer import _get_browser_bin, HTML_FONTS

sat_file = Path("test_real_satellite_stitched.jpg")
if not sat_file.exists():
    print("Error: test_real_satellite_stitched.jpg not found")
    exit(1)

sat_bytes = sat_file.read_bytes()
b64_data = "data:image/jpeg;base64," + base64.b64encode(sat_bytes).decode("utf-8")

html_content = f"""<!DOCTYPE html>
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
  .map-card {{
    width: 960px;
    height: 540px;
    position: relative;
    border-radius: 20px;
    overflow: hidden;
    border: 1px solid rgba(255, 255, 255, 0.16);
    box-shadow: 0 35px 90px rgba(0, 0, 0, 0.95), 0 0 50px rgba(56, 189, 248, 0.18);
    background: #020617;
  }}
  .sat-photo {{
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    filter: brightness(0.85) contrast(1.22) saturate(1.15);
  }}
  .vignette {{
    position: absolute;
    inset: 0;
    background: radial-gradient(circle at 58% 46%, rgba(10, 15, 26, 0.08) 0%, rgba(2, 6, 23, 0.88) 100%);
    pointer-events: none;
  }}
  .hud-header {{
    position: absolute;
    top: 24px;
    left: 24px;
    right: 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    z-index: 10;
  }}
  .hud-badge {{
    background: rgba(10, 15, 26, 0.88);
    backdrop-filter: blur(16px);
    border: 1px solid rgba(56, 189, 248, 0.4);
    border-radius: 999px;
    padding: 7px 20px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11.5px;
    font-weight: 700;
    color: #38bdf8;
    letter-spacing: 1.5px;
    display: flex;
    align-items: center;
    gap: 8px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.6);
  }}
  .hud-badge::before {{
    content: '';
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #38bdf8;
    box-shadow: 0 0 12px #38bdf8;
  }}
  .hud-coords {{
    background: rgba(10, 15, 26, 0.88);
    backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 999px;
    padding: 7px 18px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: #cbd5e1;
    letter-spacing: 1.2px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.6);
  }}
  .hud-panel {{
    position: absolute;
    bottom: 24px;
    left: 24px;
    background: rgba(10, 15, 26, 0.90);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.16);
    border-radius: 14px;
    padding: 22px 26px;
    max-width: 440px;
    box-shadow: 0 24px 60px rgba(0, 0, 0, 0.85);
    z-index: 10;
  }}
  .loc-flag {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11.5px;
    font-weight: 700;
    color: #38bdf8;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-bottom: 6px;
  }}
  .loc-name {{
    font-family: 'Outfit', sans-serif;
    font-size: 26px;
    font-weight: 800;
    color: #ffffff;
    line-height: 1.2;
    margin-bottom: 8px;
    letter-spacing: -0.5px;
  }}
  .loc-desc {{
    font-size: 13.5px;
    color: #cbd5e1;
    line-height: 1.55;
  }}
  .target-wrap {{
    position: absolute;
    left: 550px;
    top: 275px;
    transform: translate(-50%, -50%);
    pointer-events: none;
    z-index: 8;
  }}
  .radar-ring-lg {{
    position: absolute;
    left: -40px; top: -40px;
    width: 80px; height: 80px;
    border-radius: 50%;
    border: 1.5px dashed rgba(56, 189, 248, 0.6);
    box-shadow: 0 0 25px rgba(56, 189, 248, 0.4);
  }}
  .radar-ring-md {{
    position: absolute;
    left: -22px; top: -22px;
    width: 44px; height: 44px;
    border-radius: 50%;
    border: 2px solid #38bdf8;
  }}
  .radar-dot {{
    position: absolute;
    left: -5px; top: -5px;
    width: 10px; height: 10px;
    border-radius: 50%;
    background: #38bdf8;
    box-shadow: 0 0 15px #38bdf8, 0 0 30px #38bdf8;
  }}
  .reticle-h {{
    position: absolute;
    left: -32px; top: 0;
    width: 64px; height: 2px;
    background: linear-gradient(90deg, transparent, #38bdf8 30%, #38bdf8 70%, transparent);
  }}
  .reticle-v {{
    position: absolute;
    left: 0; top: -32px;
    width: 2px; height: 64px;
    background: linear-gradient(180deg, transparent, #38bdf8 30%, #38bdf8 70%, transparent);
  }}
  .target-label {{
    position: absolute;
    left: 48px; top: -14px;
    background: rgba(10, 15, 26, 0.90);
    border: 1px solid #38bdf8;
    border-radius: 6px;
    padding: 5px 12px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 700;
    color: #ffffff;
    white-space: nowrap;
    box-shadow: 0 8px 20px rgba(0,0,0,0.7);
  }}
</style>
</head>
<body>
  <div class="map-card">
    <img class="sat-photo" src="{b64_data}" />
    <div class="vignette"></div>

    <div class="hud-header">
      <div class="hud-badge">🛰️ RECONOCIMIENTO SATELITAL // ESCANEO ÓRBITAL</div>
      <div class="hud-coords">39.702° N, 44.299° E</div>
    </div>

    <div class="target-wrap">
      <div class="radar-ring-lg"></div>
      <div class="radar-ring-md"></div>
      <div class="reticle-h"></div>
      <div class="reticle-v"></div>
      <div class="radar-dot"></div>
      <div class="target-label">🎯 MONTE ARARAT · 5,137m</div>
    </div>

    <div class="hud-panel">
      <div class="loc-flag">📍 TURQUÍA · REGIÓN ORIENTAL</div>
      <div class="loc-name">Formación Geológica Ararat</div>
      <div class="loc-desc">Estratovolcán de 5,137 metros y meseta circundante. Análisis de teledetección revela sedimentos marinos y actividad geológica del Holoceno.</div>
    </div>
  </div>
</body>
</html>"""

html_file = Path("test_real_sat_render.html")
html_file.write_text(html_content, encoding="utf-8")

out_png = Path("test_hyperrealistic_satellite_map.png")
browser = _get_browser_bin()
args = [
    browser,
    "--headless",
    "--disable-gpu",
    "--no-sandbox",
    "--hide-scrollbars",
    "--default-background-color=00000000",
    f"--screenshot={out_png.resolve()}",
    "--window-size=1200,750",
    html_file.resolve().as_uri(),
]
subprocess.run(args, capture_output=True, check=True, timeout=15)
print("HYPERREALISTIC MAP SUCCESS:", out_png.exists(), out_png.stat().st_size)
