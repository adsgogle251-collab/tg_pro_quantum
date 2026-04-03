"""User Manager - Authentication & Session Management"""
import hashlib
import json
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from .utils import DATA_DIR, log

USERS_FILE = DATA_DIR / "users.json"
SESSIONS_FILE = DATA_DIR / "sessions.json"

# Enums for backward compatibility
class UserRole(Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    TRIAL = "trial"

class Permission(Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    OWNER = "owner"

class UserManager:
    def __init__(self):
        self.users = self._load_users()
        self.sessions = self._load_sessions()
    
    def _load_users(self):
        """Load users from file with proper error handling"""
        try:
            if USERS_FILE.exists():
                with open(USERS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Ensure proper structure
                    if isinstance(data, dict) and "users" in data:
                        return data
                    # If file exists but wrong structure, create default
                    log("Users file has wrong structure, creating default", "warning")
            else:
                log("Users file not found, creating default", "info")
        except Exception as e:
            log(f"Error loading users: {e}", "error")
        
        # Default admin user
        return {
            "users": [
                {
                    "email": "admin@tgproquantum.com",
                    "password": self._hash_password("admin123"),
                    "name": "Admin",
                    "role": "owner",
                    "created": datetime.now().isoformat(),
                    "security_question": "What is your favorite color?",
                    "security_answer": self._hash_password("blue"),
                    "last_login": None,
                    "license_key": None,
                    "permissions": ["read", "write", "delete", "admin", "owner"]
                }
            ]
        }
    
    def _save_users(self):
        """Save users to file"""
        try:
            USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(USERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, indent=2)
        except Exception as e:
            log(f"Error saving users: {e}", "error")
    
    def _load_sessions(self):
        """Load sessions from file"""
        try:
            if SESSIONS_FILE.exists():
                with open(SESSIONS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            log(f"Error loading sessions: {e}", "error")
        return {"sessions": []}
    
    def _save_sessions(self):
        """Save sessions to file"""
        try:
            SESSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(SESSIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.sessions, f, indent=2)
        except Exception as e:
            log(f"Error saving sessions: {e}", "error")
    
    def _hash_password(self, password):
        """Hash password with salt"""
        salt = "tgpro_salt_2024"
        return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
    
    def _generate_token(self):
        """Generate secure session token"""
        return secrets.token_urlsafe(32)
    
    def add_user(self, email, password, name, role="member", security_question="", security_answer="", permissions=None):
        """Add new user"""
        # Ensure structure exists
        if "users" not in self.users:
            self.users["users"] = []
        
        # Check if email exists
        for user in self.users["users"]:
            if user["email"] == email:
                return {"success": False, "error": "Email already registered"}
        
        user = {
            "email": email,
            "password": self._hash_password(password),
            "name": name,
            "role": role,
            "created": datetime.now().isoformat(),
            "security_question": security_question or "What is your favorite color?",
            "security_answer": self._hash_password(security_answer or "blue"),
            "last_login": None,
            "license_key": None,
            "permissions": permissions or (["read", "write"] if role == "member" else ["read", "write", "delete", "admin"])
        }
        
        self.users["users"].append(user)
        self._save_users()
        log(f"User added: {email}", "success")
        return {"success": True, "user": user}
    
    def authenticate(self, email, password):
        """Authenticate user"""
        if "users" not in self.users:
            return {"success": False, "error": "No users found"}
        
        for user in self.users["users"]:
            if user["email"] == email and user["password"] == self._hash_password(password):
                # Update last login
                user["last_login"] = datetime.now().isoformat()
                self._save_users()
                log(f"User authenticated: {email}", "success")
                return {"success": True, "user": user}
        log(f"Authentication failed: {email}", "warning")
        return {"success": False, "error": "Invalid email or password"}
    
    def get_user(self, email):
        """Get user by email"""
        if "users" not in self.users:
            return None
        
        for user in self.users["users"]:
            if user["email"] == email:
                return user
        return None
    
    def update_user_license(self, email, license_key):
        """Update user's license key"""
        if "users" not in self.users:
            return False
        
        for user in self.users["users"]:
            if user["email"] == email:
                user["license_key"] = license_key
                self._save_users()
                return True
        return False
    
    def create_session(self, email):
        """Create session for auto-login"""
        token = self._generate_token()
        session = {
            "token": token,
            "email": email,
            "created": datetime.now().isoformat(),
            "expires": (datetime.now() + timedelta(days=30)).isoformat()
        }
        self.sessions["sessions"].append(session)
        self._save_sessions()
        return token
    
    def validate_session(self, token):
        """Validate session token"""
        for session in self.sessions.get("sessions", []):
            if session["token"] == token:
                # Check expiry
                expiry = datetime.fromisoformat(session["expires"])
                if datetime.now() > expiry:
                    self.sessions["sessions"].remove(session)
                    self._save_sessions()
                    return None
                return session["email"]
        return None
    
    def clear_session(self, token):
        """Clear session (logout)"""
        self.sessions["sessions"] = [s for s in self.sessions.get("sessions", []) if s["token"] != token]
        self._save_sessions()
    
    def reset_password(self, email, security_answer, new_password):
        """Reset password with security question"""
        if "users" not in self.users:
            return {"success": False, "error": "No users found"}
        
        for user in self.users["users"]:
            if user["email"] == email:
                if user["security_answer"] == self._hash_password(security_answer):
                    user["password"] = self._hash_password(new_password)
                    self._save_users()
                    log(f"Password reset: {email}", "success")
                    return {"success": True}
                return {"success": False, "error": "Incorrect security answer"}
        return {"success": False, "error": "User not found"}
    
    def get_all_users(self):
        """Get all users (for admin)"""
        return self.users.get("users", [])
    
    def delete_user(self, email):
        """Delete user"""
        if "users" not in self.users:
            return False
        
        self.users["users"] = [u for u in self.users["users"] if u["email"] != email]
        self._save_users()
        return True
    
    def has_permission(self, email, permission):
        """Check if user has permission"""
        user = self.get_user(email)
        if not user:
            return False
        return permission in user.get("permissions", [])

# Global instance
user_manager = UserManager()
__all__ = ["UserManager", "user_manager", "UserRole", "Permission"]