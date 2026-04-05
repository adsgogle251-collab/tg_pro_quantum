"""TG PRO QUANTUM - Broadcast Manager
Real broadcast workflow:
1. Load target groups (from valid.txt or campaign)
2. Load active accounts (assigned to broadcast feature + validate sessions)
3. Prepare messages
4. Distribute accounts per group (round-robin)
5. Send with proper delays
6. Track progress (sent, failed, pending) - REAL
7. Provide real-time updates via callbacks
8. Handle errors gracefully
9. Log all activity events
"""
from __future__ import annotations

import asyncio
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .utils import (
    DATA_DIR, SESSIONS_DIR, GROUPS_VALID_FILE,
    log, log_error,
)
from .account_manager import account_manager
from .account_router import account_router, Feature
from . import campaign_manager as _cm_module


# ── Helper ─────────────────────────────────────────────────────────────────

def _load_valid_groups() -> List[str]:
    """Load target group links from data/groups/valid.txt."""
    groups: List[str] = []
    if GROUPS_VALID_FILE.exists():
        try:
            with open(GROUPS_VALID_FILE, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        groups.append(line)
        except Exception as exc:
            log_error(f"broadcast_manager: failed to load valid groups: {exc}")
    return groups


def _check_session(account_name: str) -> bool:
    """Return True if a .session file exists for *account_name*."""
    session_file = SESSIONS_DIR / f"{account_name}.session"
    return session_file.exists() and session_file.stat().st_size > 100


# ── Main class ─────────────────────────────────────────────────────────────

class BroadcastManager:
    """
    Orchestrates the full broadcast lifecycle.

    It wraps the low-level :class:`~core.broadcast_engine.BroadcastEngine`
    and adds:
    * Account health tracking
    * Group loading / validation
    * Activity logging
    * Real-time progress state
    * Pause / resume / stop controls
    """

    def __init__(self) -> None:
        # Control flags
        self.running: bool = False
        self.paused: bool = False

        # Live stats (updated during a broadcast run)
        self.stats: Dict[str, Any] = self._empty_stats()

        # Activity log: newest entry first
        self.activity_log: List[Dict[str, Any]] = []

        # Accounts currently participating in this broadcast
        self.active_accounts: List[Dict[str, Any]] = []

        # Target groups for this broadcast
        self.target_groups: List[str] = []

        # Current campaign id (if started via campaign)
        self.current_campaign_id: Optional[str] = None

        # Callbacks registered by the UI
        self._progress_cb: Optional[Callable] = None
        self._activity_cb: Optional[Callable] = None

        # Background thread / event loop
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    # ── Public API ─────────────────────────────────────────────────────────

    def start(
        self,
        message: str,
        accounts: Optional[List[str]] = None,
        groups: Optional[List[str]] = None,
        delay_min: int = 10,
        delay_max: int = 30,
        round_robin: bool = True,
        campaign_id: Optional[str] = None,
        progress_callback: Optional[Callable] = None,
        activity_callback: Optional[Callable] = None,
    ) -> bool:
        """
        Start a broadcast in a background thread.

        If *accounts* is None the manager auto-selects all accounts that have
        the "broadcast" feature assigned AND have a valid session file.

        If *groups* is None the manager loads from data/groups/valid.txt.

        Returns True if the broadcast thread was started.
        """
        if self.running:
            log("BroadcastManager: already running", "warning")
            return False

        # Resolve accounts
        resolved_accounts = self._resolve_accounts(accounts)
        if not resolved_accounts:
            log("BroadcastManager: no active accounts available", "error")
            return False

        # Resolve groups
        resolved_groups = groups if groups else _load_valid_groups()
        if not resolved_groups:
            log("BroadcastManager: no target groups found – add groups via Finder tab first", "error")
            return False

        self.current_campaign_id = campaign_id
        self._progress_cb = progress_callback
        self._activity_cb = activity_callback

        # Build active_accounts metadata (for detail page)
        self.active_accounts = self._build_account_meta(resolved_accounts)
        self.target_groups = list(resolved_groups)

        # Reset state
        self.stats = self._empty_stats()
        self.stats["total"] = len(resolved_groups)
        self.stats["accounts_total"] = len(resolved_accounts)
        self.stats["_start_ts"] = time.time()
        self.activity_log = []
        self.running = True
        self.paused = False

        # Start background thread
        self._thread = threading.Thread(
            target=self._run_sync,
            kwargs={
                "accounts": resolved_accounts,
                "groups": resolved_groups,
                "message": message,
                "delay_min": delay_min,
                "delay_max": delay_max,
                "round_robin": round_robin,
            },
            daemon=True,
        )
        self._thread.start()
        log(
            f"BroadcastManager: started – {len(resolved_accounts)} accounts, "
            f"{len(resolved_groups)} groups",
            "success",
        )
        return True

    def pause(self) -> None:
        """Pause the running broadcast."""
        if self.running and not self.paused:
            self.paused = True
            log("BroadcastManager: paused", "warning")

    def resume(self) -> None:
        """Resume a paused broadcast."""
        if self.running and self.paused:
            self.paused = False
            log("BroadcastManager: resumed", "success")

    def stop(self) -> None:
        """Stop the broadcast immediately."""
        self.running = False
        self.paused = False
        log("BroadcastManager: stopped", "warning")

    def get_status(self) -> Dict[str, Any]:
        """Return a snapshot of the current broadcast state for the UI."""
        return {
            "running": self.running,
            "paused": self.paused,
            "stats": dict(self.stats),
            "active_accounts": list(self.active_accounts),
            "target_groups": list(self.target_groups),
            "activity_log": list(self.activity_log[:100]),
            "campaign_id": self.current_campaign_id,
        }

    def get_account_rows(self) -> List[Dict[str, Any]]:
        """Return account rows formatted for BroadcastDetailPage._account_rows."""
        return list(self.active_accounts)

    def register_progress_callback(self, cb: Callable) -> None:
        self._progress_cb = cb

    def register_activity_callback(self, cb: Callable) -> None:
        self._activity_cb = cb

    # ── Internal helpers ────────────────────────────────────────────────────

    @staticmethod
    def _empty_stats() -> Dict[str, Any]:
        return {
            "sent": 0,
            "failed": 0,
            "total": 0,
            "accounts_total": 0,
            "accounts_active": 0,
            "_start_ts": None,
        }

    def _resolve_accounts(self, accounts: Optional[List[str]]) -> List[str]:
        """
        Return account names to use for the broadcast.

        Priority:
        1. Explicit *accounts* list from caller
        2. Accounts assigned to the "broadcast" feature
        3. All accounts (fallback)

        Only includes accounts with a valid session file.
        """
        if accounts:
            candidates = accounts
        else:
            broadcast_accs = account_manager.get_accounts_by_feature("broadcast")
            if broadcast_accs:
                candidates = [a["name"] for a in broadcast_accs]
            else:
                candidates = [a["name"] for a in account_manager.get_all()]

        # Filter to those with valid sessions
        valid = [name for name in candidates if _check_session(name)]
        if not valid and candidates:
            # Fall back to all candidates even without session verification
            # (session check may fail in dev environments)
            log(
                "BroadcastManager: no session files found – using all candidates "
                "(broadcast may fail without valid sessions)",
                "warning",
            )
            valid = list(candidates)
        return valid

    def _build_account_meta(self, account_names: List[str]) -> List[Dict[str, Any]]:
        """Build account metadata dicts for the detail page."""
        result = []
        for name in account_names:
            acc = account_manager.get(name) or {}
            has_session = _check_session(name)
            status = "active" if has_session and acc.get("status", "active") == "active" else "inactive"
            result.append({
                "name": name,
                "status": status,
                "health": 100.0 if has_session else 30.0,
                "msgs": 0,
                "warnings": 0,
                "banned": acc.get("status", "") == "banned",
                "last_used": acc.get("last_active") or "--",
            })
        return result

    def _log_activity(self, account: str, group: str, success: bool, detail: str = "") -> None:
        """Record an activity event and fire the activity callback."""
        entry = {
            "ts": datetime.now().strftime("%H:%M:%S"),
            "account": account,
            "group": group,
            "success": success,
            "detail": detail,
        }
        self.activity_log.insert(0, entry)
        if len(self.activity_log) > 1000:
            self.activity_log = self.activity_log[:1000]
        if self._activity_cb:
            try:
                self._activity_cb(entry)
            except Exception:
                pass

    def _fire_progress(self, completed: bool = False, error: Optional[str] = None) -> None:
        """Fire the progress callback with current stats."""
        if not self._progress_cb:
            return
        total = max(self.stats["total"], 1)
        processed = self.stats["sent"] + self.stats["failed"]
        pct = min(100.0, processed / total * 100)
        try:
            self._progress_cb(
                sent=self.stats["sent"],
                failed=self.stats["failed"],
                total=self.stats["total"],
                progress_percent=pct,
                completed=completed,
                error=error,
                active_accounts=self.active_accounts,
            )
        except Exception:
            pass

    def _update_account_msgs(self, account_name: str) -> None:
        """Increment message count for an account in active_accounts list."""
        for acc in self.active_accounts:
            if acc["name"] == account_name:
                acc["msgs"] = acc.get("msgs", 0) + 1
                acc["last_used"] = datetime.now().strftime("%H:%M:%S")
                break

    # ── Broadcast loop (sync wrapper + async core) ─────────────────────────

    def _run_sync(self, **kwargs) -> None:
        """Thread entry point: run async broadcast on a fresh event loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        try:
            loop.run_until_complete(self._run_async(**kwargs))
        except Exception as exc:
            log_error(f"BroadcastManager: fatal error: {exc}")
            self._fire_progress(completed=True, error=str(exc))
        finally:
            loop.close()
            self._loop = None
            self.running = False

    async def _run_async(
        self,
        accounts: List[str],
        groups: List[str],
        message: str,
        delay_min: int,
        delay_max: int,
        round_robin: bool,
    ) -> None:
        """
        Core async broadcast loop.

        Iterates over target groups, distributes accounts in round-robin,
        and calls the existing broadcast_engine.send_message_real() for
        actual Telegram delivery.
        """
        import random

        # Late import to avoid circular imports at module load time
        from .broadcast_engine import broadcast_engine as _engine
        from .config_manager import get as _cfg_get

        api_id = _cfg_get("telegram.api_id", 0)
        api_hash = _cfg_get("telegram.api_hash", "")

        if not api_id or not api_hash:
            log_error(
                "BroadcastManager: API ID / API HASH not configured. "
                "Go to Settings tab and enter your Telegram API credentials."
            )
            self._fire_progress(
                completed=True,
                error="API ID/HASH not configured – go to Settings tab",
            )
            self.running = False
            return

        log("=" * 60, "info")
        log(f"🚀 BROADCAST STARTED: {len(accounts)} accounts, {len(groups)} groups", "success")
        log("=" * 60, "info")

        acc_idx = 0  # for round-robin

        for grp_idx, group in enumerate(groups, 1):
            if not self.running:
                log("BroadcastManager: stopped by user", "warning")
                break

            # Wait while paused
            while self.paused and self.running:
                await asyncio.sleep(0.5)

            if not self.running:
                break

            # Pick account (round-robin or sequential) – guard against empty list
            if not accounts:
                log_error("BroadcastManager: accounts list became empty during broadcast")
                break
            account = accounts[acc_idx % len(accounts)]
            if round_robin:
                acc_idx += 1

            log(f"📤 [{grp_idx}/{len(groups)}] {account} → {group}", "info")

            # Get Telegram client
            client = await _engine.get_client(account, api_id, api_hash)

            if not client:
                self.stats["failed"] += 1
                self._log_activity(account, group, False, "No valid session")
                self._fire_progress()
                continue

            # Send message
            success = await _engine.send_message_real(client, group, message)

            if success:
                self.stats["sent"] += 1
                self._update_account_msgs(account)
                self._log_activity(account, group, True)
            else:
                self.stats["failed"] += 1
                self._log_activity(account, group, False, "Send failed")

            self._fire_progress()

            # Rate-limit delay
            delay = random.uniform(delay_min, delay_max)
            elapsed = 0.0
            interval = 0.5
            while elapsed < delay and self.running:
                await asyncio.sleep(interval)
                elapsed += interval
                while self.paused and self.running:
                    await asyncio.sleep(0.5)

        # Save history
        try:
            from . import broadcast_history as _bh
            _bh.broadcast_history.add_broadcast(
                campaign_name=self.current_campaign_id or "Manual",
                accounts=accounts,
                groups=groups,
                sent=self.stats["sent"],
                failed=self.stats["failed"],
                duration_sec=int(time.time() - (self.stats.get("_start_ts") or time.time())),
            )
        except Exception as exc:
            log_error(f"BroadcastManager: failed to save history: {exc}")

        log("=" * 60, "success")
        log(f"✅ BROADCAST DONE – Sent: {self.stats['sent']}, Failed: {self.stats['failed']}", "success")
        log("=" * 60, "success")

        self.running = False
        self._fire_progress(completed=True)


# Global singleton
broadcast_manager = BroadcastManager()

__all__ = ["BroadcastManager", "broadcast_manager"]
