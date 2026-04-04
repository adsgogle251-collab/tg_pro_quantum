"""Account Manager - With Session Validation (Phase 1000)"""
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from enum import Enum
from .utils import DATA_DIR, SESSIONS_DIR, log, log_error

ACCOUNTS_FILE = DATA_DIR / "accounts.json"
GROUPS_FILE = DATA_DIR / "account_groups.json"

class AccountStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BANNED = "banned"
    SESSION_EXPIRED = "session_expired"

class AccountManager:
    SUPPORTED_FEATURES = ["broadcast", "campaign", "finder", "scrape", "join", "ai_cs", "analytics", "crm", "cs"]

    def __init__(self):
        self.accounts_file = ACCOUNTS_FILE
        self.groups_file = GROUPS_FILE
        self.accounts: Dict[str, dict] = {}
        self.account_groups: Dict[str, List[str]] = {}
        self._load()
    
    def _load(self):
        """Load accounts and groups"""
        if self.accounts_file.exists():
            try:
                with open(self.accounts_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list):
                    self.accounts = {acc.get('name', f"acc_{i}"): acc for i, acc in enumerate(data)}
                elif isinstance(data, dict):
                    self.accounts = data
                else:
                    self.accounts = {}
                log(f"Loaded {len(self.accounts)} accounts", "info")
            except Exception as e:
                log_error(f"Failed to load accounts: {e}")
                self.accounts = {}
        
        self.account_groups = self.load_groups()
    
    def _save_accounts(self):
        try:
            self.accounts_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.accounts_file, 'w', encoding='utf-8') as f:
                json.dump(self.accounts, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log_error(f"Failed to save accounts: {e}")
    
    def _save_groups(self):
        try:
            self.groups_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.groups_file, 'w', encoding='utf-8') as f:
                json.dump(self.account_groups, f, indent=2, ensure_ascii=False)
            log(f"Saved {len(self.account_groups)} groups", "success")
        except Exception as e:
            log_error(f"Failed to save groups: {e}")
    
    def load_groups(self) -> Dict[str, List[str]]:
        if self.groups_file.exists():
            try:
                with open(self.groups_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def save_groups(self, groups: Dict[str, List[str]]):
        self.account_groups = groups
        self._save_groups()
    
    def get_all(self) -> List[dict]:
        if isinstance(self.accounts, dict):
            return list(self.accounts.values())
        elif isinstance(self.accounts, list):
            return self.accounts
        return []
    
    def get(self, account_name: str) -> Optional[dict]:
        return self.accounts.get(account_name)
    
    def add(self, name: str, phone: str, level: int = 1, status: str = "active") -> bool:
        if name in self.accounts:
            log(f"Account {name} already exists", "warning")
            return False
        
        self.accounts[name] = {
            "name": name,
            "phone": phone,
            "level": level,
            "status": status,
            "created_at": datetime.now().isoformat(),
            "last_active": None,
            "total_sent": 0,
            "total_failed": 0,
            "success_rate": 100.0,
            "features": [],
            "groups": []
        }
        self._save_accounts()
        log(f"Account added: {name}", "success")
        return True
    
    def delete(self, name: str) -> bool:
        if name in self.accounts:
            # Remove from all groups
            for grp in list(self.account_groups.keys()):
                if name in self.account_groups[grp]:
                    self.account_groups[grp].remove(name)
            self._save_groups()
            
            # Delete session file
            session_file = SESSIONS_DIR / f"{name}.session"
            if session_file.exists():
                session_file.unlink()
            
            del self.accounts[name]
            self._save_accounts()
            log(f"Account deleted: {name}", "info")
            return True
        return False
    
    def update_stats(self, name: str, sent: int = 0, failed: int = 0):
        if name not in self.accounts:
            return
        acc = self.accounts[name]
        acc["last_active"] = datetime.now().isoformat()
        acc["total_sent"] = acc.get("total_sent", 0) + sent
        acc["total_failed"] = acc.get("total_failed", 0) + failed
        total = acc["total_sent"] + acc["total_failed"]
        if total > 0:
            acc["success_rate"] = round((acc["total_sent"] / total) * 100, 2)
        if acc["total_sent"] >= 1000 and acc["success_rate"] >= 95 and acc["level"] < 4:
            acc["level"] += 1
            log(f"Account {name} leveled up to {acc['level']}", "success")
        self._save_accounts()
    
    def get_stats(self) -> dict:
        accounts = self.get_all()
        by_level = {1: 0, 2: 0, 3: 0, 4: 0}
        by_status = {"active": 0, "inactive": 0, "banned": 0, "session_expired": 0}
        
        for acc in accounts:
            by_level[acc.get('level', 1)] = by_level.get(acc.get('level', 1), 0) + 1
            by_status[acc.get('status', 'active')] = by_status.get(acc.get('status', 'active'), 0) + 1
        
        return {
            "total": len(accounts),
            "by_level": by_level,
            "by_status": by_status,
            "active": sum(1 for a in accounts if a.get('status') == 'active'),
            "avg_success_rate": sum(a.get('success_rate', 0) for a in accounts) / len(accounts) if accounts else 0
        }
    
    # ═══════════════════════════════════════════════════════
    # SESSION VALIDATION - CRITICAL FOR REAL BROADCAST
    # ═══════════════════════════════════════════════════════
    
    def check_session(self, account_name: str) -> dict:
        """Check if account session is valid"""
        session_file = SESSIONS_DIR / f"{account_name}.session"
        
        result = {
            "exists": session_file.exists(),
            "valid": False,
            "authorized": False,
            "message": ""
        }
        
        if not result["exists"]:
            result["message"] = "Session file not found - perlu login"
            result["valid"] = False
            return result
        
        # Check session file size (valid sessions have data)
        try:
            size = session_file.stat().st_size
            if size < 1000:  # Valid sessions are usually > 1KB
                result["message"] = "Session file too small - mungkin corrupted"
                result["valid"] = False
                return result
        except:
            result["message"] = "Cannot read session file"
            result["valid"] = False
            return result
        
        result["valid"] = True
        result["message"] = "Session file exists and looks valid"
        return result
    
    def get_valid_accounts(self) -> List[str]:
        """Get list of accounts with valid sessions"""
        valid = []
        for name, acc in self.accounts.items():
            session_check = self.check_session(name)
            if session_check["valid"]:
                valid.append(name)
            else:
                # Update status if session invalid
                acc["status"] = "session_expired"
                self._save_accounts()
        
        log(f"Found {len(valid)} valid accounts out of {len(self.accounts)}", "info")
        return valid
    
    def get_accounts_with_status(self) -> List[dict]:
        """Get all accounts with session status"""
        result = []
        for name, acc in self.accounts.items():
            session_check = self.check_session(name)
            acc_copy = acc.copy()
            acc_copy["session_valid"] = session_check["valid"]
            acc_copy["session_message"] = session_check["message"]
            result.append(acc_copy)
        return result
    
    # ═══════════════════════════════════════════════════════
    # GROUP MANAGEMENT
    # ═══════════════════════════════════════════════════════
    
    def get_all_groups(self) -> Dict[str, List[str]]:
        self.account_groups = self.load_groups()
        log(f"get_all_groups: returning {len(self.account_groups)} groups", "info")
        return self.account_groups.copy()
    
    def get_group_accounts(self, group_name: str) -> List[str]:
        groups = self.load_groups()
        accounts = groups.get(group_name, [])
        log(f"get_group_accounts('{group_name}'): found {len(accounts)} accounts", "info")
        return accounts.copy()
    
    def create_group(self, group_name: str) -> bool:
        groups = self.load_groups()
        if group_name in groups:
            log(f"Group {group_name} already exists", "warning")
            return False
        groups[group_name] = []
        self.save_groups(groups)
        log(f"Group created: {group_name}", "success")
        return True
    
    def delete_group(self, group_name: str) -> bool:
        groups = self.load_groups()
        if group_name in groups:
            del groups[group_name]
            self.save_groups(groups)
            log(f"Group deleted: {group_name}", "info")
            return True
        return False
    
    def add_account_to_group(self, group_name: str, account_name: str) -> bool:
        groups = self.load_groups()
        if group_name not in groups:
            groups[group_name] = []
        if account_name not in groups[group_name]:
            groups[group_name].append(account_name)
            self.save_groups(groups)
            log(f"Account {account_name} added to group {group_name}", "success")
            return True
        return False
    
    def remove_account_from_group(self, group_name: str, account_name: str) -> bool:
        groups = self.load_groups()
        if group_name in groups and account_name in groups[group_name]:
            groups[group_name].remove(account_name)
            self.save_groups(groups)
            log(f"Account {account_name} removed from group {group_name}", "info")
            return True
        return False
    
    def get_groups_summary(self) -> dict:
        groups = self.load_groups()
        return {
            "total_groups": len(groups),
            "groups": {name: {"account_count": len(accounts), "accounts": accounts} 
                      for name, accounts in groups.items()}
        }

    # ═══════════════════════════════════════════════════════
    # FEATURE ASSIGNMENT - CRITICAL FOR INTEGRATION
    # ═══════════════════════════════════════════════════════

    def assign_feature(self, account_name: str, feature: str) -> bool:
        """Assign a feature to an account."""
        acc = self.accounts.get(account_name)
        if not acc:
            log(f"Account not found: {account_name}", "warning")
            return False
        features = acc.setdefault("features", [])
        if feature not in features:
            features.append(feature)
            self._save_accounts()
            log(f"Feature '{feature}' assigned to {account_name}", "success")
        return True

    def remove_feature(self, account_name: str, feature: str) -> bool:
        """Remove a feature from an account."""
        acc = self.accounts.get(account_name)
        if not acc:
            return False
        features = acc.get("features", [])
        if feature in features:
            features.remove(feature)
            acc["features"] = features
            self._save_accounts()
            log(f"Feature '{feature}' removed from {account_name}", "info")
            return True
        return False

    def get_accounts_by_feature(self, feature: str) -> List[dict]:
        """Return all accounts assigned to a given feature."""
        result = []
        for acc in self.get_all():
            if feature in acc.get("features", []):
                result.append(acc)
        return result

    def get_featured_accounts(self) -> Dict[str, List[dict]]:
        """Return a dict mapping feature name → list of assigned accounts."""
        mapping: Dict[str, List[dict]] = {}
        for acc in self.get_all():
            for feature in acc.get("features", []):
                mapping.setdefault(feature, []).append(acc)
        return mapping

    def get_all_assigned(self) -> Dict[str, list]:
        """Return all feature and group assignments for every account."""
        result = {}
        for acc in self.get_all():
            name = acc.get("name", "")
            result[name] = {
                "features": acc.get("features", []),
                "groups": acc.get("assigned_groups", []),
            }
        return result

    # ═══════════════════════════════════════════════════════
    # ACCOUNT ↔ GROUP ASSIGNMENT (feature-level linking)
    # ═══════════════════════════════════════════════════════

    def assign_group(self, account_name: str, group_id: str) -> bool:
        """Assign a group id to an account's personal group list."""
        acc = self.accounts.get(account_name)
        if not acc:
            log(f"Account not found: {account_name}", "warning")
            return False
        assigned = acc.setdefault("assigned_groups", [])
        if group_id not in assigned:
            assigned.append(group_id)
            self._save_accounts()
            log(f"Group '{group_id}' assigned to account {account_name}", "success")
        return True

    def remove_assigned_group(self, account_name: str, group_id: str) -> bool:
        """Remove a group from an account's personal group list."""
        acc = self.accounts.get(account_name)
        if not acc:
            return False
        assigned = acc.get("assigned_groups", [])
        if group_id in assigned:
            assigned.remove(group_id)
            acc["assigned_groups"] = assigned
            self._save_accounts()
            log(f"Group '{group_id}' removed from account {account_name}", "info")
            return True
        return False

    def get_account_groups(self, account_name: str) -> List[str]:
        """Return the list of group ids assigned to an account."""
        acc = self.accounts.get(account_name)
        if not acc:
            return []
        return acc.get("assigned_groups", [])

    def get_account_features(self, account_name: str) -> List[str]:
        """Return the list of features assigned to an account."""
        acc = self.accounts.get(account_name)
        if not acc:
            return []
        return acc.get("features", [])


# Global instance
account_manager = AccountManager()
__all__ = ["AccountManager", "account_manager", "AccountStatus"]