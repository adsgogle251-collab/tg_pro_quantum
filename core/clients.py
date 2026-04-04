"""Clients Manager - Enhanced Multi-Client Support (Phase 10 Week 2)"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from .utils import DATA_DIR, log, log_error

CLIENTS_FILE = DATA_DIR / "clients.json"
USAGE_FILE = DATA_DIR / "client_usage.json"

class ClientManager:
    def __init__(self):
        self.clients_file = CLIENTS_FILE
        self.usage_file = USAGE_FILE
        self.clients: Dict[str, dict] = {}
        self.usage: Dict[str, dict] = {}
        self._load()
    
    def _load(self):
        """Load clients and usage data"""
        # Load clients
        if self.clients_file.exists():
            try:
                with open(self.clients_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list):
                    self.clients = {c.get('id', f"client_{i}"): c for i, c in enumerate(data)}
                elif isinstance(data, dict):
                    self.clients = data
                else:
                    self.clients = {}
                log(f"Loaded {len(self.clients)} clients", "info")
            except Exception as e:
                log_error(f"Failed to load clients: {e}")
                self.clients = {}
        
        # Load usage data
        if self.usage_file.exists():
            try:
                with open(self.usage_file, 'r', encoding='utf-8') as f:
                    self.usage = json.load(f)
                log(f"Loaded usage data for {len(self.usage)} clients", "info")
            except:
                self.usage = {}
    
    def _save_clients(self):
        """Save clients to file"""
        try:
            self.clients_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.clients_file, 'w', encoding='utf-8') as f:
                json.dump(self.clients, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log_error(f"Failed to save clients: {e}")
    
    def _save_usage(self):
        """Save usage data"""
        try:
            self.usage_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.usage_file, 'w', encoding='utf-8') as f:
                json.dump(self.usage, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log_error(f"Failed to save usage: {e}")
    
    def create_client(self, name: str, email: str, company: str = "",
                      phone: str = "", notes: str = "", tier: str = "basic",
                      plan_type: str = "starter", usage_limit_monthly: int = 10000,
                      account_groups: list = None, webhook_url: str = "") -> str:
        """Create new client"""
        import uuid, secrets, string
        client_id = f"CLIENT_{uuid.uuid4().hex[:8].upper()}"
        alphabet = string.ascii_letters + string.digits
        api_key = "".join(secrets.choice(alphabet) for _ in range(40))

        self.clients[client_id] = {
            "id": client_id,
            "name": name,
            "email": email,
            "company": company,
            "phone": phone,
            "notes": notes,
            "tier": tier,
            "plan_type": plan_type,
            "api_key": api_key,
            "status": "active",
            "usage_limit_monthly": usage_limit_monthly,
            "current_usage_monthly": 0,
            "webhook_url": webhook_url,
            "created_at": datetime.now().isoformat(),
            "last_active": None,
            "account_groups": list(account_groups) if account_groups else [],
            "campaigns": [],
            "settings": {
                "timezone": "Asia/Jakarta",
                "notifications": True,
                "auto_reports": True,
                "report_frequency": "weekly"
            },
            "limits": {
                "max_accounts": 10 if plan_type == "starter" else 50 if plan_type == "pro" else 999,
                "max_broadcasts_per_day": 100 if plan_type == "starter" else 500 if plan_type == "pro" else 9999,
                "max_messages_per_day": 1000 if plan_type == "starter" else 10000 if plan_type == "pro" else 999999
            }
        }

        self.usage[client_id] = {
            "accounts_used": 0,
            "broadcasts_today": 0,
            "messages_today": 0,
            "last_reset": datetime.now().date().isoformat(),
            "total_sent": 0,
            "total_failed": 0,
            "last_broadcast": None
        }

        self._save_clients()
        self._save_usage()
        log(f"Client created: {name} ({client_id})", "success")
        return client_id
    
    def get_client(self, client_id: str) -> Optional[dict]:
        """Get client by ID"""
        return self.clients.get(client_id)
    
    def get_client_by_email(self, email: str) -> Optional[dict]:
        """Get client by email"""
        for client in self.clients.values():
            if client.get("email") == email:
                return client
        return None
    
    def get_all_clients(self) -> List[dict]:
        """Get all clients"""
        return list(self.clients.values())
    
    def update_client(self, client_id: str, **kwargs) -> bool:
        """Update client settings.

        Allowed fields: name, email, company, phone, notes, tier, plan_type, status,
        usage_limit_monthly, current_usage_monthly, webhook_url, account_groups,
        campaigns, settings, billing_info, last_active.
        """
        if client_id not in self.clients:
            return False
        allowed = {
            "name", "email", "company", "phone", "notes", "tier", "plan_type",
            "status", "usage_limit_monthly", "current_usage_monthly", "webhook_url",
            "account_groups", "campaigns", "settings", "billing_info", "last_active",
            "limits",
        }
        for key, value in kwargs.items():
            if key in allowed:
                self.clients[client_id][key] = value
        self._save_clients()
        log(f"Client updated: {client_id}", "info")
        return True

    def regenerate_api_key(self, client_id: str) -> str:
        """Generate a new API key for a client and return it."""
        import secrets, string
        alphabet = string.ascii_letters + string.digits
        new_key = "".join(secrets.choice(alphabet) for _ in range(40))
        if client_id in self.clients:
            self.clients[client_id]["api_key"] = new_key
            self._save_clients()
            log(f"API key regenerated for client: {client_id}", "info")
        return new_key
    
    def delete_client(self, client_id: str) -> bool:
        """Delete client"""
        if client_id in self.clients:
            del self.clients[client_id]
            if client_id in self.usage:
                del self.usage[client_id]
            self._save_clients()
            self._save_usage()
            log(f"Client deleted: {client_id}", "info")
            return True
        return False
    
    # === USAGE TRACKING ===
    
    def track_broadcast(self, client_id: str, sent: int = 0, failed: int = 0):
        """Track broadcast usage for a client"""
        if client_id not in self.usage:
            return
        usage = self.usage[client_id]
        today = datetime.now().date().isoformat()
        if usage.get("last_reset") != today:
            usage["broadcasts_today"] = 0
            usage["messages_today"] = 0
            usage["last_reset"] = today
        usage["broadcasts_today"] += 1
        usage["messages_today"] += sent + failed
        usage["total_sent"] += sent
        usage["total_failed"] += failed
        usage["last_broadcast"] = datetime.now().isoformat()
        self._save_usage()
    
    def check_limits(self, client_id: str, requested_messages: int = 0) -> dict:
        """Check if client is within limits"""
        if client_id not in self.clients or client_id not in self.usage:
            return {"allowed": False, "reason": "Client not found"}
        
        client = self.clients[client_id]
        usage = self.usage[client_id]
        limits = client.get("limits", {})
        
        today = datetime.now().date().isoformat()
        if usage.get("last_reset") != today:
            usage["broadcasts_today"] = 0
            usage["messages_today"] = 0
            usage["last_reset"] = today
        
        checks = {
            "accounts": usage.get("accounts_used", 0) < limits.get("max_accounts", 10),
            "broadcasts": usage.get("broadcasts_today", 0) < limits.get("max_broadcasts_per_day", 100),
            "messages": (usage.get("messages_today", 0) + requested_messages) < limits.get("max_messages_per_day", 1000)
        }
        
        return {
            "allowed": all(checks.values()),
            "checks": checks,
            "usage": {
                "accounts": f"{usage.get('accounts_used', 0)}/{limits.get('max_accounts', 10)}",
                "broadcasts": f"{usage.get('broadcasts_today', 0)}/{limits.get('max_broadcasts_per_day', 100)}/day",
                "messages": f"{usage.get('messages_today', 0)}/{limits.get('max_messages_per_day', 1000)}/day"
            }
        }
    
    def get_client_stats(self, client_id: str) -> dict:
        """Get statistics for a client"""
        if client_id not in self.clients or client_id not in self.usage:
            return {}
        usage = self.usage[client_id]
        total = usage.get("total_sent", 0) + usage.get("total_failed", 0)
        return {
            "total_broadcasts": usage.get("broadcasts_today", 0),
            "total_sent": usage.get("total_sent", 0),
            "total_failed": usage.get("total_failed", 0),
            "avg_success_rate": round((usage.get("total_sent", 0) / total) * 100, 2) if total > 0 else 0,
            "last_broadcast": usage.get("last_broadcast"),
            "messages_today": usage.get("messages_today", 0),
            "broadcasts_today": usage.get("broadcasts_today", 0)
        }
    
    def get_usage_summary(self) -> dict:
        """Get usage summary for all clients"""
        summary = {
            "total_clients": len(self.clients),
            "active_clients": sum(1 for c in self.clients.values() if c.get("status") == "active"),
            "total_messages_sent": sum(u.get("total_sent", 0) for u in self.usage.values()),
            "total_messages_failed": sum(u.get("total_failed", 0) for u in self.usage.values()),
            "by_tier": {}
        }
        for client in self.clients.values():
            tier = client.get("tier", "basic")
            if tier not in summary["by_tier"]:
                summary["by_tier"][tier] = {"count": 0, "messages": 0}
            summary["by_tier"][tier]["count"] += 1
            if client["id"] in self.usage:
                summary["by_tier"][tier]["messages"] += self.usage[client["id"]].get("total_sent", 0)
        return summary


# Global instance
client_manager = ClientManager()
__all__ = ["ClientManager", "client_manager"]