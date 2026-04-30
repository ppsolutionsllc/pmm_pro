#!/usr/bin/env sh
set -eu

PROJECT_NAME="${1:-}"
COMPOSE_FILE="${2:-docker-compose.prod.yml}"

if [ -z "${PROJECT_NAME}" ]; then
  echo "Usage: $0 <compose-project-name> [compose-file]" >&2
  exit 1
fi

COMPOSE_CMD="docker compose -p ${PROJECT_NAME} -f ${COMPOSE_FILE}"

echo "[1/5] Service status"
sh -c "${COMPOSE_CMD} ps"

echo "[2/5] Backend readiness"
sh -c "${COMPOSE_CMD} exec -T backend /app/scripts/healthcheck-ready.sh"

echo "[3/5] Frontend health"
sh -c "${COMPOSE_CMD} exec -T frontend sh -lc 'wget -qO- http://127.0.0.1/health'"

echo "[4/5] Frontend shell page"
sh -c "${COMPOSE_CMD} exec -T frontend sh -lc 'wget -qO- http://127.0.0.1/ | head -n 3'"

echo "[5/5] Frontend proxied backend readiness"
sh -c "${COMPOSE_CMD} exec -T frontend sh -lc 'wget -qO- http://127.0.0.1/ready'"

echo "Production post-deploy checks completed."
