@echo off
chcp 65001 >nul
title Helios - panel en la WiFi local
cd /d "%~dp0"
call "%~dp0_python.bat"
if not defined PY ( pause & exit /b 1 )
set HELIOS_HOST=0.0.0.0
echo ============================================
echo  HELIOS - panel para la MISMA WiFi
echo  Escucha en todas las interfaces locales.
echo  NO abrir el puerto 8765 en el router.
echo  Para parar: cerrate esta ventana.
echo ============================================
%PY% servidor.py
echo.
echo El panel se cerro. Si ves un error arriba, avisame.
pause