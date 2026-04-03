"""TG PRO QUANTUM - Security Ultimate"""
import json
import hashlib
import secrets
import base64
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from .utils import DATA_DIR, log, log_error

SECURITY_FILE = DATA_DIR / "security.json"
AUDIT_LOG_FILE = DATA_DIR / "audit_log.json"
ENCRYPTION_KEY_FILE = DATA_DIR / ".encryption_key"

@dataclass
class SecurityConfig:
    two_factor_enabled: bool = False
    ip_whitelist_enabled: bool = False
    ip_whitelist: List[str] = field(default_factory=list)
    session_timeout: int = 3600
    max_login_attempts: int = 5
    lockout_duration: int = 900
    password_min_length: int = 8
    require_special_chars: bool = True
    audit_logging: bool = True
    encrypt_database: bool = True

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(**data)

@dataclass
class AuditLogEntry:
    timestamp: str
    user_id: str
    action: str
    resource: str
    ip_address: str
    success: bool
    details: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)

class SecurityUltimate:
    def __init__(self):
        self.security_file = SECURITY_FILE
        self.audit_file = AUDIT_LOG_FILE
        self.config = SecurityConfig()
        self.login_attempts: Dict[str, List[str]] = {}
        self.locked_accounts: Dict[str, datetime] = {}
        self.cipher = None
        self._load()
        self._init_encryption()

    def _load(self):
        if self.security_file.exists():
            try:
                with open(self.security_file, 'r', encoding='utf-8') as f:
                    self.config = SecurityConfig.from_dict(json.load(f))
            except: pass

    def _save(self):
        try:
            self.security_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.security_file, 'w', encoding='utf-8') as f: json.dump(self.config.to_dict(), f, indent=2)
        except: pass

    def _init_encryption(self):
        try:
            key_file = Path(ENCRYPTION_KEY_FILE)
            if not key_file.exists():
                key = Fernet.generate_key()
                key_file.parent.mkdir(parents=True, exist_ok=True)
                with open(key_file, 'wb') as f: f.write(key)
            else:
                with open(key_file, 'rb') as f: key = f.read()
            self.cipher = Fernet(key)
        except Exception as e: log_error(f"Encryption init failed: {e}")

    def hash_password(self, password: str) -> str:
        salt = secrets.token_hex(16)
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt.encode(), iterations=100000)
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return f"{salt}${key.decode()}"

    def verify_password(self, password: str, password_hash: str) -> bool:
        try:
            salt, hash_hex = password_hash.split('$')
            kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt.encode(), iterations=100000)
            expected = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            return expected.decode() == hash_hex
        except: return False

    def validate_password_strength(self, password: str) -> Tuple[bool, List[str]]:
        issues = []
        if len(password) < self.config.password_min_length: issues.append(f"Minimum {self.config.password_min_length} characters")
        if self.config.require_special_chars and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password): issues.append("Special characters required")
        if not any(c.isdigit() for c in password): issues.append("Numbers required")
        if not any(c.isupper() for c in password): issues.append("Uppercase required")
        return len(issues) == 0, issues

    def log_action(self, user_id: str, action: str, resource: str, ip_address: str = "0.0.0.0", success: bool = True, details: str = ""):
        if not self.config.audit_logging: return
        entry = AuditLogEntry(timestamp=datetime.now().isoformat(), user_id=user_id, action=action, resource=resource, ip_address=ip_address, success=success, details=details)
        try:
            logs = []
            if self.audit_file.exists():
                with open(self.audit_file, 'r', encoding='utf-8') as f: logs = json.load(f)
            logs.append(entry.to_dict())
            logs = logs[-10000:]
            self.audit_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.audit_file, 'w', encoding='utf-8') as f: json.dump(logs, f, indent=2)
        except: pass

    def get_audit_logs(self, user_id: Optional[str] = None, limit: int = 100) -> List[Dict]:
        try:
            if not self.audit_file.exists(): return []
            with open(self.audit_file, 'r', encoding='utf-8') as f: logs = json.load(f)
            if user_id: logs = [l for l in logs if l.get("user_id") == user_id]
            logs = sorted(logs, key=lambda x: x.get("timestamp", ""), reverse=True)
            return logs[:limit]
        except: return []

    def run_security_check(self) -> Dict:
        checks = {
            "two_factor": {"enabled": self.config.two_factor_enabled, "status": "✅" if self.config.two_factor_enabled else "⚠️ Recommended"},
            "ip_whitelist": {"enabled": self.config.ip_whitelist_enabled, "count": len(self.config.ip_whitelist)},
            "encryption": {"database": self.config.encrypt_database, "status": "✅" if self.config.encrypt_database else "⚠️ Recommended"},
            "audit_logging": {"enabled": self.config.audit_logging, "status": "✅" if self.config.audit_logging else "⚠️ Recommended"},
            "password_policy": {"min_length": self.config.password_min_length, "status": "✅" if self.config.password_min_length >= 8 else "⚠️ Weak"},
        }
        overall_score = sum(1 for c in checks.values() if c.get("status", "").startswith("✅"))
        return {"checks": checks, "overall_score": f"{overall_score}/{len(checks)}", "security_level": "High" if overall_score >= 4 else "Medium" if overall_score >= 3 else "Low", "recommendations": self._get_security_recommendations()}

    def _get_security_recommendations(self) -> List[str]:
        recommendations = []
        if not self.config.two_factor_enabled: recommendations.append("Enable 2FA for all admin accounts")
        if not self.config.ip_whitelist_enabled: recommendations.append("Enable IP whitelist for admin access")
        if not self.config.encrypt_database: recommendations.append("Enable database encryption")
        if not self.config.audit_logging: recommendations.append("Enable audit logging")
        return recommendations

security_ultimate = SecurityUltimate()
__all__ = ["SecurityUltimate", "SecurityConfig", "AuditLogEntry", "security_ultimate"]