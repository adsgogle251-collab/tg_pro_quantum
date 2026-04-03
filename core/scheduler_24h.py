"""24/7 Scheduler - Automated Broadcast Scheduling (Phase 10)"""
import asyncio
import json
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Callable
from .utils import DATA_DIR, log, log_error
from .account_manager import account_manager
from .campaign_manager import campaign_manager

SCHEDULES_FILE = DATA_DIR / "schedules_24h.json"

class ScheduleConfig:
    """24/7 schedule configuration"""
    def __init__(self):
        self.enabled = True
        self.timezone = "Asia/Jakarta"
        self.shift_hours = 6  # 4 shifts per day
        self.accounts_per_shift = 25
        self.messages_per_hour = 100
        self.delay_min = 10
        self.delay_max = 30
        self.auto_rotate_accounts = True
        self.pause_on_low_balance = True
        self.notify_on_completion = True

class ScheduledBroadcast:
    """Represents a scheduled broadcast task"""
    def __init__(self, 
                 campaign_id: str,
                 client_id: str,
                 accounts: List[str],
                 groups: List[str],
                 message: str,
                 start_time: datetime,
                 end_time: datetime = None,
                 repeat: str = None):  # "daily", "weekly", "monthly"
        
        self.campaign_id = campaign_id
        self.client_id = client_id
        self.accounts = accounts
        self.groups = groups
        self.message = message
        self.start_time = start_time
        self.end_time = end_time
        self.repeat = repeat
        self.status = "pending"  # pending, running, completed, failed
        self.created_at = datetime.now()
        self.last_run = None
        self.stats = {
            "sent": 0,
            "failed": 0,
            "success_rate": 0
        }
    
    def to_dict(self):
        return {
            "campaign_id": self.campaign_id,
            "client_id": self.client_id,
            "accounts": self.accounts,
            "groups": self.groups,
            "message": self.message,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "repeat": self.repeat,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "stats": self.stats
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        obj = cls(
            campaign_id=data["campaign_id"],
            client_id=data["client_id"],
            accounts=data["accounts"],
            groups=data["groups"],
            message=data["message"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            repeat=data.get("repeat")
        )
        obj.status = data.get("status", "pending")
        obj.created_at = datetime.fromisoformat(data["created_at"])
        obj.last_run = datetime.fromisoformat(data["last_run"]) if data.get("last_run") else None
        obj.stats = data.get("stats", {})
        return obj

class Scheduler24H:
    """24/7 broadcast scheduler for multi-client operations"""
    
    def __init__(self):
        self.config = ScheduleConfig()
        self.schedules: Dict[str, ScheduledBroadcast] = {}
        self.running = False
        self._thread = None
        self._load()
    
    def _load(self):
        """Load schedules from file"""
        if Path(SCHEDULES_FILE).exists():
            try:
                with open(SCHEDULES_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for sched_id, sched_data in data.get("schedules", {}).items():
                    self.schedules[sched_id] = ScheduledBroadcast.from_dict(sched_data)
                
                # Load config
                if "config" in data:
                    for key, value in data["config"].items():
                        if hasattr(self.config, key):
                            setattr(self.config, key, value)
                
                log(f"Loaded {len(self.schedules)} scheduled broadcasts", "info")
            except Exception as e:
                log_error(f"Failed to load schedules: {e}")
                self.schedules = {}
    
    def _save(self):
        """Save schedules to file"""
        try:
            SCHEDULES_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "schedules": {k: v.to_dict() for k, v in self.schedules.items()},
                "config": {k: v for k, v in self.config.__dict__.items()}
            }
            with open(SCHEDULES_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log_error(f"Failed to save schedules: {e}")
    
    def configure(self, **kwargs):
        """Configure scheduler settings"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        self._save()
        log(f"Scheduler configured: {kwargs}", "info")
    
    def create_schedule(self,
                       campaign_id: str,
                       client_id: str,
                       accounts: List[str],
                       groups: List[str],
                       message: str,
                       start_time: datetime,
                       end_time: datetime = None,
                       repeat: str = None) -> str:
        """Create a new scheduled broadcast"""
        import uuid
        sched_id = f"SCHED_{uuid.uuid4().hex[:8].upper()}"
        
        schedule = ScheduledBroadcast(
            campaign_id=campaign_id,
            client_id=client_id,
            accounts=accounts,
            groups=groups,
            message=message,
            start_time=start_time,
            end_time=end_time,
            repeat=repeat
        )
        
        self.schedules[sched_id] = schedule
        self._save()
        
        log(f"Schedule created: {sched_id} for client {client_id}", "success")
        return sched_id
    
    def update_schedule(self, sched_id: str, **kwargs) -> bool:
        """Update an existing schedule"""
        if sched_id not in self.schedules:
            return False
        
        schedule = self.schedules[sched_id]
        for key, value in kwargs.items():
            if hasattr(schedule, key):
                setattr(schedule, key, value)
        
        self._save()
        log(f"Schedule updated: {sched_id}", "info")
        return True
    
    def delete_schedule(self, sched_id: str) -> bool:
        """Delete a schedule"""
        if sched_id in self.schedules:
            del self.schedules[sched_id]
            self._save()
            log(f"Schedule deleted: {sched_id}", "info")
            return True
        return False
    
    def get_schedules(self, client_id: str = None, status: str = None) -> List[ScheduledBroadcast]:
        """Get schedules with optional filters"""
        result = list(self.schedules.values())
        
        if client_id:
            result = [s for s in result if s.client_id == client_id]
        
        if status:
            result = [s for s in result if s.status == status]
        
        return sorted(result, key=lambda x: x.start_time)
    
    def get_due_schedules(self) -> List[ScheduledBroadcast]:
        """Get schedules that are due to run"""
        now = datetime.now()
        due = []
        
        for schedule in self.schedules.values():
            if schedule.status != "pending":
                continue
            
            if schedule.start_time <= now:
                # Check if end_time has passed
                if schedule.end_time and schedule.end_time < now:
                    continue
                due.append(schedule)
        
        return due
    
    def start(self):
        """Start the scheduler background thread"""
        if self.running or not self.config.enabled:
            return
        
        self.running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        log("24/7 Scheduler started", "success")
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)
        log("24/7 Scheduler stopped", "info")
    
    def _run_loop(self):
        """Background loop to check and execute schedules"""
        while self.running:
            try:
                # Check for due schedules
                due_schedules = self.get_due_schedules()
                
                for schedule in due_schedules:
                    log(f"Executing schedule: {schedule.campaign_id} for client {schedule.client_id}", "info")
                    asyncio.create_task(self._execute_schedule(schedule))
                
                # Check every 5 minutes
                time.sleep(300)
                
            except Exception as e:
                log_error(f"Scheduler loop error: {e}")
                time.sleep(300)
    
    async def _execute_schedule(self, schedule: ScheduledBroadcast):
        """Execute a scheduled broadcast"""
        try:
            schedule.status = "running"
            schedule.last_run = datetime.now()
            self._save()
            
            # Import broadcast engine
            from .broadcast_engine import broadcast_engine
            
            # Configure broadcast
            broadcast_engine.configure(
                delay_min=self.config.delay_min,
                delay_max=self.config.delay_max,
                round_robin=self.config.auto_rotate_accounts,
                rate_limit_per_hour=self.config.messages_per_hour
            )
            
            # Run broadcast
            success = await broadcast_engine.run(
                campaign_id=schedule.campaign_id,
                accounts=schedule.accounts,
                message=schedule.message,
                groups=schedule.groups
            )
            
            # Update stats
            schedule.stats = broadcast_engine.stats.to_dict()
            schedule.status = "completed" if success else "failed"
            
            # Handle repeat
            if schedule.repeat and success:
                self._schedule_repeat(schedule)
            
            self._save()
            
            # Notify if enabled
            if self.config.notify_on_completion:
                self._notify_completion(schedule)
            
            log(f"Schedule completed: {schedule.campaign_id} - Status: {schedule.status}", 
                "success" if success else "error")
            
        except Exception as e:
            log_error(f"Schedule execution error: {e}")
            schedule.status = "failed"
            self._save()
    
    def _schedule_repeat(self, schedule: ScheduledBroadcast):
        """Schedule next run for repeating broadcasts"""
        if not schedule.repeat:
            return
        
        now = datetime.now()
        
        if schedule.repeat == "daily":
            next_run = schedule.start_time + timedelta(days=1)
        elif schedule.repeat == "weekly":
            next_run = schedule.start_time + timedelta(weeks=1)
        elif schedule.repeat == "monthly":
            next_run = schedule.start_time + timedelta(days=30)
        else:
            return
        
        # Create new schedule for next run
        self.create_schedule(
            campaign_id=schedule.campaign_id,
            client_id=schedule.client_id,
            accounts=schedule.accounts,
            groups=schedule.groups,
            message=schedule.message,
            start_time=next_run,
            end_time=schedule.end_time + timedelta(days=1) if schedule.end_time else None,
            repeat=schedule.repeat
        )
    
    def _notify_completion(self, schedule: ScheduledBroadcast):
        """Send notification on schedule completion"""
        # TODO: Implement email/Telegram notification
        log(f"Notification: Schedule {schedule.campaign_id} completed for client {schedule.client_id}", "info")
    
    def get_client_summary(self, client_id: str) -> dict:
        """Get summary of schedules for a client"""
        schedules = self.get_schedules(client_id=client_id)
        
        return {
            "total": len(schedules),
            "pending": sum(1 for s in schedules if s.status == "pending"),
            "running": sum(1 for s in schedules if s.status == "running"),
            "completed": sum(1 for s in schedules if s.status == "completed"),
            "failed": sum(1 for s in schedules if s.status == "failed"),
            "total_sent": sum(s.stats.get("sent", 0) for s in schedules),
            "total_failed": sum(s.stats.get("failed", 0) for s in schedules),
            "avg_success_rate": sum(s.stats.get("success_rate", 0) for s in schedules) / len(schedules) if schedules else 0
        }


# Global instance
scheduler_24h = Scheduler24H()
__all__ = ["Scheduler24H", "scheduler_24h", "ScheduleConfig", "ScheduledBroadcast"]