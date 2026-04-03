"""Auto Backup Manager - Automatic Backup Scheduler"""
import json
import shutil
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from .utils import DATA_DIR, BACKUPS_DIR, log, log_error

BACKUP_CONFIG_FILE = DATA_DIR / "backup_config.json"

class AutoBackupManager:
    def __init__(self):
        self.config_file = BACKUP_CONFIG_FILE
        self.config = self._load_config()
        self._running = False
        self._thread = None
    
    def _load_config(self):
        """Load backup configuration"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        # Default config
        return {
            "enabled": True,
            "interval_hours": 24,
            "max_backups": 10,
            "last_backup": None,
            "include_sessions": False,
            "include_logs": False
        }
    
    def _save_config(self):
        """Save backup configuration"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log_error(f"Failed to save backup config: {e}")
    
    def enable(self, interval_hours: int = 24):
        """Enable auto-backup"""
        self.config["enabled"] = True
        self.config["interval_hours"] = interval_hours
        self._save_config()
        log(f"Auto-backup enabled: every {interval_hours} hours", "success")
    
    def disable(self):
        """Disable auto-backup"""
        self.config["enabled"] = False
        self._save_config()
        log("Auto-backup disabled", "info")
    
    def start(self):
        """Start auto-backup background thread"""
        if self._running or not self.config["enabled"]:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        log("Auto-backup scheduler started", "info")
    
    def stop(self):
        """Stop auto-backup"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        log("Auto-backup scheduler stopped", "info")
    
    def _run_loop(self):
        """Background loop to check and create backups"""
        while self._running:
            try:
                # Check if backup is due
                if self._should_backup():
                    log("Auto-backup triggered", "info")
                    self.create_backup()
                
                # Check every hour
                time.sleep(3600)
            except Exception as e:
                log_error(f"Auto-backup loop error: {e}")
                time.sleep(3600)
    
    def _should_backup(self) -> bool:
        """Check if backup is due"""
        if not self.config["enabled"]:
            return False
        
        last_backup = self.config.get("last_backup")
        if not last_backup:
            return True  # No backup yet
        
        try:
            last_dt = datetime.fromisoformat(last_backup)
            interval = timedelta(hours=self.config["interval_hours"])
            return datetime.now() >= last_dt + interval
        except:
            return True
    
    def create_backup(self) -> str:
        """Create backup"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{timestamp}"
            backup_path = BACKUPS_DIR / backup_name
            
            # Create backup directory
            backup_path.mkdir(parents=True, exist_ok=True)
            
            # Copy data files
            files_to_backup = [
                DATA_DIR / "accounts.json",
                DATA_DIR / "account_groups.json",
                DATA_DIR / "campaigns.json",
                DATA_DIR / "config.json",
                DATA_DIR / "statistics.json",
                DATA_DIR / "groups",
                DATA_DIR / "scraped",
                DATA_DIR / "clients.json",
                DATA_DIR / "templates.json"
            ]
            
            for file_path in files_to_backup:
                if file_path.exists():
                    if file_path.is_file():
                        shutil.copy2(file_path, backup_path / file_path.name)
                    else:
                        shutil.copytree(file_path, backup_path / file_path.name, dirs_exist_ok=True)
            
            # Optionally include sessions
            if self.config.get("include_sessions", False):
                sessions_dir = Path("sessions")
                if sessions_dir.exists():
                    shutil.copytree(sessions_dir, backup_path / "sessions", dirs_exist_ok=True)
            
            # Update last backup time
            self.config["last_backup"] = datetime.now().isoformat()
            self._save_config()
            
            # Cleanup old backups
            self._cleanup_old_backups()
            
            log(f"Backup created: {backup_name}", "success")
            return backup_name
            
        except Exception as e:
            log_error(f"Failed to create backup: {e}")
            return None
    
    def _cleanup_old_backups(self):
        """Remove old backups beyond max limit"""
        try:
            max_backups = self.config.get("max_backups", 10)
            backups = sorted(BACKUPS_DIR.glob("backup_*"))
            
            # Remove oldest backups beyond limit
            while len(backups) > max_backups:
                oldest = backups.pop(0)
                shutil.rmtree(oldest)
                log(f"Removed old backup: {oldest.name}", "info")
        except Exception as e:
            log_error(f"Failed to cleanup old backups: {e}")
    
    def list_backups(self) -> list:
        """List all backups"""
        backups = []
        for backup_dir in sorted(BACKUPS_DIR.glob("backup_*"), reverse=True):
            backups.append({
                "name": backup_dir.name,
                "path": str(backup_dir),
                "created": datetime.fromtimestamp(backup_dir.stat().st_ctime).isoformat(),
                "size": sum(f.stat().st_size for f in backup_dir.rglob("*") if f.is_file())
            })
        return backups
    
    def restore_backup(self, backup_name: str) -> bool:
        """Restore from backup"""
        try:
            backup_path = BACKUPS_DIR / backup_name
            if not backup_path.exists():
                log_error(f"Backup not found: {backup_name}")
                return False
            
            # Restore data files
            files_to_restore = [
                "accounts.json",
                "account_groups.json",
                "campaigns.json",
                "config.json",
                "statistics.json",
                "clients.json",
                "templates.json"
            ]
            
            for filename in files_to_restore:
                backup_file = backup_path / filename
                if backup_file.exists():
                    shutil.copy2(backup_file, DATA_DIR / filename)
            
            # Restore directories
            dirs_to_restore = ["groups", "scraped"]
            for dirname in dirs_to_restore:
                backup_dir = backup_path / dirname
                if backup_dir.exists():
                    target_dir = DATA_DIR / dirname
                    if target_dir.exists():
                        shutil.rmtree(target_dir)
                    shutil.copytree(backup_dir, target_dir)
            
            # Optionally restore sessions
            sessions_backup = backup_path / "sessions"
            if sessions_backup.exists():
                sessions_dir = Path("sessions")
                if sessions_dir.exists():
                    shutil.rmtree(sessions_dir)
                shutil.copytree(sessions_backup, sessions_dir)
            
            log(f"Backup restored: {backup_name}", "success")
            return True
            
        except Exception as e:
            log_error(f"Failed to restore backup: {e}")
            return False


# Global instance
auto_backup = AutoBackupManager()
__all__ = ["AutoBackupManager", "auto_backup"]