SHELL := /bin/sh

DEV_COMPOSE := docker compose --env-file .env.dev -f docker-compose.yml -f docker-compose.dev.yml
PROD_COMPOSE := docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml

.PHONY: \
	help \
	check check-backend check-frontend check-compose smoke \
	dev-up dev-build dev-down dev-logs dev-migrate dev-rebuild dev-admin \
	prod-up prod-build prod-down prod-logs prod-migrate prod-rebuild prod-backup

help:
	@echo "Environment commands:"
	@echo "  make dev-up        - start local development stack"
	@echo "  make dev-build     - build dev images"
	@echo "  make dev-down      - stop dev stack (keeps volumes)"
	@echo "  make dev-logs      - follow dev logs"
	@echo "  make dev-migrate   - run Alembic migrations in dev"
	@echo "  make dev-rebuild   - rebuild and restart dev stack"
	@echo "  make dev-admin     - create first admin in dev"
	@echo "  make prod-up       - start production stack"
	@echo "  make prod-build    - build production images"
	@echo "  make prod-down     - stop prod stack (keeps volumes)"
	@echo "  make prod-logs     - follow prod logs"
	@echo "  make prod-migrate  - run Alembic migrations in prod"
	@echo "  make prod-rebuild  - rebuild and restart prod stack"
	@echo "  make prod-backup   - create database backup in prod"
	@echo "  make check         - syntax/build/compose validation"
	@echo "  make smoke         - run smoke checks"

check: check-backend check-frontend check-compose

check-backend:
	python3 -m compileall backend/app >/dev/null

check-frontend:
	@if command -v npm >/dev/null 2>&1; then \
		cd frontend && npm run build; \
	else \
		$(DEV_COMPOSE) run --rm --no-deps frontend npm run build; \
	fi

check-compose:
	$(DEV_COMPOSE) config >/dev/null
	$(PROD_COMPOSE) config >/dev/null

smoke:
	./scripts/smoke-checks.sh

dev-up:
	$(DEV_COMPOSE) up -d

dev-build:
	$(DEV_COMPOSE) build

dev-down:
	$(DEV_COMPOSE) down

dev-logs:
	$(DEV_COMPOSE) logs -f --tail=100

dev-migrate:
	$(DEV_COMPOSE) run --rm migrate

dev-rebuild:
	$(DEV_COMPOSE) up -d --build

dev-admin:
	$(DEV_COMPOSE) run --rm \
		-e FIRST_ADMIN_LOGIN=admin \
		-e FIRST_ADMIN_PASSWORD=ChangeMe_Strong_123 \
		-e FIRST_ADMIN_FULL_NAME=System\ Admin \
		backend python -m app.cli create-first-admin

prod-up:
	$(PROD_COMPOSE) up -d

prod-build:
	$(PROD_COMPOSE) build

prod-down:
	$(PROD_COMPOSE) down

prod-logs:
	$(PROD_COMPOSE) logs -f --tail=100

prod-migrate:
	$(PROD_COMPOSE) run --rm migrate

prod-rebuild:
	$(PROD_COMPOSE) up -d --build

prod-backup:
	$(PROD_COMPOSE) exec backend python -c "from app.services import backup_service; print(backup_service.create_backup())"
