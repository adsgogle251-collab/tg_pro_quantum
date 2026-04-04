#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# TG PRO QUANTUM – Staging Restore Script
# Restores PostgreSQL, Redis, and configuration from a backup archive.
# Usage: ./restore-staging.sh [--archive <path>] [--list]
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env.staging"
ARCHIVE=""
LIST_ONLY=false

# ── Parse arguments ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case $1 in
        --archive=*) ARCHIVE="${1#*=}" ;;
        --archive)   shift; ARCHIVE="$1" ;;
        --list)      LIST_ONLY=true ;;
    esac
    shift
done

# ── Load environment ─────────────────────────────────────────────────────────
if [[ -f "${ENV_FILE}" ]]; then
    # shellcheck disable=SC2046
    export $(grep -v '^#' "${ENV_FILE}" | grep -v '^$' | xargs)
fi

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# ── List available backups ────────────────────────────────────────────────────
if [[ "${LIST_ONLY}" == "true" ]]; then
    log "=== Available Staging Backups ==="
    if command -v aws >/dev/null 2>&1; then
        aws s3 ls "s3://${BACKUP_S3_BUCKET:-tgpq-staging-backups}/" \
            --region "${BACKUP_S3_REGION:-ap-southeast-1}" \
            | sort -r | head -20
    else
        ls -la /tmp/tgpq_staging_backup_*.tar.gz 2>/dev/null || log "No local backups found"
    fi
    exit 0
fi

# ── Require archive ───────────────────────────────────────────────────────────
if [[ -z "${ARCHIVE}" ]]; then
    log "Usage: $0 --archive <path-or-s3-key>"
    log "       $0 --list"
    exit 1
fi

log "=== TG PRO QUANTUM – Staging Restore ==="
log "Archive : ${ARCHIVE}"
echo ""

# ── Download from S3 if needed ────────────────────────────────────────────────
if [[ "${ARCHIVE}" == s3://* ]]; then
    LOCAL_ARCHIVE="/tmp/$(basename "${ARCHIVE}")"
    log "[1/6] Downloading from S3..."
    aws s3 cp "${ARCHIVE}" "${LOCAL_ARCHIVE}" \
        --region "${BACKUP_S3_REGION:-ap-southeast-1}"
    ARCHIVE="${LOCAL_ARCHIVE}"
    log "  ✅ Downloaded to ${ARCHIVE}"
else
    log "[1/6] Using local archive: ${ARCHIVE}"
fi

# ── Extract archive ──────────────────────────────────────────────────────────
log "[2/6] Extracting archive..."
RESTORE_DIR=$(mktemp -d /tmp/tgpq_restore_XXXXXX)
trap 'rm -rf "${RESTORE_DIR}"' EXIT
tar -xzf "${ARCHIVE}" -C "${RESTORE_DIR}" --strip-components=1
log "  ✅ Extracted to ${RESTORE_DIR}"

# ── Confirm ──────────────────────────────────────────────────────────────────
read -r -p "⚠️  This will OVERWRITE the staging database. Continue? [y/N] " confirm
[[ "${confirm}" =~ ^[Yy]$ ]] || { log "Restore cancelled."; exit 0; }

# ── Restore PostgreSQL ───────────────────────────────────────────────────────
log "[3/6] Restoring PostgreSQL..."
PGPASSWORD="${POSTGRES_PASSWORD}" pg_restore \
    -h "${POSTGRES_HOST:-localhost}" \
    -p "${POSTGRES_PORT:-5433}" \
    -U "${POSTGRES_USER:-tgpq_staging}" \
    -d "${POSTGRES_DB:-tg_quantum_staging}" \
    --clean --if-exists --no-password \
    "${RESTORE_DIR}/postgres.dump"
log "  ✅ PostgreSQL restored"

# ── Restore Redis ────────────────────────────────────────────────────────────
log "[4/6] Restoring Redis..."
if [[ -f "${RESTORE_DIR}/redis.rdb" ]]; then
    docker cp "${RESTORE_DIR}/redis.rdb" "tgpq-staging-redis:/data/dump.rdb" 2>/dev/null || \
        log "  ⚠️  Could not restore Redis RDB (container may not be running)"
    docker restart "tgpq-staging-redis" 2>/dev/null || true
    log "  ✅ Redis restored"
else
    log "  ⚠️  No Redis backup found in archive – skipping"
fi

# ── Verify restoration ───────────────────────────────────────────────────────
log "[5/6] Verifying restoration..."
sleep 5
"${SCRIPT_DIR}/health-check.sh" || log "⚠️  Health checks failed – review manually"

# ── Summary ──────────────────────────────────────────────────────────────────
log "[6/6] Restore complete."
echo ""
log "=== Restore complete ✅ ==="
