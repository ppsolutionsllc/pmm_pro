# Dokploy Deploy Guide (Docker Compose from GitHub)

> This document assumes the Dokploy production model:
> use only `docker-compose.prod.yml` with production environment variables.

## Purpose
This repository is prepared for deployment in Dokploy using:
- Service type: `Docker Compose`
- Compose file: `docker-compose.prod.yml`
- Public domain: `https://pmm.66br.pp.ua`

Routing is managed by Dokploy Domains UI. Manual Traefik labels in compose are intentionally removed.

## What Changed for Dokploy
- Removed manual `traefik.*` labels from `frontend` in `docker-compose.prod.yml`.
- Removed hard dependency on `${DOMAIN}` in compose routing labels.
- Removed Coolify-specific external network dependency from prod compose.
- Added source builds in prod compose:
  - `backend` builds from `./backend/Dockerfile` target `prod`
  - `frontend` builds from `./frontend/Dockerfile` target `prod`
- `db` now uses a direct stable image: `postgres:15`
- `docker-compose.prod.yml` is self-contained and does not depend on `docker-compose.yml`
- backend entrypoint waits for PostgreSQL and runs `alembic upgrade head` before starting `gunicorn`
- Kept only internal ports with `expose`:
  - `frontend: 80`
  - `backend: 8000`
- Preserved named volumes for persistent data:
  - `pgdata`, `pmm_artifacts`, `pmm_backups`, `pmm_logs`
- Kept healthchecks for db/backend/frontend.
- Backend startup in prod now uses `/app/scripts/start-backend-prod.sh`.

## Which Service Gets the Domain in Dokploy
- Public service: `frontend`
- Container port in Dokploy Domains: `80`

`backend` and `db` remain internal-only (no host `ports:` publish).

## Required Environment Variables in Dokploy
Set these in Dokploy project Environment/Secrets before deploy:

- `POSTGRES_PASSWORD`
  - DB password for PostgreSQL and backend connection string.
- `POSTGRES_USER`
  - Example: `pmm`
- `POSTGRES_DB`
  - Example: `pmm`
- `JWT_SECRET`
  - Required auth secret, **minimum 32 characters**.
- `CORS_ORIGINS`
  - Example: `https://pmm.66br.pp.ua`
- `FRONTEND_BASE_URL`
  - Example: `https://pmm.66br.pp.ua`
- `ALLOWED_HOSTS`
  - Example: `pmm.66br.pp.ua`

## Optional Environment Variables
- `APP_VERSION` (default `dev`)
- `BACKEND_WORKERS` (default `3`)
- `PRINT_QR_TARGET_URL` (default `https://pmm.66br.pp.ua`)
- `FIRST_ADMIN_LOGIN`, `FIRST_ADMIN_PASSWORD`, `FIRST_ADMIN_FULL_NAME` (bootstrap helper)
- Update subsystem vars: `UPDATE_*`, `UPDATER_*` (only if you use updater feature)
- Runtime storage vars: `ARTIFACTS_DIR`, `BACKUP_DIR`, `POSTING_ERROR_LOG_PATH` (app-level paths)

## Dokploy UI Deployment Steps (Click-Path)
1. `Projects` -> open/create project.
2. `Create Service` -> choose `Docker Compose`.
3. Connect/select GitHub repository and branch.
4. Set `Compose Path` to `docker-compose.prod.yml`.
5. Open `Environment` and add required env vars listed above.
6. Deploy service.
7. Open `Domains` tab:
   - Add domain `pmm.66br.pp.ua`
   - Select service `frontend`
   - Set container port `80`
   - Enable TLS/HTTPS in Dokploy UI.
8. Save and redeploy (if Dokploy prompts).

## Post-Deploy Verification
Run/check:
- `https://pmm.66br.pp.ua/` -> frontend loads.
- `https://pmm.66br.pp.ua/api/health` -> backend liveness via frontend nginx proxy.
- `https://pmm.66br.pp.ua/api/ready` -> backend readiness.
- Dokploy logs:
  - `db` healthy
  - `backend` healthy
  - `frontend` healthy

## Migration Note (from Old Deployment Logic)
`migrate` remains in compose as an `ops` profile service and does not start during normal Dokploy deploy.
Production startup is safe even without it, because backend applies migrations before app startup.
Run migrations separately when needed:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml --profile ops run --rm migrate
```

Removed from `docker-compose.prod.yml`:
- dependency on `docker-compose.yml`
- manual Traefik labels and `${DOMAIN}` interpolation
- host `ports:` publishing for internal services
- nested or fragile image interpolation logic

Now configured in Dokploy instead of compose:
- Domain binding
- TLS/HTTPS certificates
- Router/public entrypoint

This avoids compose parse failures like `required variable DOMAIN is missing` and aligns with Dokploy best practices.
