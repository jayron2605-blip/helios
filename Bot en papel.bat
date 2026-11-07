@echo off
chcp 65001 >nul
title Helios - bot en PAPEL
cd /d "%~dp0bot"
echo ============================================
echo  BOT EN PAPEL: decide y anota, no mueve plata.
echo  Revisa el mercado cada 15 minutos.
echo  Para parar: cerrate esta ventana.
echo ============================================
:loop
py -3.12 cerebro.py 24 --bajar
timeout /t 900 /nobreak >nul
goto loop
