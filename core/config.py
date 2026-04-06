"""
core/config.py - Simple settings management using SQLite
"""
import sqlite3
import os
from datetime import datetime
from pathlib import Path

# Data directory
DATA_DIR = Path(os.environ.get("TG_DATA_DIR", "data"))
DATA_DIR.mkdir(exist_ok=True)

# Database paths
ACCOUNTS_DB = DATA_DIR / "accounts.db"
GROUPS_DB   = DATA_DIR / "groups.db"
BROADCASTS_DB = DATA_DIR / "broadcasts.db"
SETTINGS_DB = DATA_DIR / "settings.db"

# Sessions directory
SESSIONS_DIR = DATA_DIR / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)


def _get_conn(db_path: Path) -> sqlite3.Connection:
    """Get a SQLite connection with row_factory."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_databases():
    """Create all tables if they don't exist."""
    # Accounts DB
    with _get_conn(ACCOUNTS_DB) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                phone       TEXT NOT NULL UNIQUE,
                status      TEXT NOT NULL DEFAULT 'active',
                session_file TEXT,
                created_at  TEXT DEFAULT (datetime('now')),
                updated_at  TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS account_groups (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                account_phone TEXT NOT NULL,
                group_link    TEXT NOT NULL,
                joined_at     TEXT DEFAULT (datetime('now')),
                status        TEXT DEFAULT 'joined',
                UNIQUE(account_phone, group_link)
            )
        """)
        conn.commit()

    # Groups DB
    with _get_conn(GROUPS_DB) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                group_link   TEXT NOT NULL UNIQUE,
                member_count INTEGER DEFAULT 0,
                members_json TEXT DEFAULT '[]',
                created_at   TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS group_searches (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword      TEXT NOT NULL,
                group_link   TEXT NOT NULL UNIQUE,
                group_title  TEXT DEFAULT '',
                member_count INTEGER DEFAULT 0,
                is_group     INTEGER DEFAULT 1,
                joined       INTEGER DEFAULT 0,
                found_at     TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS keywords (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword        TEXT NOT NULL,
                generated_from TEXT DEFAULT '',
                created_at     TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()

    # Broadcasts DB
    with _get_conn(BROADCASTS_DB) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS broadcasts (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL,
                sent       INTEGER DEFAULT 0,
                failed     INTEGER DEFAULT 0,
                total      INTEGER DEFAULT 0,
                duration   REAL DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ban_logs (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                account_phone TEXT NOT NULL,
                group_link    TEXT NOT NULL,
                reason        TEXT DEFAULT '',
                action        TEXT DEFAULT 'auto',
                detected_at   TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS broadcast_queue (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                account_phone TEXT NOT NULL,
                group_link    TEXT NOT NULL,
                message       TEXT NOT NULL,
                status        TEXT DEFAULT 'pending',
                created_at    TEXT DEFAULT (datetime('now')),
                sent_at       TEXT
            )
        """)
        conn.commit()

    # Settings DB
    with _get_conn(SETTINGS_DB) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.commit()


def get_setting(key: str, default: str = "") -> str:
    """Get a setting value by key."""
    with _get_conn(SETTINGS_DB) as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str):
    """Set a setting value."""
    with _get_conn(SETTINGS_DB) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value)
        )
        conn.commit()


def get_api_id() -> int:
    """Return API ID as integer (0 if not set)."""
    try:
        return int(get_setting("api_id", "0"))
    except ValueError:
        return 0


def get_api_hash() -> str:
    return get_setting("api_hash", "")


def get_app_version() -> str:
    return get_setting("app_version", "4.16.11")


# ─────────────────────────────────────────────────────────────────────────────
# Group search helpers
# ─────────────────────────────────────────────────────────────────────────────

def save_group_search_result(
    keyword: str,
    group_link: str,
    group_title: str,
    member_count: int,
    is_group: bool,
):
    """Save a group found during keyword search."""
    now = datetime.utcnow().isoformat()
    with _get_conn(GROUPS_DB) as conn:
        conn.execute("""
            INSERT INTO group_searches
                (keyword, group_link, group_title, member_count, is_group, joined, found_at)
            VALUES (?, ?, ?, ?, ?, 0, ?)
            ON CONFLICT(group_link) DO UPDATE SET
                keyword      = excluded.keyword,
                group_title  = excluded.group_title,
                member_count = excluded.member_count,
                is_group     = excluded.is_group,
                found_at     = excluded.found_at
        """, (keyword, group_link, group_title, member_count, int(is_group), now))
        conn.commit()


def list_group_search_results(only_unjoined: bool = False) -> list[dict]:
    """Return all found groups, optionally only unjoined ones."""
    with _get_conn(GROUPS_DB) as conn:
        if only_unjoined:
            rows = conn.execute(
                "SELECT * FROM group_searches WHERE joined = 0 ORDER BY found_at DESC"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM group_searches ORDER BY found_at DESC"
            ).fetchall()
    return [dict(r) for r in rows]


def mark_group_search_joined(group_link: str):
    """Mark a found group as joined."""
    with _get_conn(GROUPS_DB) as conn:
        conn.execute(
            "UPDATE group_searches SET joined = 1 WHERE group_link = ?",
            (group_link,)
        )
        conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Account-group membership helpers
# ─────────────────────────────────────────────────────────────────────────────

def save_account_group(phone: str, group_link: str):
    """Record that an account has joined a group."""
    now = datetime.utcnow().isoformat()
    with _get_conn(ACCOUNTS_DB) as conn:
        conn.execute("""
            INSERT INTO account_groups (account_phone, group_link, joined_at, status)
            VALUES (?, ?, ?, 'joined')
            ON CONFLICT(account_phone, group_link) DO UPDATE SET
                status    = 'joined',
                joined_at = excluded.joined_at
        """, (phone, group_link, now))
        conn.commit()
    mark_group_search_joined(group_link)


def list_account_groups(phone: str) -> list[dict]:
    """Return groups an account has joined."""
    with _get_conn(ACCOUNTS_DB) as conn:
        rows = conn.execute(
            "SELECT * FROM account_groups WHERE account_phone = ? ORDER BY joined_at DESC",
            (phone,)
        ).fetchall()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# Ban log helpers
# ─────────────────────────────────────────────────────────────────────────────

def log_ban(phone: str, group_link: str, reason: str, action: str = "auto"):
    """Log a ban event."""
    now = datetime.utcnow().isoformat()
    with _get_conn(BROADCASTS_DB) as conn:
        conn.execute("""
            INSERT INTO ban_logs (account_phone, group_link, reason, action, detected_at)
            VALUES (?, ?, ?, ?, ?)
        """, (phone, group_link, reason, action, now))
        conn.commit()


def list_ban_logs() -> list[dict]:
    """Return all ban log entries."""
    with _get_conn(BROADCASTS_DB) as conn:
        rows = conn.execute(
            "SELECT * FROM ban_logs ORDER BY detected_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# Broadcast queue helpers
# ─────────────────────────────────────────────────────────────────────────────

def save_broadcast_queue_item(
    account_phone: str,
    group_link: str,
    message: str,
    status: str = "pending",
):
    """Add an item to the broadcast queue."""
    now = datetime.utcnow().isoformat()
    with _get_conn(BROADCASTS_DB) as conn:
        conn.execute("""
            INSERT INTO broadcast_queue
                (account_phone, group_link, message, status, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (account_phone, group_link, message, status, now))
        conn.commit()


def get_pending_queue_items() -> list[dict]:
    """Return all pending broadcast queue items."""
    with _get_conn(BROADCASTS_DB) as conn:
        rows = conn.execute(
            "SELECT * FROM broadcast_queue WHERE status = 'pending' ORDER BY created_at ASC"
        ).fetchall()
    return [dict(r) for r in rows]


def update_queue_item_status(item_id: int, status: str):
    """Update the status of a broadcast queue item."""
    now = datetime.utcnow().isoformat()
    with _get_conn(BROADCASTS_DB) as conn:
        conn.execute(
            "UPDATE broadcast_queue SET status = ?, sent_at = ? WHERE id = ?",
            (status, now if status == "sent" else None, item_id)
        )
        conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Initialise on import
# ─────────────────────────────────────────────────────────────────────────────

init_databases()
