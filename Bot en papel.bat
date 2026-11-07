@echo off
chcp 65001 >nul
title Helios - bot en PAPEL
cd /d "%~dp0bot"
call "%~dp0_python.bat"
if not defined PY ( pause & exit /b 1 )
echo ============================================
echo  BOT EN PAPEL: decide y anota, no mueve plata.
echo  Revisa el mercado cada 15 minutos.
echo  Para parar: cerrate esta ventana.
echo ============================================
:loop
%PY% cerebro.py 24 --bajar
timeout /t 900 /nobreak >nul
goto loop
