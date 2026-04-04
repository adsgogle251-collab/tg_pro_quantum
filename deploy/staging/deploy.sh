#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# TG PRO QUANTUM – Staging Deployment Script
# Usage: ./deploy.sh [--skip-tests] [--image-tag <tag>]
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env.staging"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.staging.yml"
IMAGE_TAG="${IMAGE_TAG:-latest}"
SKIP_TESTS=false
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/tmp/deploy_${TIMESTAMP}.log"

# ── Parse arguments ──────────────────────────────────────────────────────────
for arg in "$@"; do
    case $arg in
        --skip-tests)          SKIP_TESTS=true ;;
        --image-tag)           shift; IMAGE_TAG="$1" ;;
        --image-tag=*)         IMAGE_TAG="${arg#*=}" ;;
    esac
done

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "${LOG_FILE}"; }
fail() { log "❌ $*"; exit 1; }

log "=== TG PRO QUANTUM – Staging Deployment ==="
log "Image tag  : ${IMAGE_TAG}"
log "Skip tests : ${SKIP_TESTS}"
log "Log file   : ${LOG_FILE}"
echo ""

# ── Pre-deployment checks ────────────────────────────────────────────────────
log "[1/8] Pre-deployment checks..."
[[ -f "${ENV_FILE}" ]]     || fail "Missing ${ENV_FILE}"
[[ -f "${COMPOSE_FILE}" ]] || fail "Missing ${COMPOSE_FILE}"
command -v docker          >/dev/null || fail "docker not found"
command -v docker compose  >/dev/null 2>&1 || \
    command -v docker-compose >/dev/null   || fail "docker compose not found"
log "  ✅ Pre-flight checks passed"

# ── Pull latest code ─────────────────────────────────────────────────────────
log "[2/8] Pulling latest code..."
cd "${PROJECT_ROOT}"
git fetch origin
git status
log "  ✅ Code up to date"

# ── Build Docker images ──────────────────────────────────────────────────────
log "[3/8] Building Docker images..."
docker compose \
    --env-file "${ENV_FILE}" \
    -f "${COMPOSE_FILE}" \
    build --no-cache --parallel
log "  ✅ Images built"

# ── Run database migrations ──────────────────────────────────────────────────
log "[4/8] Running database migrations..."
"${SCRIPT_DIR}/migrate-staging.sh" || fail "Migration failed"
log "  ✅ Migrations applied"

# ── Start services ───────────────────────────────────────────────────────────
log "[5/8] Starting services..."
docker compose \
    --env-file "${ENV_FILE}" \
    -f "${COMPOSE_FILE}" \
    up -d --remove-orphans
log "  ✅ Services started"

# ── Wait for healthy state ───────────────────────────────────────────────────
log "[6/8] Waiting for services to become healthy..."
MAX_WAIT=120
ELAPSED=0
while true; do
    UNHEALTHY=$(docker compose \
        --env-file "${ENV_FILE}" \
        -f "${COMPOSE_FILE}" \
        ps --format json 2>/dev/null \
        | python3 -c "
import sys, json
containers = [json.loads(l) for l in sys.stdin if l.strip()]
unhealthy = [c.get('Name','?') for c in containers if c.get('Health','') not in ('healthy','')]
print(len(unhealthy))
" 2>/dev/null || echo "0")
    [[ "${UNHEALTHY}" -eq 0 ]] && break
    [[ "${ELAPSED}" -ge "${MAX_WAIT}" ]] && fail "Services did not become healthy in ${MAX_WAIT}s"
    sleep 5
    ELAPSED=$((ELAPSED + 5))
    log "  Waiting... (${ELAPSED}s)"
done
log "  ✅ All services healthy"

# ── Run health checks ────────────────────────────────────────────────────────
log "[7/8] Running health checks..."
"${SCRIPT_DIR}/health-check.sh" || fail "Health checks failed"
log "  ✅ Health checks passed"

# ── Smoke tests ──────────────────────────────────────────────────────────────
if [[ "${SKIP_TESTS}" == "false" ]]; then
    log "[8/8] Running smoke tests..."
    cd "${PROJECT_ROOT}"
    python3 -m pytest tests/smoke/ -v --timeout=30 2>&1 | tee -a "${LOG_FILE}" \
        || fail "Smoke tests failed"
    log "  ✅ Smoke tests passed"
else
    log "[8/8] Smoke tests skipped (--skip-tests)"
fi

echo ""
log "=== Deployment complete ✅ ==="
log "Staging URL : https://api-staging.tg-pro-quantum.app"
log "Docs        : https://api-staging.tg-pro-quantum.app/docs"
log "Health      : https://api-staging.tg-pro-quantum.app/health"
log "Grafana     : https://monitoring-staging.tg-pro-quantum.app"
log "Log file    : ${LOG_FILE}"
