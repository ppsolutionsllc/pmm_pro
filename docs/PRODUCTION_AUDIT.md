# Production Audit Report

Дата аудиту: 2026-03-18  
Репозиторій: `PMM_ONLINE`

## 1) Scope
- Backend runtime (FastAPI, DB sessions, error handling, security baseline).
- Frontend runtime/build (Vite, nginx reverse-proxy mode).
- Docker/Compose deployment paths (dev/prod/Coolify).
- ENV configuration consistency and deployment UX.
- Smoke checks and operational documentation.

## 2) Findings (prioritized)

## Critical
1. Відсутня окрема production-ready конфігурація для Coolify.
   - Ризик: нестабільний деплой, ручні костилі, високий шанс збоїв на першому запуску.
   - Статус: fixed (`docker-compose.coolify.yml`).
2. Тестовий контур backend падав під час колекції (`httpx` відсутній).
   - Ризик: smoke-тести не запускаються, CI/локальна перевірка неповна.
   - Статус: fixed (`backend/requirements.txt`).

## High
1. Backend логування було орієнтовано переважно на файли, без request-correlation.
   - Ризик: слабка діагностика інцидентів у контейнерному середовищі.
   - Статус: fixed (stdout logging + request_id filter + `X-Request-ID`).
2. Відсутня нормалізація глобальних помилок API та єдиного формату 5xx.
   - Ризик: витік внутрішніх деталей/непередбачувані відповіді.
   - Статус: fixed (exception handlers у `app/main.py`).
3. Відсутні security headers на API та frontend nginx.
   - Ризик: гірший baseline security posture.
   - Статус: fixed (middleware + nginx headers).
4. Blocking I/O (`pg_dump` / `pg_restore` / файлові операції) у async endpoints.
   - Ризик: блокування event loop під навантаженням.
   - Статус: fixed (`asyncio.to_thread` у backup endpoints).

## Medium
1. Docker images використовували bleeding-edge Node 24 для runtime/build.
   - Ризик: нестабільність та несумісності.
   - Статус: fixed (Node 20 LTS у Dockerfile).
2. Непрозорі env-вимоги та розсинхрон між code/compose/docs.
   - Ризик: помилки конфігурації при деплої.
   - Статус: fixed (оновлені `.env*.example`, README, deployment docs).
3. Відсутні documented smoke checks.
   - Ризик: регресії помічаються пізно.
   - Статус: fixed (`scripts/smoke-checks.sh`, `Makefile`).

## Low
1. Відсутність `/health` і `/ready` alias-ів (тільки `/healthz`, `/readyz`).
   - Ризик: зайва інтеграційна неоднорідність.
   - Статус: fixed (додані alias-и, legacy endpoints збережено).
2. Невизначений локальний frontend proxy target поза Docker.
   - Ризик: `npm run dev` може не знаходити backend.
   - Статус: fixed (`VITE_DEV_PROXY_TARGET` + fallback на localhost).

## 3) Remediation summary

## Infrastructure / deployment
- Додано `docker-compose.coolify.yml`:
  - healthchecks для `db`, `backend`, `frontend`;
  - required env guardrails (`${VAR:?Set VAR}`);
  - persistent volumes для БД, backup/artifacts/logs;
  - production command для backend через entrypoint script.
- Додано `backend/scripts/start-backend.sh`:
  - опціональний автозапуск міграцій (`RUN_MIGRATIONS=true`);
  - старт gunicorn/uvicorn worker.
- Оновлено Dockerfiles:
  - backend: non-root runtime user, `tini`, minimal runtime packages.
  - frontend: Node 20 LTS.

## Backend runtime/security
- Request correlation:
  - `X-Request-ID` для кожного запиту;
  - request-id у логах (stdout/file/memory handlers).
- Error handling:
  - глобальні handlers для `HTTPException`, validation errors, unhandled exceptions.
  - у 5xx повертається safe message без stack trace.
- Security baseline:
  - security headers middleware (керується `ENABLE_SECURITY_HEADERS`);
  - optional trusted hosts (`ALLOWED_HOSTS`).
- DB runtime config:
  - pool settings винесено в env (`DB_POOL_*`, `DB_CONNECT_TIMEOUT_SECONDS`).
- Backup endpoints:
  - переведені на `asyncio.to_thread` для уникнення event-loop blocking.
- Rate-limit:
  - уніфікований limiter singleton (`app/core/rate_limit.py`).

## Frontend/runtime
- API base:
  - підтримка `VITE_API_URL` для direct API mode;
  - fallback на same-origin `/api/v1`.
- Dev proxy:
  - `VITE_DEV_PROXY_TARGET` з fallback `http://localhost:8000`.
- nginx:
  - `/health` endpoint;
  - security headers.

## DX / checks / docs
- Додано:
  - `scripts/smoke-checks.sh`
  - `Makefile` (`make check`, `make smoke`)
  - `docs/DEPLOY_COOLIFY.md`
  - `docs/RUNBOOK.md`
- Оновлено:
  - `README.md`
  - `docs/API_MAP.md`
  - `.env.example`, `.env.prod.example`, `.env.backend.example`, `.env.frontend.example`

## 4) Verification performed
- `python3 -m compileall backend/app` -> OK.
- `make check-compose` -> OK.
- `docker compose run --rm --no-deps frontend npm run build` -> OK.
- `docker compose run --rm --no-deps backend pytest -q` -> `1 skipped` (очікувано, без `TEST_DATABASE_URL`).
- `./scripts/smoke-checks.sh` -> OK (pytest block skipped без test DB).

## 5) Remaining risks / deferred items
1. Немає повноцінного CI pipeline у репозиторії (авто-checks/auto-build/auto-test).
2. Інтеграційні backend тести залежать від `TEST_DATABASE_URL`; без test DB покривається лише syntax/build/compose.
3. Frontend bundle великий (Vite warning > 500KB), потрібне code-splitting у наступному циклі.
4. Update subsystem (`update_service`) все ще складний та потребує окремого hardening/ops policy для прод-середовищ, де Docker-in-Docker заборонений.
