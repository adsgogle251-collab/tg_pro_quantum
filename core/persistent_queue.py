"""
core/persistent_queue.py - Persistent join queue with resume support

Queue state is stored in data/join_queue.json so that interrupted sessions
can be resumed from where they stopped.
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Optional

from core.utils import DATA_DIR

QUEUE_FILE = DATA_DIR / "join_queue.json"


class PersistentQueue:
    """Thread-safe persistent queue for join sessions."""

    def __init__(self):
        self._lock = Lock()
        self._state: dict = {}

    # ─────────────────────────────────────────────────────────────────
    # Persistence
    # ─────────────────────────────────────────────────────────────────

    def _save(self):
        try:
            QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(QUEUE_FILE, "w", encoding="utf-8") as f:
                json.dump(self._state, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def load(self) -> Optional[dict]:
        """Load persisted queue from disk. Returns state dict or None."""
        if not QUEUE_FILE.exists():
            return None
        try:
            with open(QUEUE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("status") in ("paused", "running"):
                with self._lock:
                    self._state = data
                return data
        except Exception:
            pass
        return None

    # ─────────────────────────────────────────────────────────────────
    # Session management
    # ─────────────────────────────────────────────────────────────────

    def create_session(self, groups: list[dict], accounts: list[str]) -> str:
        """Create a new session and persist it. Returns session_id."""
        session_id = str(uuid.uuid4())
        queue_items = []
        for g in groups:
            queue_items.append({
                "group_id": g.get("group_id") or g.get("id") or 0,
                "group_name": g.get("group_title") or g.get("title") or g.get("group_link", ""),
                "group_link": g.get("group_link", ""),
                "status": "pending",
                "account": None,
                "time": None,
                "reason": "",
            })
        with self._lock:
            self._state = {
                "session_id": session_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "running",
                "total_groups": len(groups),
                "completed": 0,
                "joined": 0,
                "failed": 0,
                "banned": 0,
                "accounts": accounts,
                "queue": queue_items,
            }
            self._save()
        return session_id

    def mark_item(
        self,
        index: int,
        status: str,
        account: Optional[str] = None,
        reason: str = "",
    ):
        """Mark a queue item (joined / failed / banned / skipped)."""
        with self._lock:
            if 0 <= index < len(self._state.get("queue", [])):
                item = self._state["queue"][index]
                item["status"] = status
                item["account"] = account
                item["time"] = datetime.now().strftime("%H:%M:%S")
                item["reason"] = reason
                # Update counters
                self._state["completed"] = sum(
                    1 for i in self._state["queue"] if i["status"] != "pending"
                )
                self._state["joined"] = sum(
                    1 for i in self._state["queue"] if i["status"] == "joined"
                )
                self._state["failed"] = sum(
                    1 for i in self._state["queue"] if i["status"] == "failed"
                )
                self._state["banned"] = sum(
                    1 for i in self._state["queue"] if i["status"] == "banned"
                )
                self._save()

    def pause(self):
        with self._lock:
            self._state["status"] = "paused"
            self._save()

    def resume(self):
        with self._lock:
            self._state["status"] = "running"
            self._save()

    def complete(self):
        with self._lock:
            self._state["status"] = "completed"
            self._state["completed_at"] = datetime.now(timezone.utc).isoformat()
            self._save()

    def stop(self):
        with self._lock:
            self._state["status"] = "stopped"
            self._save()

    def clear(self):
        with self._lock:
            self._state = {}
            if QUEUE_FILE.exists():
                try:
                    QUEUE_FILE.unlink()
                except Exception:
                    pass

    # ─────────────────────────────────────────────────────────────────
    # Accessors
    # ─────────────────────────────────────────────────────────────────

    @property
    def state(self) -> dict:
        with self._lock:
            return dict(self._state)

    def pending_items(self) -> list[tuple[int, dict]]:
        """Return (index, item) pairs that are still pending."""
        with self._lock:
            return [
                (i, item)
                for i, item in enumerate(self._state.get("queue", []))
                if item["status"] == "pending"
            ]

    def has_resumable(self) -> bool:
        """Return True if a paused/interrupted session exists on disk."""
        data = self.load()
        if data and data.get("status") in ("paused", "running", "stopped"):
            total = data.get("total_groups", 0)
            completed = data.get("completed", 0)
            return completed < total
        return False

    def resume_info(self) -> Optional[dict]:
        """Return info about the resumable session (for UI prompt)."""
        if not QUEUE_FILE.exists():
            return None
        try:
            with open(QUEUE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("status") in ("paused", "running", "stopped"):
                return {
                    "session_id": data.get("session_id", ""),
                    "total": data.get("total_groups", 0),
                    "completed": data.get("completed", 0),
                    "created_at": data.get("created_at", ""),
                }
        except Exception:
            pass
        return None


# Singleton
persistent_queue = PersistentQueue()

__all__ = ["PersistentQueue", "persistent_queue"]
