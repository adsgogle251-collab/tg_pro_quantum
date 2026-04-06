"""
core/broadcaster.py - Advanced round-robin broadcast engine.
24/7 continuous operation with fair account rotation.
"""
import asyncio
import threading
from datetime import datetime
from typing import Callable, Optional, List

from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError,
    ChatWriteForbiddenError,
    UserBannedInChannelError,
    UserNotParticipantError,
    PeerFloodError,
    ChatAdminRequiredError,
    SlowModeWaitError,
)

from core.config import get_api_id, get_api_hash, log_ban
from core.account import list_accounts, _session_path, update_account_status

SEND_DELAY = 5.0       # seconds between individual sends
ROUND_DELAY = 120.0    # seconds to wait after a full round


class BroadcastStats:
    def __init__(self):
        self.sent = 0
        self.failed = 0
        self.banned = 0
        self.pending = 0
        self.rounds = 0
        self.log: list[str] = []
        # Live mapping tracking
        self.mapping_entries: list[dict] = []   # newest first
        self.start_time: Optional[datetime] = None
        self._total_groups: int = 0
        self.failed_groups: list[str] = []      # groups that failed, for retry

    def add_log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log.insert(0, f"[{ts}] {msg}")
        if len(self.log) > 1000:
            self.log = self.log[:1000]

    def add_mapping(self, account: str, group: str, status: str,
                    link: str, msg_preview: str = "") -> None:
        """Add or update an account→group mapping entry (newest first)."""
        ts = datetime.now().strftime("%H:%M:%S")
        entry = {
            "account": account,
            "group": group,
            "status": status,
            "link": link,
            "timestamp": ts,
            "msg_preview": msg_preview[:50] if msg_preview else "",
        }
        for i, e in enumerate(self.mapping_entries):
            if e["account"] == account and e["group"] == group:
                self.mapping_entries[i] = entry
                return
        self.mapping_entries.insert(0, entry)
        if len(self.mapping_entries) > 500:
            self.mapping_entries = self.mapping_entries[:500]

    @property
    def speed_msg_per_min(self) -> float:
        """Messages sent per minute since broadcast started."""
        if not self.start_time or self.sent == 0:
            return 0.0
        elapsed = (datetime.now() - self.start_time).total_seconds() / 60.0
        return round(self.sent / elapsed, 1) if elapsed > 0 else 0.0

    @property
    def eta_seconds(self) -> int:
        """Estimated time remaining in seconds."""
        spd = self.speed_msg_per_min
        if self._total_groups == 0 or spd == 0:
            return 0
        remaining = max(0, self._total_groups - self.sent - self.failed)
        return int(remaining / spd * 60)

    @property
    def progress_pct(self) -> float:
        """Progress percentage (0–100)."""
        if self._total_groups == 0:
            return 0.0
        return min(100.0, round((self.sent + self.failed) / self._total_groups * 100, 1))

    @property
    def total(self) -> int:
        return self.sent + self.failed


class AdvancedBroadcaster:
    """
    Round-robin broadcaster:
    - Cycles through accounts fairly across groups
    - After a full round waits ROUND_DELAY seconds then restarts
    - 24/7 continuous until manually stopped
    - Live account→group mapping tracking with speed/ETA
    """

    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._stop_flag = False
        self._pause_event = threading.Event()
        self._pause_event.set()
        self.stats = BroadcastStats()
        self._on_update: Optional[Callable] = None
        self._on_done: Optional[Callable] = None
        self._running = False
        # Store last broadcast params for retry
        self._last_message: str = ""
        self._last_accounts: List[str] = []
        # Phone → display name lookup (populated on start)
        self._phone_to_name: dict = {}

    @property
    def running(self) -> bool:
        return self._running

    def start(
        self,
        message: str,
        accounts: List[str],
        groups: List[str],
        on_update: Optional[Callable] = None,
        on_done: Optional[Callable] = None,
    ):
        if self._running:
            return
        if not accounts or not groups:
            return
        self._stop_flag = False
        self._pause_event.set()
        self._on_update = on_update
        self._on_done = on_done
        self._last_message = message
        self._last_accounts = list(accounts)
        # Build phone→name lookup
        try:
            acct_list = list_accounts()
            self._phone_to_name = {a["phone"]: a.get("name", a["phone"]) for a in acct_list}
        except Exception:
            self._phone_to_name = {}
        self.stats = BroadcastStats()
        self.stats.pending = len(groups)
        self.stats._total_groups = len(groups)
        self.stats.start_time = datetime.now()
        self._thread = threading.Thread(
            target=self._run,
            args=(message, accounts, groups),
            daemon=True,
        )
        self._running = True
        self._thread.start()

    def pause(self):
        self._pause_event.clear()

    def resume(self):
        self._pause_event.set()

    def stop(self):
        self._stop_flag = True
        self._pause_event.set()

    def retry_failed(
        self,
        on_update: Optional[Callable] = None,
        on_done: Optional[Callable] = None,
    ):
        """Retry all previously failed groups using the same message and accounts."""
        failed = list(self.stats.failed_groups)
        if not failed or not self._last_accounts or not self._last_message:
            return
        self.start(
            message=self._last_message,
            accounts=self._last_accounts,
            groups=failed,
            on_update=on_update,
            on_done=on_done,
        )

    def _run(self, message: str, accounts: List[str], groups: List[str]):
        api_id = get_api_id()
        api_hash = get_api_hash()
        if not api_id or not api_hash:
            self.stats.add_log("❌ API not configured")
            self._running = False
            if self._on_done:
                self._on_done(self.stats)
            return

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(
                self._async_loop(loop, api_id, api_hash, message, accounts, groups)
            )
        finally:
            loop.close()
            self._running = False
            if self._on_done:
                self._on_done(self.stats)

    async def _async_loop(self, loop, api_id, api_hash, message, accounts, groups):
        account_idx = 0
        round_num = 0
        msg_preview = message[:50]

        while not self._stop_flag:
            round_num += 1
            self.stats.rounds = round_num
            self.stats.add_log(
                f"🔄 Round {round_num} started ({len(groups)} groups, {len(accounts)} accounts)"
            )
            if self._on_update:
                self._on_update(self.stats)

            for group_link in groups:
                if self._stop_flag:
                    break

                self._pause_event.wait()
                if self._stop_flag:
                    break

                phone = accounts[account_idx % len(accounts)]
                account_idx += 1
                display_name = self._phone_to_name.get(phone, phone)

                # Mark as "Sending" in mapping
                self.stats.add_mapping(display_name, group_link, "⏳ Sending",
                                       group_link, msg_preview)
                if self._on_update:
                    self._on_update(self.stats)

                session = _session_path(phone)
                client = TelegramClient(session, api_id, api_hash)

                sent = False
                try:
                    await client.connect()
                    if not await client.is_user_authorized():
                        await client.disconnect()
                        self.stats.failed += 1
                        self.stats.failed_groups.append(group_link)
                        self.stats.add_log(f"⚠️ {display_name}: session expired")
                        self.stats.add_mapping(display_name, group_link, "❌ Expired",
                                               group_link, msg_preview)
                        if self._on_update:
                            self._on_update(self.stats)
                        continue

                    entity = await client.get_entity(group_link)
                    await client.send_message(entity, message)
                    self.stats.sent += 1
                    sent = True
                    self.stats.add_log(f"✅ {display_name} → {group_link}")
                    self.stats.add_mapping(display_name, group_link, "✅ Sent",
                                           group_link, msg_preview)

                except (UserBannedInChannelError, ChatWriteForbiddenError, ChatAdminRequiredError) as e:
                    self.stats.failed += 1
                    self.stats.banned += 1
                    reason = type(e).__name__
                    log_ban(phone, group_link, reason)
                    self.stats.add_log(f"🚫 {display_name} banned in {group_link}: {reason}")
                    self.stats.failed_groups.append(group_link)
                    self.stats.add_mapping(display_name, group_link, "🚫 Banned",
                                           group_link, msg_preview)

                except UserNotParticipantError:
                    self.stats.failed += 1
                    self.stats.add_log(f"⚠️ {display_name} not in {group_link}")
                    self.stats.failed_groups.append(group_link)
                    self.stats.add_mapping(display_name, group_link, "❌ Not Member",
                                           group_link, msg_preview)

                except FloodWaitError as e:
                    self.stats.failed += 1
                    wait = min(e.seconds, 60)
                    self.stats.add_log(f"⏳ {display_name}: flood wait {e.seconds}s (capped {wait}s)")
                    self.stats.failed_groups.append(group_link)
                    self.stats.add_mapping(display_name, group_link, "⏳ FloodWait",
                                           group_link, msg_preview)
                    await asyncio.sleep(wait)

                except PeerFloodError:
                    self.stats.failed += 1
                    self.stats.add_log(f"🚫 {display_name}: PeerFlood - rate limited")
                    self.stats.failed_groups.append(group_link)
                    self.stats.add_mapping(display_name, group_link, "🚫 PeerFlood",
                                           group_link, msg_preview)

                except SlowModeWaitError as e:
                    self.stats.failed += 1
                    self.stats.add_log(f"🐌 {group_link}: slow mode {e.seconds}s")
                    self.stats.failed_groups.append(group_link)
                    self.stats.add_mapping(display_name, group_link, "🐌 SlowMode",
                                           group_link, msg_preview)

                except Exception as e:
                    self.stats.failed += 1
                    self.stats.add_log(f"❌ {display_name} → {group_link}: {str(e)[:60]}")
                    self.stats.failed_groups.append(group_link)
                    self.stats.add_mapping(display_name, group_link, "❌ Failed",
                                           group_link, msg_preview)

                finally:
                    try:
                        await client.disconnect()
                    except Exception:
                        pass

                # Update pending count
                self.stats.pending = max(
                    0,
                    self.stats._total_groups - self.stats.sent - self.stats.failed,
                )
                if self._on_update:
                    self._on_update(self.stats)

                if not self._stop_flag and sent:
                    await asyncio.sleep(SEND_DELAY)

            if not self._stop_flag:
                self.stats.add_log(
                    f"⏸️ Round {round_num} complete. Waiting {int(ROUND_DELAY)}s before next round..."
                )
                if self._on_update:
                    self._on_update(self.stats)

                for _ in range(int(ROUND_DELAY)):
                    if self._stop_flag:
                        break
                    self._pause_event.wait()
                    await asyncio.sleep(1)


advanced_broadcaster = AdvancedBroadcaster()

__all__ = [
    "AdvancedBroadcaster",
    "BroadcastStats",
    "advanced_broadcaster",
    "SEND_DELAY",
    "ROUND_DELAY",
]
