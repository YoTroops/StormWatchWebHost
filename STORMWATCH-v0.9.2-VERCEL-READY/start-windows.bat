@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if errorlevel 1 (
  echo Python 3.11+ is required. Install Python from https://www.python.org/downloads/
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  if errorlevel 1 ( echo Unable to create Python virtual environment & pause & exit /b 1 )
)
".venv\Scripts\python.exe" -m pip install -r "apps\api\requirements.txt"
if errorlevel 1 ( echo Python package installation failed. Check your internet connection. & pause & exit /b 1 )
set PYTHONPATH=%CD%\apps\api
start "" "http://127.0.0.1:8000"
echo STORMWATCH running at http://127.0.0.1:8000
".venv\Scripts\python.exe" -m uvicorn stormwatch.main:app --host 127.0.0.1 --port 8000
pause
