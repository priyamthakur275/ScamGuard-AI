# Deployment Guide

Three deployment paths are supported:

1. **Vercel (frontend) + Railway (backends + Postgres)** — recommended, covered in detail below.
2. **Self-hosted via docker-compose** — a single `docker compose up` on any VM, using `infra/docker-compose.yml` and `infra/nginx/nginx.conf`. See that file's inline comments; it wires all six services together and needs no further explanation beyond `cp infra/.env.example infra/.env` (fill in real secrets) and `cd infra && docker compose up --build`.
3. **CI/CD** — `.github/workflows/{backend-ci,ml-ci,frontend-ci}.yml` run tests and Docker builds on every push/PR; wire in your own deploy step (Railway and Vercel both support git-push-to-deploy natively, which is simpler than driving their APIs from Actions — see each section below).

---

## 1. Railway — app_service + ml_service + PostgreSQL

Railway is used for the two Python backends because they need a long-running process (Postgres connections, an in-memory loaded ML model) rather than Vercel's serverless model.

### 1.1 Create the project and database

1. Create a new Railway project.
2. Add a **PostgreSQL** plugin — Railway provisions it and exposes a `DATABASE_URL` you'll reference below.

### 1.2 Deploy `app_service`

1. Add a new service → **Deploy from GitHub repo** → select this repo.
2. Set the **root directory** to `backend`.
3. Set the **Dockerfile path** to `infra/docker/Dockerfile.app_service` (Railway supports a custom Dockerfile path outside the root directory; if your Railway plan doesn't, copy the Dockerfile to `backend/Dockerfile` instead — no code changes needed, just a file location).
4. Environment variables (Settings → Variables):
   | Key | Value |
   |---|---|
   | `SECRET_KEY` | Generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
   | `DATABASE_URL` | Reference Railway's Postgres plugin variable, converted to the `postgresql+psycopg2://` scheme (Railway gives you `postgresql://`; SQLAlchemy needs the `+psycopg2` driver suffix — e.g. `postgresql+psycopg2://user:pass@host:port/db`) |
   | `CORS_ORIGINS` | Your Vercel frontend URL, e.g. `https://scamguard.vercel.app` |
   | `ML_SERVICE_URL` | Your Railway `ml_service` URL (set once you've deployed it in step 1.3) |
   | `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` |
   | `REFRESH_TOKEN_EXPIRE_DAYS` | `7` |
   | `RATE_LIMIT_DEFAULT` | `100/minute` |
   | `RATE_LIMIT_AUTH` | `10/minute` |
   | `LOG_LEVEL` | `INFO` |
5. Railway auto-detects the exposed port from the Dockerfile's `EXPOSE 8000`. Note the generated public URL (e.g. `https://app-service-production.up.railway.app`).
6. The container's `CMD` runs `alembic upgrade head` before starting Uvicorn, so migrations apply automatically on every deploy.

### 1.3 Train and register a model, then deploy `ml_service`

`ml_service` needs a populated `artifacts/` directory (a registered, promoted model) before it can serve predictions. Two options:

**Option A — bake a model into the image (simplest for a first deploy):**
Before deploying, run the training pipeline locally or in CI and commit the resulting `artifacts/` directory into the repo (or a dedicated branch/release), then have `Dockerfile.ml_service` `COPY artifacts ./artifacts` instead of expecting a mounted volume. This trades "no rebuild needed for a new model" for deployment simplicity — reasonable for a first production deploy.

**Option B — Railway volume (matches the architecture's intended rollout strategy):**
1. Add a **Volume** to the `ml_service` Railway service, mounted at `/app/artifacts`.
2. Run the training job once via Railway's one-off command feature (or `railway run python -m ml_training.run_training --dataset ml_training/datasets/sample_messages.csv --version v1 --artifacts-dir /app/artifacts`) against that same volume.
3. Every future retrain writes a new version into the same volume; promote it with the registry's `promote()` API (see `ml_common/registry/model_registry.py`) without rebuilding the `ml_service` image at all.

Either way, deploy `ml_service` the same way as `app_service`:
1. New service → root directory `backend` → Dockerfile path `infra/docker/Dockerfile.ml_service`.
2. Environment variables:
   | Key | Value |
   |---|---|
   | `ARTIFACTS_DIR` | `/app/artifacts` |
   | `PRODUCTION_MODEL_NAME` | The `model_name` your training run promoted, e.g. `naive_bayes` |
   | `RATE_LIMIT_DEFAULT` | `200/minute` |
   | `RATE_LIMIT_PREDICT` | `60/minute` |
   | `LOG_LEVEL` | `INFO` |
3. **Do not** add CORS-related variables here — `ml_service` has no CORS middleware by design. It is called only by `app_service` server-to-server, never directly from a browser.
4. Note its public URL (e.g. `https://ml-service-production.up.railway.app`) — you'll set it as `ML_SERVICE_URL` on the `app_service` deployment (step 1.2).

---

## 2. Vercel — Frontend

1. Import the repo into Vercel; set the **root directory** to `frontend`.
2. Vercel auto-detects Next.js; no build command override is needed (`next build` runs automatically). The `output: "standalone"` setting in `next.config.js` is harmless on Vercel (Vercel ignores it and uses its own runtime), so no changes are needed to deploy the same codebase to both Vercel and Docker.
3. Environment variables (Project Settings → Environment Variables) — **server-side, not `NEXT_PUBLIC_`**:
   | Key | Value |
   |---|---|
   | `APP_SERVICE_URL` | Your Railway `app_service` URL from step 1.2, e.g. `https://app-service-production.up.railway.app` |
4. Deploy. Vercel's serverless functions execute `next.config.js`'s `rewrites()` on every request, proxying `/backend-api/*` to `app_service` server-side — the browser never makes a cross-origin request to it, so no CORS configuration is needed for this path. `app_service` in turn calls `ml_service` server-to-server using its own `ML_SERVICE_URL` variable (step 1.2/1.3) — the browser never talks to `ml_service` at all.
5. Once deployed, go back to the `app_service` Railway variables and set `CORS_ORIGINS` to the real Vercel URL (this only matters if something other than the Next.js rewrite ever calls `app_service` directly; the rewrite path itself doesn't need it, but it's a reasonable defense-in-depth default).

---

## 3. Post-deploy checklist

- [ ] `https://<your-app>.vercel.app/backend-api/api/v1/health` returns `{"status": "ok"}`
- [ ] Registering an account and analyzing a message end-to-end works from the deployed frontend (this exercises `frontend` → `app_service` → `ml_service` in one request)
- [ ] `SECRET_KEY` is a real random value, not the placeholder from `.env.example`, on the `app_service` deployment
