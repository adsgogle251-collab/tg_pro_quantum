"""
core/broadcast.py - Message broadcasting with real-time progress tracking.

Usage
-----
engine = BroadcastEngine()
engine.start(message, groups, accounts, min_delay, max_delay,
             on_update=callback, on_done=callback)
engine.pause()
engine.resume()
engine.stop()
"""
import asyncio
import random
import sqlite3
import threading
import time
from datetime import datetime
from typing import Callable

from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError,
    ChatWriteForbiddenError,
    UserBannedInChannelError,
    UserNotParticipantError,
    PeerFloodError,
)

from core.config import BROADCASTS_DB, get_api_id, get_api_hash
from core.account import _session_path


# ─────────────────────────────────────────────────────────────────────────────
# Database helpers
# ─────────────────────────────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(BROADCASTS_DB))
    conn.row_factory = sqlite3.Row
    return conn


def list_broadcasts() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM broadcasts ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def save_broadcast(name: str, sent: int, failed: int, total: int, duration: float):
    with _conn() as conn:
        conn.execute("""
            INSERT INTO broadcasts (name, sent, failed, total, duration, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, sent, failed, total, duration, datetime.utcnow().isoformat()))
        conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Progress data class
# ─────────────────────────────────────────────────────────────────────────────

class BroadcastProgress:
    def __init__(self, total: int):
        self.total   = total
        self.sent    = 0
        self.failed  = 0
        self.pending = total
        self.log: list[str] = []   # newest first

    @property
    def done(self) -> int:
        return self.sent + self.failed

    def add_log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log.insert(0, f"[{ts}] {msg}")
        # Keep log bounded
        if len(self.log) > 500:
            self.log = self.log[:500]


# ─────────────────────────────────────────────────────────────────────────────
# Engine
# ─────────────────────────────────────────────────────────────────────────────

class BroadcastEngine:
    """Thread-safe broadcast engine."""

    def __init__(self):
        self._thread: threading.Thread | None = None
        self._stop_flag  = False
        self._pause_event = threading.Event()
        self._pause_event.set()   # not paused by default
        self.progress: BroadcastProgress | None = None
        self._on_update: Callable | None = None
        self._on_done: Callable | None = None
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_paused(self) -> bool:
        return not self._pause_event.is_set()

    def start(
        self,
        message: str,
        groups: list[str],
        accounts: list[str],
        min_delay: float = 3.0,
        max_delay: float = 8.0,
        on_update: Callable[["BroadcastProgress"], None] | None = None,
        on_done: Callable[["BroadcastProgress"], None] | None = None,
        broadcast_name: str = "",
    ):
        """Start broadcasting in a background thread."""
        if self._running:
            return

        self.progress = BroadcastProgress(len(groups))
        self._stop_flag  = False
        self._pause_event.set()
        self._on_update  = on_update
        self._on_done    = on_done
        self._running    = True
        self._start_time = time.time()
        self._broadcast_name = broadcast_name or datetime.now().strftime("Broadcast %Y-%m-%d %H:%M")

        self._thread = threading.Thread(
            target=self._run,
            args=(message, groups, accounts, min_delay, max_delay),
            daemon=True
        )
        self._thread.start()

    def pause(self):
        """Pause the broadcast."""
        if self._running and self._pause_event.is_set():
            self._pause_event.clear()
            if self.progress:
                self.progress.add_log("⏸️ Broadcast paused.")

    def resume(self):
        """Resume a paused broadcast."""
        if self._running and not self._pause_event.is_set():
            self._pause_event.set()
            if self.progress:
                self.progress.add_log("▶️ Broadcast resumed.")

    def stop(self):
        """Stop the broadcast."""
        self._stop_flag = True
        self._pause_event.set()   # unblock any wait

    # ── Internal ──────────────────────────────────────────────────────────────

    def _notify(self):
        if self._on_update and self.progress:
            try:
                self._on_update(self.progress)
            except Exception:
                pass

    def _run(
        self,
        message: str,
        groups: list[str],
        accounts: list[str],
        min_delay: float,
        max_delay: float,
    ):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                self._async_run(message, groups, accounts, min_delay, max_delay)
            )
        finally:
            loop.close()
            self._running = False
            duration = time.time() - self._start_time
            if self.progress:
                save_broadcast(
                    self._broadcast_name,
                    self.progress.sent,
                    self.progress.failed,
                    self.progress.total,
                    round(duration, 1),
                )
                self.progress.add_log(
                    f"✅ Finished — Sent: {self.progress.sent}, "
                    f"Failed: {self.progress.failed}, "
                    f"Time: {duration:.0f}s"
                )
            if self._on_done and self.progress:
                try:
                    self._on_done(self.progress)
                except Exception:
                    pass

    async def _async_run(
        self,
        message: str,
        groups: list[str],
        accounts: list[str],
        min_delay: float,
        max_delay: float,
    ):
        if not accounts:
            if self.progress:
                self.progress.add_log("❌ No accounts selected.")
            return

        api_id   = get_api_id()
        api_hash = get_api_hash()
        if not api_id or not api_hash:
            if self.progress:
                self.progress.add_log("❌ API not configured.")
            return

        account_idx = 0

        for group in groups:
            # Check stop
            if self._stop_flag:
                if self.progress:
                    self.progress.add_log("⏹️ Broadcast stopped by user.")
                break

            # Check pause (block until resumed)
            self._pause_event.wait()
            if self._stop_flag:
                break

            phone = accounts[account_idx % len(accounts)]
            account_idx += 1

            session = _session_path(phone)
            client  = TelegramClient(session, api_id, api_hash)

            try:
                await client.connect()
                if not await client.is_user_authorized():
                    if self.progress:
                        self.progress.failed  += 1
                        self.progress.pending -= 1
                        self.progress.add_log(f"❌ {group} — account {phone} session expired")
                    self._notify()
                    await client.disconnect()
                    continue

                await client.send_message(group, message)

                if self.progress:
                    self.progress.sent    += 1
                    self.progress.pending -= 1
                    self.progress.add_log(f"✅ Sent → {group} (via {phone})")
                self._notify()

            except FloodWaitError as e:
                if self.progress:
                    self.progress.failed  += 1
                    self.progress.pending -= 1
                    self.progress.add_log(
                        f"⚠️ FloodWait {e.seconds}s — {group}"
                    )
                self._notify()
                await asyncio.sleep(min(e.seconds, 60))

            except (ChatWriteForbiddenError, UserBannedInChannelError,
                    UserNotParticipantError, PeerFloodError) as e:
                if self.progress:
                    self.progress.failed  += 1
                    self.progress.pending -= 1
                    self.progress.add_log(f"❌ {group} — {type(e).__name__}")
                self._notify()

            except Exception as e:
                if self.progress:
                    self.progress.failed  += 1
                    self.progress.pending -= 1
                    self.progress.add_log(f"❌ {group} — {e}")
                self._notify()

            finally:
                try:
                    await client.disconnect()
                except Exception:
                    pass

            # Delay between sends
            delay = random.uniform(min_delay, max_delay)
            await asyncio.sleep(delay)


# Singleton for GUI use
broadcast_engine = BroadcastEngine()
