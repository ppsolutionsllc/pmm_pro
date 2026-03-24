# Production Audit Report

Дата аудиту: 2026-03-19  
Репозиторій: `PMM_ONLINE`  
Target deploy: Coolify + `pmm.66br.pp.ua`

> Historical note: цей аудит описує стан до повного розділення `dev`/`prod`.
> Поточний source of truth для deployment:
> - базовий шар: `docker-compose.yml`
> - production overlay: `docker-compose.prod.yml`
> - production env: `.env.prod`
> Актуальні команди та структура описані в `README.md`.

## 1) Summary
Статус готовності: `READY WITH MANUAL ACTIONS`.

Базовий production deploy через Coolify підготовлено:
- `docker-compose.yml` + `docker-compose.prod.yml` є основним source of truth.
- назовні публікується тільки `frontend`.
- `backend` і `db` лишаються внутрішніми сервісами.
- health/readiness, міграції, env-шаблон та docs синхронізовані.

## 2) Findings (severity)

## Critical
1. Небезпечні production fallback-и у compose (`ALLOWED_HOSTS=*`, `localhost` origins/urls).
   - Ризик: host-header bypass, CORS помилки, помилковий прод-конфіг.
   - Статус: fixed.
2. Ризик падіння backend при недоступному файловому логуванні (permissions у volume).
   - Ризик: backend crash при старті через `RotatingFileHandler`.
   - Статус: fixed (graceful fallback на stdout/stderr, warning у лог).

## High
1. ALLOWED_HOSTS не був обов'язковим для Coolify stack.
   - Ризик: запуск без trusted host validation.
   - Статус: fixed (`docker-compose.prod.yml` -> required env).
2. Доменні значення були не нормалізовані під production домен.
   - Ризик: конфігураційний дрейф між кодом/env/docs.
   - Статус: fixed (`.env.prod`, docs, checks).
3. Потенційна проблема прав доступу до persistent runtime директорій.
   - Ризик: неможливість писати артефакти/бекупи/логи у проді.
   - Статус: fixed (`backend/Dockerfile`, `start-backend-prod.sh` preflight checks).
4. Backend healthcheck був несумісний з strict `ALLOWED_HOSTS`.
   - Ризик: backend позначався unhealthy (`400` на `/ready`) при правильному production host whitelist.
   - Статус: fixed (healthcheck переведено на локальний `/readyz` без залежності від зовнішнього `Host` header).

## Medium
1. Легасі `docker-compose.prod.yml` суперечив secure defaults.
   - Ризик: помилкове використання insecure значень.
   - Статус: fixed (required vars + без wildcard/localhost defaults).
2. Smoke/check scripts не перевіряли нові required env для compose.
   - Ризик: false-positive перевірки.
   - Статус: fixed (`Makefile`, `scripts/smoke-checks.sh`).
3. Колізія локальних image names між різними compose-режимами.
   - Ризик: dev frontend image (Vite) міг підхоплюватись у coolify-стеку під час локальної валідації.
   - Статус: fixed (dev/prod збираються через окремі targets та overlays).

## Low
1. Історичні документи можуть описувати застарілий deployment path.
   - Ризик: оператор може обрати не ту схему запуску.
   - Статус: mitigated (README та deployment docs вказують актуальну модель `base + prod overlay`).

## 3) Fixes Applied
- Hardened `docker-compose.yml` + `docker-compose.prod.yml`:
  - production overlay повністю відокремлено від dev-поведінки.
  - `ALLOWED_HOSTS`, `CORS_ORIGINS`, `FRONTEND_BASE_URL`, `DOMAIN` винесено в production env.
  - bind mounts прибрано з production.
  - дані винесено в persistent named volumes.
  - healthchecks узгоджено з `/readyz` і `/health`.
- Added `docker-compose.dev.yml`:
  - bind mounts, autoreload, dev ports і dev workflow живуть тільки тут.
  - frontend працює через Vite dev server, backend через reload startup.
- Hardened backend startup/runtime:
  - preflight writable checks для artifacts/backups/log dir (`start-backend-prod.sh`).
  - graceful degradation при недоступному file logging (`app/main.py`).
  - secure defaults для `ALLOWED_HOSTS` parsing (`app/config.py`).
  - runtime dir ownership у Docker image (`backend/Dockerfile`).
- Normalized production env and docs:
  - `.env.prod` орієнтовано на production overlay і documented як deployment template.
  - детальний Coolify deployment guide оновлено.
  - smoke/config checks синхронізовано з required vars.

## 4) Manual Actions Required
1. Заповнити production secrets у Coolify:
   - `POSTGRES_PASSWORD`
   - `JWT_SECRET`
2. Встановити production env values:
   - `CORS_ORIGINS=https://pmm.66br.pp.ua`
   - `FRONTEND_BASE_URL=https://pmm.66br.pp.ua`
   - `ALLOWED_HOSTS=pmm.66br.pp.ua`
3. Прив'язати домен `pmm.66br.pp.ua` до сервісу `frontend` на порту `80`.
4. Одноразово створити першого адміністратора через backend CLI.

## 5) Known Limitations
1. Немає повного CI pipeline (lint/test/build/deploy gates).
2. Backend інтеграційні smoke-тести повністю працюють тільки за наявності `TEST_DATABASE_URL`.
3. Update subsystem потребує окремої ops-політики (доступ до docker/host на прод-сервері).
