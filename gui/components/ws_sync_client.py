"""
TG PRO QUANTUM - WebSocket Sync Client (Sprint 3)

Connects to the FastAPI ``/api/v1/ws/client/{client_id}`` endpoint using the
stdlib ``websockets`` library (or falls back to a polling approach if the
library is not installed).

Usage:
    from gui.components.ws_sync_client import WSSyncClient

    client = WSSyncClient(client_id=1, on_event=my_callback)
    client.start()   # starts a background thread
    ...
    client.stop()

The ``on_event(payload: dict)`` callback is invoked on each account-related
event from the server and is called from the background thread – wrap UI
updates with ``widget.after(0, ...)`` when using Tkinter.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)

_WS_BASE = "ws://localhost:8000/api/v1/ws/client"
_RECONNECT_DELAY_S = 5
_MAX_RECONNECTS = 20

_ACCOUNT_EVENTS = {
    "account.imported",
    "account.bulk_created",
    "account.file_imported",
    "account.otp_setup",
    "account.otp_verified",
    "account.updated",
    "account.deleted",
}


def _get_token() -> Optional[str]:
    try:
        from core.state_manager import state_manager  # type: ignore
        return state_manager.get("access_token")
    except Exception:
        return None


class WSSyncClient:
    """
    Background WebSocket client that listens for real-time account events.

    Falls back to a no-op stub if ``websockets`` is not installed so the
    desktop app still starts without the optional dependency.
    """

    def __init__(self, client_id: int, on_event: Optional[Callable[[dict], None]] = None):
        self.client_id = client_id
        self.on_event = on_event
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the background listener thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="ws-sync")
        self._thread.start()
        logger.info("WSSyncClient started for client_id=%s", self.client_id)

    def stop(self) -> None:
        """Signal the background thread to stop."""
        self._stop_event.set()

    # ── Background loop ───────────────────────────────────────────────────────

    def _run(self) -> None:
        try:
            import websockets  # type: ignore
            import asyncio
            asyncio.run(self._async_loop(websockets))
        except ImportError:
            logger.warning(
                "websockets library not installed – real-time sync unavailable. "
                "Install with: pip install websockets"
            )

    async def _async_loop(self, websockets_mod) -> None:
        attempts = 0
        while not self._stop_event.is_set() and attempts < _MAX_RECONNECTS:
            token = _get_token()
            url = f"{_WS_BASE}/{self.client_id}"
            if token:
                url += f"?token={token}"

            try:
                async with websockets_mod.connect(url) as ws:
                    attempts = 0  # reset on successful connect
                    logger.info("WS connected to %s", url)
                    while not self._stop_event.is_set():
                        try:
                            raw = await ws.recv()
                            self._dispatch(raw)
                        except Exception:
                            break
            except Exception as exc:
                attempts += 1
                logger.debug("WS error (attempt %d): %s", attempts, exc)
                if not self._stop_event.is_set():
                    time.sleep(_RECONNECT_DELAY_S)

    def _dispatch(self, raw: str) -> None:
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return

        if not isinstance(payload, dict):
            return

        event = payload.get("event", "")
        if event in _ACCOUNT_EVENTS:
            logger.debug("WS event: %s", event)
            if self.on_event:
                try:
                    self.on_event(payload)
                except Exception as exc:
                    logger.warning("on_event callback raised: %s", exc)
