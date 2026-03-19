# RUNBOOK (Operations)

Операційний мінімум для підтримки PMM Online у production.

## 1) Health / readiness
- Liveness: `GET /health`
- Readiness: `GET /ready`
- Через frontend proxy:
  - `GET /health`
  - `GET /ready`

Очікуване:
- `/health` -> `{"ok": true}`
- `/ready` -> `{"ok": true, "db": "ok"}`

Якщо `/ready` не `200`:
1. Перевірити стан Postgres.
2. Перевірити `DATABASE_URL`.
3. Перевірити логи backend container.

## 2) Логи
- API додає `X-Request-ID` у відповіді.
- Усі ключові app-логи містять request id (формат `[req=...]`).
- Для контейнерної діагностики використовувати stdout/stderr у Coolify.
- Додатково доступні admin endpoints логів:
  - `GET /api/v1/settings/logs`
  - `GET /api/v1/settings/logs/export`

## 3) Backup / restore
Основні endpoints:
- `POST /api/v1/settings/backups/create`
- `GET /api/v1/settings/backups`
- `POST /api/v1/settings/backups/{filename}/verify`
- `POST /api/v1/settings/backups/{filename}/restore`
- `POST /api/v1/settings/backups/upload`
- `POST /api/v1/settings/backups/upload-and-restore`

Рекомендації:
1. Робити backup перед релізом.
2. Тестувати `verify` для кожного нового dump.
3. Періодично перевіряти restore-процедуру в staging.

## 4) Планова перевірка після релізу
1. `/health` та `/ready`.
2. Авторизація admin.
3. Створення тестового draft request.
4. Перевірка, що backup endpoint працює.
5. Відсутність нових unresolved incident spikes.

## 5) Часті інциденти
1. `JWT_SECRET` короткий/відсутній:
   - backend не стартує через валідацію settings.
   - placeholder-значення також блокуються (навмисно), потрібно задати реальний секрет 32+ символи.
2. Некоректний `CORS_ORIGINS`:
   - браузер блокує API запити.
3. Відсутній `POSTGRES_PASSWORD`:
   - db сервіс не стартує.
4. Невалідний `DATABASE_URL`:
   - `/ready` повертає `db: down`.

## 6) Smoke checks
Локально/на CI runner:
```bash
./scripts/smoke-checks.sh
```

Що перевіряється:
1. Python syntax compile backend.
2. Frontend production build.
3. Compose config validation (dev/prod/coolify).
4. Backend pytest smoke (опційно, якщо задано `TEST_DATABASE_URL`).

## 7) Безпечні операційні дефолти
- `RUN_MIGRATIONS=true` у production (один backend instance).
- `ENABLE_SECURITY_HEADERS=true`.
- `ALLOWED_HOSTS=pmm.66br.pp.ua`.
- `CORS_ORIGINS=https://pmm.66br.pp.ua`.
- `FRONTEND_BASE_URL=https://pmm.66br.pp.ua`.
- Не публікувати `backend`/`db` в інтернет.
