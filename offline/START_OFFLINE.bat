@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Run SETUP_ONCE.bat first.
  pause
  exit /b 1
)

start "" http://127.0.0.1:8765/
".venv\Scripts\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 8765
pause
