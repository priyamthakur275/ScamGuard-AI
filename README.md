<div align="center">

# ScamGuard

### AI-Based Online Scam and Fraud Detection System

Detects scams in SMS, WhatsApp text, links, emails, screenshots, PDFs, QR codes and calls, and explains every verdict.

[![Live site](https://img.shields.io/badge/Live_site-open-14b8a6?style=for-the-badge)](https://scamguard-frontend-r6t7.onrender.com)
[![F1](https://img.shields.io/badge/F1-97.5%25-f59e0b?style=for-the-badge)](backend/ml_training/research/results_v2.md)
[![Evasion](https://img.shields.io/badge/Recall_under_evasion-97.2%25-22c55e?style=for-the-badge)](backend/ml_training/research/results_v2.md)
[![Hindi/Hinglish](https://img.shields.io/badge/English_·_Hindi_·_Hinglish-8b5cf6?style=for-the-badge)](docs/v2/V2_SUMMARY.md)
[![Tests](https://img.shields.io/badge/Tests-863_back--end_·_14_front--end-3b82f6?style=for-the-badge)](#tests)

![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?logo=scikitlearn&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js_14-000000?logo=nextdotjs&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)

**[Open the live site](https://scamguard-frontend-r6t7.onrender.com)** · paste a message into the quick check, or press **Try the demo account** on the sign-in page.

</div>

<p align="center">
  <img src="docs/screenshots/home.jpg" alt="ScamGuard home page" width="49%">
  <img src="docs/screenshots/quick_check.jpg" alt="Quick check result with Scam X-Ray" width="49%">
</p>

## Project documents

Major Project Phase-2, Department of CSE, B.M.S. College of Engineering, Group 56.

| Document | File |
|---|---|
| Project report | [docs/report/ScamGuard_Project_Report.pdf](docs/report/ScamGuard_Project_Report.pdf) (LaTeX source in [docs/report](docs/report)) |
| Presentation | [docs/presentation/ScamGuard_Final_Presentation.pptx](docs/presentation/ScamGuard_Final_Presentation.pptx) |
| Poster (A3) | [docs/poster/ScamGuard_Poster_A3.pdf](docs/poster/ScamGuard_Poster_A3.pdf) |
| Conference paper (COMP-SIF 2027, Paper ID 1206) | [docs/paper/ScamGuard_Conference_Paper.pdf](docs/paper/ScamGuard_Conference_Paper.pdf) |
| Cross-domain study (notebook and Streamlit app) | [research/cross_domain](research/cross_domain) |

## Results (v2)

Deployed system (classifier + intent rules, model v5) on **1,874 real Indian messages from scam campaigns held out of training**:

| Accuracy | Precision | Recall | F1 (95% CI) | False-alarm rate | ROC-AUC |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **96.7%** | **97.8%** | **97.1%** | **97.5%** (96.8–98.0) | **3.9%** | **0.994** |

What v2 adds, measured by [`v2_experiments.py`](backend/ml_training/research/v2_experiments.py) ([full tables](backend/ml_training/research/results_v2.md)):

| Test | v1 (as deployed) | v2 |
|---|:---:|:---:|
| Real test set, F1 / false alarms | 97.1% / 3.9% | 97.5% / 3.9% |
| Evasion attack (lookalike letters, zero-width, leetspeak, defanged links): scams caught | 88.4% | **97.2%** |
| Held-out Hinglish/Hindi set B (synthetic, 36 templates), F1 / false alarms | 85.0% / 12.7% | **100% / 0%** |
| Scams that contain no link: caught (a "has a link" rule catches 0%) | – | 95.8% |
| Calibration error (ECE) / latency | – | 0.017 / 0.67 ms per message (CPU) |

Notes: the v1 report scored raw text (97.7% F1, 3.2% false alarms); the live v1 app appended a concept summary
the model was never trained on, which cost about 0.6 F1. v2 removes that mismatch. The Hinglish sets are synthetic
and written by the same team that wrote the rules, so they show coverage of these phrasings, not real-world
accuracy. On the English test set v2 and v1 are not significantly different (McNemar p = 0.12).
See [docs/v2/V2_SUMMARY.md](docs/v2/V2_SUMMARY.md) and the [model card](docs/v2/MODEL_CARD.md).

- **Dataset:** ScamGuard-IN-2026, 11,399 Indian messages with audited labels ([datasheet](backend/ml_training/datasets/scamguard_in_2026/DATASHEET.md)).
- **No leakage:** the split is by scam campaign, so no near-duplicate of a test message appears in training.
- **Reproducible:** from `backend/`, `python -m ml_training.research.v2_experiments` regenerates every v2 number in about 40 seconds ([results_v2.md](backend/ml_training/research/results_v2.md)); `run_experiments` regenerates the v1 study ([results.md](backend/ml_training/research/results.md)).

### Cross-domain study

| Logistic Regression | Spam F1 |
|---|:---:|
| Trained on UK SMS (UCI), tested on UK SMS | 0.911 |
| Same model tested on Indian SMS | 0.678 |
| After adding 143 labelled Indian messages (10%) | 0.964 |

The website's **Cross-domain study** page runs the baseline and adapted models side by side on any message.

<p align="center"><img src="docs/screenshots/cross_domain_compare.jpg" alt="Baseline vs adapted model on the cross-domain page" width="80%"></p>

## Features

**Check**
- **Quick check** on the home page, no account needed and nothing stored.
- **Telegram bot**: forward a message, get a verdict ([setup](docs/v2/TELEGRAM_SETUP.md)). Also a **browser extension** ([browser-extension](browser-extension)).
- **English, Hindi and Hinglish**, and robust to disguised words (lookalike letters, hidden characters, "cl1ck", "hxxp").
- **Investigate** for text, links, emails, screenshots (OCR), PDFs, QR codes and voice calls.

**Explain**
- **Scam X-Ray** highlights the trap phrases and maps them to the four stages of a scam: hook, pressure, the ask, cash-out.
- **TrustLens** shows the model probability and the final risk score side by side, with the evidence for and against.
- **Website trust score**: domain age, HTTPS, redirects and whether the page asks for passwords, OTPs or card details.
- **ScamGuard Copilot** answers "is this a scam?" and "I already paid, what now?", grounded in the scan and 42 known Indian scam patterns.

**Act**
- **Golden Hour** help for people who already paid: a one-hour countdown, a call to 1930 and a ready complaint.
- One-tap reporting to **Chakshu** (Sanchar Saathi), **1930** and **cybercrime.gov.in**.
- **Safety tools**: QR payment check, UPI "before you pay" check, payment screenshot check, file check and chat timeline.

**Track and learn**
- **Dashboard, History and Analytics** for signed-in users, with PDF and CSV reports.
- **Scam trends**, **Flashcards**, an installable app (PWA) and a **browser extension** for Chrome, Edge and Brave.

## Architecture

```mermaid
graph LR
    U[Browser / PWA / Extension] --> F[Next.js 14 front end]
    T[Telegram] -->|webhook| B
    F -->|/backend-api| B[FastAPI back end]
    B --> D[(PostgreSQL / SQLite)]
    B --> X[De-obfuscation]
    X --> M[Classifier + intent rules, English / Hindi / Hinglish]
    M --> R[(Model registry: LR v5, TF-IDF)]
    N[Training and cross-domain notebooks] -.-> R
```

| Layer | Technology |
|---|---|
| Front end | Next.js 14, React, TypeScript, Tailwind CSS, PWA |
| Back end | Python, FastAPI, SQLAlchemy, Alembic, JWT with refresh rotation, rate limiting |
| ML | scikit-learn logistic regression on word + character TF-IDF, intent-based risk engine |
| Copilot | Google Gemini with built-in fallback answers |
| Inputs | OCR, PDF parsing, QR decoding, speech-to-text |
| Research | Jupyter notebook, Streamlit; MuRIL / XLM-R comparison notebook (PyTorch, Colab) |

## Run it locally

Needs **Python 3.10–3.14** and **Node.js 18+**. No database, `.env` file or Docker is required.

```bash
python run.py      # Windows (or double-click start_all.bat)
python3 run.py     # macOS / Linux (or ./start.sh)
```

The first run installs everything (2–5 minutes), then opens http://localhost:3000. The API runs on http://127.0.0.1:8000 (docs at `/docs`). In VS Code, use **Terminal → Run Task → ScamGuard: Run (backend + frontend)**. See [START_HERE.md](START_HERE.md) for troubleshooting.

Optional full stack with PostgreSQL: `docker compose up --build`.

## Tests

```bash
cd backend && python -m pytest -q                              # 863 tests
cd frontend && npm run typecheck && npm run lint && npm test   # 14 tests
```

## Security and privacy

- bcrypt passwords, short-lived JWTs with refresh rotation, self-hosted CAPTCHA and rate limits.
- Links are opened only on the server, with SSRF protection; uploads are capped at 8 MB.
- Quick checks are never stored; saved scans are visible only to their owner, who can download or delete them.

## Repository structure

```
backend/
  app_service/    FastAPI app: API routes, services, database
  ml_common/      shared preprocessing, features, model registry
  ml_training/    training pipeline, ScamGuard-IN-2026 dataset, experiments
  ml_service/     optional separate inference service
  artifacts/      trained models
  tests/          back-end tests
frontend/         Next.js app
browser-extension/
research/cross_domain/   cross-domain notebook, data, outputs, Streamlit app
research/transformer/    MuRIL / XLM-R vs TF-IDF comparison (Colab notebook)
docs/             report, presentation, poster, paper, screenshots; docs/v2 for v2
infra/            Dockerfiles and nginx config
run.py            one-command local run
```

## Team

| | |
|---|---|
| Author | **Priyam Thakur** (1BM23CS252) · [@priyamthakur275](https://github.com/priyamthakur275) |
| Team | Bhavya Goyal (1BM23CS063), Samir Chaudhary (1BM23CS294), Sana Subodh (1BM23CS296) |
| Guide | Dr. Kayarvizhy N, Professor, Department of CSE, B.M.S. College of Engineering, Bengaluru |
