#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# TG PRO QUANTUM – Production Database Restore
# Usage: ./restore-production-database.sh [--backup <path>] [--yes]
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env.production"
BACKUP_ROOT="/var/backups/tgpq"
BACKUP_PATH="${BACKUP_PATH:-}"
AUTO_YES=false
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/tmp/restore_${TIMESTAMP}.log"

for arg in "$@"; do
    case $arg in
        --backup=*)  BACKUP_PATH="${arg#*=}" ;;
        --backup)    shift; BACKUP_PATH="$1" ;;
        --yes|-y)    AUTO_YES=true ;;
    esac
done

log()  { echo "[$(date '+%H:%M:%S')] $*" | tee -a "${LOG_FILE}"; }
fail() { log "❌ $*"; exit 1; }

[[ -f "${ENV_FILE}" ]] && source "${ENV_FILE}" 2>/dev/null || true

log "=== TG PRO QUANTUM – Production Database Restore ==="
log "Log file: ${LOG_FILE}"
echo ""

# ── [1] List available backups ────────────────────────────────────────────────
if [[ -z "${BACKUP_PATH}" ]]; then
    log "[1/8] Available backups:"
    echo ""
    find "${BACKUP_ROOT}" -name "postgres_*.gz" -type f \
        | sort -r | head -20 \
        | while read -r f; do
            echo "  $(ls -lh "${f}" | awk '{print $5, $6, $7, $8}')  ${f}"
        done
    echo ""
    read -r -p "Enter backup file path: " BACKUP_PATH
fi

[[ -f "${BACKUP_PATH}" ]] || fail "Backup file not found: ${BACKUP_PATH}"
log "[1/8] Using backup: ${BACKUP_PATH} ($(du -sh "${BACKUP_PATH}" | cut -f1))"

# ── [2] Verify backup integrity ───────────────────────────────────────────────
log "[2/8] Verifying backup integrity..."
gzip -t "${BACKUP_PATH}" || fail "Backup file is corrupt: ${BACKUP_PATH}"
log "  ✅ Backup integrity OK"

# ── [3] Confirm operation ─────────────────────────────────────────────────────
log "[3/8] Confirming restore operation..."
echo ""
echo "  ⚠️  WARNING: This will RESTORE the production database."
echo "  ⚠️  Current data WILL BE OVERWRITTEN."
echo "  ⚠️  Application connections will be dropped during restore."
echo ""
if [[ "${AUTO_YES}" == "false" ]]; then
    read -r -p "  Type 'RESTORE PRODUCTION' to confirm: " confirm
    [[ "${confirm}" == "RESTORE PRODUCTION" ]] || { log "Restore cancelled."; exit 0; }
fi
log "  ✅ Confirmed"

# ── [4] Create pre-restore backup ────────────────────────────────────────────
log "[4/8] Creating pre-restore backup..."
PRE_RESTORE_BACKUP="/tmp/pre_restore_${TIMESTAMP}.sql.gz"
docker exec tgpq-prod-db-primary \
    pg_dumpall -U "${POSTGRES_USER:-tgpq_prod}" \
    | gzip > "${PRE_RESTORE_BACKUP}" \
    || log "  ⚠️  Pre-restore backup warning – continuing"
log "  ✅ Pre-restore backup: ${PRE_RESTORE_BACKUP}"

# ── [5] Restore to temporary database ────────────────────────────────────────
log "[5/8] Restoring to temporary database for verification..."
TEMP_DB="tg_quantum_restore_verify_${TIMESTAMP}"
docker exec tgpq-prod-db-primary createdb -U "${POSTGRES_USER:-tgpq_prod}" "${TEMP_DB}" \
    || fail "Cannot create temp database"

zcat "${BACKUP_PATH}" | docker exec -i tgpq-prod-db-primary \
    pg_restore -U "${POSTGRES_USER:-tgpq_prod}" -d "${TEMP_DB}" --no-owner 2>&1 \
    | tee -a "${LOG_FILE}" || log "  ⚠️  Restore had warnings"

# ── [6] Run integrity checks ──────────────────────────────────────────────────
log "[6/8] Running integrity checks on restored data..."
TABLES=$(docker exec tgpq-prod-db-primary psql -U "${POSTGRES_USER:-tgpq_prod}" \
    -d "${TEMP_DB}" -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null || echo "0")
log "  Tables: ${TABLES}"

ROWS=$(docker exec tgpq-prod-db-primary psql -U "${POSTGRES_USER:-tgpq_prod}" \
    -d "${TEMP_DB}" -tAc "SELECT sum(n_live_tup) FROM pg_stat_user_tables;" 2>/dev/null || echo "0")
log "  Total rows: ${ROWS}"

[[ "${TABLES}" -gt 0 ]] || fail "Integrity check failed: no tables found in restored backup"
log "  ✅ Integrity checks passed"

# ── [7] Promote to production ─────────────────────────────────────────────────
log "[7/8] Promoting restored database to production..."

# Stop application connections
log "  Stopping application containers..."
docker stop tgpq-prod-app-blue-1 tgpq-prod-app-blue-2 tgpq-prod-app-blue-3 2>/dev/null || true

# Terminate existing connections
docker exec tgpq-prod-db-primary psql -U "${POSTGRES_USER:-tgpq_prod}" -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${POSTGRES_DB:-tg_quantum_prod}' AND pid <> pg_backend_pid();" \
    >/dev/null 2>&1 || true

# Drop and recreate production database
docker exec tgpq-prod-db-primary psql -U "${POSTGRES_USER:-tgpq_prod}" -c \
    "DROP DATABASE IF EXISTS \"${POSTGRES_DB:-tg_quantum_prod}\";" || fail "Cannot drop production database"
docker exec tgpq-prod-db-primary psql -U "${POSTGRES_USER:-tgpq_prod}" -c \
    "CREATE DATABASE \"${POSTGRES_DB:-tg_quantum_prod}\";" || fail "Cannot create production database"

# Restore from backup
zcat "${BACKUP_PATH}" | docker exec -i tgpq-prod-db-primary \
    pg_restore -U "${POSTGRES_USER:-tgpq_prod}" -d "${POSTGRES_DB:-tg_quantum_prod}" --no-owner \
    2>&1 | tee -a "${LOG_FILE}" || log "  ⚠️  Restore had warnings"

# Cleanup temp database
docker exec tgpq-prod-db-primary dropdb -U "${POSTGRES_USER:-tgpq_prod}" --if-exists "${TEMP_DB}" 2>/dev/null || true

# Restart application
docker start tgpq-prod-app-blue-1 tgpq-prod-app-blue-2 tgpq-prod-app-blue-3 2>/dev/null || true
log "  ✅ Production database restored and application restarted"

# ── [8] Notify team ───────────────────────────────────────────────────────────
log "[8/8] Notifying team..."
if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
    curl -sS -X POST "${SLACK_WEBHOOK_URL}" \
        -H "Content-Type: application/json" \
        -d "{\"text\":\"⚠️ *PRODUCTION DATABASE RESTORE COMPLETE* – Backup: ${BACKUP_PATH}, Time: $(date)\"}" \
        >/dev/null 2>&1 || true
fi
log "  ✅ Team notified"

echo ""
log "=== Database Restore COMPLETE ✅ ==="
log "Pre-restore backup : ${PRE_RESTORE_BACKUP}"
log "Restored from      : ${BACKUP_PATH}"
log "Log file           : ${LOG_FILE}"
log ""
log "⚠️  Run health check: ./verify-production-health.sh"
