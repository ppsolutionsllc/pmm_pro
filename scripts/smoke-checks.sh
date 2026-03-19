#!/usr/bin/env sh
set -eu

echo "[1/4] Python syntax check (backend/app)"
python3 -m compileall backend/app >/dev/null

echo "[2/4] Frontend production build"
if command -v npm >/dev/null 2>&1; then
  (cd frontend && npm run build >/dev/null)
else
  JWT_SECRET=check-secret-key-with-at-least-32-characters docker compose -f docker-compose.yml run --rm --no-deps --build frontend npm run build >/dev/null
fi

echo "[3/4] Compose validation (dev/prod/coolify)"
JWT_SECRET=check-secret-key-with-at-least-32-characters docker compose -f docker-compose.yml config >/dev/null
POSTGRES_PASSWORD=check-password JWT_SECRET=check-secret-key-with-at-least-32-characters CORS_ORIGINS=https://pmm.66br.pp.ua FRONTEND_BASE_URL=https://pmm.66br.pp.ua ALLOWED_HOSTS=pmm.66br.pp.ua DOMAIN=pmm.66br.pp.ua docker compose -f docker-compose.prod.yml config >/dev/null
POSTGRES_PASSWORD=check-password JWT_SECRET=check-secret-key-with-at-least-32-characters CORS_ORIGINS=https://pmm.66br.pp.ua FRONTEND_BASE_URL=https://pmm.66br.pp.ua ALLOWED_HOSTS=pmm.66br.pp.ua docker compose -f docker-compose.coolify.yml config >/dev/null

echo "[4/4] Backend smoke test (optional, requires TEST_DATABASE_URL)"
if [ -n "${TEST_DATABASE_URL:-}" ]; then
  (cd backend && pytest -q)
else
  echo "TEST_DATABASE_URL is not set, skipping backend pytest smoke tests."
fi

echo "Smoke checks completed."
