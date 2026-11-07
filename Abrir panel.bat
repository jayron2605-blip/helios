@echo off
title Helios - panel de mercado
cd /d "%~dp0"
echo ============================================
echo  HELIOS - panel de mercado con datos reales
echo  Se abre solo en el navegador.
echo  Para parar: cerrate esta ventana.
echo ============================================
py -3.12 servidor.py
echo.
echo El panel se cerro. Si ves un error arriba, avisame.
pause
