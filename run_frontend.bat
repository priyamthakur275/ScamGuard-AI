@echo off
title ScamGuard Frontend
cd /d "%~dp0frontend"
if not exist "node_modules" call npm ci --no-audit --no-fund
set APP_SERVICE_URL=http://127.0.0.1:8000
echo Starting ScamGuard Frontend on http://localhost:3000 (start the backend first: run_backend.bat)
npm run dev
pause
