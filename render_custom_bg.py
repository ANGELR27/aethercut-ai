import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import subprocess

out_dir = Path(r"C:\Users\angel\.gemini\antigravity-ide\brain\8227ece0-7eab-4ea0-b070-6f4914d1188a")
demo_dir = out_dir / "scratch" / "custom_bg_frames"
demo_dir.mkdir(parents=True, exist_ok=True)

fps = 20
total_frames = 50
W, H = 1920, 1080

# 1. GENERAR EL FONDO EXCLUSIVO (Negro Mate con sutiles sombras de blanco y azul oscuro profundo)
bg_base = Image.new("RGBA", (W, H), (8, 9, 13, 255)) # Negro mate puro espacial

# Sombra / Resplandor orgánico azul oscuro muy profundo en el tercio inferior izquierdo
glow_blue = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ImageDraw.Draw(glow_blue).ellipse(( -100, 350, 900, 1150 ), fill=(14, 28, 54, 85)) # Azul noche oscuro profundo
glow_blue = glow_blue.filter(ImageFilter.GaussianBlur(140))
bg_base.paste(glow_blue, (0, 0), glow_blue)

# Sombra / Resplandor difuso blanco muy sutil en el borde superior derecho para dar relieve de estudio
glow_white = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ImageDraw.Draw(glow_white).ellipse(( 1200, -150, 2050, 600 ), fill=(255, 255, 255, 12)) # 5% blanco difuso
glow_white = glow_white.filter(ImageFilter.GaussianBlur(160))
bg_base.paste(glow_white, (0, 0), glow_white)

# Guardar imagen del fondo oficial para referencia futura del motor
bg_official_path = Path(r"C:\Users\angel\.gemini\antigravity-ide\scratch\ai-video-editor\assets\aethercut_studio_matte_dark.jpg")
bg_base.convert("RGB").save(bg_official_path, "JPEG", quality=95)
print("FONDO OFICIAL GUARDADO EN ASSETS:", bg_official_path.exists())

# Fuentes
font_tag = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 13)
font_hero = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 44)
font_sub = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 18)
font_node_title = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 15)
font_node_sub = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 12)
font_stat_val = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 36)
font_hud_title = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 14)
font_hud_item = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 13)

nodes = [
    {"x": 250, "y": 380, "w": 180, "h": 64, "label": "PERCEPCION", "sub": "Estimulos sensoriales", "color": (56, 189, 248)},
    {"x": 250, "y": 520, "w": 180, "h": 64, "label": "MEMORIA", "sub": "Contexto historico", "color": (56, 189, 248)},
    {"x": 250, "y": 660, "w": 180, "h": 64, "label": "LOGICA FORMAL", "sub": "Hechos verificados", "color": (56, 189, 248)},
    {"x": 580, "y": 440, "w": 200, "h": 70, "label": "SINTESIS", "sub": "Interconexion neuronal", "color": (168, 85, 247)},
    {"x": 580, "y": 600, "w": 200, "h": 70, "label": "PODA DE SESGOS", "sub": "Auditoria de verdad", "color": (168, 85, 247)},
    {"x": 960, "y": 520, "w": 240, "h": 82, "label": "PENSAMIENTO", "sub": "Razonamiento Profundo", "color": (251, 191, 36)},
]

synapses = [(0, 3), (1, 3), (1, 4), (2, 4), (3, 5), (4, 5)]

def eval_cubic_bezier(p0, p1, p2, p3, t_val):
    inv = 1.0 - t_val
    return (inv**3 * p0 + 3 * inv**2 * t_val * p1 + 3 * inv * t_val**2 * p2 + t_val**3 * p3)

print("Generando frames con nuestro fondo negro mate oficial...")
for f in range(total_frames):
    t = f / fps
    im = bg_base.copy()
    d = ImageDraw.Draw(im)

    # 1. Grilla arquitectonica de puntos ultra sutil
    for gx in range(80, 1340, 80):
        for gy in range(80, 980, 80):
            d.ellipse((gx - 1, gy - 1, gx + 1, gy + 1), fill=(255, 255, 255, 14))

    # 2. Hero Typography
    hero_x, hero_y = 120, 110
    d.rounded_rectangle((hero_x, hero_y, hero_x + 200, hero_y + 28), radius=14, fill=(255, 255, 255, 12), outline=(56, 189, 248, 110), width=1)
    d.ellipse((hero_x + 10 - 3, hero_y + 14 - 3, hero_x + 10 + 3, hero_y + 14 + 3), fill=(56, 189, 248, 255))
    d.text((hero_x + 20, hero_y + 14), "SISTEMA DE INFERENCIA", font=font_tag, fill=(255, 255, 255, 230), anchor="lm")

    d.text((hero_x, hero_y + 44), "CONECTIVIDAD NEURONAL", font=font_hero, fill=(255, 255, 255, 255))
    off = d.textlength("CONECTIVIDAD NEURONAL ", font=font_hero)
    d.text((hero_x + off, hero_y + 44), "PRO", font=font_hero, fill=(251, 191, 36, 255))
    d.text((hero_x, hero_y + 105), "Las sinapsis convergen dinamicamente para producir razonamiento emergente.", font=font_sub, fill=(148, 163, 184, 220))

    # 3. Sinapsis Curvas de Bezier con pulsos
    for src_idx, dst_idx in synapses:
        n1 = nodes[src_idx]
        n2 = nodes[dst_idx]
        x1, y1 = n1["x"] + n1["w"] // 2, n1["y"]
        x2, y2 = n2["x"] - n2["w"] // 2, n2["y"]
        dx = (x2 - x1) * 0.55
        p0 = (x1, y1)
        p1 = (x1 + dx, y1)
        p2 = (x2 - dx, y2)
        p3 = (x2, y2)

        curve_pts = []
        for step in range(21):
            s_val = step / 20
            cx_val = eval_cubic_bezier(p0[0], p1[0], p2[0], p3[0], s_val)
            cy_val = eval_cubic_bezier(p0[1], p1[1], p2[1], p3[1], s_val)
            curve_pts.append((cx_val, cy_val))

        for pt_i in range(len(curve_pts) - 1):
            d.line([curve_pts[pt_i], curve_pts[pt_i + 1]], fill=(255, 255, 255, 30), width=2)

        pulse_val = (t * 1.5 + (src_idx * 0.22) + (dst_idx * 0.15)) % 1.0
        cur_px = eval_cubic_bezier(p0[0], p1[0], p2[0], p3[0], pulse_val)
        cur_py = eval_cubic_bezier(p0[1], p1[1], p2[1], p3[1], pulse_val)
        c_glow = n2["color"]
        d.ellipse((cur_px - 8, cur_py - 8, cur_px + 8, cur_py + 8), fill=(c_glow[0], c_glow[1], c_glow[2], 65))
        d.ellipse((cur_px - 4, cur_py - 4, cur_px + 4, cur_py + 4), fill=(255, 255, 255, 255))

    # 4. Nodos Glassmorphism Bento
    for idx, node in enumerate(nodes):
        nx, ny, nw, nh = node["x"], node["y"], node["w"], node["h"]
        col = node["color"]
        x_min, y_min = nx - nw // 2, ny - nh // 2
        x_max, y_max = nx + nw // 2, ny + nh // 2
        r_box = 16
        is_hero_node = (idx == 5)

        # Sombra
        d.rounded_rectangle((x_min, y_min + 6, x_max, y_max + 6), radius=r_box, fill=(0, 0, 0, 110))
        # Fondo cristal
        d.rounded_rectangle((x_min, y_min, x_max, y_max), radius=r_box, fill=(16, 21, 32, 225), outline=(col[0], col[1], col[2], 220 if is_hero_node else 95), width=2 if is_hero_node else 1)

        pip_r = 4 if not is_hero_node else 5
        d.ellipse((x_min + 20 - pip_r, ny - pip_r, x_min + 20 + pip_r, ny + pip_r), fill=col)
        tx = x_min + 34
        d.text((tx, ny - 9), node["label"], font=font_node_title, fill=(255, 255, 255, 255), anchor="lm")
        d.text((tx, ny + 11), node["sub"], font=font_node_sub, fill=(160, 175, 195, 220), anchor="lm")

    # 5. Panel Lateral HUD de Telemetria (x=1340 a 1800)
    hud_x, hud_y, hud_w, hud_h = 1340, 240, 460, 480
    hud_r = 22
    d.rounded_rectangle((hud_x, hud_y + 8, hud_x + hud_w, hud_y + hud_h + 8), radius=hud_r, fill=(0, 0, 0, 120))
    d.rounded_rectangle((hud_x, hud_y, hud_x + hud_w, hud_y + hud_h), radius=hud_r, fill=(14, 19, 28, 235), outline=(255, 255, 255, 55), width=1)

    d.text((hud_x + 32, hud_y + 40), "ESTUDIO COGNITIVO // TELEMETRIA", font=font_hud_title, fill=(251, 191, 36, 255))
    cur_coherence = 94.2 + 3.5 * math.sin(t * 4.0)
    d.text((hud_x + 32, hud_y + 75), f"{cur_coherence:.1f}%", font=font_stat_val, fill=(255, 255, 255, 255))
    d.text((hud_x + 32, hud_y + 125), "Indice de Razonamiento Coherente", font=font_sub, fill=(148, 163, 184, 220))

    bar_w = 380
    bar_active = int(bar_w * (cur_coherence / 100.0))
    d.rounded_rectangle((hud_x + 32, hud_y + 160, hud_x + 32 + bar_w, hud_y + 168), radius=4, fill=(25, 32, 45, 255))
    d.rounded_rectangle((hud_x + 32, hud_y + 160, hud_x + 32 + bar_active, hud_y + 168), radius=4, fill=(52, 211, 153, 255))

    items = [
        ("1. Entradas multi-fuente sincronizadas", (56, 189, 248)),
        ("2. Filtrado de sesgos cognitivos activo", (168, 85, 247)),
        ("3. Sintesis y deduccion de alto nivel", (251, 191, 36)),
        ("4. Pensamiento profundo completado", (52, 211, 153)),
    ]
    for i_idx, (item_txt, i_col) in enumerate(items):
        iy = hud_y + 205 + (i_idx * 40)
        d.ellipse((hud_x + 34 - 3, iy + 10 - 3, hud_x + 34 + 3, iy + 10 + 3), fill=i_col)
        d.text((hud_x + 48, iy + 10), item_txt, font=font_hud_item, fill=(215, 225, 240, 240), anchor="lm")

    d.text((hud_x + 32, hud_y + 420), "AetherCut Studio Architecture  -  Kernel 2026", font=font_node_sub, fill=(120, 135, 155, 200))

    im.convert("RGB").save(demo_dir / f"custom_{f:03d}.png")

print("Compilando GIF de alta calidad...")
out_gif_custom = out_dir / "signature_matte_dark_pro.gif"
cmd = [
    "ffmpeg", "-y",
    "-framerate", str(fps),
    "-i", str(demo_dir / "custom_%03d.png"),
    "-vf", "scale=1080:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer",
    str(out_gif_custom)
]
subprocess.run(cmd, check=True)
print("CUSTOM_BG_DONE:", out_gif_custom.exists(), out_gif_custom.stat().st_size)
