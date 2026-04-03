"""TG PRO QUANTUM - Backup Manager"""
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from .utils import DATA_DIR, BACKUPS_DIR, log, log_error

class BackupManager:
    def __init__(self):
        self.backups_dir = BACKUPS_DIR

    def create_backup(self) -> Optional[str]:
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backups_dir / f"backup_{timestamp}.zip"
            shutil.make_archive(str(backup_file).replace('.zip', ''), 'zip', DATA_DIR)
            log(f"Backup created: {backup_file}", "success")
            return str(backup_file)
        except Exception as e:
            log_error(f"Backup failed: {e}")
            return None

    def list_backups(self) -> List[Dict]:
        backups = []
        for file in self.backups_dir.glob("*.zip"):
            backups.append({"name": file.stem, "path": str(file), "size": file.stat().st_size, "date": datetime.fromtimestamp(file.stat().st_mtime).isoformat()})
        return sorted(backups, key=lambda x: x['date'], reverse=True)

    def restore_backup(self, backup_name: str) -> bool:
        try:
            backup_file = self.backups_dir / f"{backup_name}.zip"
            if not backup_file.exists():
                log_error(f"Backup not found: {backup_name}")
                return False
            shutil.unpack_archive(backup_file, DATA_DIR)
            log(f"Backup restored: {backup_name}", "success")
            return True
        except Exception as e:
            log_error(f"Restore failed: {e}")
            return False

backup_manager = BackupManager()
__all__ = ["BackupManager", "backup_manager"]