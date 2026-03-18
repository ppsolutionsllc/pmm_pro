#!/usr/bin/env sh
set -eu

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "[entrypoint] applying database migrations"
  alembic upgrade head
fi

BACKEND_WORKERS="${BACKEND_WORKERS:-3}"

exec gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  -w "${BACKEND_WORKERS}" \
  -b 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
