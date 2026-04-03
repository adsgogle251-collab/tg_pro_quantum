"""Notification Manager - Alert System for Important Events"""
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from .utils import DATA_DIR, log

NOTIFICATIONS_FILE = DATA_DIR / "notifications.json"

class NotificationManager:
    def __init__(self):
        self.notifications_file = NOTIFICATIONS_FILE
        self.notifications = self._load()
    
    def _load(self):
        """Load notifications from file"""
        if self.notifications_file.exists():
            try:
                with open(self.notifications_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {"notifications": [], "settings": {"enabled": True, "sound": False}}
    
    def _save(self):
        """Save notifications to file"""
        try:
            self.notifications_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.notifications_file, 'w', encoding='utf-8') as f:
                json.dump(self.notifications, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log(f"Failed to save notifications: {e}", "error")
    
    def add_notification(self, title: str, message: str, level: str = "info",
                         auto_dismiss: int = 0) -> dict:
        """Add new notification"""
        import uuid
        notification = {
            "id": f"NOT_{uuid.uuid4().hex[:8].upper()}",
            "title": title,
            "message": message,
            "level": level,  # info, warning, error, success
            "created_at": datetime.now().isoformat(),
            "read": False,
            "auto_dismiss": auto_dismiss  # seconds, 0 = no auto-dismiss
        }
        
        self.notifications["notifications"].append(notification)
        
        # Keep only last 100 notifications
        self.notifications["notifications"] = self.notifications["notifications"][-100:]
        
        self._save()
        log(f"Notification: {title} - {message}", level)
        return notification
    
    def get_unread(self) -> List[dict]:
        """Get unread notifications"""
        return [n for n in self.notifications["notifications"] if not n["read"]]
    
    def get_all(self, limit: int = 50) -> List[dict]:
        """Get all notifications"""
        return self.notifications["notifications"][-limit:]
    
    def mark_read(self, notification_id: str) -> bool:
        """Mark notification as read"""
        for n in self.notifications["notifications"]:
            if n["id"] == notification_id:
                n["read"] = True
                self._save()
                return True
        return False
    
    def mark_all_read(self):
        """Mark all notifications as read"""
        for n in self.notifications["notifications"]:
            n["read"] = True
        self._save()
    
    def clear_old(self, days: int = 7):
        """Clear notifications older than specified days"""
        cutoff = datetime.now().timestamp() - (days * 86400)
        self.notifications["notifications"] = [
            n for n in self.notifications["notifications"]
            if datetime.fromisoformat(n["created_at"]).timestamp() > cutoff
        ]
        self._save()
    
    def get_settings(self) -> dict:
        """Get notification settings"""
        return self.notifications.get("settings", {})
    
    def update_settings(self, **kwargs):
        """Update notification settings"""
        if "settings" not in self.notifications:
            self.notifications["settings"] = {}
        
        for key, value in kwargs.items():
            self.notifications["settings"][key] = value
        
        self._save()


# Global instance
notification_manager = NotificationManager()
__all__ = ["NotificationManager", "notification_manager"]