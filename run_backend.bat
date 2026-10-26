@echo off
title ScamGuard Backend
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 run.py --backend-only %*
) else (
  python run.py --backend-only %*
)
pause
