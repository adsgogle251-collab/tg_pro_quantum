#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# TG PRO QUANTUM – Staging Database Migration Script
# Runs Alembic migrations and verifies schema integrity.
# Usage: ./migrate-staging.sh [--dry-run]
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env.staging"
DRY_RUN=false

# ── Parse arguments ──────────────────────────────────────────────────────────
for arg in "$@"; do
    case $arg in
        --dry-run) DRY_RUN=true ;;
    esac
done

# ── Load environment ─────────────────────────────────────────────────────────
if [[ -f "${ENV_FILE}" ]]; then
    # shellcheck disable=SC2046
    export $(grep -v '^#' "${ENV_FILE}" | grep -v '^$' | xargs)
fi

echo "=== TG PRO QUANTUM – Staging Migration ==="
echo "Project root : ${PROJECT_ROOT}"
echo "Dry run      : ${DRY_RUN}"
echo "Database     : ${DATABASE_URL:-<not set>}"
echo ""

# ── Connectivity check ───────────────────────────────────────────────────────
echo "[1/5] Checking database connectivity..."
python3 - <<'PYCHECK'
import os, asyncio, sys
async def check():
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text
        url = os.environ["DATABASE_URL"]
        engine = create_async_engine(url, pool_pre_ping=True)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
        await engine.dispose()
        print("  ✅ Database reachable")
    except Exception as e:
        print(f"  ❌ Cannot connect to database: {e}", file=sys.stderr)
        sys.exit(1)
asyncio.run(check())
PYCHECK

# ── Current revision ─────────────────────────────────────────────────────────
echo "[2/5] Current Alembic revision..."
cd "${PROJECT_ROOT}"
python3 -m alembic current 2>&1 || echo "  (no existing revisions)"

# ── Run migrations ───────────────────────────────────────────────────────────
if [[ "${DRY_RUN}" == "true" ]]; then
    echo "[3/5] Dry run – showing pending migrations..."
    python3 -m alembic upgrade head --sql 2>&1 | head -40
else
    echo "[3/5] Running migrations to HEAD..."
    python3 -m alembic upgrade head
    echo "  ✅ Migrations applied"
fi

# ── Verify schema ────────────────────────────────────────────────────────────
echo "[4/5] Verifying core tables..."
python3 - <<'PYVERIFY'
import os, asyncio, sys
EXPECTED_TABLES = [
    "clients", "telegram_accounts", "campaigns", "groups",
    "account_groups", "account_assignments", "account_health",
    "group_analytics", "broadcast_logs", "campaign_activities",
    "failed_messages", "safety_alerts", "client_broadcast_stats",
]
async def verify():
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text, inspect
    url = os.environ["DATABASE_URL"]
    engine = create_async_engine(url)
    async with engine.connect() as conn:
        result = await conn.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
        ))
        existing = {row[0] for row in result.fetchall()}
    await engine.dispose()
    missing = [t for t in EXPECTED_TABLES if t not in existing]
    if missing:
        print(f"  ❌ Missing tables: {missing}", file=sys.stderr)
        sys.exit(1)
    print(f"  ✅ All {len(EXPECTED_TABLES)} expected tables present")
asyncio.run(verify())
PYVERIFY

# ── Post-migration revision ───────────────────────────────────────────────────
echo "[5/5] Final Alembic revision..."
python3 -m alembic current

echo ""
echo "=== Migration complete ✅ ==="
