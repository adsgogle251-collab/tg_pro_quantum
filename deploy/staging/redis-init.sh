#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# TG PRO QUANTUM – Redis Staging Initialization & Verification
# Usage: ./redis-init.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env.staging"

# ── Load environment ─────────────────────────────────────────────────────────
if [[ -f "${ENV_FILE}" ]]; then
    # shellcheck disable=SC2046
    export $(grep -v '^#' "${ENV_FILE}" | grep -v '^$' | xargs)
fi

REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6380}"
REDIS_PASS="${REDIS_PASSWORD:-}"
CLI_FLAGS=(-h "${REDIS_HOST}" -p "${REDIS_PORT}")
[[ -n "${REDIS_PASS}" ]] && CLI_FLAGS+=(-a "${REDIS_PASS}")

echo "=== TG PRO QUANTUM – Redis Staging Init ==="
echo "Host : ${REDIS_HOST}:${REDIS_PORT}"
echo ""

# ── Connectivity check ───────────────────────────────────────────────────────
echo "[1/5] Checking Redis connectivity..."
redis-cli "${CLI_FLAGS[@]}" PING | grep -q "PONG" && echo "  ✅ Redis reachable" || {
    echo "  ❌ Cannot reach Redis"; exit 1
}

# ── Server info ──────────────────────────────────────────────────────────────
echo "[2/5] Redis server info..."
redis-cli "${CLI_FLAGS[@]}" INFO server | grep -E "redis_version|uptime_in_seconds|connected_clients"

# ── Set cache metadata keys ──────────────────────────────────────────────────
echo "[3/5] Setting cache metadata..."
redis-cli "${CLI_FLAGS[@]}" SET "tgpq:staging:init" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" EX 86400
redis-cli "${CLI_FLAGS[@]}" SET "tgpq:staging:env"  "staging" EX 86400
echo "  ✅ Metadata keys set"

# ── Performance test ─────────────────────────────────────────────────────────
echo "[4/5] Running basic performance test..."
redis-cli "${CLI_FLAGS[@]}" --latency-history -i 1 -c 5 2>/dev/null || true
echo "  ✅ Latency check complete"

# ── Memory report ────────────────────────────────────────────────────────────
echo "[5/5] Memory report..."
redis-cli "${CLI_FLAGS[@]}" INFO memory | grep -E "used_memory_human|maxmemory_human|mem_fragmentation_ratio"

echo ""
echo "=== Redis initialization complete ✅ ==="
