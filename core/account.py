"""
core/account.py - Account management with OTP login via Telethon
"""
import sqlite3
import asyncio
import threading
from datetime import datetime
from pathlib import Path

from telethon import TelegramClient
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    FloodWaitError,
)

from core.config import ACCOUNTS_DB, SESSIONS_DIR, get_api_id, get_api_hash


# ─────────────────────────────────────────────────────────────────────────────
# Database helpers
# ─────────────────────────────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(ACCOUNTS_DB))
    conn.row_factory = sqlite3.Row
    return conn


# ─────────────────────────────────────────────────────────────────────────────
# Account CRUD
# ─────────────────────────────────────────────────────────────────────────────

def list_accounts() -> list[dict]:
    """Return all accounts as a list of dicts."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM accounts ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_account(phone: str) -> dict | None:
    """Get one account by phone."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM accounts WHERE phone = ?", (phone,)
        ).fetchone()
    return dict(row) if row else None


def _upsert_account(name: str, phone: str, session_file: str, status: str = "active"):
    now = datetime.utcnow().isoformat()
    with _conn() as conn:
        conn.execute("""
            INSERT INTO accounts (name, phone, session_file, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(phone) DO UPDATE SET
                name         = excluded.name,
                session_file = excluded.session_file,
                status       = excluded.status,
                updated_at   = excluded.updated_at
        """, (name, phone, session_file, status, now, now))
        conn.commit()


def delete_account(phone: str) -> bool:
    """Delete account and its session file."""
    acc = get_account(phone)
    if not acc:
        return False
    # Remove session file if it exists
    if acc.get("session_file"):
        sf = Path(acc["session_file"])
        for ext in ("", ".session", ".session-journal"):
            p = Path(str(sf) + ext) if ext else sf
            if p.exists():
                try:
                    p.unlink()
                except OSError:
                    pass
    with _conn() as conn:
        conn.execute("DELETE FROM accounts WHERE phone = ?", (phone,))
        conn.commit()
    return True


def update_account_status(phone: str, status: str):
    with _conn() as conn:
        conn.execute(
            "UPDATE accounts SET status = ?, updated_at = ? WHERE phone = ?",
            (status, datetime.utcnow().isoformat(), phone)
        )
        conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# OTP Login (async)
# ─────────────────────────────────────────────────────────────────────────────

def _session_path(phone: str) -> str:
    """Return string path for Telethon session file (without extension)."""
    safe = phone.replace("+", "").replace(" ", "")
    return str(SESSIONS_DIR / safe)


async def send_otp(phone: str) -> tuple[bool, str]:
    """
    Start Telegram login - sends OTP to the phone.
    Returns (success, message).
    """
    api_id = get_api_id()
    api_hash = get_api_hash()
    if not api_id or not api_hash:
        return False, "API ID / API Hash not configured. Go to Settings first."

    session = _session_path(phone)
    client = TelegramClient(session, api_id, api_hash)
    try:
        await client.connect()
        if await client.is_user_authorized():
            await client.disconnect()
            return True, "already_authorized"
        await client.send_code_request(phone)
        await client.disconnect()
        return True, "otp_sent"
    except FloodWaitError as e:
        await client.disconnect()
        return False, f"Too many attempts. Wait {e.seconds}s."
    except Exception as e:
        try:
            await client.disconnect()
        except Exception:
            pass
        return False, str(e)


async def verify_otp(
    phone: str,
    code: str,
    name: str = "",
    password: str = "",
) -> tuple[bool, str]:
    """
    Complete OTP login.
    Returns (success, message).
    """
    api_id = get_api_id()
    api_hash = get_api_hash()
    if not api_id or not api_hash:
        return False, "API ID / API Hash not configured."

    session = _session_path(phone)
    client = TelegramClient(session, api_id, api_hash)
    try:
        await client.connect()

        # Already logged in (resent flow)
        if await client.is_user_authorized():
            me = await client.get_me()
            display = name or (me.first_name or phone)
            session_file = session + ".session"
            _upsert_account(display, phone, session_file, "active")
            await client.disconnect()
            return True, f"Account '{display}' logged in."

        try:
            await client.sign_in(phone, code)
        except SessionPasswordNeededError:
            if not password:
                await client.disconnect()
                return False, "2FA_required"
            await client.sign_in(password=password)
        except PhoneCodeInvalidError:
            await client.disconnect()
            return False, "Invalid OTP code."
        except PhoneCodeExpiredError:
            await client.disconnect()
            return False, "OTP code expired. Request a new one."

        me = await client.get_me()
        display = name or (me.first_name or phone)
        session_file = session + ".session"
        _upsert_account(display, phone, session_file, "active")
        await client.disconnect()
        return True, f"Account '{display}' added successfully."
    except Exception as e:
        try:
            await client.disconnect()
        except Exception:
            pass
        return False, str(e)


async def check_account_health(phone: str) -> tuple[str, str]:
    """
    Check if account session is valid.
    Returns (status, message): status is 'active' | 'expired' | 'error'.
    """
    acc = get_account(phone)
    if not acc:
        return "error", "Account not found."
    api_id = get_api_id()
    api_hash = get_api_hash()
    if not api_id or not api_hash:
        return "error", "API not configured."
    session = _session_path(phone)
    client = TelegramClient(session, api_id, api_hash)
    try:
        await client.connect()
        if await client.is_user_authorized():
            me = await client.get_me()
            await client.disconnect()
            update_account_status(phone, "active")
            return "active", f"OK - {me.first_name}"
        await client.disconnect()
        update_account_status(phone, "expired")
        return "expired", "Session expired."
    except Exception as e:
        try:
            await client.disconnect()
        except Exception:
            pass
        update_account_status(phone, "error")
        return "error", str(e)


# ─────────────────────────────────────────────────────────────────────────────
# Thread-safe wrappers
# ─────────────────────────────────────────────────────────────────────────────

def run_async(coro):
    """Run a coroutine in a new event loop (for use from GUI threads)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
