# ScamGuard — AI-Powered Online Scam & Fraud Detection System

ScamGuard is a full-stack, production-grade cybersecurity intelligence platform designed to detect phishing attacks, lottery fraud, UPI/banking scams, and social engineering in real time using Machine Learning and Explainable AI (XAI).

---

## 🌐 Live demo

**https://scamguard-frontend-r6t7.onrender.com** — use **"Try the demo account"** on the sign-in page, or paste a message into the quick check on the home page (no account needed).

Hosted on Render's free tier (frontend + `app_service` + PostgreSQL). The backend keeps both services awake 08:00–22:00 IST (`app_service/services/keep_alive.py`); outside that window the first request can take up to a minute while the server wakes. ML inference runs in-process inside `app_service`; a separate `ml_service` container exists only in the local `docker-compose` setup.

---

## 🎯 What ScamGuard does

**Check anything** — SMS/WhatsApp text, links, emails, screenshots (WhatsApp chat-aware OCR, dark mode supported), PDFs, QR codes and voice calls (live captions or private on-device Whisper transcription, Hindi→English).

**Explain the verdict**
- **Scam X-Ray** — highlights the exact trap phrases in the message and maps them onto the four stages of a scam: hook, pressure, the ask, cash-out.
- **Scam likelihood** — an SVM model (v3, trained on the SMS Spam Collection + a documented Indian scam supplement) fused with an intent-based risk engine; the model's own probability is always shown alongside. Unseen-set accuracy: 87.5% (see `backend/ml_training/datasets/README.md`).
- **Website trust score** — domain age from RDAP, HTTPS, link signals and a live inspection of the page (password/OTP/card forms, forms posting elsewhere, brand impersonation).
- **Ask ScamGuard** — answers "is this a scam?", "I already paid, what now?", "how do I report it?" (English/Hindi), optionally backed by Gemini/Anthropic/OpenAI via env vars.

**Act on it**
- One-tap reporting to **Chakshu** (Sanchar Saathi) or **1930 / cybercrime.gov.in**, with a ready-to-paste complaint.
- **Community reports** for numbers, link domains, UPI IDs and emails (one vote per user; 2+ reports raise the score).
- **Family guardian** — link a family member; with consent on both sides they see your high-risk scans and can call before money is sent.
- Share a warning on WhatsApp; export PDF/CSV/JSON reports.

**Learn and reach people**
- **Scam Awareness Trainer** — spot-the-scam rounds with red-flag lessons.
- **Public scam trends** (anonymous aggregates), **English/Hindi interface**, installable **PWA with Android share target**, and a **Chrome/Edge/Brave extension** (`browser-extension/`).

**Platform** — JWT auth with refresh rotation, bcrypt, self-hosted CAPTCHA, per-visitor rate limits, SSRF-safe URL fetching, CSP, admin model evaluation and robustness testing, 560+ automated tests.

---

## 🏗️ System Architecture

```mermaid
graph TD
    Client[Web Browser] -->|HTTPS| Frontend[Next.js 14 Frontend - Vercel / Port 3000]
    Frontend -->|Same-Origin /backend-api Rewrite| AppService[FastAPI App Service - Port 8000]
    AppService -->|SQLAlchemy / Alembic| DB[(PostgreSQL / SQLite)]
    AppService -->|In-process, same container| MLEngine[ML Inference Engine]
    MLEngine -->|Joblib Serialization| ModelRegistry[(Trained ML Artifacts - SVM / TF-IDF)]
```

> **Note on the deployed topology:** the codebase supports running ML
> inference as a separate `ml_service` container (see `infra/docker-compose.yml`
> and `backend/docs/ML_SERVICE.md` for the multi-service local/self-hosted setup, useful
> for independently scaling inference). The **current Render deployment
> (`render.yaml`) only provisions the single `app_service` container**, which
> loads the model in-process — there is no separate ML microservice running in
> production today. This is a deliberate simplification (one fewer moving part,
> one fewer cold start) rather than an oversight; the app_service code still
> checks for a remote ML service first for forward-compatibility, but always
> falls through to serving the real trained model in-process on the current
> deployment.

---

## ⚙️ Environment variables

All backend configuration is via `backend/.env` (copy from `backend/.env.example`). Every variable actually used by the app:

| Variable | Purpose | Required? |
|---|---|---|
| `SECRET_KEY` | JWT signing secret. **Refuses to start if left at the known placeholder value while `DEBUG=false`** -- generate a real one for anything beyond local dev. | Yes |
| `DEBUG` | Defaults to `false`. Set `true` only for local development. | No |
| `DATABASE_URL` | Postgres (production) or SQLite (local fallback) connection string. | Yes |
| `ML_SERVICE_URL` | URL of a separate `ml_service` container, if running one (self-hosted `docker-compose` setup only -- **not used by the current Render deployment**, which runs ML in-process). | No |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins. | Yes |
| `ACCESS_TOKEN_EXPIRE_MINUTES` / `REFRESH_TOKEN_EXPIRE_DAYS` | JWT lifetimes. | No |
| `RATE_LIMIT_DEFAULT` / `RATE_LIMIT_AUTH` | SlowAPI rate limits. | No |
| `VOICE_TRANSCRIPTION_PROVIDER` / `VOICE_TRANSCRIPTION_API_KEY` | Optional server-side audio transcription provider. Unset by default -- browser-based live transcription (Web Speech API) works regardless; only server-side audio-*file* transcription needs this. | No |
| `COPILOT_LLM_PROVIDER` / `COPILOT_LLM_API_KEY` | Optional external LLM for Copilot. Unset by default -- Copilot answers via the deterministic, evidence-grounded engine instead. | No |

The frontend needs no `.env` for local dev beyond what Next.js generates (`frontend/.env.local`) for its own tooling; the API base URL is proxied same-origin via `next.config.js` rewrites, not an environment variable.

---

## 🚀 Getting Started

### Prerequisites
- **Node.js**: v18+ or v20+ LTS
- **Python**: v3.10, v3.11, or v3.12
- **Docker & Docker Compose**: Optional (recommended for one-command containerized run)

---

### Option A: One-Command Startup with Docker Compose (Recommended)

From the project root directory, run:

```bash
docker compose up --build
```

This starts all services together:
- **Web UI**: [http://localhost:3000](http://localhost:3000) (or via Nginx on port 80)
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **API Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ML Service**: [http://localhost:8002](http://localhost:8002)
- **PostgreSQL**: localhost:5432

---

### Quickest: one command (macOS / Linux)

```bash
./start.sh
```

First run installs everything (Python virtual environment in `backend/.venv` and npm packages), then it starts the backend on :8000 and the frontend on :3000, waits until both answer and opens http://localhost:3000. Ctrl+C stops both. Logs are in `.run-logs/`. No `.env` file is needed for local use.

### Option B: Local Setup Without Docker (VS Code / Terminal)

Open **three terminal windows** in your IDE/command prompt:

#### Terminal 1 — Backend App Service
```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
# source venv/bin/activate

pip install -r requirements.txt
# Starts on http://localhost:8000 (uses local SQLite database automatically if PostgreSQL is not set)
uvicorn app_service.main:app --port 8000 --reload
```

#### Terminal 2 — ML Inference Service
```bash
cd backend
# Windows:
venv\Scripts\activate
# macOS/Linux:
# source venv/bin/activate

pip install -r requirements-ml.txt
# Starts on http://localhost:8002 (uses pre-trained models bundled in backend/artifacts)
uvicorn ml_service.main:app --port 8002 --reload
```

#### Terminal 3 — Frontend UI
```bash
cd frontend
npm install
npm run dev
```
Open **[http://localhost:3000](http://localhost:3000)** in your browser.

---

## 🧪 Testing and Verification

The project includes an automated test suite with **509 unit and integration tests**, all passing as of the last verified run.

Run all tests:
```bash
cd backend
python -m pytest tests -v
python -m pytest ml_service/tests -v
python -m pytest ml_common/tests ml_training/tests -v
```

---

## 📁 Repository Structure

```
ScamGuard-AI/
├── docker-compose.yml          # Root one-command multi-container setup
├── backend/
│   ├── app_service/            # Core business logic, auth, REST API routes
│   │   ├── api/v1/             # Endpoints: auth, messages, users, health
│   │   ├── core/               # Config, JWT security, exceptions, rate-limiting
│   │   ├── db/                 # Models, database session, SQLite/PostgreSQL
│   │   └── services/           # Business logic & extraction service
│   ├── ml_service/             # Dedicated ML inference microservice
│   ├── ml_training/            # ML model training scripts & datasets
│   ├── ml_common/              # Shared NLP tokenizers, TF-IDF vectorizers
│   ├── artifacts/              # Bundled trained ML model weights & metadata
│   ├── requirements.txt        # App service dependencies
│   └── requirements-ml.txt     # ML service dependencies
├── frontend/                   # Next.js 14 React frontend with Tailwind CSS
│   ├── src/app/                # App router: login, register, dashboard, analyze, settings
│   ├── src/components/         # Reusable UI widgets, badges, verdict cards, camera scanner
│   └── src/lib/api/            # Typed API client with auto token refresh
├── infra/
│   └── docker/                 # Dockerfiles for each microservice
└── docs/                       # Architecture documentation and specs
```

---

## 🔒 Security Best Practices

- Passwords hashed using bcrypt.
- JWT access tokens with short expiry (15m) + secure refresh token rotation (7d).
- Strict Content Security Policy (CSP) & CORS configuration.
- Rate-limiting enabled via SlowAPI on sensitive auth & prediction routes.
- Privacy-first in-memory vectorization: message content is never sold or used for model retraining without consent.
- **URL analysis is SSRF-hardened**: every hostname the server actually connects to (including redirect targets, checked via an httpx request-level hook) is resolved and rejected if it's a loopback, private, link-local, multicast, or reserved address -- so a submitted URL can't be used to make the server fetch its own internal network or cloud metadata endpoint (`169.254.169.254`). TLS certificate verification is enforced (previously disabled).
- **File uploads (image/PDF/QR/email) are capped at 8 MB** server-side, independent of any reverse proxy in front of the service, to prevent memory exhaustion during OCR/PDF parsing.
- **No fabricated ML fallback**: if neither the remote ML microservice nor the in-process model can produce a real prediction, the API returns a `503 MODEL_UNAVAILABLE` error. There is no keyword-heuristic tier that manufactures a plausible-looking probability, confidence score, or model name when the real model is unavailable.

### Known limitations

- Scans happen when a user submits something; there is no automatic SMS or call interception (that would need a native Android app).
- Domain age depends on the public RDAP service; if it is unreachable the trust score says "registration date not available".
- The Indian scam supplement is curated by the team, not field-collected; accuracy is reported on separately written hold-out sets.
- No real third-party CAPTCHA, no independent SPF/DKIM/DMARC DNS verification, and CAPTCHA/login-attempt state is in-process (single instance).

### CAPTCHA / abuse protection (added)

Registration and step-up login protection now use a real, self-hosted, stateless CAPTCHA (`app_service/core/captcha.py`, 11 tests): a short arithmetic challenge with an HMAC-SHA256-signed, time-limited token -- no server-side storage needed, tamper-evident, timing-safe verification. This is honestly scoped as a lightweight bot-friction mechanism, not a claim of parity with a third-party CAPTCHA service (reCAPTCHA/hCaptcha/Turnstile), which would need external account credentials this environment doesn't have; swapping one in later only requires changing the verification call site.

- **Registration**: always requires a solved CAPTCHA.
- **Login**: only requires one after 3 failed attempts for that email within 15 minutes (`app_service/core/login_attempts.py`) -- not on every normal login. That tracker is in-process (documented limitation: resets on restart, not shared across multiple app_service replicas; a multi-instance deployment would need to move it to Redis or the database).

### URL intelligence (added)

URL analysis now computes real, deterministic signals from the URL string itself (`ml_common/security/url_intelligence.py`, 20+ tests): punycode/IDN detection, IP-literal hosts, known URL shorteners, a short list of TLDs commonly abused in phishing campaigns, userinfo-obfuscation (`user@host` tricks), and lookalike/brand-impersonation detection via edit distance against a small explicit brand list. This is a best-effort heuristic layer, not a full public-suffix-list implementation or a live reputation/WHOIS/TLS lookup -- it does not claim domain age, certificate details, or a definitive verdict, only what's structurally observable in the URL text. TLS certificate metadata (subject/issuer/expiry) is best-effort and untested against a live host from this project's own dev environment. Results are surfaced as "Observed URL signals," kept explicitly separate from the model's own interpretation.

### Model evaluation (extended)

`ModelEvaluator` (`ml_training/evaluation/evaluator.py`) computes real accuracy/precision/recall/F1/ROC-AUC/false-positive-rate via scikit-learn on an actual train/test split, plus the raw confusion matrix counts (TP/TN/FP/FN). The production model (`svm` v2) is trained on the public SMS Spam Collection from Kaggle plus 24 project samples (5,193 unique messages, 80/20 split). On the 1,039-message test split it scores accuracy 0.987, precision 0.955, recall 0.947, F1 0.951, ROC-AUC 0.998 and false-positive rate 0.007. See `backend/ml_training/datasets/README.md` for the dataset source and the exact training command. The dataset is English SMS from the UK and does not contain Indian UPI, job or investment scams, so the rule-based threat scorer remains important for those.

---

## 👤 Author & Project Team

- **Project Lead & Author**: **Priyam Thakur** (1BM23CS252) ([@priyamthakur275](https://github.com/priyamthakur275))
- **Team Members**: Bhavya Goyal (1BM23CS063), Samir Chaudhary (1BM23CS294), Sana Subodh (1BM23CS296)
- **Guide**: Dr. Kayarvizhy N, Professor, Department of CSE, B.M.S. College of Engineering, Bengaluru
- **Repository**: [https://github.com/priyamthakur275/ScamGuard-AI](https://github.com/priyamthakur275/ScamGuard-AI)
- **Project**: ScamGuard AI — AI-Powered Online Scam & Fraud Detection System (Major Project, B.E. Computer Science and Engineering)
