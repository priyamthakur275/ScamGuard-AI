# Troubleshooting Guide

## Docker Compose Issues

### Problem: Port 80, 5432, 8000, 3000 is already in use
**Symptom**: `Bind for 0.0.0.0:80 failed: port is already allocated.`
**Solution**: Another application is currently running on the port Nginx is trying to use. Stop the competing service (e.g. Apache, local Postgres, local Next.js server).
```bash
# Check what is using the port
lsof -i :80
```

### Problem: Database Migration Errors
**Symptom**: App service container fails to start, throwing Alembic database URL errors.
**Solution**: This typically happens if the `POSTGRES_USER` or `POSTGRES_PASSWORD` env vars were changed *after* the initial volume was created. Wipe the volume to reset it.
```bash
docker compose -f infra/docker-compose.yml down -v
docker compose -f infra/docker-compose.yml up --build -d
```

### Problem: ML Service keeps restarting
**Symptom**: Nginx returns 502 Bad Gateway when scanning messages.
**Solution**: The ML Trainer container might have failed to build the artifacts correctly.
Check the trainer logs:
```bash
docker compose -f infra/docker-compose.yml logs ml_trainer
```
If it failed, you can run a full system prune and rebuild:
```bash
docker system prune -a --volumes -f
docker compose -f infra/docker-compose.yml up --build -d
```

## Cleaning up Cache

Sometimes Docker caches bad builds. If you want a 100% clean slate:
```bash
docker compose -f infra/docker-compose.yml down -v
docker system prune -a --volumes -f
```
Warning: This will delete the database contents permanently.
