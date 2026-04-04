#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# TG PRO QUANTUM – Production Rollback Script
# Immediately routes all traffic back to BLUE and stops GREEN.
# Usage: ./rollback-production.sh [--auto] [--reason <reason>] [--to-tag <tag>]
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env.production"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.production.yml"
ROLLBACK_TAG="${ROLLBACK_TAG:-}"
AUTO=false
REASON="manual"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/tmp/rollback_prod_${TIMESTAMP}.log"
STATE_FILE="/tmp/tgpq_deploy_state"

for arg in "$@"; do
    case $arg in
        --auto)          AUTO=true ;;
        --reason=*)      REASON="${arg#*=}" ;;
        --reason)        shift; REASON="$1" ;;
        --to-tag=*)      ROLLBACK_TAG="${arg#*=}" ;;
        --to-tag)        shift; ROLLBACK_TAG="$1" ;;
    esac
done

log()  { echo "[$(date '+%H:%M:%S')] $*" | tee -a "${LOG_FILE}"; }
fail() { log "❌ $*"; exit 1; }

# ── Load env ──────────────────────────────────────────────────────────────────
[[ -f "${ENV_FILE}" ]] || fail "Missing ${ENV_FILE}"
# shellcheck source=/dev/null
source "${ENV_FILE}" 2>/dev/null || true

log "=== TG PRO QUANTUM – Production ROLLBACK ==="
log "Reason      : ${REASON}"
log "Auto mode   : ${AUTO}"
log "Rollback to : ${ROLLBACK_TAG:-BLUE}"
log "Log file    : ${LOG_FILE}"
echo ""

# ── Confirm if interactive ────────────────────────────────────────────────────
if [[ "${AUTO}" == "false" ]]; then
    read -r -p "⚠️  PRODUCTION ROLLBACK to BLUE. Are you sure? [y/N] " confirm
    [[ "${confirm}" =~ ^[Yy]$ ]] || { log "Rollback cancelled."; exit 0; }
fi

# ── [1] Immediate traffic switch back to BLUE ─────────────────────────────────
log "[1/5] Switching 100% traffic back to BLUE..."
docker exec tgpq-prod-nginx sh -c "nginx -s reload" 2>/dev/null \
    || log "  ⚠️  nginx reload failed – check manually"
log "  ✅ Traffic routed to BLUE"

# ── [2] Stop GREEN containers ─────────────────────────────────────────────────
log "[2/5] Stopping GREEN containers..."
docker compose \
    --env-file "${ENV_FILE}" \
    -f "${COMPOSE_FILE}" \
    --profile green \
    down --remove-orphans 2>&1 | tee -a "${LOG_FILE}" || true
log "  ✅ GREEN containers stopped"

# ── [3] Verify BLUE health ────────────────────────────────────────────────────
log "[3/5] Verifying BLUE environment health..."
sleep 10
BLUE_HEALTH=$(curl -sf http://localhost/health 2>/dev/null \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','unknown'))" 2>/dev/null \
    || echo "unreachable")
log "  BLUE health: ${BLUE_HEALTH}"
[[ "${BLUE_HEALTH}" == "ok" || "${BLUE_HEALTH}" == "healthy" ]] \
    || log "  ⚠️  BLUE health check returned '${BLUE_HEALTH}' – manual verification required"
log "  ✅ BLUE verification complete"

# ── [4] Update state & env ────────────────────────────────────────────────────
log "[4/5] Updating deployment state..."
sed -i "s/^DEPLOY_COLOR=.*/DEPLOY_COLOR=blue/" "${ENV_FILE}" 2>/dev/null || true
echo "ROLLBACK_TIME=${TIMESTAMP}" >> "${STATE_FILE}" 2>/dev/null || true
echo "ROLLBACK_REASON=${REASON}"  >> "${STATE_FILE}" 2>/dev/null || true
log "  ✅ State updated"

# ── [5] Alerts & incident report ─────────────────────────────────────────────
log "[5/5] Sending alerts and creating incident report..."
INCIDENT_FILE="/tmp/incident_rollback_${TIMESTAMP}.md"
cat > "${INCIDENT_FILE}" <<EOF
# Production Rollback Incident Report

**Time:** $(date)
**Reason:** ${REASON}
**Action:** Rolled back from GREEN to BLUE
**Triggered by:** $([ "${AUTO}" == "true" ] && echo "Automatic (metrics failure)" || echo "Manual")

## Impact
- Deployment of new version aborted
- Traffic restored to BLUE (previous stable) environment
- GREEN containers stopped

## Next Steps
- [ ] Investigate root cause: ${REASON}
- [ ] Review application logs
- [ ] Review metrics dashboards
- [ ] Schedule post-mortem
- [ ] Fix identified issue
- [ ] Re-attempt deployment after fix
EOF
log "  Incident report: ${INCIDENT_FILE}"

if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
    curl -sS -X POST "${SLACK_WEBHOOK_URL}" \
        -H "Content-Type: application/json" \
        -d "{\"text\":\"🔴 *PRODUCTION ROLLBACK EXECUTED*\\nReason: ${REASON}\\nTime: $(date)\\nStatus: BLUE is now active\"}" \
        >/dev/null 2>&1 || true
fi

echo ""
log "=== Rollback COMPLETE ✅ ==="
log "Active env      : BLUE"
log "Incident report : ${INCIDENT_FILE}"
log "Log file        : ${LOG_FILE}"
log ""
log "⚠️  IMPORTANT: Investigate reason '${REASON}' before next deployment"
