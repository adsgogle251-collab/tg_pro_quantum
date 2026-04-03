"""TG PRO QUANTUM - Account Warming System
Gradual activity increase to prevent bans
"""
import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
from telethon import TelegramClient
from .utils import log, log_error, log_success, SESSIONS_DIR
from .account_manager import account_manager

class WarmingSchedule:
    """Warming schedule by account level"""
    
    SCHEDULES = {
        1: {"joins_per_day": 10, "messages_per_day": 5, "delay_min": 300, "delay_max": 600},
        2: {"joins_per_day": 25, "messages_per_day": 15, "delay_min": 180, "delay_max": 400},
        3: {"joins_per_day": 50, "messages_per_day": 30, "delay_min": 120, "delay_max": 300},
        4: {"joins_per_day": 100, "messages_per_day": 50, "delay_min": 60, "delay_max": 180},
    }
    
    @classmethod
    def get_schedule(cls, level: int) -> Dict:
        return cls.SCHEDULES.get(level, cls.SCHEDULES[1])

class AccountWarmer:
    """Account warming manager"""
    
    def __init__(self, api_id: int, api_hash: str):
        self.api_id = api_id
        self.api_hash = api_hash
        self.warming_data: Dict[str, Dict] = {}
        self._load_data()
    
    def _load_data(self):
        """Load warming data"""
        warming_file = Path("data/warming.json")
        if warming_file.exists():
            import json
            try:
                with open(warming_file, 'r', encoding='utf-8') as f:
                    self.warming_data = json.load(f)
            except:
                self.warming_data = {}
    
    def _save_data(self):
        """Save warming data"""
        warming_file = Path("data/warming.json")
        warming_file.parent.mkdir(parents=True, exist_ok=True)
        import json
        with open(warming_file, 'w', encoding='utf-8') as f:
            json.dump(self.warming_data, f, indent=2)
    
    def start_warming(self, account_name: str):
        """Start warming for account"""
        self.warming_data[account_name] = {
            "started_at": datetime.now().isoformat(),
            "level": 1,
            "today_joins": 0,
            "today_messages": 0,
            "last_activity": datetime.now().isoformat(),
            "status": "warming"
        }
        self._save_data()
        log(f"Warming started for {account_name}", "success")
    
    def stop_warming(self, account_name: str):
        """Stop warming for account"""
        if account_name in self.warming_data:
            self.warming_data[account_name]["status"] = "completed"
            self._save_data()
            log(f"Warming completed for {account_name}", "success")
    
    def get_warming_status(self, account_name: str) -> Dict:
        """Get warming status for account"""
        return self.warming_data.get(account_name, {"status": "not_started"})
    
    def can_perform_action(self, account_name: str, action: str) -> Tuple[bool, str]:
        """Check if account can perform action"""
        data = self.warming_data.get(account_name)
        if not data:
            return True, "OK"
        
        if data.get("status") == "completed":
            return True, "Warming completed"
        
        level = data.get("level", 1)
        schedule = WarmingSchedule.get_schedule(level)
        
        if action == "join":
            if data.get("today_joins", 0) >= schedule["joins_per_day"]:
                return False, "Daily join limit reached"
        elif action == "message":
            if data.get("today_messages", 0) >= schedule["messages_per_day"]:
                return False, "Daily message limit reached"
        
        return True, "OK"
    
    def record_action(self, account_name: str, action: str):
        """Record action for account"""
        if account_name not in self.warming_data:
            self.start_warming(account_name)
        
        data = self.warming_data[account_name]
        
        # Reset daily counters if new day
        last_activity = datetime.fromisoformat(data.get("last_activity", datetime.now().isoformat()))
        if last_activity.date() < datetime.now().date():
            data["today_joins"] = 0
            data["today_messages"] = 0
        
        # Record action
        if action == "join":
            data["today_joins"] = data.get("today_joins", 0) + 1
        elif action == "message":
            data["today_messages"] = data.get("today_messages", 0) + 1
        
        data["last_activity"] = datetime.now().isoformat()
        
        # Check if level up
        self._check_level_up(account_name)
        
        self._save_data()
    
    def _check_level_up(self, account_name: str):
        """Check if account should level up"""
        data = self.warming_data[account_name]
        started = datetime.fromisoformat(data.get("started_at", datetime.now().isoformat()))
        days_warming = (datetime.now() - started).days
        
        # Level up every 7 days
        new_level = min(4, 1 + (days_warming // 7))
        
        if new_level > data.get("level", 1):
            data["level"] = new_level
            log(f"Account {account_name} leveled up to {new_level}!", "success")
            
            # Update account manager
            accounts = account_manager.get_all()
            for acc in accounts:
                if acc['name'] == account_name:
                    acc['level'] = new_level
                    account_manager._save()
                    break
    
    def get_all_warming_status(self) -> Dict:
        """Get warming status for all accounts"""
        return {
            "total": len(self.warming_data),
            "warming": sum(1 for d in self.warming_data.values() if d.get("status") == "warming"),
            "completed": sum(1 for d in self.warming_data.values() if d.get("status") == "completed"),
            "by_level": {
                level: sum(1 for d in self.warming_data.values() if d.get("level") == level)
                for level in [1, 2, 3, 4]
            }
        }

# Global instance (lazy init)
_warmer_instance = None

def get_account_warmer(api_id: int, api_hash: str) -> AccountWarmer:
    """Get AccountWarmer instance"""
    global _warmer_instance
    if _warmer_instance is None:
        _warmer_instance = AccountWarmer(api_id, api_hash)
    return _warmer_instance

__all__ = ["AccountWarmer", "WarmingSchedule", "get_account_warmer"]