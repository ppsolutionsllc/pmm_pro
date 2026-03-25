#!/usr/bin/env sh
set -eu

PROJECT_NAME="${1:?Usage: migrate-prod-data-to-host.sh <compose-project-name> [data-root]}"
DATA_ROOT="${2:-/opt/pmm-data}"

"$(dirname "$0")/prepare-prod-data-root.sh" "${DATA_ROOT}"

copy_volume() {
  volume_name="$1"
  target_dir="$2"

  if ! docker volume inspect "${volume_name}" >/dev/null 2>&1; then
    echo "Skipping missing volume: ${volume_name}"
    return 0
  fi

  echo "Copying ${volume_name} -> ${target_dir}"
  docker run --rm \
    -v "${volume_name}:/from:ro" \
    -v "${target_dir}:/to" \
    alpine:3.20 \
    sh -c 'cd /from && cp -a . /to/'
}

copy_volume "${PROJECT_NAME}_db_data" "${DATA_ROOT}/postgres"
copy_volume "${PROJECT_NAME}_backend_artifacts" "${DATA_ROOT}/artifacts"
copy_volume "${PROJECT_NAME}_backend_backups" "${DATA_ROOT}/backups"
copy_volume "${PROJECT_NAME}_backend_logs" "${DATA_ROOT}/logs"

echo "Data migration completed into ${DATA_ROOT}"
