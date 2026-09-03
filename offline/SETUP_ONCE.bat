@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python not found.
  echo Install Python 3.12+ and enable "Add Python to PATH".
  pause
  exit /b 1
)

python -m venv .venv
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo Setup complete. Run START_OFFLINE.bat
pause
