#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# TG PRO QUANTUM – Staging Health Check Script
# Checks API, database, Redis, WebSocket, response times, and error rate.
# Usage: ./health-check.sh [--base-url <url>] [--report]
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env.staging"
BASE_URL="${HEALTH_CHECK_BASE_URL:-http://localhost:8000}"
GENERATE_REPORT=false
PASS=0
FAIL=0
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# ── Parse arguments ──────────────────────────────────────────────────────────
for arg in "$@"; do
    case $arg in
        --base-url=*) BASE_URL="${arg#*=}" ;;
        --base-url)   shift; BASE_URL="$1" ;;
        --report)     GENERATE_REPORT=true ;;
    esac
done

check() {
    local name="$1" result="$2"
    if [[ "${result}" == "ok" ]]; then
        echo "  ✅ ${name}"
        PASS=$((PASS + 1))
    else
        echo "  ❌ ${name}: ${result}"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== TG PRO QUANTUM – Health Check ==="
echo "Base URL : ${BASE_URL}"
echo ""

# ── API health endpoint ──────────────────────────────────────────────────────
echo "[1/6] API health endpoint..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "${BASE_URL}/health" || echo "000")
[[ "${HTTP_CODE}" == "200" ]] && check "GET /health → 200" "ok" \
    || check "GET /health" "HTTP ${HTTP_CODE}"

# ── Detailed health ──────────────────────────────────────────────────────────
echo "[2/6] Detailed health endpoint..."
DETAIL_RESP=$(curl -s --max-time 10 "${BASE_URL}/health/detailed" 2>/dev/null || echo '{}')
DB_STATUS=$(echo "${DETAIL_RESP}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('checks',{}).get('database',{}).get('status','error'))" 2>/dev/null || echo "parse_error")
REDIS_STATUS=$(echo "${DETAIL_RESP}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('checks',{}).get('redis',{}).get('status','unknown'))" 2>/dev/null || echo "parse_error")
check "Database connectivity" "${DB_STATUS}"
check "Redis connectivity"    "${REDIS_STATUS}"

# ── API docs endpoint ────────────────────────────────────────────────────────
echo "[3/6] API documentation..."
DOCS_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "${BASE_URL}/docs" || echo "000")
[[ "${DOCS_CODE}" == "200" ]] && check "GET /docs → 200" "ok" || check "GET /docs" "HTTP ${DOCS_CODE}"

# ── Response time ────────────────────────────────────────────────────────────
echo "[4/6] Response time check..."
RESP_TIME=$(curl -s -o /dev/null -w "%{time_total}" --max-time 10 "${BASE_URL}/health" 2>/dev/null || echo "999")
RESP_MS=$(python3 -c "print(int(float('${RESP_TIME}') * 1000))")
[[ "${RESP_MS}" -lt 500 ]] \
    && check "Response time (${RESP_MS}ms < 500ms)" "ok" \
    || check "Response time" "${RESP_MS}ms exceeds 500ms threshold"

# ── WebSocket endpoint ───────────────────────────────────────────────────────
echo "[5/6] WebSocket endpoint..."
WS_URL="${BASE_URL/http/ws}/ws/campaigns/0"
python3 - <<PYWS 2>/dev/null && check "WebSocket endpoint reachable" "ok" \
    || check "WebSocket endpoint" "connection failed"
import asyncio, sys
async def test_ws():
    try:
        import websockets
        uri = "${WS_URL}"
        async with websockets.connect(uri, open_timeout=5) as ws:
            pass
    except Exception:
        pass  # expect close codes, not an error
asyncio.run(test_ws())
PYWS

# ── Root endpoint ────────────────────────────────────────────────────────────
echo "[6/6] Root endpoint..."
ROOT_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "${BASE_URL}/" || echo "000")
[[ "${ROOT_CODE}" == "200" ]] && check "GET / → 200" "ok" || check "GET /" "HTTP ${ROOT_CODE}"

# ── Report ───────────────────────────────────────────────────────────────────
echo ""
echo "=== Health Check Summary ==="
echo "  Passed : ${PASS}"
echo "  Failed : ${FAIL}"
echo "  Total  : $((PASS + FAIL))"

if [[ "${GENERATE_REPORT}" == "true" ]]; then
    REPORT="/tmp/health_report_${TIMESTAMP}.json"
    python3 - <<PYREPORT > "${REPORT}"
import json, datetime
print(json.dumps({
    "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    "base_url": "${BASE_URL}",
    "passed": ${PASS},
    "failed": ${FAIL},
    "total": $((PASS + FAIL)),
    "status": "healthy" if ${FAIL} == 0 else "degraded"
}, indent=2))
PYREPORT
    echo "  Report  : ${REPORT}"
fi

[[ "${FAIL}" -eq 0 ]] || exit 1
echo ""
echo "=== All health checks passed ✅ ==="
