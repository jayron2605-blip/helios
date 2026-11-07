@echo off
chcp 65001 >nul
title Helios - panel de mercado
cd /d "%~dp0"
call "%~dp0_python.bat"
if not defined PY ( pause & exit /b 1 )
echo ============================================
echo  HELIOS - panel de mercado con datos reales
echo  Se abre solo en el navegador.
echo  Para parar: cerrate esta ventana.
echo ============================================
%PY% servidor.py
echo.
echo El panel se cerro. Si ves un error arriba, avisame.
pause
