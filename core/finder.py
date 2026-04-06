"""
core/finder.py - Scrape members from Telegram groups + keyword-based group search
"""
import asyncio
import csv
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from telethon import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.types import ChannelParticipantsSearch

from core.config import (
    GROUPS_DB, SESSIONS_DIR, get_api_id, get_api_hash,
    save_group_search_result, list_group_search_results,
    save_search_history_entry,
)
from core.account import _session_path
from core.group_detector import is_group as _is_group, get_entity_type


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


# ─────────────────────────────────────────────────────────────────────────────
# Keyword-based group search
# ─────────────────────────────────────────────────────────────────────────────

async def search_groups_by_keyword(
    phone: str,
    keyword: str,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
    stop_flag: Optional[list] = None,
) -> tuple[int, list[dict]]:
    """
    Search for Telegram groups using a keyword via the Telegram contacts search API.
    Returns (count_found, results_list).
    Each result: {group_link, title, member_count, is_group, username}
    """
    api_id = get_api_id()
    api_hash = get_api_hash()
    if not api_id or not api_hash:
        return 0, []

    if stop_flag is None:
        stop_flag = [False]

    session = _session_path(phone)
    client = TelegramClient(session, api_id, api_hash)
    results: list[dict] = []

    try:
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            return 0, []

        if on_progress:
            on_progress(0, 0, f"Searching: {keyword}")

        try:
            search_result = await client(SearchRequest(q=keyword, limit=100))
        except Exception:
            await client.disconnect()
            return 0, []

        chats = getattr(search_result, "chats", [])
        for chat in chats:
            if stop_flag[0]:
                break
            entity_type = get_entity_type(chat)
            if entity_type not in ("group", "channel"):
                continue

            username = getattr(chat, "username", None) or ""
            group_link = f"https://t.me/{username}" if username else f"https://t.me/c/{chat.id}"
            title = getattr(chat, "title", username) or username
            member_count = getattr(chat, "participants_count", 0) or 0
            group_flag = _is_group(chat)

            entry = {
                "group_link": group_link,
                "title": title,
                "member_count": member_count,
                "is_group": group_flag,
                "username": username,
                "keyword": keyword,
            }
            results.append(entry)
            save_group_search_result(keyword, group_link, title, member_count, group_flag)

        await client.disconnect()

        if on_progress:
            on_progress(len(results), len(results), f"Found {len(results)} for '{keyword}'")

        return len(results), results

    except Exception:
        try:
            await client.disconnect()
        except Exception:
            pass
        return 0, []


async def search_groups_batch(
    phone: str,
    keywords: list[str],
    on_progress: Optional[Callable[[int, int, str], None]] = None,
    stop_flag: Optional[list] = None,
) -> tuple[int, int]:
    """Search multiple keywords. Returns (total_found, keywords_searched)."""
    if stop_flag is None:
        stop_flag = [False]

    total_found = 0
    searched = 0

    for i, kw in enumerate(keywords):
        if stop_flag[0]:
            break
        if on_progress:
            on_progress(i + 1, len(keywords), f"Keyword {i+1}/{len(keywords)}: {kw}")
        count, _ = await search_groups_by_keyword(phone, kw, stop_flag=stop_flag)
        total_found += count
        searched += 1
        await asyncio.sleep(1.5)  # avoid flood

    return total_found, searched


def list_found_groups(only_unjoined: bool = False) -> list[dict]:
    """List groups found by search. Optionally filter unjoined only."""
    return list_group_search_results(only_unjoined=only_unjoined)


def export_found_groups_txt(file_path: str) -> tuple[bool, str]:
    """Export found groups to TXT file (one link per line)."""
    groups = list_group_search_results()
    if not groups:
        return False, "No groups found yet."
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            for g in groups:
                f.write(g.get("group_link", "") + "\n")
        return True, f"Exported {len(groups)} groups to {file_path}"
    except Exception as e:
        return False, str(e)


def export_found_groups_txt_full(file_path: str) -> tuple[bool, str]:
    """Export found groups to TXT with full details."""
    groups = list_group_search_results()
    if not groups:
        return False, "No groups found yet."
    try:
        date_str = datetime.now().strftime("%Y-%m-%d")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"FINDER RESULTS - {date_str}\n")
            f.write(f"Found {len(groups)} groups\n\n")
            for i, g in enumerate(groups, 1):
                members = g.get("member_count", 0)
                members_str = f"{members:,}" if members else "?"
                status = "Joined" if g.get("joined") else "New"
                f.write(f"{i}. {g.get('group_title', 'Unknown')} (ID: {g.get('id', '?')})\n")
                f.write(f"   Members: {members_str}\n")
                f.write(f"   Link: {g.get('group_link', '')}\n")
                f.write(f"   Status: {status}\n\n")
        return True, f"Exported {len(groups)} groups to {file_path}"
    except Exception as e:
        return False, str(e)


def export_found_groups_csv_file(file_path: str) -> tuple[bool, str]:
    """Export found groups to CSV file with full columns."""
    groups = list_group_search_results()
    if not groups:
        return False, "No groups found yet."
    try:
        fieldnames = ["id", "group_title", "member_count", "group_link", "is_group", "joined", "keyword", "found_at"]
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for g in groups:
                row = {k: g.get(k, "") for k in fieldnames}
                row["joined"] = "Joined" if row.get("joined") else "New"
                writer.writerow(row)
        return True, f"Exported {len(groups)} groups to {file_path}"
    except Exception as e:
        return False, str(e)


def export_found_groups_json_file(file_path: str) -> tuple[bool, str]:
    """Export found groups to JSON file."""
    groups = list_group_search_results()
    if not groups:
        return False, "No groups found yet."
    try:
        export_data = []
        for g in groups:
            export_data.append({
                "id": g.get("id", ""),
                "name": g.get("group_title", ""),
                "members": g.get("member_count", 0),
                "link": g.get("group_link", ""),
                "is_group": bool(g.get("is_group", True)),
                "status": "Joined" if g.get("joined") else "New",
                "keyword": g.get("keyword", ""),
                "found_at": g.get("found_at", ""),
            })
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        return True, f"Exported {len(groups)} groups to {file_path}"
    except Exception as e:
        return False, str(e)


def auto_append_found_groups_txt(groups: list[dict], txt_path: Path | str) -> int:
    """Append a list of group links to a TXT file. Returns count of links actually written."""
    written = 0
    try:
        txt_path = Path(txt_path)
        txt_path.parent.mkdir(parents=True, exist_ok=True)
        with open(txt_path, "a", encoding="utf-8") as f:
            for g in groups:
                link = g.get("group_link", "")
                if link:
                    f.write(link + "\n")
                    written += 1
        return written
    except Exception:
        return 0

