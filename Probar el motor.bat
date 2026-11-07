@echo off
chcp 65001 >nul
title Helios - pruebas del motor
cd /d "%~dp0bot"
call "%~dp0_python.bat"
if not defined PY ( pause & exit /b 1 )
%PY% pruebas.py
echo.
pause
