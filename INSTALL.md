# Current local setup

Use [START_HERE.md](START_HERE.md) for the verified local startup path and configuration requirements. The older Docker/development notes below are retained for context; Docker was not executed in this verification.

# Installation & Local Development Guide

## Prerequisites

- **Docker Desktop** (v20+) or equivalent container runtime.
- **Git** (to clone the repository).

## One-Command Setup

ScamGuard is designed to be completely portable. The entire environment is containerized.

1. Clone the repository:
   ```bash
   git clone https://github.com/PreranaPJois-123/ScamGuard-AI.git
   cd ScamGuard-AI
   ```

2. Start the application:
   ```bash
   docker compose -f infra/docker-compose.yml up --build -d
   ```

3. Access the application:
   - Web UI: http://localhost
   - API Docs: http://localhost/backend-api/docs

## Stopping the Application

To shut down the containers safely without losing data:
```bash
docker compose -f infra/docker-compose.yml down
```

To shut down and wipe the database (useful for resetting state):
```bash
docker compose -f infra/docker-compose.yml down -v
```

## Local Development (Without Docker)

If you wish to develop components natively without Docker, follow these steps.

### 1. Database
Ensure PostgreSQL is running locally on port 5432 with a database named `scam_detection`.

### 2. Backend (FastAPI & ML)
Requires Python 3.12.
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
pip install -r requirements-ml.txt

# Train the initial ML model
python -m ml_training.pipeline

# Apply Database migrations
alembic upgrade head

# Run ML Service (Port 8002)
python -m uvicorn ml_service.main:app --port 8002 &

# Run App Service (Port 8000)
python -m uvicorn app_service.main:app --port 8000 &
```

### 3. Frontend (Next.js)
Requires Node.js 18+.
```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at http://localhost:3000.
