"""TG PRO QUANTUM - Health Checker"""
import psutil
from pathlib import Path
from datetime import datetime
from .utils import BASE_DIR, SESSIONS_DIR, log_error

class HealthChecker:
    def __init__(self):
        self.start_time = datetime.now()

    def get_health_summary(self) -> dict:
        try:
            cpu = psutil.cpu_percent()
            memory = psutil.virtual_memory().percent
            disk = psutil.disk_usage(str(BASE_DIR)).percent
            sessions_count = len(list(SESSIONS_DIR.glob("*.session*")))
            if cpu > 90 or memory > 90 or disk > 90: status = "critical"
            elif cpu > 70 or memory > 70 or disk > 70: status = "warning"
            else: status = "healthy"
            uptime = str(datetime.now() - self.start_time).split('.')[0]
            return {"status": status, "uptime": uptime, "cpu": f"{cpu}%", "memory": f"{memory}%", "disk": f"{disk}%", "sessions": sessions_count}
        except Exception as e:
            log_error(f"Health check failed: {e}")
            return {"status": "unknown", "uptime": "N/A", "cpu": "N/A", "memory": "N/A", "disk": "N/A", "sessions": 0}

    def check_system(self) -> dict:
        try:
            return {"status": "healthy", "uptime": str(datetime.now() - self.start_time).split('.')[0], "system": {"cpu_percent": psutil.cpu_percent(), "memory_percent": psutil.virtual_memory().percent}, "disk": {"used_percent": psutil.disk_usage(str(BASE_DIR)).percent}, "sessions": {"total": len(list(SESSIONS_DIR.glob("*.session*")))}, "alerts": []}
        except Exception as e:
            return {"status": "error", "error": str(e)}

health_checker = HealthChecker()
__all__ = ["HealthChecker", "health_checker"]