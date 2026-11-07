@echo off
chcp 65001 >nul
title Helios - entrenar el modelo
cd /d "%~dp0bot"
echo ============================================
echo  ENTRENANDO el modelo con velas reales.
echo  Tarda unos minutos. No cierres esta ventana.
echo ============================================
py -3.12 datos.py
py -3.12 modelo.py 24 0.55
echo.
echo Listo. El puntaje queda en la carpeta bot\resultados
pause
