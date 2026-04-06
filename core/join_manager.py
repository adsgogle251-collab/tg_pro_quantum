"""
core/join_manager.py - Multi-account join automation for found groups
"""
import asyncio
import threading
import time
from typing import Callable, Optional
from datetime import datetime

from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError,
    UserAlreadyParticipantError,
    InviteHashExpiredError,
    ChannelPrivateError,
)
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest

from core.config import get_api_id, get_api_hash, save_account_group, list_group_search_results
from core.account import list_accounts, _session_path, update_account_status

MAX_FLOOD_WAIT = 60  # seconds: cap on flood-wait sleep duration


class JoinProgress:
    def __init__(self, total: int):
        self.total = total
        self.joined = 0
        self.failed = 0
        self.skipped = 0
        self.log: list[str] = []

    def add_log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log.insert(0, f"[{ts}] {msg}")
        if len(self.log) > 500:
            self.log = self.log[:500]


class JoinManager:
    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._stop_flag = False
        self.progress: Optional[JoinProgress] = None
        self._on_update: Optional[Callable] = None
        self._on_done: Optional[Callable] = None
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    def start(
        self,
        accounts: list[str],
        groups: list[dict],
        delay_between_joins: float = 3.0,
        on_update: Optional[Callable] = None,
        on_done: Optional[Callable] = None,
    ):
        if self._running:
            return
        self._stop_flag = False
        self._on_update = on_update
        self._on_done = on_done
        self.progress = JoinProgress(len(accounts) * len(groups))
        self._thread = threading.Thread(
            target=self._run,
            args=(accounts, groups, delay_between_joins),
            daemon=True,
        )
        self._running = True
        self._thread.start()

    def stop(self):
        self._stop_flag = True

    def _run(self, accounts: list[str], groups: list[dict], delay: float):
        api_id = get_api_id()
        api_hash = get_api_hash()

        if not api_id or not api_hash:
            if self.progress:
                self.progress.add_log("❌ API not configured")
            self._running = False
            if self._on_done:
                self._on_done(self.progress)
            return

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(
                self._async_run(loop, api_id, api_hash, accounts, groups, delay)
            )
        finally:
            loop.close()
            self._running = False
            if self._on_done:
                self._on_done(self.progress)

    async def _async_run(self, loop, api_id, api_hash, accounts, groups, delay):
        account_idx = 0

        for group_info in groups:
            if self._stop_flag:
                break

            group_link = group_info.get("group_link", "")
            group_title = group_info.get("title", group_link)

            if not accounts:
                break
            phone = accounts[account_idx % len(accounts)]
            account_idx += 1

            session = _session_path(phone)
            client = TelegramClient(session, api_id, api_hash)

            try:
                await client.connect()
                if not await client.is_user_authorized():
                    await client.disconnect()
                    self.progress.add_log(f"⚠️ {phone}: session expired, skipping")
                    self.progress.skipped += 1
                    if self._on_update:
                        self._on_update(self.progress)
                    continue

                link = group_link.replace("https://t.me/", "").replace("@", "")
                try:
                    if link.startswith("+") or (link.isalnum() and len(link) == 22):
                        await client(ImportChatInviteRequest(link.lstrip("+")))
                    else:
                        entity = await client.get_entity(group_link)
                        await client(JoinChannelRequest(entity))

                    save_account_group(phone, group_link)
                    self.progress.joined += 1
                    self.progress.add_log(f"✅ {phone} joined {group_title}")

                except UserAlreadyParticipantError:
                    save_account_group(phone, group_link)
                    self.progress.skipped += 1
                    self.progress.add_log(f"ℹ️ {phone} already in {group_title}")

                except (InviteHashExpiredError, ChannelPrivateError) as e:
                    self.progress.failed += 1
                    self.progress.add_log(f"❌ {group_title}: {e}")

                except FloodWaitError as e:
                    self.progress.add_log(f"⏳ {phone}: flood wait {e.seconds}s")
                    await asyncio.sleep(min(e.seconds, MAX_FLOOD_WAIT))
                    self.progress.failed += 1

                await client.disconnect()

            except Exception as e:
                try:
                    await client.disconnect()
                except Exception:
                    pass
                self.progress.failed += 1
                self.progress.add_log(f"❌ {phone} → {group_title}: {str(e)[:60]}")

            if self._on_update:
                self._on_update(self.progress)

            if not self._stop_flag:
                await asyncio.sleep(delay)


join_manager = JoinManager()

__all__ = ["JoinManager", "JoinProgress", "join_manager"]
