"""
core/join_engine.py - Smart Join Engine
Complete automated join system with:
  - Account health detection and rotation
  - Adaptive flood-wait delay
  - Ban detection + auto-leave
  - Persistent queue (resume on interrupt)
  - Real-time progress and ETA
  - Account-group mapping for broadcast integration
"""
import asyncio
import json
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from telethon import TelegramClient
from telethon.errors import (
    AuthKeyUnregisteredError,
    ChannelPrivateError,
    ChatAdminRequiredError,
    ChatWriteForbiddenError,
    FloodWaitError,
    InviteHashExpiredError,
    SessionExpiredError,
    UserAlreadyParticipantError,
    UserBannedInChannelError,
    UserDeactivatedBanError,
    UserDeactivatedError,
    UserRestrictedError,
)
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest, DeleteChatUserRequest
from telethon.tl.types import Channel, Chat

from core.config import (
    get_api_id,
    get_api_hash,
    save_account_group,
    ACCOUNTS_DB,
)
from core.account import _session_path
from core.account_health import (
    get_health,
    get_sorted_by_health,
    record_join_attempt,
    upsert_health,
    init_health_table,
)
from core.adaptive_delay import AdaptiveDelay
from core.persistent_queue import PersistentQueue
from core.utils import DATA_DIR

import sqlite3

# Account-group mapping file (for Broadcast integration)
MAPPING_FILE = DATA_DIR / "account_group_mapping.json"

MAX_FLOOD_CAP = 120  # seconds
JOIN_ROUND_ROBIN = 5  # rotate account after this many joins per account


# ─────────────────────────────────────────────────────────────────────────────
# Stats dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class JoinStats:
    total: int = 0
    joined: int = 0
    failed: int = 0
    banned: int = 0
    skipped: int = 0
    pending: int = 0
    start_time: float = field(default_factory=time.time)
    current_account: str = ""
    current_group: str = ""
    current_health: int = 100
    current_delay: float = 3.0
    log: list = field(default_factory=list)

    @property
    def completed(self) -> int:
        return self.joined + self.failed + self.banned + self.skipped

    @property
    def elapsed(self) -> float:
        return time.time() - self.start_time

    @property
    def speed(self) -> float:
        """Joins per minute."""
        mins = self.elapsed / 60.0
        return round(self.joined / mins, 1) if mins > 0 else 0.0

    @property
    def eta_seconds(self) -> Optional[float]:
        remaining = self.total - self.completed
        if remaining <= 0:
            return 0.0
        if self.speed > 0:
            return (remaining / self.speed) * 60
        return None

    def add_log(self, msg: str, level: str = "info"):
        ts = datetime.now().strftime("%H:%M:%S")
        entry = {"ts": ts, "msg": msg, "level": level}
        self.log.insert(0, entry)
        if len(self.log) > 1000:
            self.log = self.log[:1000]


# ─────────────────────────────────────────────────────────────────────────────
# Account-group mapping (for Broadcast integration)
# ─────────────────────────────────────────────────────────────────────────────

def _load_mapping() -> dict:
    if MAPPING_FILE.exists():
        try:
            with open(MAPPING_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_mapping(mapping: dict):
    MAPPING_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MAPPING_FILE, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)


def update_account_group_mapping(account_name: str, group_link: str):
    """Record that account_name has joined group_link."""
    mapping = _load_mapping()
    if account_name not in mapping:
        mapping[account_name] = []
    if group_link not in mapping[account_name]:
        mapping[account_name].append(group_link)
    _save_mapping(mapping)


def get_accounts_in_group(group_link: str) -> list:
    """Return all account names that have joined group_link (for Broadcast use)."""
    mapping = _load_mapping()
    return [acc for acc, groups in mapping.items() if group_link in groups]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _is_ban_error(exc: Exception) -> bool:
    return isinstance(
        exc,
        (UserBannedInChannelError, UserRestrictedError, ChatAdminRequiredError, ChatWriteForbiddenError),
    )


def _is_expired_error(exc: Exception) -> bool:
    return isinstance(
        exc,
        (AuthKeyUnregisteredError, SessionExpiredError, UserDeactivatedError, UserDeactivatedBanError),
    )


def _parse_invite_link(group_link: str) -> tuple[str, bool]:
    """Return (clean_identifier, is_private_invite)."""
    link = group_link.strip()
    for prefix in ("https://t.me/+", "https://t.me/joinchat/", "t.me/+", "t.me/joinchat/"):
        if link.startswith(prefix):
            return link[len(prefix):], True
    link = link.replace("https://t.me/", "").replace("@", "").lstrip("/")
    return link, False


# ─────────────────────────────────────────────────────────────────────────────
# Smart Join Engine
# ─────────────────────────────────────────────────────────────────────────────

class JoinEngine:
    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._stop_flag = False
        self._pause_flag = False
        self._running = False
        self.stats: Optional[JoinStats] = None
        self._on_update: Optional[Callable] = None
        self._on_done: Optional[Callable] = None
        self.delay = AdaptiveDelay()
        self.queue = PersistentQueue()

        # Settings
        self.settings = {
            "speed_preset": "normal",          # conservative / normal / aggressive
            "skip_unhealthy": True,            # skip accounts with score < 40
            "on_ban": "auto_continue",         # auto_continue / pause / stop
            "auto_leave_on_ban": True,
            "resume_mode": "ask",              # ask / auto / never
            "skip_already_joined": True,
            "max_retries": 3,
            "health_check_before_start": True,
        }

    # ─────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────

    @property
    def running(self) -> bool:
        return self._running

    @property
    def paused(self) -> bool:
        return self._pause_flag

    def start(
        self,
        accounts: list,
        groups: list,
        on_update: Optional[Callable] = None,
        on_done: Optional[Callable] = None,
        resume: bool = False,
    ):
        if self._running:
            return
        self._stop_flag = False
        self._pause_flag = False
        self._on_update = on_update
        self._on_done = on_done
        self.delay.set_preset(self.settings.get("speed_preset", "normal"))

        init_health_table()

        if resume and self.queue.has_resumable():
            self.queue.resume()
        else:
            # Sort accounts by health (healthiest first)
            sorted_phones = get_sorted_by_health(
                [a.get("phone") or a.get("name", "") if isinstance(a, dict) else a for a in accounts]
            )
            self.queue.create_session(groups, sorted_phones)

        self.stats = JoinStats(total=self.queue.state.get("total_groups", len(groups)))
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def pause(self):
        self._pause_flag = True
        self.queue.pause()
        if self.stats:
            self.stats.add_log("⏸ Session paused", "pause")

    def resume(self):
        self._pause_flag = False
        self.queue.resume()
        if self.stats:
            self.stats.add_log("▶ Session resumed", "info")

    def stop(self):
        self._stop_flag = True
        self._pause_flag = False
        self.queue.stop()

    # ─────────────────────────────────────────────────────────────────
    # Background runner
    # ─────────────────────────────────────────────────────────────────

    def _run(self):
        api_id = get_api_id()
        api_hash = get_api_hash()

        if not api_id or not api_hash:
            if self.stats:
                self.stats.add_log("❌ API credentials not configured", "error")
            self._finish()
            return

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self._async_run(int(api_id), api_hash))
        finally:
            loop.close()
            self._finish()

    def _finish(self):
        self._running = False
        if not self._stop_flag:
            self.queue.complete()
        if self._on_done:
            self._on_done(self.stats)

    async def _async_run(self, api_id: int, api_hash: str):
        state = self.queue.state
        accounts: list = state.get("accounts", [])
        if not accounts:
            if self.stats:
                self.stats.add_log("❌ No accounts available", "error")
            return

        # Build health-sorted account pool
        account_pool = list(accounts)  # already sorted by health at session creation
        account_usage: dict = {p: 0 for p in account_pool}

        pending = self.queue.pending_items()

        for idx, item in pending:
            if self._stop_flag:
                break

            # Pause support
            while self._pause_flag and not self._stop_flag:
                await asyncio.sleep(0.5)

            if self._stop_flag:
                break

            group_link = item["group_link"]
            group_name = item["group_name"] or group_link

            # Pick healthiest available account (round-robin + health)
            phone = self._pick_account(account_pool, account_usage, api_id, api_hash)
            if phone is None:
                self.stats.add_log("❌ No healthy accounts available – stopping", "error")
                self.queue.mark_item(idx, "failed", reason="No healthy accounts")
                break

            if self.stats:
                h = get_health(phone)
                self.stats.current_account = phone
                self.stats.current_group = group_name
                self.stats.current_health = h["health_score"] if h else 100
                self.stats.current_delay = self.delay.current_delay
                self.stats.pending = self.queue.state.get("total_groups", 0) - self.queue.state.get("completed", 0)

            await self._join_one(api_id, api_hash, phone, idx, item, account_pool, account_usage)

            if self._on_update and self.stats:
                self._on_update(self.stats)

            # Adaptive delay before next join
            if not self._stop_flag:
                await asyncio.sleep(self.delay.current_delay)

    def _pick_account(
        self,
        account_pool: list,
        account_usage: dict,
        api_id: int,
        api_hash: str,
    ) -> Optional[str]:
        """Pick the least-used healthy account (round-robin + health score)."""
        skip_unhealthy = self.settings.get("skip_unhealthy", True)
        # Sort by usage (fewest first), then health score descending
        def sort_key(p):
            h = get_health(p)
            score = h["health_score"] if h else 100
            status = h["status"] if h else "active"
            if skip_unhealthy and score < 40:
                return (999, -score)
            if status in ("banned", "deactivated", "expired"):
                return (999, -score)
            return (account_usage.get(p, 0), -score)

        sorted_pool = sorted(account_pool, key=sort_key)
        for phone in sorted_pool:
            h = get_health(phone)
            score = h["health_score"] if h else 100
            status = h["status"] if h else "active"
            if status in ("banned", "deactivated", "expired"):
                continue
            if skip_unhealthy and score < 40:
                continue
            return phone
        # If all are unhealthy, fall back to least-bad
        if sorted_pool:
            return sorted_pool[0]
        return None

    async def _join_one(
        self,
        api_id: int,
        api_hash: str,
        phone: str,
        idx: int,
        item: dict,
        account_pool: list,
        account_usage: dict,
    ):
        group_link = item["group_link"]
        group_name = item["group_name"] or group_link
        session = _session_path(phone)
        client = TelegramClient(str(session), api_id, api_hash)

        try:
            await client.connect()
            if not await client.is_user_authorized():
                upsert_health(phone, status="expired", health_score=0)
                self.stats.add_log(f"⚠️ {phone}: session expired – skipping", "warning")
                self.stats.skipped += 1
                self.queue.mark_item(idx, "skipped", account=phone, reason="Session expired")
                return

            identifier, is_private = _parse_invite_link(group_link)
            joined_entity = None

            try:
                if is_private:
                    result = await client(ImportChatInviteRequest(identifier))
                    joined_entity = getattr(result, "chats", [None])[0] if result else None
                else:
                    entity = await client.get_entity(group_link)
                    await client(JoinChannelRequest(entity))
                    joined_entity = entity

                # Success
                account_usage[phone] = account_usage.get(phone, 0) + 1
                record_join_attempt(phone, success=True)
                self.delay.on_success()
                save_account_group(phone, group_link)
                # Update account→group mapping
                h = get_health(phone)
                acc_name = (h.get("account_name") if h else None) or phone
                update_account_group_mapping(acc_name, group_link)
                self.queue.mark_item(idx, "joined", account=phone)
                self.stats.joined += 1
                self.stats.add_log(
                    f"✓ [{datetime.now().strftime('%H:%M:%S')}] {phone} → {group_name} – Joined successfully",
                    "success",
                )

            except UserAlreadyParticipantError:
                save_account_group(phone, group_link)
                self.queue.mark_item(idx, "skipped", account=phone, reason="Already joined")
                self.stats.skipped += 1
                self.stats.add_log(f"ℹ️ {phone} already in {group_name}", "info")

            except FloodWaitError as e:
                wait = min(e.seconds, MAX_FLOOD_CAP)
                self.delay.on_flood(wait_seconds=float(e.seconds))
                self.stats.add_log(
                    f"⏳ Flood wait {e.seconds}s – increasing delay to {self.delay.current_delay:.0f}s",
                    "warning",
                )
                record_join_attempt(phone, success=False)
                self.queue.mark_item(idx, "failed", account=phone, reason=f"FloodWait {e.seconds}s")
                self.stats.failed += 1
                await asyncio.sleep(wait)

            except (InviteHashExpiredError, ChannelPrivateError) as e:
                record_join_attempt(phone, success=False)
                self.delay.on_failure()
                self.queue.mark_item(idx, "failed", account=phone, reason=str(e)[:120])
                self.stats.failed += 1
                self.stats.add_log(f"✗ {group_name} – {e}", "error")

            except Exception as exc:
                if _is_ban_error(exc):
                    await self._handle_ban(client, phone, idx, group_name, group_link, account_pool)
                elif _is_expired_error(exc):
                    upsert_health(phone, status="banned", health_score=0)
                    self.stats.add_log(f"🚫 {phone}: account deactivated/banned", "error")
                    self.queue.mark_item(idx, "failed", account=phone, reason=str(exc)[:120])
                    self.stats.failed += 1
                    if phone in account_pool:
                        account_pool.remove(phone)
                else:
                    record_join_attempt(phone, success=False, error=str(exc))
                    self.delay.on_failure()
                    self.queue.mark_item(idx, "failed", account=phone, reason=str(exc)[:120])
                    self.stats.failed += 1
                    self.stats.add_log(
                        f"✗ [{datetime.now().strftime('%H:%M:%S')}] {phone} → {group_name} – {str(exc)[:80]}",
                        "error",
                    )

        except Exception as outer:
            self.stats.failed += 1
            self.queue.mark_item(idx, "failed", account=phone, reason=str(outer)[:120])
            self.stats.add_log(f"❌ Connection error {phone}: {str(outer)[:80]}", "error")
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass

    async def _handle_ban(
        self,
        client: TelegramClient,
        phone: str,
        idx: int,
        group_name: str,
        group_link: str,
        account_pool: list,
    ):
        record_join_attempt(phone, success=False, banned=True, error="Banned from group")
        h = get_health(phone)
        acc_name = (h.get("account_name") if h else None) or phone
        self.stats.banned += 1
        self.stats.add_log(
            f"⚠️ [{datetime.now().strftime('%H:%M:%S')}] {acc_name} → {group_name} – Ban detected, auto-left",
            "ban",
        )
        self.queue.mark_item(idx, "banned", account=phone, reason="Banned from group")

        # Auto-leave
        if self.settings.get("auto_leave_on_ban", True):
            try:
                identifier, is_private = _parse_invite_link(group_link)
                if not is_private:
                    entity = await client.get_entity(group_link)
                    if isinstance(entity, (Channel, Chat)):
                        await client(LeaveChannelRequest(entity))
            except Exception:
                pass

        on_ban = self.settings.get("on_ban", "auto_continue")
        if on_ban == "pause":
            self._pause_flag = True
            self.queue.pause()
            self.stats.add_log("⏸ Paused after ban detection", "pause")
        elif on_ban == "stop":
            self._stop_flag = True


# Singleton
join_engine = JoinEngine()

__all__ = [
    "JoinEngine",
    "JoinStats",
    "join_engine",
    "update_account_group_mapping",
    "get_accounts_in_group",
]
