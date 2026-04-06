"""
core/account_health.py - Account health detection and scoring
"""
import asyncio
import threading
from datetime import datetime, timezone
from typing import Optional, Callable

from telethon import TelegramClient
from telethon.errors import (
    AuthKeyUnregisteredError,
    UserDeactivatedError,
    UserDeactivatedBanError,
    SessionPasswordNeededError,
    FloodWaitError,
    PhoneNumberBannedError,
    SessionExpiredError,
)

from core.config import ACCOUNTS_DB, get_api_id, get_api_hash
from core.account import _session_path
import sqlite3

HEALTH_DB_PATH = ACCOUNTS_DB  # reuse existing accounts DB


def _conn():
    c = sqlite3.connect(str(HEALTH_DB_PATH))
    c.row_factory = sqlite3.Row
    return c


def init_health_table():
    """Create account_health table if not exists."""
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS account_health (
                account_phone   TEXT PRIMARY KEY,
                account_name    TEXT DEFAULT '',
                health_score    INTEGER DEFAULT 100,
                status          TEXT DEFAULT 'unknown',
                last_checked    TEXT DEFAULT NULL,
                join_attempts   INTEGER DEFAULT 0,
                join_success    INTEGER DEFAULT 0,
                join_failed     INTEGER DEFAULT 0,
                banned_from     INTEGER DEFAULT 0,
                last_error      TEXT DEFAULT ''
            )
        """)
        conn.commit()


def get_health(phone: str) -> Optional[dict]:
    init_health_table()
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM account_health WHERE account_phone = ?", (phone,)
        ).fetchone()
    return dict(row) if row else None


def upsert_health(phone: str, **kwargs):
    init_health_table()
    now = datetime.now(timezone.utc).isoformat()
    existing = get_health(phone)
    if existing is None:
        # insert
        kwargs.setdefault("health_score", 100)
        kwargs.setdefault("status", "unknown")
        kwargs.setdefault("join_attempts", 0)
        kwargs.setdefault("join_success", 0)
        kwargs.setdefault("join_failed", 0)
        kwargs.setdefault("banned_from", 0)
        kwargs.setdefault("last_error", "")
        kwargs.setdefault("account_name", "")
        kwargs["last_checked"] = now
        cols = ", ".join(kwargs.keys())
        qmarks = ", ".join("?" * len(kwargs))
        with _conn() as conn:
            conn.execute(
                f"INSERT OR REPLACE INTO account_health (account_phone, {cols}) VALUES (?, {qmarks})",
                [phone] + list(kwargs.values()),
            )
            conn.commit()
    else:
        kwargs["last_checked"] = now
        sets = ", ".join(f"{k} = ?" for k in kwargs.keys())
        with _conn() as conn:
            conn.execute(
                f"UPDATE account_health SET {sets} WHERE account_phone = ?",
                list(kwargs.values()) + [phone],
            )
            conn.commit()


def record_join_attempt(phone: str, success: bool, banned: bool = False, error: str = ""):
    init_health_table()
    existing = get_health(phone) or {}
    attempts = existing.get("join_attempts", 0) + 1
    successes = existing.get("join_success", 0) + (1 if success else 0)
    failures = existing.get("join_failed", 0) + (0 if success else 1)
    banned_from = existing.get("banned_from", 0) + (1 if banned else 0)

    # Recalculate score
    score = _calculate_score(attempts, successes, failures, banned_from, existing.get("status", "active"))

    status = existing.get("status", "active")
    if banned:
        status = "restricted"

    upsert_health(
        phone,
        join_attempts=attempts,
        join_success=successes,
        join_failed=failures,
        banned_from=banned_from,
        health_score=score,
        status=status,
        last_error=error[:200] if error else "",
    )


def _calculate_score(attempts: int, successes: int, failures: int, banned_from: int, status: str) -> int:
    if status in ("banned", "deactivated"):
        return 0
    if status == "expired":
        return 10
    if status == "2fa_required":
        return 50

    score = 100
    # Penalise failures
    if attempts > 0:
        fail_rate = failures / attempts
        score -= int(fail_rate * 40)
    # Penalise bans
    score -= banned_from * 15
    score = max(0, min(100, score))
    return score


def health_label(score: int) -> str:
    if score >= 70:
        return "🟢 Healthy"
    if score >= 40:
        return "🟡 Caution"
    return "🔴 Unhealthy"


# ─────────────────────────────────────────────────────────────────────────────
# Async health check via Telegram API
# ─────────────────────────────────────────────────────────────────────────────

async def _check_account_async(phone: str, api_id: int, api_hash: str) -> dict:
    """Connect to Telegram and verify session is active. Returns health dict."""
    session = _session_path(phone)
    client = TelegramClient(str(session), api_id, api_hash)
    result = {
        "phone": phone,
        "status": "unknown",
        "health_score": 50,
        "error": "",
    }
    try:
        await client.connect()
        authorized = await client.is_user_authorized()
        if not authorized:
            result["status"] = "expired"
            result["health_score"] = 10
            result["error"] = "Session not authorized"
        else:
            # Get self to confirm full access
            me = await client.get_me()
            if me is None:
                result["status"] = "expired"
                result["health_score"] = 10
                result["error"] = "get_me() returned None"
            else:
                result["status"] = "active"
                result["health_score"] = 100
                result["name"] = getattr(me, "first_name", "") or phone
    except SessionPasswordNeededError:
        result["status"] = "2fa_required"
        result["health_score"] = 50
        result["error"] = "2FA required"
    except (AuthKeyUnregisteredError, SessionExpiredError):
        result["status"] = "expired"
        result["health_score"] = 0
        result["error"] = "Session expired"
    except (UserDeactivatedError, UserDeactivatedBanError, PhoneNumberBannedError):
        result["status"] = "banned"
        result["health_score"] = 0
        result["error"] = "Account banned or deactivated"
    except FloodWaitError as e:
        result["status"] = "active"
        result["health_score"] = 60
        result["error"] = f"FloodWait {e.seconds}s"
    except Exception as e:
        result["status"] = "error"
        result["health_score"] = 30
        result["error"] = str(e)[:200]
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass

    # Merge with existing DB data
    existing = get_health(phone)
    if existing:
        # Keep historical stats, just update status/score/error
        attempts = existing.get("join_attempts", 0)
        successes = existing.get("join_success", 0)
        failures = existing.get("join_failed", 0)
        banned_from = existing.get("banned_from", 0)
        recalc = _calculate_score(attempts, successes, failures, banned_from, result["status"])
        result["health_score"] = min(result["health_score"], recalc) if result["status"] != "active" else recalc

    upsert_health(
        phone,
        status=result["status"],
        health_score=result["health_score"],
        last_error=result.get("error", ""),
        account_name=result.get("name", ""),
    )
    return result


def check_accounts_health(
    phones: list,
    on_result: Optional[Callable] = None,
    on_done: Optional[Callable] = None,
):
    """Run health checks for all phones in a background thread."""
    api_id = get_api_id()
    api_hash = get_api_hash()

    if not api_id or not api_hash:
        results = [{"phone": p, "status": "error", "health_score": 0, "error": "API not configured"} for p in phones]
        for r in results:
            if on_result:
                on_result(r)
        if on_done:
            on_done(results)
        return

    def _run():
        loop = asyncio.new_event_loop()
        results = []
        try:
            for phone in phones:
                r = loop.run_until_complete(_check_account_async(phone, int(api_id), api_hash))
                results.append(r)
                if on_result:
                    on_result(r)
        finally:
            loop.close()
            if on_done:
                on_done(results)

    threading.Thread(target=_run, daemon=True).start()


def get_sorted_by_health(phones: list) -> list:
    """Return phones sorted by health_score descending."""
    init_health_table()
    scored = []
    for phone in phones:
        h = get_health(phone)
        score = h["health_score"] if h else 100
        scored.append((phone, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [p for p, _ in scored]


__all__ = [
    "init_health_table",
    "get_health",
    "upsert_health",
    "record_join_attempt",
    "health_label",
    "check_accounts_health",
    "get_sorted_by_health",
]
