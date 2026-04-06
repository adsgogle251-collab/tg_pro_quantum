"""
core/config.py - Simple settings management using SQLite
"""
import sqlite3
import os
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


# Initialise on import
init_databases()
