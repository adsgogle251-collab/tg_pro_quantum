"""TG PRO QUANTUM - Account Router
Route accounts to specific features
"""
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
from .utils import DATA_DIR, log, log_error

ROUTER_FILE = DATA_DIR / "account_router.json"

class Feature(Enum):
    BROADCAST = "broadcast"
    JOIN = "join"
    SCRAPE = "scrape"
    FINDER = "finder"
    CS = "cs"

class AssignmentMode(Enum):
    EXCLUSIVE = "exclusive"
    PRIMARY = "primary"
    SECONDARY = "secondary"
    MULTI = "multi"

@dataclass
class AccountAssignment:
    account_id: str
    feature: Feature
    mode: AssignmentMode = AssignmentMode.PRIMARY
    config: Dict = field(default_factory=dict)
    assigned_at: str = field(default_factory=lambda: datetime.now().isoformat())
    performance_score: float = 0.0

    def to_dict(self) -> Dict:
        return {"account_id": self.account_id, "feature": self.feature.value, "mode": self.mode.value, "config": self.config, "assigned_at": self.assigned_at, "performance_score": self.performance_score}

    @classmethod
    def from_dict(cls, data: Dict):
        data["feature"] = Feature(data.get("feature", "broadcast"))
        data["mode"] = AssignmentMode(data.get("mode", "primary"))
        return cls(**data)

class AccountRouter:
    def __init__(self):
        self.router_file = ROUTER_FILE
        self.assignments: Dict[str, AccountAssignment] = {}
        self._load()

    def _load(self):
        if self.router_file.exists():
            try:
                with open(self.router_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for aid, adata in data.get("assignments", {}).items():
                        self.assignments[aid] = AccountAssignment.from_dict(adata)
            except Exception as e: log_error(f"Failed to load router: {e}")

    def _save(self):
        try:
            self.router_file.parent.mkdir(parents=True, exist_ok=True)
            data = {"assignments": {aid: a.to_dict() for aid, a in self.assignments.items()}}
            with open(self.router_file, 'w', encoding='utf-8') as f: json.dump(data, f, indent=2)
        except Exception as e: log_error(f"Failed to save router: {e}")

    def assign(self, account_id: str, feature: Feature, mode: AssignmentMode = AssignmentMode.PRIMARY, config: Optional[Dict] = None) -> bool:
        if account_id in self.assignments:
            self.assignments[account_id].feature = feature
            self.assignments[account_id].mode = mode
            if config: self.assignments[account_id].config.update(config)
        else:
            self.assignments[account_id] = AccountAssignment(account_id=account_id, feature=feature, mode=mode, config=config or {})
        self._save()
        log(f"Account {account_id} assigned to {feature.value}", "success")
        return True

    def unassign(self, account_id: str) -> bool:
        if account_id in self.assignments:
            del self.assignments[account_id]
            self._save()
            return True
        return False

    def get_assignments(self, feature: Optional[Feature] = None):
        result = list(self.assignments.values())
        if feature:
            result = [a for a in result if a.feature == feature]
        return result

    def get_accounts_for_feature(self, feature: Feature) -> List[str]:
        return [a.account_id for a in self.assignments.values() if a.feature == feature]

    def auto_assign(self, account_id: str) -> Optional[Feature]:
        from .account_manager import account_manager
        accounts = account_manager.get_all()
        acc = next((a for a in accounts if a.get("name") == account_id), None)
        if not acc: return None
        level = acc.get("level", 1)
        if level >= 4: return Feature.BROADCAST
        if level >= 3: return Feature.CS
        if level >= 2: return Feature.FINDER
        return Feature.JOIN

account_router = AccountRouter()
__all__ = ["AccountRouter", "AccountAssignment", "Feature", "AssignmentMode", "account_router"]