"""Statistics Manager - Complete with All Tracking"""
import json
from datetime import datetime
from pathlib import Path
from .utils import DATA_DIR, log, load_statistics, save_statistics

STATS_FILE = DATA_DIR / "statistics.json"

class StatisticsManager:
    def __init__(self):
        self.stats_file = STATS_FILE
        self.stats = self._load()
    
    def _load(self):
        """Load statistics from file"""
        return load_statistics()
    
    def _save(self):
        """Save statistics to file"""
        save_statistics(self.stats)
    
    def get_summary(self) -> dict:
        """Get statistics summary"""
        return self.stats.copy()
    
    def increment_sent(self, count: int = 1):
        """Increment messages sent counter"""
        self.stats["total_messages_sent"] = self.stats.get("total_messages_sent", 0) + count
        self._update_success_rate()
        self._save()
    
    def increment_failed(self, count: int = 1):
        """Increment messages failed counter"""
        self.stats["total_messages_failed"] = self.stats.get("total_messages_failed", 0) + count
        self._update_success_rate()
        self._save()
    
    def increment_broadcasts(self, count: int = 1):
        """Increment broadcast counter"""
        self.stats["total_broadcasts"] = self.stats.get("total_broadcasts", 0) + count
        self.stats["last_broadcast"] = datetime.now().isoformat()
        self._save()
    
    def increment_groups_joined(self, count: int = 1):
        """Increment groups joined counter"""
        self.stats["total_groups_joined"] = self.stats.get("total_groups_joined", 0) + count
        self._save()
    
    def increment_members_scraped(self, count: int = 1):
        """Increment members scraped counter"""
        self.stats["total_members_scraped"] = self.stats.get("total_members_scraped", 0) + count
        self._save()
    
    def _update_success_rate(self):
        """Calculate and update success rate"""
        total = self.stats.get("total_messages_sent", 0) + self.stats.get("total_messages_failed", 0)
        if total > 0:
            self.stats["success_rate"] = round(
                self.stats.get("total_messages_sent", 0) / total * 100, 2
            )
        else:
            self.stats["success_rate"] = 0.0
    
    def reset(self):
        """Reset all statistics"""
        self.stats = {
            "total_broadcasts": 0,
            "total_messages_sent": 0,
            "total_messages_failed": 0,
            "total_groups_joined": 0,
            "total_members_scraped": 0,
            "success_rate": 0.0,
            "last_broadcast": None
        }
        self._save()


# Global instance
statistics = StatisticsManager()
__all__ = ["StatisticsManager", "statistics"]