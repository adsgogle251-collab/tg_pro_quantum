#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# TG PRO QUANTUM – Production Health Verification
# Usage: ./verify-production-health.sh [--json]
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env.production"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.production.yml"
JSON_OUTPUT=false
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/tmp/health_check_${TIMESTAMP}.log"
PASS=0; FAIL=0; WARN=0

for arg in "$@"; do
    case $arg in --json) JSON_OUTPUT=true ;; esac
done

log()   { echo "[$(date '+%H:%M:%S')] $*" | tee -a "${LOG_FILE}"; }
check() {
    local name="$1"; local cmd="$2"
    if eval "${cmd}" >/dev/null 2>&1; then
        log "  ✅ ${name}"
        PASS=$((PASS + 1))
    else
        log "  ❌ ${name}"
        FAIL=$((FAIL + 1))
    fi
}
check_warn() {
    local name="$1"; local cmd="$2"
    if eval "${cmd}" >/dev/null 2>&1; then
        log "  ✅ ${name}"
        PASS=$((PASS + 1))
    else
        log "  ⚠️  ${name} (non-critical)"
        WARN=$((WARN + 1))
    fi
}

[[ -f "${ENV_FILE}" ]] && source "${ENV_FILE}" 2>/dev/null || true

log "=== TG PRO QUANTUM – Production Health Verification ==="
log "Timestamp : ${TIMESTAMP}"
echo ""

# ── Services running ──────────────────────────────────────────────────────────
log "--- Container Health ---"
check "BLUE app-1 running"   "docker inspect -f '{{.State.Health.Status}}' tgpq-prod-app-blue-1 2>/dev/null | grep -q healthy"
check "BLUE app-2 running"   "docker inspect -f '{{.State.Health.Status}}' tgpq-prod-app-blue-2 2>/dev/null | grep -q healthy"
check "BLUE app-3 running"   "docker inspect -f '{{.State.Health.Status}}' tgpq-prod-app-blue-3 2>/dev/null | grep -q healthy"
check "Nginx running"        "docker inspect -f '{{.State.Running}}' tgpq-prod-nginx 2>/dev/null | grep -q true"
check "DB primary running"   "docker inspect -f '{{.State.Health.Status}}' tgpq-prod-db-primary 2>/dev/null | grep -q healthy"
check "DB replica running"   "docker inspect -f '{{.State.Health.Status}}' tgpq-prod-db-replica 2>/dev/null | grep -q healthy"
check "Redis-1 running"      "docker inspect -f '{{.State.Health.Status}}' tgpq-prod-redis-1 2>/dev/null | grep -q healthy"
check "Redis-2 running"      "docker inspect -f '{{.State.Health.Status}}' tgpq-prod-redis-2 2>/dev/null | grep -q healthy"
check "Redis-3 running"      "docker inspect -f '{{.State.Health.Status}}' tgpq-prod-redis-3 2>/dev/null | grep -q healthy"
check "Prometheus running"   "docker inspect -f '{{.State.Running}}' tgpq-prod-prometheus 2>/dev/null | grep -q true"
check "Grafana running"      "docker inspect -f '{{.State.Running}}' tgpq-prod-grafana 2>/dev/null | grep -q true"
check "AlertManager running" "docker inspect -f '{{.State.Running}}' tgpq-prod-alertmanager 2>/dev/null | grep -q true"
check_warn "Elasticsearch-1" "docker inspect -f '{{.State.Health.Status}}' tgpq-prod-es-1 2>/dev/null | grep -q healthy"
check_warn "Kibana running"  "docker inspect -f '{{.State.Running}}' tgpq-prod-kibana 2>/dev/null | grep -q true"

# ── API endpoints ─────────────────────────────────────────────────────────────
echo ""
log "--- API Endpoint Health ---"
check "GET /health"           "curl -sf http://localhost/health | python3 -c \"import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get('status') in ('ok','healthy') else 1)\""
check_warn "GET /docs"        "curl -sf http://localhost/docs | grep -q 'swagger'"
check_warn "Prometheus scrape" "curl -sf http://localhost:9090/-/healthy | grep -q 'Prometheus'"
check_warn "Grafana health"   "curl -sf http://localhost:3000/api/health | python3 -c \"import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get('database','ok')=='ok' else 1)\""

# ── Database connectivity ─────────────────────────────────────────────────────
echo ""
log "--- Database Connectivity ---"
check "PostgreSQL primary" "docker exec tgpq-prod-db-primary pg_isready -U \${POSTGRES_USER:-tgpq_prod}"
check_warn "PostgreSQL replica" "docker exec tgpq-prod-db-replica pg_isready -U \${POSTGRES_USER:-tgpq_prod}"

# ── Redis connectivity ────────────────────────────────────────────────────────
echo ""
log "--- Cache Connectivity ---"
check "Redis-1 PING" "docker exec tgpq-prod-redis-1 redis-cli -a \${REDIS_PASSWORD:-''} ping | grep -q PONG"
check_warn "Redis-2 PING" "docker exec tgpq-prod-redis-2 redis-cli -a \${REDIS_PASSWORD:-''} ping | grep -q PONG"
check_warn "Redis-3 PING" "docker exec tgpq-prod-redis-3 redis-cli -a \${REDIS_PASSWORD:-''} ping | grep -q PONG"

# ── Monitoring & logging ──────────────────────────────────────────────────────
echo ""
log "--- Monitoring & Logging ---"
check_warn "Prometheus targets up" "curl -sf 'http://localhost:9090/api/v1/targets' | python3 -c \"import sys,json; d=json.load(sys.stdin); active=[t for t in d.get('data',{}).get('activeTargets',[]) if t.get('health')=='up']; sys.exit(0 if active else 1)\""
check_warn "Alert rules loaded"    "curl -sf 'http://localhost:9090/api/v1/rules' | python3 -c \"import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get('data',{}).get('groups') else 1)\""

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "Health Verification Summary"
log "  ✅ Passed  : ${PASS}"
log "  ⚠️  Warnings: ${WARN}"
log "  ❌ Failed  : ${FAIL}"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

REPORT_FILE="/tmp/health_report_${TIMESTAMP}.json"
python3 - <<EOF
import json, datetime
report = {
    "timestamp": "${TIMESTAMP}",
    "passed": ${PASS},
    "warnings": ${WARN},
    "failed": ${FAIL},
    "status": "healthy" if ${FAIL} == 0 else "degraded"
}
with open("${REPORT_FILE}", "w") as f:
    json.dump(report, f, indent=2)
print(f"Report: ${REPORT_FILE}")
EOF

if [[ "${FAIL}" -gt 0 ]]; then
    log ""
    log "❌ ${FAIL} critical health checks FAILED"
    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        curl -sS -X POST "${SLACK_WEBHOOK_URL}" \
            -H "Content-Type: application/json" \
            -d "{\"text\":\"❌ *PRODUCTION HEALTH CHECK FAILED* – ${FAIL} critical checks failed at ${TIMESTAMP}\"}" \
            >/dev/null 2>&1 || true
    fi
    exit 1
fi

log ""
log "=== Health Verification PASSED ✅ ==="
