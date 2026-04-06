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

    def add_log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log.insert(0, f"[{ts}] {msg}")
        if len(self.log) > 1000:
            self.log = self.log[:1000]

    @property
    def total(self) -> int:
        return self.sent + self.failed


class AdvancedBroadcaster:
    """
    Round-robin broadcaster:
    - Cycles through accounts fairly across groups
    - After a full round waits ROUND_DELAY seconds then restarts
    - 24/7 continuous until manually stopped
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
        self.stats = BroadcastStats()
        self.stats.pending = len(groups)
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

                session = _session_path(phone)
                client = TelegramClient(session, api_id, api_hash)

                sent = False
                try:
                    await client.connect()
                    if not await client.is_user_authorized():
                        await client.disconnect()
                        self.stats.failed += 1
                        self.stats.add_log(f"⚠️ {phone}: session expired")
                        if self._on_update:
                            self._on_update(self.stats)
                        continue

                    entity = await client.get_entity(group_link)
                    await client.send_message(entity, message)
                    self.stats.sent += 1
                    sent = True
                    self.stats.add_log(f"✅ {phone} → {group_link}")

                except (UserBannedInChannelError, ChatWriteForbiddenError, ChatAdminRequiredError) as e:
                    self.stats.failed += 1
                    self.stats.banned += 1
                    reason = type(e).__name__
                    log_ban(phone, group_link, reason)
                    self.stats.add_log(f"🚫 {phone} banned in {group_link}: {reason}")

                except UserNotParticipantError:
                    self.stats.failed += 1
                    self.stats.add_log(f"⚠️ {phone} not in {group_link}")

                except FloodWaitError as e:
                    self.stats.failed += 1
                    wait = min(e.seconds, 60)
                    self.stats.add_log(f"⏳ {phone}: flood wait {e.seconds}s (capped {wait}s)")
                    await asyncio.sleep(wait)

                except PeerFloodError:
                    self.stats.failed += 1
                    self.stats.add_log(f"🚫 {phone}: PeerFlood - rate limited")

                except SlowModeWaitError as e:
                    self.stats.failed += 1
                    self.stats.add_log(f"🐌 {group_link}: slow mode {e.seconds}s")

                except Exception as e:
                    self.stats.failed += 1
                    self.stats.add_log(f"❌ {phone} → {group_link}: {str(e)[:60]}")

                finally:
                    try:
                        await client.disconnect()
                    except Exception:
                        pass

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
