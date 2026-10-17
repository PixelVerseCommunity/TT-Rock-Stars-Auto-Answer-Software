@echo off
setlocal
cd /d "%~dp0"
set "PYLAUNCH="
where py >nul 2>nul
if not errorlevel 1 (
  py -3.12 --version >nul 2>nul
  if not errorlevel 1 set "PYLAUNCH=py -3.12"
)
if not defined PYLAUNCH (
  where python >nul 2>nul
  if not errorlevel 1 (
    python -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>nul
    if not errorlevel 1 set "PYLAUNCH=python"
  )
)
if not defined PYLAUNCH (
  echo This app's OCR library does not support Python 3.15 yet.
  echo Install Python 3.12 alongside your existing Python, then run this file again.
  echo Download Python 3.12 from https://www.python.org/downloads/ .
  pause
  exit /b 1
)
if not exist .venv312\Scripts\python.exe (
  %PYLAUNCH% -m venv .venv312
  if errorlevel 1 (
    echo Could not create the app's Python environment. See setup.log if present.
    pause
    exit /b 1
  )
)
.venv312\Scripts\python.exe -m pip install -r requirements.txt > setup.log 2>&1
if errorlevel 1 (
  echo Dependency installation failed. Details follow:
  type setup.log
  echo.
  echo If the log mentions a network or certificate error, check internet access and retry.
  echo If it mentions an unsupported Python version, make sure Python 3.12 is installed and retry.
  pause
  exit /b 1
)
.venv312\Scripts\python.exe quick_maths.py
if errorlevel 1 (
  echo The app stopped with an error. Review setup.log for dependency details.
  pause
)
