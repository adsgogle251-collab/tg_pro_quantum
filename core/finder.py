"""
core/finder.py - Scrape members from Telegram groups
"""
import asyncio
import csv
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Callable

from telethon import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import ChannelParticipantsSearch

from core.config import GROUPS_DB, SESSIONS_DIR, get_api_id, get_api_hash
from core.account import _session_path


# ─────────────────────────────────────────────────────────────────────────────
# Database helpers
# ─────────────────────────────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(GROUPS_DB))
    conn.row_factory = sqlite3.Row
    return conn


def list_groups() -> list[dict]:
    """Return all saved groups."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM groups ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_group(group_link: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM groups WHERE group_link = ?", (group_link,)
        ).fetchone()
    return dict(row) if row else None


def save_group(group_link: str, member_count: int, members: list[dict]):
    members_json = json.dumps(members, ensure_ascii=False)
    now = datetime.utcnow().isoformat()
    with _conn() as conn:
        conn.execute("""
            INSERT INTO groups (group_link, member_count, members_json, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(group_link) DO UPDATE SET
                member_count = excluded.member_count,
                members_json = excluded.members_json
        """, (group_link, member_count, members_json, now))
        conn.commit()


def delete_group(group_link: str) -> bool:
    with _conn() as conn:
        conn.execute("DELETE FROM groups WHERE group_link = ?", (group_link,))
        conn.commit()
    return True


def get_members(group_link: str) -> list[dict]:
    """Return scraped members for a group."""
    grp = get_group(group_link)
    if not grp:
        return []
    try:
        return json.loads(grp.get("members_json") or "[]")
    except Exception:
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Scrape logic
# ─────────────────────────────────────────────────────────────────────────────

async def scrape_group(
    phone: str,
    group_link: str,
    on_progress: Callable[[int, int, str], None] | None = None,
    stop_flag: list[bool] | None = None,
) -> tuple[bool, str, list[dict]]:
    """
    Scrape members from a Telegram group/channel.

    Parameters
    ----------
    phone      : account phone to use
    group_link : group username, link, or invite hash
    on_progress: callback(current, total, message)
    stop_flag  : mutable [False] - set to [True] to stop early

    Returns
    -------
    (success, message, members_list)
    """
    api_id = get_api_id()
    api_hash = get_api_hash()
    if not api_id or not api_hash:
        return False, "API not configured.", []

    if stop_flag is None:
        stop_flag = [False]

    session = _session_path(phone)
    client = TelegramClient(session, api_id, api_hash)

    try:
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            return False, f"Account {phone} session expired.", []

        # Resolve entity
        try:
            entity = await client.get_entity(group_link)
        except Exception as e:
            await client.disconnect()
            return False, f"Cannot find group: {e}", []

        members: list[dict] = []

        if on_progress:
            on_progress(0, 0, f"Connecting to {group_link}...")

        # Iterate participants
        total_approx = 0
        try:
            full = await client(GetFullChannelRequest(entity))
            total_approx = full.full_chat.participants_count or 0
        except Exception:
            total_approx = 0

        async for user in client.iter_participants(entity):
            if stop_flag[0]:
                break
            member = {
                "id":         user.id,
                "username":   user.username or "",
                "first_name": user.first_name or "",
                "last_name":  user.last_name or "",
                "phone":      getattr(user, "phone", "") or "",
            }
            members.append(member)
            if on_progress and len(members) % 50 == 0:
                on_progress(
                    len(members),
                    total_approx,
                    f"Scraped {len(members)} members..."
                )

        await client.disconnect()

        # Save to database
        save_group(group_link, len(members), members)

        if on_progress:
            on_progress(len(members), len(members), f"Done! {len(members)} members scraped.")

        return True, f"Scraped {len(members)} members from {group_link}", members

    except Exception as e:
        try:
            await client.disconnect()
        except Exception:
            pass
        return False, str(e), []


def export_csv(group_link: str, file_path: str) -> tuple[bool, str]:
    """Export scraped members to CSV."""
    members = get_members(group_link)
    if not members:
        return False, "No members found for this group."
    try:
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["id", "username", "first_name", "last_name", "phone"]
            )
            writer.writeheader()
            writer.writerows(members)
        return True, f"Exported {len(members)} members to {file_path}"
    except Exception as e:
        return False, str(e)
