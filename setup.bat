@echo off
setlocal

cd /d "%~dp0"

echo [1/4] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
  echo Python not found. Please install Python 3.11+ and add it to PATH.
  exit /b 1
)

echo [2/4] Creating virtual environment (.venv)...
if not exist ".venv" (
  python -m venv .venv
)

echo [3/4] Activating virtual environment...
call ".venv\Scripts\activate.bat"

echo [4/4] Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo Setup completed successfully.
echo Next step: run run.bat
endlocal
