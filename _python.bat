@echo off
rem Busca un Python que sirva de verdad. No inventa una version: usa la que haya.
rem El "python" de WindowsApps suele ser un acceso roto a la Microsoft Store.
set "PY="
py -3.12 -c "import sys" >nul 2>&1
if not errorlevel 1 set "PY=py -3.12"
if defined PY goto :listo
if exist "%LOCALAPPDATA%\Programs\Python\Launcher\py.exe" (
  "%LOCALAPPDATA%\Programs\Python\Launcher\py.exe" -3.12 -c "import sys" >nul 2>&1
  if not errorlevel 1 set "PY=%LOCALAPPDATA%\Programs\Python\Launcher\py.exe -3.12"
)
if defined PY goto :listo
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
  if exist "%%~D\python.exe" (
    "%%~D\python.exe" -c "import sys" >nul 2>&1
    if not errorlevel 1 set "PY=%%~D\python.exe"
  )
)
if defined PY goto :listo
python -c "import sys" >nul 2>&1
if not errorlevel 1 set "PY=python"
if defined PY goto :listo
python3 -c "import sys" >nul 2>&1
if not errorlevel 1 set "PY=python3"
:listo
if not defined PY (
  echo No se encontro un Python que funcione en esta PC.
  echo Instala Python 3.12 o mas nuevo, o corre a mano: python servidor.py
)
