#!/usr/bin/env sh
set -eu

DATA_ROOT="${1:-/opt/pmm-data}"
BACKEND_UID="${BACKEND_UID:-10001}"
BACKEND_GID="${BACKEND_GID:-10001}"

mkdir -p "${DATA_ROOT}/postgres" "${DATA_ROOT}/artifacts" "${DATA_ROOT}/backups" "${DATA_ROOT}/logs"

# PostgreSQL official image can adjust ownership on startup if needed.
chmod 700 "${DATA_ROOT}/postgres"

chown -R "${BACKEND_UID}:${BACKEND_GID}" "${DATA_ROOT}/artifacts" "${DATA_ROOT}/backups" "${DATA_ROOT}/logs"
chmod 775 "${DATA_ROOT}/artifacts" "${DATA_ROOT}/backups" "${DATA_ROOT}/logs"

echo "Prepared production data root at ${DATA_ROOT}"
