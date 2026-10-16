@echo off
setlocal
cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] .venv not found. Run scripts\setup.ps1 first.
  exit /b 1
)
if "%COLLECTOR_TOKEN%"=="" (
  echo [ERROR] Set COLLECTOR_TOKEN before starting.
  exit /b 1
)
if "%ADMIN_TOKEN%"=="" (
  echo [ERROR] Set ADMIN_TOKEN before starting.
  exit /b 1
)
if "%DB_PATH%"=="" set DB_PATH=data\messages.db
if "%DRY_RUN%"=="" set DRY_RUN=true

echo Starting bridge at http://127.0.0.1:8000
call ".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000

