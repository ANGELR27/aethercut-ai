import json
from pathlib import Path

notebook = {
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# 🎬 AetherCut AI - Cloud Studio (Google Colab)\n",
                "Edita y genera videos con Inteligencia Artificial **100% en la nube**, sin consumir la memoria RAM de tu computadora ni gastar batería.\n",
                "\n",
                "> **Instrucciones rápidas:**\n",
                "> 1. Haz clic en **Entorno de ejecución > Cambiar tipo de entorno de ejecución** y selecciona **GPU T4** (o CPU estándar gratis).\n",
                "> 2. Ejecuta los pasos 1, 2 y 3 abajo en orden.\n",
                "> 3. Haz clic en el enlace público HTTPS de Cloudflare generado en el paso 3 para abrir tu estudio."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {"cellView": "form"},
            "outputs": [],
            "source": [
                "# @title 🚀 1. Descargar proyecto e instalar dependencias (~1 min)\n",
                "import os\n",
                "import subprocess\n",
                "\n",
                "# Clonar o actualizar el repositorio\n",
                "if not os.path.exists('aethercut-ai'):\n",
                "    !git clone https://github.com/ANGELR27/aethercut-ai.git\n",
                "    %cd aethercut-ai\n",
                "else:\n",
                "    %cd aethercut-ai\n",
                "    !git pull origin master\n",
                "\n",
                "# Instalar dependencias requeridas y tunelizador Cloudflare\n",
                "!pip install -q --no-warn-conflicts -r requirements.txt pycloudflared\n",
                "print('✅ Dependencias instaladas y código listo.')\n"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {"cellView": "form"},
            "outputs": [],
            "source": [
                "# @title 🔑 2. Configurar Claves de API\n",
                "# @markdown Pega tus claves de IA (Gemini, NVIDIA, GLM y KIMI):\n",
                "GEMINI_API_KEY = '' # @param {type:'string'}\n",
                "NVIDIA_API_KEY = '' # @param {type:'string'}\n",
                "GLM_API_KEY = '' # @param {type:'string'}\n",
                "GLM_FLASH_API_KEY = '' # @param {type:'string'}\n",
                "KIMI_API_KEY = '' # @param {type:'string'}\n",
                "\n",
                "# Si dejaste vacío, intenta leer de Colab Secrets (ícono de llave en la barra izquierda)\n",
                "try:\n",
                "    from google.colab import userdata\n",
                "    if not GEMINI_API_KEY: GEMINI_API_KEY = userdata.get('GEMINI_API_KEY')\n",
                "    if not NVIDIA_API_KEY: NVIDIA_API_KEY = userdata.get('NVIDIA_API_KEY')\n",
                "    if not GLM_API_KEY: GLM_API_KEY = userdata.get('GLM_API_KEY')\n",
                "    if not GLM_FLASH_API_KEY: GLM_FLASH_API_KEY = userdata.get('GLM_FLASH_API_KEY')\n",
                "    if not KIMI_API_KEY: KIMI_API_KEY = userdata.get('KIMI_API_KEY')\n",
                "except Exception:\n",
                "    pass\n",
                "\n",
                "if not GEMINI_API_KEY:\n",
                "    print('⚠️ Recuerda ingresar al menos tu GEMINI_API_KEY en la casilla.')\n",
                "else:\n",
                "    env_lines = [\n",
                "        f'GEMINI_API_KEY={GEMINI_API_KEY}',\n",
                "        f'NVIDIA_API_KEY={NVIDIA_API_KEY or \"\"}',\n",
                "        f'GLM_API_KEY={GLM_API_KEY or \"\"}',\n",
                "        f'GLM_FLASH_API_KEY={GLM_FLASH_API_KEY or \"\"}',\n",
                "        f'KIMI_API_KEY={KIMI_API_KEY or \"\"}',\n",
                "        'GEMINI_MODEL=gemini-flash-lite-latest',\n",
                "    ]\n",
                "    with open('.env', 'w', encoding='utf-8') as f:\n",
                "        f.write('\\n'.join(env_lines) + '\\n')\n",
                "    print('✅ Archivo .env configurado con todas tus claves.')\n"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {"cellView": "form"},
            "outputs": [],
            "source": [
                "# @title 🌐 3. Iniciar AetherCut AI y Generar Enlace HTTPS\n",
                "# @markdown Ejecuta esta celda para iniciar el servidor y obtener tus enlaces de acceso.\n",
                "import subprocess\n",
                "import time\n",
                "import sys\n",
                "from pycloudflared import try_cloudflare\n",
                "\n",
                "# Limpiar cualquier proceso antiguo para evitar bloqueos de puertos\n",
                "subprocess.run(['pkill', '-9', '-f', 'uvicorn'], capture_output=True)\n",
                "subprocess.run(['pkill', '-9', '-f', 'cloudflared'], capture_output=True)\n",
                "subprocess.run(['git', 'pull', 'origin', 'master'], capture_output=True)\n",
                "time.sleep(1)\n",
                "\n",
                "print('Iniciando servidor de AetherCut AI en segundo plano...')\n",
                "server_process = subprocess.Popen(\n",
                "    ['uvicorn', 'server:app', '--host', '0.0.0.0', '--port', '8000'],\n",
                "    stdout=subprocess.PIPE,\n",
                "    stderr=subprocess.STDOUT,\n",
                "    text=True\n",
                ")\n",
                "\n",
                "# Esperar a que el servidor inicialice\n",
                "time.sleep(4)\n",
                "\n",
                "# 1. Obtener enlace oficial directo de Google Colab (sin caídas ni problemas de DNS)\n",
                "colab_url = None\n",
                "try:\n",
                "    from google.colab.output import eval_js\n",
                "    colab_url = eval_js('google.colab.kernel.proxyPort(8000)')\n",
                "except Exception:\n",
                "    pass\n",
                "\n",
                "# 2. Obtener enlace público Cloudflare (para celular o compartir)\n",
                "cf_url = None\n",
                "try:\n",
                "    tunnel = try_cloudflare(port=8000)\n",
                "    cf_url = getattr(tunnel, 'tunnel', str(tunnel))\n",
                "except Exception:\n",
                "    pass\n",
                "\n",
                "print('\\n' + '='*65)\n",
                "print('🎉 ¡AETHERCUT AI ESTÁ ACTIVO EN LA NUBE!')\n",
                "if colab_url:\n",
                "    print('⭐ ENLACE DIRECTO (Google Oficial - Máxima velocidad):')\n",
                "    print(f'👉 {colab_url}\\n')\n",
                "if cf_url:\n",
                "    print('📱 ENLACE PÚBLICO (Cloudflare - Para celular o compartir):')\n",
                "    print(f'👉 {cf_url}')\n",
                "print('='*65 + '\\n')\n",
                "print('Tu laptop local consume 0% de memoria RAM.')\n",
                "\n",
                "# Mostrar logs del servidor\n",
                "try:\n",
                "    while True:\n",
                "        line = server_process.stdout.readline()\n",
                "        if line:\n",
                "            print(line.strip())\n",
                "        time.sleep(0.2)\n",
                "except KeyboardInterrupt:\n",
                "    server_process.terminate()\n",
                "    print('Servidor detenido.')\n"
            ]
        }
    ],
    "metadata": {
        "accelerator": "GPU",
        "colab": {
            "gpuType": "T4",
            "provenance": []
        },
        "language_info": {
            "name": "python"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 0
}

out_path = Path(__file__).resolve().parent.parent / "AetherCut_AI_Colab.ipynb"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=1, ensure_ascii=False)

print(f"Generado exitosamente en: {out_path}")
