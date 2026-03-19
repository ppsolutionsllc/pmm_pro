# PMM Online MVP

Веб-система обліку ПММ: заявки підрозділів, склад, видача оператором, проведення, інциденти, резервні копії, звітність.

## Стек
- `frontend`: React 19 + Vite 7 + TypeScript + Tailwind CSS.
- `backend`: FastAPI + SQLAlchemy 2 + Alembic.
- `database`: PostgreSQL 15.
- `containers`: Docker Compose.

## Структура
- `frontend/` — клієнт.
- `backend/app/` — API та бізнес-логіка.
- `backend/alembic/` — міграції.
- `docker-compose.yml` — локальна dev-конфігурація.
- `docker-compose.prod.yml` — production стек (legacy).
- `docker-compose.coolify.yml` — production стек для Coolify.
- `docs/` — документація.

## Вимоги
- Docker + Docker Compose.
- Для локального запуску без Docker:
  - Python `3.12+`
  - Node.js `20+`

## Локальний запуск (Docker, dev)
1. Підготувати env:
```bash
cp .env.example .env
# заповнити JWT_SECRET (мінімум 32 символи)
```
2. Застосувати міграції:
```bash
docker compose run --rm migrator
```
3. Створити першого адміністратора (одноразово):
```bash
docker compose run --rm \
  -e FIRST_ADMIN_LOGIN=admin \
  -e FIRST_ADMIN_PASSWORD='ChangeMe_Strong_123' \
  -e FIRST_ADMIN_FULL_NAME='System Admin' \
  backend python -m app.cli create-first-admin
```
4. Запустити стек:
```bash
docker compose up --build
```

Доступ:
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- OpenAPI: `http://localhost:8000/docs`

## Production / Coolify
Використовуйте тільки `docker-compose.coolify.yml` як source of truth для production deploy у Coolify.
Цільовий домен: `https://pmm.66br.pp.ua`.

Ключові production env:
- `CORS_ORIGINS=https://pmm.66br.pp.ua`
- `FRONTEND_BASE_URL=https://pmm.66br.pp.ua`
- `ALLOWED_HOSTS=pmm.66br.pp.ua`
- `POSTGRES_PASSWORD` (secret)
- `JWT_SECRET` (secret, 32+ chars)

Швидкі посилання:
- [DEPLOY_COOLIFY.md](docs/DEPLOY_COOLIFY.md)
- [RUNBOOK.md](docs/RUNBOOK.md)
- [PRODUCTION_AUDIT.md](docs/PRODUCTION_AUDIT.md)

## Основні health endpoints
- `GET /health` — liveness.
- `GET /ready` — readiness (перевірка БД).
- Сумісність з legacy:
  - `GET /healthz`
  - `GET /readyz`

## Перевірки
- Повний smoke-check:
```bash
./scripts/smoke-checks.sh
```
- Або через `make`:
```bash
make check
```

## Безпека та конфігурація
- CORS і frontend origin керуються через env (`CORS_ORIGINS`, `FRONTEND_BASE_URL`).
- Дозволені host-и: `ALLOWED_HOSTS` (у проді не залишати `*`).
- Security headers на API вмикаються `ENABLE_SECURITY_HEADERS=true`.
- Secrets у репозиторій не зберігаються.

## Статус
MVP, активна розробка. Поточний production hardening та деплой-процедури описані в `docs/`.
