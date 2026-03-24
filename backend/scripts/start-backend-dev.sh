#!/usr/bin/env sh
set -eu

ARTIFACTS_DIR="${ARTIFACTS_DIR:-/var/lib/pmm/artifacts}"
BACKUP_DIR="${BACKUP_DIR:-/var/lib/pmm/backups}"
POSTING_ERROR_LOG_PATH="${POSTING_ERROR_LOG_PATH:-/var/log/pmm/posting_errors.log}"
LOG_DIR="$(dirname "${POSTING_ERROR_LOG_PATH}")"

ensure_writable_dir() {
  dir_path="$1"
  mkdir -p "${dir_path}"
  if [ ! -d "${dir_path}" ]; then
    echo "[dev-entrypoint] directory does not exist: ${dir_path}" >&2
    exit 1
  fi
}

ensure_writable_dir "${ARTIFACTS_DIR}"
ensure_writable_dir "${BACKUP_DIR}"
ensure_writable_dir "${LOG_DIR}"

echo "[dev-entrypoint] applying database migrations"
alembic upgrade head

exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload \
  --reload-dir /app/app \
  --reload-dir /app/alembic
