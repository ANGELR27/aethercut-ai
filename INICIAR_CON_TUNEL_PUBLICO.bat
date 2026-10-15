@echo off
title AetherCut AI Studio (Con Enlace Publico)
chcp 65001 >nul
cd /d "%~dp0"

echo ====================================================================
echo    Iniciando AetherCut AI Studio con Enlace Publico Cloudflare...
echo ====================================================================
echo.

python run_studio.py --tunnel
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ⚠️ Hubo un detalle al iniciar el servidor.
    pause
)
