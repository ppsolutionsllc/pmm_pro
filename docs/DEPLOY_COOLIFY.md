# Deploy Guide: Coolify

Цей гайд описує рекомендований деплой через `docker-compose.coolify.yml`.

## 1) Що використовувати
- Compose file: `docker-compose.coolify.yml`
- Env template: `.env.prod.example` (скопіювати в Coolify Variables/Secrets)

## 2) Мінімально обов'язкові env
- `POSTGRES_PASSWORD`
- `JWT_SECRET` (мінімум 32 символи)
- `CORS_ORIGINS` (наприклад `https://app.example.com`)
- `FRONTEND_BASE_URL` (наприклад `https://app.example.com`)

Рекомендовано також:
- `ALLOWED_HOSTS=app.example.com`
- `ENABLE_SECURITY_HEADERS=true`
- `RUN_MIGRATIONS=true`
- `BACKEND_WORKERS=3`

## 3) Створення Stack у Coolify
1. Створити новий Docker Compose stack.
2. Вставити вміст `docker-compose.coolify.yml`.
3. Додати env variables (з `.env.prod.example`).
4. Налаштувати public domain на сервіс `frontend` (порт `80`).
5. Запустити Deploy.

Примітка:
- `backend` та `db` не публікувати назовні.
- `frontend` має бути єдиною публічною точкою входу.

## 4) Міграції
- За замовчуванням `RUN_MIGRATIONS=true` і backend застосує `alembic upgrade head` на старті.
- Якщо потрібен manual режим:
  - `RUN_MIGRATIONS=false`
  - виконувати міграції окремою командою в backend container.

## 5) Перший admin
Після першого деплою виконайте одноразово в backend container:

```bash
python -m app.cli create-first-admin \
  --login admin \
  --password 'ChangeMe_Strong_123' \
  --full-name 'System Admin'
```

Команда безпечна:
- не створює дублікати, якщо ADMIN вже існує;
- не запускається автоматично.

## 6) Post-deploy checks
Виконати перевірки:
1. `GET /health` -> `200 {"ok": true}`
2. `GET /ready` -> `200 {"ok": true, "db": "ok"}`
3. Вхід у UI, авторизація admin.
4. Створення тестового чернеткового запиту.
5. Перевірка `Admin -> Logs`, що немає критичних runtime errors.

## 7) Rollback strategy
1. Зберігати попередній image tag/commit.
2. При невдалому релізі повернути попередній stack revision у Coolify.
3. Якщо міграція вже застосована:
   - rollback БД тільки з перевіреного backup;
   - перед rollback обов'язково freeze write-трафіку.

## 8) Persistent data
Зберігати як persistent volumes:
- `pgdata` — Postgres data.
- `pmm_artifacts` — артефакти генерацій.
- `pmm_backups` — backup dumps.
- `pmm_logs` — файлові логи застосунку.

## 9) Security notes
- Не відкривати `db` порт назовні.
- Не використовувати `ALLOWED_HOSTS=*` у проді.
- Ротація секретів (`JWT_SECRET`, `POSTGRES_PASSWORD`) за політикою організації.
