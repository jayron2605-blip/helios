@echo off
chcp 65001 >nul
title Helios - entrenar el modelo
cd /d "%~dp0bot"
call "%~dp0_python.bat"
if not defined PY ( pause & exit /b 1 )
echo ============================================
echo  ENTRENANDO el modelo con velas reales.
echo  Tarda unos minutos. No cierres esta ventana.
echo ============================================
%PY% datos.py
%PY% modelo.py 24 0.55
echo.
echo Listo. El puntaje queda en la carpeta bot\resultados
pause
