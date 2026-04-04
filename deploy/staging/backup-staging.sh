#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# TG PRO QUANTUM – Staging Backup Script
# Backs up PostgreSQL, Redis, and configuration files.
# Usage: ./backup-staging.sh [--no-upload]
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env.staging"
BACKUP_DIR="/tmp/tgpq_backup_$(date +%Y%m%d_%H%M%S)"
NO_UPLOAD=false

# ── Parse arguments ──────────────────────────────────────────────────────────
for arg in "$@"; do
    case $arg in
        --no-upload) NO_UPLOAD=true ;;
    esac
done

# ── Load environment ─────────────────────────────────────────────────────────
if [[ -f "${ENV_FILE}" ]]; then
    # shellcheck disable=SC2046
    export $(grep -v '^#' "${ENV_FILE}" | grep -v '^$' | xargs)
fi

log() { echo "[$(date '+%H:%M:%S')] $*"; }

log "=== TG PRO QUANTUM – Staging Backup ==="
log "Backup dir : ${BACKUP_DIR}"
echo ""

mkdir -p "${BACKUP_DIR}"

# ── Backup PostgreSQL ────────────────────────────────────────────────────────
log "[1/5] Backing up PostgreSQL..."
PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
    -h "${POSTGRES_HOST:-localhost}" \
    -p "${POSTGRES_PORT:-5433}" \
    -U "${POSTGRES_USER:-tgpq_staging}" \
    -d "${POSTGRES_DB:-tg_quantum_staging}" \
    --format=custom \
    --no-password \
    -f "${BACKUP_DIR}/postgres.dump"
log "  ✅ PostgreSQL backup: ${BACKUP_DIR}/postgres.dump"

# ── Backup Redis ─────────────────────────────────────────────────────────────
log "[2/5] Backing up Redis (BGSAVE)..."
REDIS_CLI_FLAGS=(-h "${REDIS_HOST:-localhost}" -p "${REDIS_PORT:-6380}")
[[ -n "${REDIS_PASSWORD:-}" ]] && REDIS_CLI_FLAGS+=(-a "${REDIS_PASSWORD}")
redis-cli "${REDIS_CLI_FLAGS[@]}" BGSAVE
sleep 3
docker cp "tgpq-staging-redis:/data/dump.rdb" "${BACKUP_DIR}/redis.rdb" 2>/dev/null \
    || log "  ⚠️  Could not copy Redis RDB (container may not be running)"
log "  ✅ Redis backup attempted"

# ── Backup configuration ─────────────────────────────────────────────────────
log "[3/5] Backing up configuration..."
tar -czf "${BACKUP_DIR}/config.tar.gz" \
    -C "${SCRIPT_DIR}" \
    --exclude=".env.staging" \
    --exclude="ssl/*.key" \
    . 2>/dev/null || true
log "  ✅ Configuration backup: ${BACKUP_DIR}/config.tar.gz"

# ── Compress all backups ─────────────────────────────────────────────────────
log "[4/5] Compressing backup archive..."
ARCHIVE="/tmp/tgpq_staging_backup_$(date +%Y%m%d_%H%M%S).tar.gz"
tar -czf "${ARCHIVE}" -C "$(dirname "${BACKUP_DIR}")" "$(basename "${BACKUP_DIR}")"
log "  ✅ Archive: ${ARCHIVE}"

# ── Upload to S3 ─────────────────────────────────────────────────────────────
if [[ "${NO_UPLOAD}" == "false" ]] && command -v aws >/dev/null 2>&1; then
    log "[5/5] Uploading to S3..."
    aws s3 cp "${ARCHIVE}" \
        "s3://${BACKUP_S3_BUCKET:-tgpq-staging-backups}/$(basename "${ARCHIVE}")" \
        --region "${BACKUP_S3_REGION:-ap-southeast-1}"
    log "  ✅ Uploaded to S3"

    # Clean up old backups
    log "  Cleaning up backups older than ${BACKUP_RETENTION_DAYS:-7} days..."
    aws s3 ls "s3://${BACKUP_S3_BUCKET:-tgpq-staging-backups}/" \
        | awk '{print $4}' \
        | head -n -"${BACKUP_RETENTION_DAYS:-7}" \
        | xargs -I{} aws s3 rm "s3://${BACKUP_S3_BUCKET:-tgpq-staging-backups}/{}" 2>/dev/null || true
else
    log "[5/5] S3 upload skipped (--no-upload or aws CLI not available)"
fi

# ── Cleanup temp dir ─────────────────────────────────────────────────────────
rm -rf "${BACKUP_DIR}"

echo ""
log "=== Backup complete ✅ ==="
log "Archive : ${ARCHIVE}"
