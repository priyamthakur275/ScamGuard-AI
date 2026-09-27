# Run your existing ScamGuard project

This archive updates the uploaded application. It retains the Next.js frontend,
FastAPI services, SQLAlchemy models, migrations, ML registry/artifacts, and tests.

## Windows: first-time setup

Install Python 3.12 and Node.js 20 or newer. Open PowerShell in the extracted
project folder (the folder containing this file).

```powershell
python setup_local.py
python -m venv backend/.venv
backend/.venv/Scripts/python -m pip install -r backend/requirements.txt -r backend/requirements-ml.txt
cd frontend
npm ci
cd ..
.\start_all.bat
```

Wait for both terminal windows to report ready, then open http://localhost:3000.
The backend uses http://127.0.0.1:8000. Register through the real CAPTCHA form.
Registration creates a regular user, not an administrator.

The setup script creates a private JWT key only when `backend/.env` is absent.
It preserves existing configuration. With no explicit DATABASE_URL, the backend
uses its existing local SQLite default. The shipped real model runs in-process;
a separate ML service and a new training run are not required for local startup.

## macOS / Linux

```bash
python3 setup_local.py
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements.txt -r backend/requirements-ml.txt
cd frontend
npm ci
cd ..
```

Terminal 1:

```bash
cd backend
.venv/bin/python -m uvicorn app_service.main:app --host 127.0.0.1 --port 8000
```

Terminal 2:

```bash
cd frontend
npm run dev
```

## OCR, QR, camera, voice

- OCR needs the **Tesseract executable**, in addition to the Python dependencies.
  Install Tesseract for your OS. If it is not on PATH, set `TESSERACT_CMD` in
  `backend/.env` to its executable path. Missing OCR returns an extraction error.
- QR decoding uses **pyzbar/ZBar**. Linux needs `libzbar0`; macOS needs ZBar.
  On Windows, pyzbar's native DLLs and their runtime dependencies must be present.
  Decoder failures produce an error rather than a verdict. Docker app images
  include ZBar and Tesseract; Docker itself was not executed in this verification.
- Camera requires localhost or HTTPS and a browser camera permission. It sends
  a captured frame to the existing image/OCR path. Use the QR upload tab for QR.
- Live voice uses the browser SpeechRecognition capability and may send audio
  to the browser vendor. Availability depends on browser, microphone, permission,
  and network. A pasted transcript uses the same real voice-analysis pipeline.
- Audio uploads have no implemented transcription provider in this project.
  Setting a provider name/key alone does not implement one. The API reports
  this limitation; it never substitutes a transcript.

## Quality checks

From `backend` with the virtual environment active:

```bash
python -m pytest -q
```

From `frontend`:

```bash
npm run typecheck
npm run lint
npm run build
npm run start
```

`setup_local.py` writes APP_SERVICE_URL before building. Next.js compiles the
proxy destination into its build: **rebuild after changing the backend URL**.

## Deployment notes

Keep `.env` files private. Docker Compose requires an explicit private SECRET_KEY;
it no longer accepts a public fallback. Set it in your deployment environment
before using the existing Compose setup. The frontend Dockerfile defaults its
build-time backend URL to `http://app_service:8000` for that setup.

The shipped registry records **19 training rows and 5 evaluation rows**. This is
an experimental classifier, not a validated enterprise detection model. The UI
redesign does not change or improve the model's demonstrated accuracy.

See `VERIFICATION.md` for changes, test results, tested flows, and limitations.
