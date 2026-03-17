# PMM Online MVP

Веб-система учёта паливно-мастильных материалов (ПММ): заявки подразделений, склад, выдача оператором, отчётность и админ-настройки.

## Что это
- `frontend`: React + Vite + TypeScript UI.
- `backend`: FastAPI + SQLAlchemy + Alembic API.
- `db`: PostgreSQL.

## Технологии
- Frontend: React 19, Vite 7, TypeScript 5, TailwindCSS 4.
- Backend: Python 3.13+, FastAPI, SQLAlchemy 2, Pydantic 2.
- Database: PostgreSQL 15.
- Migrations: Alembic.
- Dev: Docker Compose, npm, pip.

## Структура проекта
- `frontend/` — клиентское приложение.
- `backend/app/` — API, бизнес-логика, модели, схемы.
- `backend/alembic/` — миграции БД.
- `docs/` — дополнительная документация.
- `docker-compose.yml` — локальный запуск.
- `docker-compose.prod.yml` — production-стек.

## Требования
- Python `3.13+`.
- Node.js `20+` (рекомендуется LTS).
- npm `10+`.
- PostgreSQL `15+` (или через Docker).
- Docker + Docker Compose (для контейнерного запуска).

## Быстрый запуск (Docker)
1. Клонировать репозиторий:
```bash
git clone <your-repo-url>
cd <repo-folder>
```
2. Подготовить env:
```bash
cp .env.example .env
# заполните минимум: JWT_SECRET
```
3. Применить миграции:
```bash
docker compose run --rm migrator
```
4. Создать первого администратора (один раз):
```bash
docker compose run --rm \
  -e FIRST_ADMIN_LOGIN=admin \
  -e FIRST_ADMIN_PASSWORD='ChangeMe_Strong_123' \
  -e FIRST_ADMIN_FULL_NAME='System Admin' \
  backend python -m app.cli create-first-admin
```
5. Запустить сервисы:
```bash
docker compose up --build
```

Доступ:
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

## Локальный запуск без Docker
1. Backend env:
```bash
cp .env.backend.example .env
```
2. Установить backend-зависимости:
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m app.cli create-first-admin --login admin --password 'ChangeMe_Strong_123' --full-name 'System Admin'
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
3. Frontend:
```bash
cd ../frontend
npm install
npm run dev
```

## Переменные окружения
- Общие шаблоны:
- `.env.example` — для `docker-compose.yml`.
- `.env.prod.example` — для `docker-compose.prod.yml`.
- `.env.backend.example` — backend standalone.
- `.env.frontend.example` — frontend standalone.

Критически обязательные:
- `DATABASE_URL`
- `JWT_SECRET` (минимум 32 символа)

Для первого администратора (только первичная инициализация):
- `FIRST_ADMIN_LOGIN`
- `FIRST_ADMIN_PASSWORD`
- `FIRST_ADMIN_FULL_NAME`

## Команды разработки
- Frontend dev: `cd frontend && npm run dev`
- Frontend build: `cd frontend && npm run build`
- Backend dev: `cd backend && uvicorn app.main:app --reload`
- Миграции: `cd backend && alembic upgrade head`
- Smoke tests: `cd backend && pytest -q`
- Создать первого админа: `cd backend && python -m app.cli create-first-admin --login ... --password ...`

## Первый запуск: создание первого администратора
Реализовано через CLI-команду `python -m app.cli create-first-admin`.

Свойства безопасности:
- Администратор не создаётся автоматически при каждом старте backend.
- Команда создаёт admin только если в системе ещё нет ни одного ADMIN.
- При наличии ADMIN повторный запуск не создаёт дубликаты.
- Дефолтный пароль в коде отсутствует.

## Что не хранится в репозитории
- `.env` и любые секреты.
- `node_modules`, `dist`, `build`, `.vite`.
- Python cache/coverage артефакты.
- Локальные БД/логи/временные файлы.
- IDE и OS мусор.

## Статус проекта
`MVP`, активная разработка.
