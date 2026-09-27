@echo off
title ScamGuard - Local Launcher
cd /d "%~dp0"
python setup_local.py
start "ScamGuard Backend" cmd /k call "%~dp0run_backend.bat"
start "ScamGuard Frontend" cmd /k call "%~dp0run_frontend.bat"
echo Backend and frontend startup requested. Check both windows for readiness.
echo Open http://localhost:3000 when Next.js reports Ready.
pause
