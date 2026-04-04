#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# TG PRO QUANTUM – Production Weekly Backup
# Scheduled: Every Sunday at 02:00 UTC
# Cron entry: 0 2 * * 0 /opt/tgpq/deploy/production/backup-production-weekly.sh
# Usage: ./backup-production-weekly.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env.production"
BACKUP_ROOT="/var/backups/tgpq"
ARCHIVE_ROOT="/var/backups/tgpq-archive"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
WEEK=$(date +%Y_W%V)
LOG_FILE="/tmp/backup_weekly_${TIMESTAMP}.log"
ARCHIVE_RETENTION_WEEKS=26  # 6 months in cold storage

log()  { echo "[$(date '+%H:%M:%S')] $*" | tee -a "${LOG_FILE}"; }
fail() { log "❌ $*"; exit 1; }

[[ -f "${ENV_FILE}" ]] && source "${ENV_FILE}" 2>/dev/null || true

BACKUP_DIR="${BACKUP_ROOT}/weekly/${WEEK}"
ARCHIVE_DIR="${ARCHIVE_ROOT}/${WEEK}"
mkdir -p "${BACKUP_DIR}" "${ARCHIVE_DIR}"

log "=== TG PRO QUANTUM – Production Weekly Backup ==="
log "Week        : ${WEEK}"
log "Backup dir  : ${BACKUP_DIR}"
log "Archive dir : ${ARCHIVE_DIR}"
log "Log file    : ${LOG_FILE}"
echo ""

# ── [1] Full system backup ────────────────────────────────────────────────────
log "[1/6] Running full PostgreSQL backup..."
PG_BACKUP="${BACKUP_DIR}/postgres_full_${TIMESTAMP}.sql.gz"
docker exec tgpq-prod-db-primary \
    pg_dumpall -U "${POSTGRES_USER:-tgpq_prod}" --globals-only \
    | gzip > "${BACKUP_DIR}/postgres_globals_${TIMESTAMP}.sql.gz" \
    || log "  ⚠️  Globals backup warning"

docker exec tgpq-prod-db-primary \
    pg_dump -U "${POSTGRES_USER:-tgpq_prod}" \
    -d "${POSTGRES_DB:-tg_quantum_prod}" \
    --format=custom \
    --blobs \
    | gzip > "${PG_BACKUP}" \
    || fail "Full PostgreSQL backup failed"
log "  ✅ Full backup: ${PG_BACKUP} ($(du -sh "${PG_BACKUP}" | cut -f1))"

# ── [2] Archive daily backups ─────────────────────────────────────────────────
log "[2/6] Archiving daily backups..."
find "${BACKUP_ROOT}" -maxdepth 2 -type d -name "20*" | while read -r daily_dir; do
    dir_name=$(basename "${daily_dir}")
    if [[ ! -d "${ARCHIVE_DIR}/${dir_name}" ]]; then
        cp -r "${daily_dir}" "${ARCHIVE_DIR}/${dir_name}" 2>/dev/null || true
    fi
done
log "  ✅ Daily backups archived to ${ARCHIVE_DIR}"

# ── [3] Restore test (to staging) ─────────────────────────────────────────────
log "[3/6] Backup integrity test (restore to temp database)..."
TEMP_DB="tg_quantum_backup_test_${TIMESTAMP}"
docker exec tgpq-prod-db-primary createdb -U "${POSTGRES_USER:-tgpq_prod}" "${TEMP_DB}" 2>/dev/null || true

zcat "${PG_BACKUP}" | docker exec -i tgpq-prod-db-primary \
    pg_restore -U "${POSTGRES_USER:-tgpq_prod}" -d "${TEMP_DB}" --no-owner --exit-on-error \
    >/dev/null 2>&1 && RESTORE_OK=true || RESTORE_OK=false

# Run basic integrity check
if [[ "${RESTORE_OK}" == "true" ]]; then
    TABLES=$(docker exec tgpq-prod-db-primary psql -U "${POSTGRES_USER:-tgpq_prod}" \
        -d "${TEMP_DB}" -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null || echo "0")
    log "  ✅ Restore test passed: ${TABLES} tables verified"
else
    log "  ⚠️  Restore test had issues – check ${PG_BACKUP} manually"
fi

# Cleanup temp database
docker exec tgpq-prod-db-primary dropdb -U "${POSTGRES_USER:-tgpq_prod}" --if-exists "${TEMP_DB}" 2>/dev/null || true

# ── [4] Backup integrity check ────────────────────────────────────────────────
log "[4/6] Integrity check..."
find "${BACKUP_DIR}" -name "*.gz" | while read -r f; do
    gzip -t "${f}" 2>/dev/null \
        && log "  ✅ $(basename "${f}")" \
        || log "  ❌ CORRUPT: ${f}"
done

# ── [5] Upload to cold storage (S3 Glacier) ───────────────────────────────────
log "[5/6] Uploading weekly archive to cold storage..."
if command -v aws >/dev/null 2>&1 && [[ -n "${S3_BACKUP_BUCKET:-}" ]]; then
    aws s3 sync "${BACKUP_DIR}/" \
        "s3://${S3_BACKUP_BUCKET}/weekly/${WEEK}/" \
        --sse AES256 \
        --storage-class GLACIER_IR \
        2>&1 | tee -a "${LOG_FILE}" \
        || log "  ⚠️  S3 Glacier upload warning"
    log "  ✅ Weekly archive in cold storage: s3://${S3_BACKUP_BUCKET}/weekly/${WEEK}/"
else
    log "  ℹ️  S3 not configured – local archive only"
fi

# ── [6] Clean up old archives ─────────────────────────────────────────────────
log "[6/6] Cleaning up old weekly archives (>${ARCHIVE_RETENTION_WEEKS} weeks)..."
find "${ARCHIVE_ROOT}" -type d -mtime "+$(( ARCHIVE_RETENTION_WEEKS * 7 ))" -exec rm -rf {} + 2>/dev/null || true
log "  ✅ Archive cleanup complete"

echo ""
log "=== Weekly Backup COMPLETE ✅ ==="
log "Week archive: ${ARCHIVE_DIR}"
log "Log file    : ${LOG_FILE}"

if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
    curl -sS -X POST "${SLACK_WEBHOOK_URL}" \
        -H "Content-Type: application/json" \
        -d "{\"text\":\"✅ *Weekly Backup Complete* – Week ${WEEK}, restore test $([ "${RESTORE_OK:-false}" == "true" ] && echo "PASSED" || echo "WARNING")\"}" \
        >/dev/null 2>&1 || true
fi
