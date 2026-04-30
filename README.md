# PMM Online

Система обліку ПММ на `FastAPI + PostgreSQL + React/Vite`, повністю розділена на `dev` і `prod` режими без змішування runtime-логіки.

## Що тепер за що відповідає

- `docker-compose.yml` — base-шар для локальної розробки.
- `docker-compose.dev.yml` — лише локальна розробка: bind mounts, hot reload, відкриті dev-порти, Vite dev server.
- `docker-compose.prod.yml` — самодостатній production compose для Dokploy і звичайного `docker compose`: без bind mounts, без reload/debug, production startup, nginx зі зібраним frontend.
- `.env.dev` — локальні безпечні dev-значення.
- `.env.prod` — production template з placeholder-secret значеннями, які треба замінити перед deploy.
- `.env.example` — загальна довідка по змінних.
- `backend/Dockerfile` — multi-stage backend image з окремими `dev` і `prod` стадіями.
- `frontend/Dockerfile` — multi-stage frontend image з окремими `dev` і `prod` стадіями.
- `frontend/nginx.prod.conf` — nginx тільки для production frontend.
- `backend/scripts/start-backend-dev.sh` — dev startup з Alembic + `uvicorn --reload`.
- `backend/scripts/start-backend-prod.sh` — production startup через `gunicorn`.

## Чим dev відрізняється від prod

### Dev
- bind mounts для `backend/app`, `backend/alembic`, `frontend/`
- `uvicorn --reload` тільки в dev
- `vite` dev server тільки в dev
- порти відкриті назовні:
  - frontend: `3000`
  - backend: `8000`
  - postgres: `5432`
- backend автоматично застосовує міграції при старті
- dev-залежності встановлюються тільки в dev image stage

### Prod
- жодних bind mounts для коду
- frontend збирається заздалегідь і віддається nginx
- backend стартує через `gunicorn`, без autoreload
- перед стартом backend у production автоматично чекає БД і виконує `alembic upgrade head`
- dev-залежності не потрапляють у production image
- назовні публікується тільки `frontend` через platform ingress / Dokploy domain routing
- `make prod-migrate` лишається як ручна ops-команда для окремого прогону міграцій

## Persistent data

У production всі persistent дані лежать в одній хостовій папці `PMM_DATA_ROOT`
(за замовчуванням `/opt/pmm-data`):

- `${PMM_DATA_ROOT}/postgres` — база PostgreSQL
- `${PMM_DATA_ROOT}/artifacts` — згенеровані артефакти / друк / файли застосунку
- `${PMM_DATA_ROOT}/backups` — `pg_dump` backups
- `${PMM_DATA_ROOT}/logs` — runtime logs backend

Для локальної dev-розробки окремо лишається `frontend_node_modules` volume.

Шляхи всередині backend контейнера стандартизовані:

- `ARTIFACTS_DIR=/var/lib/pmm/artifacts`
- `BACKUP_DIR=/var/lib/pmm/backups`
- `POSTING_ERROR_LOG_PATH=/var/log/pmm/posting_errors.log`

## Запуск dev

```bash
make dev-up
```

Корисні команди:

```bash
make dev-build
make dev-migrate
make dev-admin
make dev-logs
make dev-down
make dev-rebuild
```

Доступ:

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- OpenAPI: `http://localhost:8000/docs`
- PostgreSQL: `localhost:5432`

## Запуск prod

1. Відредагуйте `.env.prod` і задайте реальні secrets, домен і `PMM_DATA_ROOT`.
2. Підготуйте хостову папку для даних:

```bash
sudo ./scripts/prepare-prod-data-root.sh /opt/pmm-data
```

3. Запустіть стек:

```bash
make prod-up
```

4. Застосуйте міграції:

```bash
make prod-migrate
```

Корисні команди:

```bash
make prod-build
make prod-logs
make prod-down
make prod-rebuild
make prod-backup
```

## Safe recreate / що можна пересоздавати

Без втрати даних можна пересоздавати:

- `backend`
- `frontend`
- `migrate`

За умови, що `${PMM_DATA_ROOT}` не видалено, можна безпечно робити:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
docker compose --env-file .env.prod -f docker-compose.prod.yml down
```

## Небезпечні команди

Небезпечно:

```bash
docker compose down -v
rm -rf /opt/pmm-data
```

Це видаляє persistent volumes і може призвести до втрати:

- БД
- backup-файлів
- runtime artifacts
- логів

## Backup / restore

- Backup створюється в `${PMM_DATA_ROOT}/backups`
- Для ручного production backup:

```bash
make prod-backup
```

- В адмінці доступні два типи резервних копій:
  - `pg_dump` бекап БД
  - `повний бекап системи` (`.tar.gz`)
- Повний бекап містить:
  - `database.dump`
  - `artifacts`
  - `logs`
- Повний бекап можна використати для переносу між серверами: завантажити архів на новий сервер і виконати повне відновлення з адмінки
- Повне відновлення з такого архіву є руйнівною операцією: воно перезаписує поточну БД, `artifacts` і `logs`
- Історичні файли з `${PMM_DATA_ROOT}/backups` у повний архів не включаються, щоб уникнути рекурсивного розростання архівів
- Backup volume треба включати в стратегію зовнішнього резервного копіювання хоста

## Production notes

- Для production не використовуйте `docker-compose.dev.yml`
- Для Dokploy використовуйте тільки `docker-compose.prod.yml`
- Для локальної розробки не використовуйте `docker-compose.prod.yml`
- Весь production storage лежить під `${PMM_DATA_ROOT}`; це зручно для backup, переносу і ручного огляду файлів
- Якщо змінюються Python або Node dependencies, потрібен rebuild image
- `frontend_node_modules` — dev-only volume; його можна безпечно видаляти при проблемах з локальним frontend
- update subsystem у production залишився окремою production-функцією і не тягнеться в dev workflow

## Міграція зі старих Docker volumes

Якщо production вже працював на named volumes, спочатку перенесіть дані в `${PMM_DATA_ROOT}`:

```bash
sudo ./scripts/migrate-prod-data-to-host.sh pmm-pmm-uy3fkl /opt/pmm-data
```

де `pmm-pmm-uy3fkl` — Dokploy compose project name.

## Мінімальний operational workflow

### Dev

```bash
make dev-up
make dev-logs
make dev-down
```

### Prod

```bash
make prod-up
make prod-migrate
make prod-logs
```

### Safe update

```bash
make prod-build
make prod-migrate
make prod-rebuild
```

## Hardening next steps

- винести production ingress/TLS у зовнішній reverse proxy або platform ingress
- додати зовнішній offsite backup для `db_data` і `backend_backups`
- налаштувати централізований log shipping
- додати image scanning і CI-перевірку compose/build
- перевірити production resource limits (`deploy.resources` або platform-level limits)
