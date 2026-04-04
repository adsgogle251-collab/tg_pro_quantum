#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# TG PRO QUANTUM – Staging Rollback Script
# Reverts to the previous Docker image tag.
# Usage: ./rollback.sh [--to-tag <tag>]
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env.staging"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.staging.yml"
ROLLBACK_TAG="${ROLLBACK_TAG:-previous}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/tmp/rollback_${TIMESTAMP}.log"

# ── Parse arguments ──────────────────────────────────────────────────────────
for arg in "$@"; do
    case $arg in
        --to-tag=*)  ROLLBACK_TAG="${arg#*=}" ;;
        --to-tag)    shift; ROLLBACK_TAG="$1" ;;
    esac
done

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "${LOG_FILE}"; }
fail() { log "❌ $*"; exit 1; }

log "=== TG PRO QUANTUM – Staging Rollback ==="
log "Rollback to : ${ROLLBACK_TAG}"
log "Log file    : ${LOG_FILE}"
echo ""

# ── Confirm rollback ─────────────────────────────────────────────────────────
read -r -p "⚠️  Rolling back staging to '${ROLLBACK_TAG}'. Continue? [y/N] " confirm
[[ "${confirm}" =~ ^[Yy]$ ]] || { log "Rollback cancelled."; exit 0; }

# ── Stop current services ────────────────────────────────────────────────────
log "[1/4] Stopping current services..."
docker compose \
    --env-file "${ENV_FILE}" \
    -f "${COMPOSE_FILE}" \
    down --remove-orphans
log "  ✅ Services stopped"

# ── Switch image tag ─────────────────────────────────────────────────────────
log "[2/4] Switching to image tag '${ROLLBACK_TAG}'..."
export IMAGE_TAG="${ROLLBACK_TAG}"
log "  ✅ Image tag set"

# ── Restart services ─────────────────────────────────────────────────────────
log "[3/4] Starting services with rollback image..."
docker compose \
    --env-file "${ENV_FILE}" \
    -f "${COMPOSE_FILE}" \
    up -d
log "  ✅ Services started"

# ── Verify rollback ──────────────────────────────────────────────────────────
log "[4/4] Verifying rollback..."
sleep 15
"${SCRIPT_DIR}/health-check.sh" || {
    log "⚠️  Health checks failed after rollback. Manual intervention required."
    exit 1
}
log "  ✅ Rollback verified successfully"

echo ""
log "=== Rollback complete ✅ ==="
log "Running tag : ${ROLLBACK_TAG}"
