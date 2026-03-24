#!/usr/bin/env sh
set -eu

DEV_COMPOSE="docker compose --env-file .env.dev -f docker-compose.yml -f docker-compose.dev.yml"
PROD_COMPOSE="docker compose --env-file .env.prod -f docker-compose.prod.yml"

echo "[1/4] Python syntax check (backend/app)"
python3 -m compileall backend/app >/dev/null

echo "[2/4] Frontend production build"
if command -v npm >/dev/null 2>&1; then
  (cd frontend && npm run build >/dev/null)
else
  sh -c "$DEV_COMPOSE run --rm --no-deps frontend npm run build >/dev/null"
fi

echo "[3/4] Compose validation (base+dev / standalone prod)"
sh -c "$DEV_COMPOSE config >/dev/null"
sh -c "$PROD_COMPOSE config >/dev/null"

echo "[4/4] Backend smoke test (optional, requires TEST_DATABASE_URL)"
if [ -n "${TEST_DATABASE_URL:-}" ]; then
  (cd backend && pytest -q)
else
  echo "TEST_DATABASE_URL is not set, skipping backend pytest smoke tests."
fi

echo "Smoke checks completed."
