import os
import sys
import time
import socket
import webbrowser
import threading

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'

def open_browser_delayed(url, delay=2.0):
    def _open():
        time.sleep(delay)
        try:
            webbrowser.open(url)
        except Exception:
            pass
    t = threading.Thread(target=_open, daemon=True)
    t.start()

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)
    local_ip = get_local_ip()

    with_tunnel = "--tunnel" in sys.argv or os.environ.get("AETHERCUT_TUNNEL") == "1"
    cf_url = None

    if with_tunnel:
        print("\n⏳ Creando enlace público mundial con Cloudflare...")
        try:
            from pycloudflared import try_cloudflare
            tunnel = try_cloudflare(port=8000)
            cf_url = getattr(tunnel, 'tunnel', str(tunnel))
        except Exception as e:
            print(f"⚠️ No se pudo generar enlace Cloudflare: {e}")

    print("\n" + "=" * 68)
    print("      🎬  AETHERCUT AI - ESTUDIO NEURAL DE EDICIÓN DE VIDEO")
    print("=" * 68)
    print(f"💻 Acceso en tu PC:                  http://localhost:8000")
    print(f"📱 En tu Celular/Tablet (WiFi casa): http://{local_ip}:8000")
    if cf_url:
        print(f"🌍 Enlace Público (Móvil / 4G / 5G): {cf_url}")
    print("=" * 68)
    print("✅ Todas tus claves de API ya están cargadas desde tu archivo .env")
    print("✅ Todos tus proyectos y videos se guardan para siempre en tu disco")
    print("🚀 Abriendo tu navegador automáticamente...")
    print("=" * 68 + "\n")

    open_browser_delayed("http://localhost:8000")

    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)

if __name__ == "__main__":
    main()
