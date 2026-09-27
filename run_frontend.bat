@echo off
title ScamGuard Frontend
cd /d "%~dp0frontend"
echo Starting ScamGuard Frontend on http://localhost:3000 ...
npm run dev
pause
