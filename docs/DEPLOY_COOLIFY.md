# Deploy Guide: Coolify (Production)

Цільовий production-домен: `pmm.66br.pp.ua`.

## 1) Source Of Truth
- Compose file: `docker-compose.coolify.yml`
- Branch: production/release branch з GitHub (рекомендовано `main`)
- Env template: `.env.prod.example`
- Публічний сервіс: `frontend`
- Target port: `80`

## 2) Обов'язкові ENV у Coolify
Заповнити вручну:
- `POSTGRES_PASSWORD`
- `JWT_SECRET` (мінімум 32 символи)
- `CORS_ORIGINS=https://pmm.66br.pp.ua`
- `FRONTEND_BASE_URL=https://pmm.66br.pp.ua`
- `ALLOWED_HOSTS=pmm.66br.pp.ua`

Рекомендовані значення:
- `DOMAIN=pmm.66br.pp.ua`
- `PRINT_QR_TARGET_URL=https://pmm.66br.pp.ua`
- `ENABLE_SECURITY_HEADERS=true`
- `RUN_MIGRATIONS=true`
- `BACKEND_WORKERS=3`

## 3) Coolify Click-Path
1. `New` -> `Project` (або existing project).
2. `Add New Resource` -> `Docker Compose`.
3. Підключити GitHub repository.
4. Вказати branch для production deploy.
5. `Compose Path`: `docker-compose.coolify.yml`.
6. Відкрити `Environment Variables` і заповнити обов'язкові змінні з розділу вище.
7. Для ресурсу `frontend` увімкнути public access:
8. `Domain` -> додати `pmm.66br.pp.ua`.
9. `Port` -> `80`.
10. `Deploy`.

## 4) Що деплоїться назовні
- Публікується тільки `frontend`.
- `backend` та `db` не мають зовнішніх `ports` і доступні тільки всередині docker network.

## 5) Перший Deploy
1. Запустити deploy stack.
2. Дочекатися `healthy` стану `db`, `backend`, `frontend`.
3. Перевірити:
   - `https://pmm.66br.pp.ua/health`
   - `https://pmm.66br.pp.ua/ready`

## 6) Перший Адміністратор
Після першого успішного deploy виконати одноразово в контейнері `backend`:

```bash
python -m app.cli create-first-admin \
  --login admin \
  --password 'ChangeMe_Strong_123' \
  --full-name 'System Admin'
```

CLI не створює дублікати (якщо ADMIN вже існує, команда завершується без змін).

## 7) Redeploy
- Через Coolify: `Deploy` на цьому ж ресурсі після нового commit/tag.
- Для forced restart без змін коду: `Redeploy` або `Restart`.

## 8) Логи та діагностика
- Основні логи: вкладка `Logs` у Coolify по сервісах `frontend`, `backend`, `db`.
- Швидкі перевірки:
  - якщо `frontend` unhealthy -> перевірити nginx startup/build.
  - якщо `backend` unhealthy -> перевірити міграції/підключення до БД.
  - якщо `db` unhealthy -> перевірити `POSTGRES_PASSWORD`, volume, disk space.

## 9) Якщо deploy неуспішний
1. Відкрити `Logs` проблемного сервісу.
2. Перевірити, що всі required env задані.
3. Перевірити health:
   - `frontend`: `/health`
   - `backend`: `/ready` (проксіюється через `frontend`)
4. Виправити env/конфіг і зробити redeploy.

## 10) Rollback (коротко)
1. Обрати попередній стабільний commit/branch.
2. Запустити redeploy на попередню ревізію.
3. Якщо були міграції:
   - використовувати тільки перевірений backup перед rollback БД.
   - призупинити write-операції на час rollback.

## 11) Persistent Data
У стеку використовуються named volumes:
- `pgdata` — Postgres data
- `pmm_artifacts` — PDF/артефакти
- `pmm_backups` — backup dumps
- `pmm_logs` — файлові логи backend (додатково до stdout/stderr)
