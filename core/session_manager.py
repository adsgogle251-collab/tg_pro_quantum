"""TG PRO QUANTUM - Session Manager"""
import shutil
from pathlib import Path
from typing import List, Dict, Optional
from .utils import SESSIONS_DIR, log, log_error

class SessionManager:
    def __init__(self):
        self.sessions_dir = SESSIONS_DIR

    def save_session(self, name: str, session_data: bytes):
        session_file = self.sessions_dir / f"{name}.session"
        with open(session_file, 'wb') as f:
            f.write(session_data)
        log(f"Session saved: {name}", "success")

    def load_session(self, name: str) -> Optional[bytes]:
        session_file = self.sessions_dir / f"{name}.session"
        if session_file.exists():
            with open(session_file, 'rb') as f:
                return f.read()
        return None

    def import_sessions(self, folder: Path) -> int:
        count = 0
        for file in folder.glob("*.session"):
            target = self.sessions_dir / f"{file.stem}.session"
            if not target.exists():
                shutil.copy2(file, target)
                count += 1
                log(f"Imported session: {file.stem}", "success")
        return count

    def list_sessions(self) -> List[Dict]:
        sessions = []
        for file in self.sessions_dir.glob("*.session*"):
            sessions.append({"name": file.stem.replace('.session', ''), "path": str(file), "size": file.stat().st_size})
        return sessions

session_manager = SessionManager()
__all__ = ["SessionManager", "session_manager"]