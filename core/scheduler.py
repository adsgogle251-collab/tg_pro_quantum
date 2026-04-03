"""Scheduler Manager - Scheduled Broadcasts & Tasks"""
import json
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from typing import List, Dict, Optional, Callable
from .utils import DATA_DIR, log, log_error

SCHEDULE_FILE = DATA_DIR / "scheduler.json"

class TaskType(Enum):
    BROADCAST = "broadcast"
    JOIN = "join"
    SCRAPE = "scrape"
    BACKUP = "backup"
    CUSTOM = "custom"

class ScheduleStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ScheduledTask:
    def __init__(self, task_id: str, task_type: TaskType, name: str,
                 schedule_time: str, callback: Callable = None, **kwargs):
        self.task_id = task_id
        self.task_type = task_type
        self.name = name
        self.schedule_time = schedule_time  # ISO format or cron-like
        self.callback = callback
        self.kwargs = kwargs
        self.status = ScheduleStatus.PENDING
        self.created_at = datetime.now().isoformat()
        self.last_run = None
        self.next_run = self._calculate_next_run()
        self.repeat = kwargs.get("repeat", False)
        self.repeat_interval = kwargs.get("repeat_interval", 86400)  # Default: daily
    
    def _calculate_next_run(self) -> Optional[str]:
        """Calculate next run time"""
        try:
            if self.repeat and self.last_run:
                last = datetime.fromisoformat(self.last_run)
                next_time = last + timedelta(seconds=self.repeat_interval)
                return next_time.isoformat()
            elif not self.repeat:
                return self.schedule_time
        except:
            pass
        return self.schedule_time
    
    def is_due(self) -> bool:
        """Check if task is due to run"""
        if self.status != ScheduleStatus.PENDING:
            return False
        try:
            due_time = datetime.fromisoformat(self.schedule_time)
            return datetime.now() >= due_time
        except:
            return False
    
    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "name": self.name,
            "schedule_time": self.schedule_time,
            "kwargs": self.kwargs,
            "status": self.status.value,
            "created_at": self.created_at,
            "last_run": self.last_run,
            "next_run": self.next_run,
            "repeat": self.repeat,
            "repeat_interval": self.repeat_interval
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ScheduledTask":
        return cls(
            task_id=data["task_id"],
            task_type=TaskType(data["task_type"]),
            name=data["name"],
            schedule_time=data["schedule_time"],
            **data.get("kwargs", {})
        )


class SchedulerManager:
    def __init__(self):
        self.schedule_file = SCHEDULE_FILE
        self.tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._thread = None
        self._load()
    
    def _load(self):
        """Load scheduled tasks from file"""
        if self.schedule_file.exists():
            try:
                with open(self.schedule_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for tid, tdata in data.get("tasks", {}).items():
                        self.tasks[tid] = ScheduledTask.from_dict(tdata)
                log(f"Loaded {len(self.tasks)} scheduled tasks", "info")
            except Exception as e:
                log_error(f"Failed to load scheduler: {e}")
    
    def _save(self):
        """Save scheduled tasks to file"""
        try:
            self.schedule_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "tasks": {tid: t.to_dict() for tid, t in self.tasks.items()},
                "last_updated": datetime.now().isoformat()
            }
            with open(self.schedule_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log_error(f"Failed to save scheduler: {e}")
    
    def create_task(self, task_type: TaskType, name: str, schedule_time: str,
                    callback: Callable = None, repeat: bool = False,
                    repeat_interval: int = 86400, **kwargs) -> ScheduledTask:
        """Create new scheduled task"""
        import uuid
        task_id = f"TSK_{uuid.uuid4().hex[:8].upper()}"
        
        task = ScheduledTask(
            task_id=task_id,
            task_type=task_type,
            name=name,
            schedule_time=schedule_time,
            callback=callback,
            repeat=repeat,
            repeat_interval=repeat_interval,
            **kwargs
        )
        
        self.tasks[task_id] = task
        self._save()
        log(f"Scheduled task created: {name} ({task_id}) at {schedule_time}", "success")
        return task
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled task"""
        if task_id in self.tasks:
            self.tasks[task_id].status = ScheduleStatus.CANCELLED
            self._save()
            log(f"Task cancelled: {task_id}", "info")
            return True
        return False
    
    def run_task(self, task_id: str) -> bool:
        """Manually run a task"""
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        try:
            task.status = ScheduleStatus.RUNNING
            task.last_run = datetime.now().isoformat()
            
            # Execute callback if provided
            if task.callback:
                task.callback(**task.kwargs)
            
            task.status = ScheduleStatus.COMPLETED
            log(f"Task completed: {task_id}", "success")
            
            # Update next run if repeating
            if task.repeat:
                task.next_run = task._calculate_next_run()
                task.status = ScheduleStatus.PENDING
            else:
                del self.tasks[task_id]
            
            self._save()
            return True
        except Exception as e:
            task.status = ScheduleStatus.FAILED
            log_error(f"Task failed {task_id}: {e}")
            self._save()
            return False
    
    def get_pending_tasks(self) -> List[ScheduledTask]:
        """Get all pending tasks"""
        return [t for t in self.tasks.values() if t.status == ScheduleStatus.PENDING]
    
    def get_due_tasks(self) -> List[ScheduledTask]:
        """Get tasks that are due to run"""
        return [t for t in self.tasks.values() if t.is_due()]
    
    def start(self):
        """Start scheduler background thread"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        log("Scheduler started", "info")
    
    def stop(self):
        """Stop scheduler"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        log("Scheduler stopped", "info")
    
    def _run_loop(self):
        """Background loop to check and run due tasks"""
        while self._running:
            try:
                due_tasks = self.get_due_tasks()
                for task in due_tasks:
                    log(f"Running scheduled task: {task.name}", "info")
                    self.run_task(task.task_id)
                
                # Check every 30 seconds
                time.sleep(30)
            except Exception as e:
                log_error(f"Scheduler loop error: {e}")
                time.sleep(60)
    
    def create_broadcast_schedule(self, campaign_id: str, schedule_time: str,
                                   accounts: List[str], message: str,
                                   repeat: bool = False, **kwargs) -> ScheduledTask:
        """Helper: Create scheduled broadcast"""
        from core.engine import broadcast_engine
        
        def run_broadcast(campaign_id, accounts, message, **kw):
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    broadcast_engine.run(
                        campaign_id=campaign_id,
                        accounts=accounts,
                        message=message,
                        **kw
                    )
                )
            finally:
                loop.close()
        
        return self.create_task(
            task_type=TaskType.BROADCAST,
            name=f"Broadcast: {campaign_id}",
            schedule_time=schedule_time,
            callback=run_broadcast,
            campaign_id=campaign_id,
            accounts=accounts,
            message=message,
            repeat=repeat,
            **kwargs
        )


# Global instance
scheduler = SchedulerManager()
__all__ = ["SchedulerManager", "ScheduledTask", "TaskType", "ScheduleStatus", "scheduler"]