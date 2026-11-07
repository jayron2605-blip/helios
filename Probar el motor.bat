@echo off
chcp 65001 >nul
title Helios - pruebas del motor
cd /d "%~dp0bot"
py -3.12 pruebas.py
echo.
pause
