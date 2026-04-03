"""Broadcast History Manager - Track All Broadcasts"""
import json
from datetime import datetime
from pathlib import Path
from .utils import DATA_DIR, log, log_error

HISTORY_FILE = DATA_DIR / "broadcasts" / "history.json"

class BroadcastHistory:
    def __init__(self):
        self.history_file = HISTORY_FILE
        self.history = self._load()
    
    def _load(self):
        """Load history from file"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {"broadcasts": []}
    
    def _save(self):
        """Save history to file"""
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log_error(f"Failed to save history: {e}")
    
    def add_broadcast(self, campaign_name: str, accounts: list, groups: list,
                      sent: int, failed: int, duration_sec: float):
        """Add broadcast to history"""
        record = {
            "id": f"BRC_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "campaign": campaign_name or "Manual Broadcast",
            "accounts_count": len(accounts),
            "groups_count": len(groups),
            "sent": sent,
            "failed": failed,
            "success_rate": round(sent/(sent+failed)*100, 2) if (sent+failed) > 0 else 0,
            "duration_sec": round(duration_sec, 2)
        }
        
        self.history["broadcasts"].append(record)
        self._save()
        log(f"Broadcast recorded: {record['id']}", "info")
        return record
    
    def get_history(self, limit: int = 50) -> list:
        """Get recent broadcast history"""
        return self.history["broadcasts"][-limit:]
    
    def get_stats(self) -> dict:
        """Get broadcast statistics"""
        broadcasts = self.history["broadcasts"]
        if not broadcasts:
            return {
                "total_broadcasts": 0,
                "total_sent": 0,
                "total_failed": 0,
                "avg_success_rate": 0
            }
        
        return {
            "total_broadcasts": len(broadcasts),
            "total_sent": sum(b["sent"] for b in broadcasts),
            "total_failed": sum(b["failed"] for b in broadcasts),
            "avg_success_rate": round(sum(b["success_rate"] for b in broadcasts) / len(broadcasts), 2)
        }


# Global instance
broadcast_history = BroadcastHistory()
__all__ = ["BroadcastHistory", "broadcast_history"]