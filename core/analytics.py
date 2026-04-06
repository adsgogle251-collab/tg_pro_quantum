"""
core/analytics.py - Statistics and history from SQLite databases
"""
import sqlite3
from datetime import datetime, timedelta

from core.config import ACCOUNTS_DB, BROADCASTS_DB


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _accounts_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(ACCOUNTS_DB))
    conn.row_factory = sqlite3.Row
    return conn


def _broadcasts_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(BROADCASTS_DB))
    conn.row_factory = sqlite3.Row
    return conn


# ─────────────────────────────────────────────────────────────────────────────
# Account stats
# ─────────────────────────────────────────────────────────────────────────────

def account_summary() -> dict:
    """
    Returns:
      total, active, expired, error counts
    """
    with _accounts_conn() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM accounts GROUP BY status"
        ).fetchall()
    counts = {r["status"]: r["cnt"] for r in rows}
    total   = sum(counts.values())
    active  = counts.get("active", 0)
    expired = counts.get("expired", 0)
    error   = counts.get("error", 0)
    return {
        "total":   total,
        "active":  active,
        "expired": expired,
        "error":   error,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Broadcast stats
# ─────────────────────────────────────────────────────────────────────────────

def broadcast_summary() -> dict:
    """
    Returns:
      total_broadcasts, total_sent, total_failed, success_rate
    """
    with _broadcasts_conn() as conn:
        row = conn.execute("""
            SELECT
                COUNT(*)        as count,
                COALESCE(SUM(sent),   0) as total_sent,
                COALESCE(SUM(failed), 0) as total_failed,
                COALESCE(SUM(total),  0) as grand_total
            FROM broadcasts
        """).fetchone()
    if not row:
        return {"total_broadcasts": 0, "total_sent": 0, "total_failed": 0, "success_rate": 0.0}
    grand_total = row["grand_total"] or 0
    total_sent  = row["total_sent"]  or 0
    rate = round((total_sent / grand_total) * 100, 1) if grand_total > 0 else 0.0
    return {
        "total_broadcasts": row["count"],
        "total_sent":       total_sent,
        "total_failed":     row["total_failed"],
        "success_rate":     rate,
    }


def recent_broadcasts(limit: int = 20) -> list[dict]:
    """Return the most recent broadcasts."""
    with _broadcasts_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM broadcasts ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def daily_stats(days: int = 7) -> list[dict]:
    """
    Returns per-day stats for the last `days` days.
    Each entry: {date, sent, failed, broadcasts}
    """
    since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    with _broadcasts_conn() as conn:
        rows = conn.execute("""
            SELECT
                DATE(created_at) as date,
                COALESCE(SUM(sent),   0) as sent,
                COALESCE(SUM(failed), 0) as failed,
                COUNT(*)                  as broadcasts
            FROM broadcasts
            WHERE DATE(created_at) >= ?
            GROUP BY DATE(created_at)
            ORDER BY date ASC
        """, (since,)).fetchall()
    return [dict(r) for r in rows]


def weekly_stats() -> list[dict]:
    return daily_stats(days=7)
