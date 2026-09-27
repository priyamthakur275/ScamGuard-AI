@echo off
title ScamGuard Backend
cd /d "%~dp0"
python setup_local.py
cd backend
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m uvicorn app_service.main:app --host 127.0.0.1 --port 8000
) else (
  echo Missing backend\.venv. Follow START_HERE.md to install dependencies first.
)
pause
