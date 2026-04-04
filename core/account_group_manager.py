"""Account Group Manager - Enterprise Multi-Feature Group Management"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from .utils import DATA_DIR, log, log_error

ACCOUNT_GROUPS_FILE = DATA_DIR / "account_groups_v2.json"

FEATURE_TYPES = ["broadcast", "finder", "scrape", "join", "cs", "warmer", "general"]


class AccountGroupManager:
    """
    Manages named account groups that can be assigned to specific features.
    Groups are stored in a JSON file with metadata, feature assignments, and health info.
    """

    def __init__(self):
        self.groups: Dict[str, dict] = {}
        self._load()

    # ─────────────────────────────────────────────────────────────────
    # Persistence
    # ─────────────────────────────────────────────────────────────────

    def _load(self):
        if ACCOUNT_GROUPS_FILE.exists():
            try:
                with open(ACCOUNT_GROUPS_FILE, "r", encoding="utf-8") as f:
                    self.groups = json.load(f)
                log(f"Loaded {len(self.groups)} account groups", "info")
            except Exception as e:
                log_error(f"Failed to load account groups: {e}")
                self.groups = {}

    def _save(self):
        try:
            ACCOUNT_GROUPS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(ACCOUNT_GROUPS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.groups, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log_error(f"Failed to save account groups: {e}")

    # ─────────────────────────────────────────────────────────────────
    # CRUD
    # ─────────────────────────────────────────────────────────────────

    def create_group(self, name: str, feature_type: str = "general",
                     client_id: Optional[str] = None, config: Optional[dict] = None) -> str:
        """Create a new account group. Returns group_id."""
        group_id = f"GRP_{uuid.uuid4().hex[:8].upper()}"
        self.groups[group_id] = {
            "id": group_id,
            "name": name,
            "feature_type": feature_type if feature_type in FEATURE_TYPES else "general",
            "client_id": client_id,
            "status": "active",
            "config": config or {},
            "accounts": [],
            "health": {
                "total": 0,
                "healthy": 0,
                "warning": 0,
                "banned": 0,
                "avg_health_score": 100.0,
            },
            "analytics": {
                "messages_sent": 0,
                "success_rate": 0.0,
                "last_activity": None,
            },
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        self._save()
        log(f"Account group created: {name} ({group_id})", "success")
        return group_id

    def get_group(self, group_id: str) -> Optional[dict]:
        return self.groups.get(group_id)

    def get_all_groups(self) -> List[dict]:
        self._load()
        return list(self.groups.values())

    def get_groups_by_feature(self, feature_type: str) -> List[dict]:
        return [g for g in self.groups.values() if g.get("feature_type") == feature_type]

    def get_groups_by_client(self, client_id: str) -> List[dict]:
        return [g for g in self.groups.values() if g.get("client_id") == client_id]

    def update_group(self, group_id: str, **kwargs) -> bool:
        if group_id not in self.groups:
            return False
        allowed = {"name", "feature_type", "client_id", "status", "config"}
        for key, value in kwargs.items():
            if key in allowed:
                self.groups[group_id][key] = value
        self.groups[group_id]["updated_at"] = datetime.now().isoformat()
        self._save()
        return True

    def delete_group(self, group_id: str) -> bool:
        if group_id not in self.groups:
            return False
        name = self.groups[group_id]["name"]
        del self.groups[group_id]
        self._save()
        log(f"Account group deleted: {name} ({group_id})", "info")
        return True

    # ─────────────────────────────────────────────────────────────────
    # Account membership
    # ─────────────────────────────────────────────────────────────────

    def add_account(self, group_id: str, account_name: str) -> bool:
        if group_id not in self.groups:
            return False
        if account_name not in self.groups[group_id]["accounts"]:
            self.groups[group_id]["accounts"].append(account_name)
            self._update_health_counts(group_id)
            self._save()
        return True

    def add_accounts_bulk(self, group_id: str, account_names: List[str]) -> int:
        """Add multiple accounts; returns count of newly added."""
        if group_id not in self.groups:
            return 0
        existing = set(self.groups[group_id]["accounts"])
        new_accounts = [a for a in account_names if a not in existing]
        self.groups[group_id]["accounts"].extend(new_accounts)
        self._update_health_counts(group_id)
        self._save()
        return len(new_accounts)

    def remove_account(self, group_id: str, account_name: str) -> bool:
        if group_id not in self.groups:
            return False
        accounts = self.groups[group_id]["accounts"]
        if account_name in accounts:
            accounts.remove(account_name)
            self._update_health_counts(group_id)
            self._save()
            return True
        return False

    def move_account(self, account_name: str, from_group_id: str, to_group_id: str) -> bool:
        """Move account from one group to another."""
        if self.remove_account(from_group_id, account_name):
            return self.add_account(to_group_id, account_name)
        return False

    def get_group_accounts(self, group_id: str) -> List[str]:
        group = self.groups.get(group_id)
        return list(group["accounts"]) if group else []

    # ─────────────────────────────────────────────────────────────────
    # Health monitoring
    # ─────────────────────────────────────────────────────────────────

    def _update_health_counts(self, group_id: str):
        group = self.groups.get(group_id)
        if not group:
            return
        total = len(group["accounts"])
        group["health"]["total"] = total

    def update_account_health(self, group_id: str, account_name: str,
                               health_score: float, status: str = "healthy"):
        """Update health info for an account in the group."""
        group = self.groups.get(group_id)
        if not group:
            return
        accounts = group["accounts"]
        total = len(accounts)
        if total == 0:
            return
        # Simple running average update
        old_avg = group["health"].get("avg_health_score", 100.0)
        group["health"]["avg_health_score"] = round(
            (old_avg * (total - 1) + health_score) / total, 2
        )
        if status == "banned":
            group["health"]["banned"] = group["health"].get("banned", 0) + 1
        elif status == "warning":
            group["health"]["warning"] = group["health"].get("warning", 0) + 1
        healthy = total - group["health"].get("banned", 0) - group["health"].get("warning", 0)
        group["health"]["healthy"] = max(0, healthy)
        self._save()

    def get_group_health(self, group_id: str) -> dict:
        group = self.groups.get(group_id)
        if not group:
            return {}
        return group.get("health", {})

    # ─────────────────────────────────────────────────────────────────
    # Analytics
    # ─────────────────────────────────────────────────────────────────

    def record_broadcast_activity(self, group_id: str, messages_sent: int, success: int):
        group = self.groups.get(group_id)
        if not group:
            return
        analytics = group.setdefault("analytics", {
            "messages_sent": 0, "success_rate": 0.0, "last_activity": None
        })
        total_prev = analytics.get("messages_sent", 0)
        total_new = total_prev + messages_sent
        if total_new > 0:
            prev_rate = analytics.get("success_rate", 0.0)
            analytics["success_rate"] = round(
                (prev_rate * total_prev + (success / messages_sent * 100 if messages_sent else 0) * messages_sent) / total_new,
                2
            )
        analytics["messages_sent"] = total_new
        analytics["last_activity"] = datetime.now().isoformat()
        self._save()

    def get_summary(self) -> dict:
        """Return platform-wide summary of all groups."""
        self._load()
        total_groups = len(self.groups)
        total_accounts = sum(len(g.get("accounts", [])) for g in self.groups.values())
        active_groups = sum(1 for g in self.groups.values() if g.get("status") == "active")
        return {
            "total_groups": total_groups,
            "active_groups": active_groups,
            "total_accounts": total_accounts,
        }

    # ─────────────────────────────────────────────────────────────────
    # Import / Export
    # ─────────────────────────────────────────────────────────────────

    def import_accounts_from_text(self, group_id: str, text: str) -> int:
        """Parse newline/comma-separated account names and add to group."""
        import re
        names = re.split(r"[\n,;]+", text)
        names = [n.strip() for n in names if n.strip()]
        return self.add_accounts_bulk(group_id, names)

    def export_group_accounts(self, group_id: str) -> str:
        """Export account names as newline-separated text."""
        accounts = self.get_group_accounts(group_id)
        return "\n".join(accounts)


# Singleton
account_group_manager = AccountGroupManager()
__all__ = ["AccountGroupManager", "account_group_manager", "FEATURE_TYPES"]
