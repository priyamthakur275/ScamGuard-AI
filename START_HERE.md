# Run ScamGuard on your computer

## 1. Install two things (once)

| Tool | Version | Download |
| --- | --- | --- |
| **Python** | 3.10 to 3.14 (3.12 or 3.13 recommended) | https://www.python.org/downloads/ (Windows: tick **"Add python.exe to PATH"**) |
| **Node.js** | 18 or newer (the **LTS** version) | https://nodejs.org |

Restart VS Code after installing them.

No database, no `.env` file, no Docker and no API keys are needed.

## 2. Run it

**VS Code:** open the project folder → **Terminal → Run Task… → "ScamGuard: Run (backend + frontend)"**, or just press **Ctrl+Shift+B**.

**Terminal:** in the project folder run

| OS | Command |
| --- | --- |
| Windows | `py run.py` (or `python run.py`, or double-click `start_all.bat`) |
| macOS / Linux | `python3 run.py` (or `./start.sh`) |

The **first run** installs everything (2–5 minutes). After that it starts in seconds.
When you see **"Everything is running"**, the browser opens http://localhost:3000.

- Frontend: http://localhost:3000
- Backend API docs: http://127.0.0.1:8000/docs
- Sign in with **"Try the demo account"**, or register (the CAPTCHA is a small sum).
- **Ctrl+C** in that terminal stops both servers.

Options: `python run.py --backend-only`, `--setup-only` (install/repair only), `--no-browser`.

## 3. Troubleshooting

| What you see | Why | Fix |
| --- | --- | --- |
| "Server busy" / "Too many quick checks" | An old version enforced the public rate limit locally | `git pull`, then run `python run.py` again (local runs have no rate limit now) |
| "Could not reach the server" / "Server waking up" | The backend isn't running, or an old one is frozen | Run `python run.py`: it stops an old ScamGuard server on ports 8000/3000 and starts fresh |
| "Port 8000 (or 3000) is used by another program" | A different app uses that port | Close it (or restart the computer) and run again |
| `'python' is not recognized` (Windows) | Python isn't on PATH | Use `py run.py`, or reinstall Python with "Add python.exe to PATH" ticked |
| `npm` / `node` not found | Node.js isn't installed or VS Code wasn't restarted | Install Node LTS, restart VS Code |
| Package install fails mentioning "Microsoft Visual C++" or a compiler | Very new or very old Python | Use Python 3.12 or 3.13, delete `backend/.venv`, run again |
| Frontend install fails | A previous `npm run dev` is still running, or a broken install | Close other terminals, delete `frontend/node_modules`, run again |
| Screenshot (OCR) scan says OCR unavailable | The Tesseract program isn't installed (optional) | Install Tesseract OCR; if not on PATH, add `TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe` to `backend/.env` |
| QR scan error | The ZBar library is missing (optional; Mac: `brew install zbar`, Linux: `sudo apt install libzbar0`) | Install it, or paste the QR link as text instead |
| Anything else | | Look at `.run-logs/backend.log` and `.run-logs/frontend.log` |

To start completely fresh: close the terminal, delete `backend/.venv`, `frontend/node_modules`, `backend/.env` and `frontend/.env.local`, then run `python run.py` again.

## 4. Tests

- VS Code: **Terminal → Run Task… → "ScamGuard: Backend tests"** (820 tests) and **"Frontend checks"**.
- Terminal: `backend/.venv/bin/python -m pytest -q` from `backend/` (Windows: `.venv\Scripts\python -m pytest -q`), and `npm run typecheck && npm run lint && npm test` from `frontend/`.

## 5. What runs where

- **Backend**: FastAPI on http://127.0.0.1:8000, local SQLite database (`backend/app_service/scam_detection.db`, created automatically). The production model (logistic regression v4, trained on ScamGuard-IN-2026) runs in-process.
- **Frontend**: Next.js dev server on http://localhost:3000; it forwards `/backend-api/*` to the backend, so the browser talks to one address.
- **Live site** (separate): https://scamguard-ai-zeta.vercel.app (Vercel + Render + Neon).

Keep `backend/.env` private: it holds your local secret key and is git-ignored.
