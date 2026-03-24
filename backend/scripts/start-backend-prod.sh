#!/usr/bin/env sh
set -eu

ARTIFACTS_DIR="${ARTIFACTS_DIR:-/var/lib/pmm/artifacts}"
BACKUP_DIR="${BACKUP_DIR:-/var/lib/pmm/backups}"
POSTING_ERROR_LOG_PATH="${POSTING_ERROR_LOG_PATH:-/var/log/pmm/posting_errors.log}"
LOG_DIR="$(dirname "${POSTING_ERROR_LOG_PATH}")"
BACKEND_WORKERS="${BACKEND_WORKERS:-3}"

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

exec gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  -w "${BACKEND_WORKERS}" \
  -b 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
