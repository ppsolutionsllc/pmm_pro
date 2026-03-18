SHELL := /bin/sh

.PHONY: help check check-backend check-frontend check-compose smoke

help:
	@echo "Targets:"
	@echo "  make check          - run backend syntax, frontend build, compose config checks"
	@echo "  make check-backend  - python compileall for backend code"
	@echo "  make check-frontend - frontend production build"
	@echo "  make check-compose  - validate docker compose files"
	@echo "  make smoke          - run scripts/smoke-checks.sh"

check: check-backend check-frontend check-compose

check-backend:
	python3 -m compileall backend/app >/dev/null

check-frontend:
	@if command -v npm >/dev/null 2>&1; then \
		cd frontend && npm run build; \
	else \
		JWT_SECRET=check-secret-key-with-at-least-32-characters docker compose run --rm --no-deps frontend npm run build; \
	fi

check-compose:
	JWT_SECRET=check-secret-key-with-at-least-32-characters docker compose -f docker-compose.yml config >/dev/null
	POSTGRES_PASSWORD=check-password JWT_SECRET=check-secret-key-with-at-least-32-characters UPDATE_GITHUB_REPO=org/repo docker compose -f docker-compose.prod.yml config >/dev/null
	POSTGRES_PASSWORD=check-password JWT_SECRET=check-secret-key-with-at-least-32-characters CORS_ORIGINS=https://example.com FRONTEND_BASE_URL=https://example.com docker compose -f docker-compose.coolify.yml config >/dev/null

smoke:
	./scripts/smoke-checks.sh
