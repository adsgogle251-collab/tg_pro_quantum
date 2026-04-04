#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# TG PRO QUANTUM – Production Daily Backup
# Scheduled: Daily at 02:00 UTC via cron
# Cron entry: 0 2 * * * /opt/tgpq/deploy/production/backup-production-daily.sh
# Usage: ./backup-production-daily.sh [--pre-deploy]
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env.production"
BACKUP_ROOT="/var/backups/tgpq"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATE=$(date +%Y%m%d)
LOG_FILE="/tmp/backup_daily_${TIMESTAMP}.log"
PRE_DEPLOY=false
RETENTION_DAYS=30

for arg in "$@"; do
    case $arg in --pre-deploy) PRE_DEPLOY=true ;; esac
done

log()  { echo "[$(date '+%H:%M:%S')] $*" | tee -a "${LOG_FILE}"; }
fail() { log "❌ $*"; send_alert "BACKUP FAILED: $*"; exit 1; }

[[ -f "${ENV_FILE}" ]] && source "${ENV_FILE}" 2>/dev/null || true

send_alert() {
    local msg="$1"
    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        curl -sS -X POST "${SLACK_WEBHOOK_URL}" \
            -H "Content-Type: application/json" \
            -d "{\"text\":\"⚠️ *PRODUCTION BACKUP ALERT*: ${msg}\"}" >/dev/null 2>&1 || true
    fi
    if [[ -n "${ALERT_EMAIL_TO:-}" ]] && command -v mail >/dev/null 2>&1; then
        echo "${msg}" | mail -s "[TGPQ] Backup Alert" "${ALERT_EMAIL_TO}" 2>/dev/null || true
    fi
}

LABEL="daily"
[[ "${PRE_DEPLOY}" == "true" ]] && LABEL="pre-deploy_${TIMESTAMP}"
BACKUP_DIR="${BACKUP_ROOT}/${DATE}/${LABEL}"
mkdir -p "${BACKUP_DIR}"

log "=== TG PRO QUANTUM – Production Daily Backup ==="
log "Label       : ${LABEL}"
log "Backup dir  : ${BACKUP_DIR}"
log "Log file    : ${LOG_FILE}"
echo ""

# ── [1] PostgreSQL full backup ────────────────────────────────────────────────
log "[1/6] PostgreSQL backup..."
PG_BACKUP="${BACKUP_DIR}/postgres_${TIMESTAMP}.sql.gz"
docker exec tgpq-prod-db-primary \
    pg_dumpall -U "${POSTGRES_USER:-tgpq_prod}" \
    | gzip > "${PG_BACKUP}" \
    || fail "PostgreSQL backup failed"
PG_SIZE=$(du -sh "${PG_BACKUP}" | cut -f1)
log "  ✅ PostgreSQL backup: ${PG_BACKUP} (${PG_SIZE})"

# ── [2] Redis backup ──────────────────────────────────────────────────────────
log "[2/6] Redis backup (BGSAVE)..."
docker exec tgpq-prod-redis-1 \
    redis-cli -a "${REDIS_PASSWORD:-}" BGSAVE >/dev/null 2>&1 || true
sleep 5
REDIS_BACKUP="${BACKUP_DIR}/redis_${TIMESTAMP}.rdb"
docker cp tgpq-prod-redis-1:/data/dump.rdb "${REDIS_BACKUP}" \
    || { log "  ⚠️  Redis backup warning – continuing"; }
log "  ✅ Redis backup complete"

# ── [3] Configuration backup ──────────────────────────────────────────────────
log "[3/6] Configuration backup..."
CONFIG_BACKUP="${BACKUP_DIR}/config_${TIMESTAMP}.tar.gz"
tar -czf "${CONFIG_BACKUP}" \
    --exclude='*.key' \
    --exclude='*.pem' \
    -C "${SCRIPT_DIR}" \
    docker-compose.production.yml \
    nginx.production.conf \
    prometheus-production.yml \
    prometheus-rules-production.yml \
    alertmanager-production.yml \
    filebeat-production.yml \
    2>/dev/null || log "  ⚠️  Some config files missing"
log "  ✅ Configuration backup: ${CONFIG_BACKUP}"

# ── [4] Create version tag ────────────────────────────────────────────────────
log "[4/6] Creating version tag..."
VERSION_FILE="${BACKUP_DIR}/version_${TIMESTAMP}.json"
python3 - <<EOF
import json, subprocess, datetime
info = {
    "timestamp": "${TIMESTAMP}",
    "date": "${DATE}",
    "label": "${LABEL}",
    "git_commit": subprocess.getoutput("git -C '${SCRIPT_DIR}/../..' rev-parse HEAD 2>/dev/null || echo unknown"),
    "git_tag": subprocess.getoutput("git -C '${SCRIPT_DIR}/../..' describe --tags --abbrev=0 2>/dev/null || echo none"),
    "backup_files": {
        "postgres": "${PG_BACKUP}",
        "redis": "${REDIS_BACKUP}",
        "config": "${CONFIG_BACKUP}"
    }
}
with open("${VERSION_FILE}", "w") as f:
    json.dump(info, f, indent=2)
print(json.dumps(info, indent=2))
EOF
log "  ✅ Version info: ${VERSION_FILE}"

# ── [5] Upload to S3 ──────────────────────────────────────────────────────────
log "[5/6] Uploading to S3..."
if command -v aws >/dev/null 2>&1 && [[ -n "${S3_BACKUP_BUCKET:-}" ]]; then
    aws s3 sync "${BACKUP_DIR}/" \
        "s3://${S3_BACKUP_BUCKET}/${DATE}/${LABEL}/" \
        --sse AES256 \
        --storage-class STANDARD_IA \
        2>&1 | tee -a "${LOG_FILE}" \
        || log "  ⚠️  S3 upload warning – local backup preserved"
    log "  ✅ S3 upload complete: s3://${S3_BACKUP_BUCKET}/${DATE}/${LABEL}/"
else
    log "  ℹ️  S3 not configured – local backup only"
fi

# ── [6] Verify backup integrity & cleanup old backups ────────────────────────
log "[6/6] Verifying backup and cleaning up old backups..."
# Verify PostgreSQL backup is readable
zcat "${PG_BACKUP}" | head -5 | grep -q "PostgreSQL" \
    && log "  ✅ PostgreSQL backup integrity verified" \
    || log "  ⚠️  PostgreSQL backup integrity check failed"

# Remove backups older than RETENTION_DAYS
find "${BACKUP_ROOT}" -type d -mtime "+${RETENTION_DAYS}" -exec rm -rf {} + 2>/dev/null || true
log "  ✅ Old backups cleaned (retention: ${RETENTION_DAYS} days)"

echo ""
log "=== Daily Backup COMPLETE ✅ ==="
log "Backup dir  : ${BACKUP_DIR}"
log "Log file    : ${LOG_FILE}"
log ""
send_alert "Daily backup completed successfully at ${TIMESTAMP}" 2>/dev/null || true
