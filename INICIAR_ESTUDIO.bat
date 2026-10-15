@echo off
title AetherCut AI Studio
chcp 65001 >nul
cd /d "%~dp0"

echo ====================================================================
echo        Iniciando AetherCut AI Studio en tu computadora...
echo ====================================================================
echo.

python run_studio.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ⚠️ Hubo un detalle al iniciar el servidor.
    pause
)
