@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
  echo Virtual environment not found. Please run setup.bat first.
  exit /b 1
)

call ".venv\Scripts\activate.bat"

echo Starting FastAPI and Flask Admin...
echo FastAPI: http://localhost:5000
echo Admin:   http://localhost:8080/admin/login

echo Launching FastAPI window...
start "FastAPI" cmd /k "cd /d %~dp0 && call .venv\Scripts\activate.bat && uvicorn main:app --host 127.0.0.1 --port 5000 --reload"

echo Launching Admin window...
start "Flask Admin" cmd /k "cd /d %~dp0 && call .venv\Scripts\activate.bat && python -m admin.app"

echo Done. Close opened windows to stop services.
endlocal
