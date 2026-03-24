#!/usr/bin/env sh
set -eu

ARTIFACTS_DIR="${ARTIFACTS_DIR:-/var/lib/pmm/artifacts}"
BACKUP_DIR="${BACKUP_DIR:-/var/lib/pmm/backups}"
POSTING_ERROR_LOG_PATH="${POSTING_ERROR_LOG_PATH:-/var/log/pmm/posting_errors.log}"
LOG_DIR="$(dirname "${POSTING_ERROR_LOG_PATH}")"
BACKEND_WORKERS="${BACKEND_WORKERS:-3}"
DATABASE_URL="${DATABASE_URL:-}"
DB_READY_MAX_ATTEMPTS="${DB_READY_MAX_ATTEMPTS:-30}"
DB_READY_SLEEP_SECONDS="${DB_READY_SLEEP_SECONDS:-2}"

ensure_writable_dir() {
  dir_path="$1"
  mkdir -p "${dir_path}" || true
  if [ ! -d "${dir_path}" ]; then
    echo "[prod-entrypoint] directory does not exist: ${dir_path}" >&2
    exit 1
  fi
  if [ ! -w "${dir_path}" ]; then
    echo "[prod-entrypoint] directory is not writable by current user: ${dir_path}" >&2
    exit 1
  fi
}

ensure_writable_dir "${ARTIFACTS_DIR}"
ensure_writable_dir "${BACKUP_DIR}"
ensure_writable_dir "${LOG_DIR}"

if [ -z "${DATABASE_URL}" ]; then
  echo "[prod-entrypoint] DATABASE_URL is required" >&2
  exit 1
fi

echo "[prod-entrypoint] waiting for database readiness"
attempt=1
while [ "${attempt}" -le "${DB_READY_MAX_ATTEMPTS}" ]; do
  if pg_isready -d "${DATABASE_URL}" >/dev/null 2>&1; then
    break
  fi
  if [ "${attempt}" -eq "${DB_READY_MAX_ATTEMPTS}" ]; then
    echo "[prod-entrypoint] database is not ready after ${DB_READY_MAX_ATTEMPTS} attempts" >&2
    exit 1
  fi
  sleep "${DB_READY_SLEEP_SECONDS}"
  attempt=$((attempt + 1))
done

echo "[prod-entrypoint] applying database migrations"
alembic upgrade head

exec gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  -w "${BACKEND_WORKERS}" \
  -b 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
