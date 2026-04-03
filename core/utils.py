"""TG PRO QUANTUM - Core Utilities (Complete & Clean)"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple

# ==================== PATHS & CONSTANTS ====================

BASE_DIR = Path(__file__).parent.parent
SESSIONS_DIR = BASE_DIR / "sessions"
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
BACKUPS_DIR = BASE_DIR / "backups"

ACCOUNTS_FILE = DATA_DIR / "accounts.json"
MESSAGE_FILE = DATA_DIR / "message.txt"
GROUPS_VALID_FILE = DATA_DIR / "groups" / "valid.txt"
GROUPS_JOINED_FILE = DATA_DIR / "groups" / "joined.txt"
GROUPS_BLOCKED_FILE = DATA_DIR / "groups" / "blocked.txt"
REPORT_FILE = DATA_DIR / "reports" / "broadcast_report.txt"
CONFIG_FILE = DATA_DIR / "config.json"
STATS_FILE = DATA_DIR / "statistics.json"

version = "5.0.0"

_gui_logger = None

# ==================== LOGGING ====================

def set_logger(callback):
    """Set GUI logger callback"""
    global _gui_logger
    _gui_logger = callback

def log(msg: str, level: str = "info"):
    """Log message to console, file, and GUI"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] [{level.upper()}] {msg}"
    print(entry)
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOGS_DIR / "app.log", 'a', encoding='utf-8') as f:
            f.write(entry + "\n")
    except: pass
    if _gui_logger:
        try: _gui_logger(entry, level)
        except: pass

def log_error(msg: str): log(msg, "error")
def log_success(msg: str): log(msg, "success")
def log_warning(msg: str): log(msg, "warning")

# ==================== DIRECTORY SETUP ====================

def ensure_dirs():
    """Ensure all required directories exist"""
    dirs = [
        SESSIONS_DIR, DATA_DIR, LOGS_DIR, BACKUPS_DIR,
        DATA_DIR / "accounts", DATA_DIR / "groups",
        DATA_DIR / "campaigns", DATA_DIR / "templates",
        DATA_DIR / "backups", DATA_DIR / "reports",
        DATA_DIR / "scraped",
        SESSIONS_DIR / "sessions_finder",
        SESSIONS_DIR / "sessions_scrape",
        SESSIONS_DIR / "sessions_join",
        SESSIONS_DIR / "sessions_broadcast"
    ]
    for d in dirs: d.mkdir(parents=True, exist_ok=True)

# ==================== MESSAGE MANAGEMENT ====================

def load_message() -> str:
    """Load broadcast message from file"""
    if MESSAGE_FILE.exists():
        try:
            with open(MESSAGE_FILE, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except: pass
    return "🔥 PROMO TERBATAS! Dapatkan harga spesial hari ini!"

def save_message(msg: str):
    """Save broadcast message to file"""
    try:
        MESSAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(MESSAGE_FILE, 'w', encoding='utf-8') as f:
            f.write(msg)
    except Exception as e: log_error(f"Failed to save message: {e}")

# ==================== GROUP MANAGEMENT ====================

def load_groups() -> List[str]:
    """Load groups from valid.txt"""
    groups = []
    if GROUPS_VALID_FILE.exists():
        try:
            with open(GROUPS_VALID_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        groups.append(line)
        except Exception as e: log_error(f"Failed to load groups: {e}")
    return groups

def save_group(group: str) -> bool:
    """Save group to valid.txt"""
    try:
        GROUPS_VALID_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(GROUPS_VALID_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{group}\n")
        return True
    except Exception as e:
        log_error(f"Failed to save group: {e}")
        return False

def load_joined_groups() -> List[str]:
    """Load successfully joined groups"""
    groups = []
    if GROUPS_JOINED_FILE.exists():
        try:
            with open(GROUPS_JOINED_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        groups.append(line)
        except Exception as e: log_error(f"Failed to load joined groups: {e}")
    return groups

def save_joined_group(group_link: str) -> bool:
    """Save successfully joined group"""
    try:
        GROUPS_JOINED_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(GROUPS_JOINED_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{group_link}\n")
        return True
    except Exception as e:
        log_error(f"Failed to save joined group: {e}")
        return False

def load_blocked_groups() -> List[str]:
    """Load blocked groups"""
    groups = []
    if GROUPS_BLOCKED_FILE.exists():
        try:
            with open(GROUPS_BLOCKED_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        groups.append(line)
        except Exception as e: log_error(f"Failed to load blocked groups: {e}")
    return groups

def save_blocked_group(group_link: str) -> bool:
    """Save blocked group"""
    try:
        GROUPS_BLOCKED_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(GROUPS_BLOCKED_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{group_link}\n")
        return True
    except Exception as e:
        log_error(f"Failed to save blocked group: {e}")
        return False

# ==================== ACCOUNT MANAGEMENT ====================

def load_accounts() -> List[Tuple[str, str]]:
    """Load accounts from file (name, phone)"""
    accounts = []
    if ACCOUNTS_FILE.exists():
        try:
            with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for acc in data:
                    accounts.append((acc.get('name', ''), acc.get('phone', '0')))
        except Exception as e: log_error(f"Failed to load accounts: {e}")
    return accounts

def save_accounts(accounts: List[Dict]):
    """Save accounts to file"""
    try:
        ACCOUNTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(accounts, f, indent=2, ensure_ascii=False)
    except Exception as e: log_error(f"Failed to save accounts: {e}")

# ==================== SCRAPED MEMBERS ====================

def save_scraped_members(group_name: str, members: list) -> bool:
    """Save scraped members to file"""
    try:
        scraped_dir = DATA_DIR / "scraped"
        scraped_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{group_name.replace('/', '_')}_{timestamp}.json"
        filepath = scraped_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(members, f, indent=2, ensure_ascii=False)
        
        log(f"Saved {len(members)} members to {filepath}", "success")
        return True
    except Exception as e:
        log_error(f"Failed to save scraped members: {e}")
        return False

def load_scraped_members(filepath: str) -> list:
    """Load scraped members from file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        log_error(f"Failed to load scraped members: {e}")
        return []

# ==================== CONFIG MANAGEMENT ====================

def load_config() -> Dict:
    """Load app configuration"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return {
        "telegram": {"api_id": 0, "api_hash": ""},
        "app": {"theme": "dark", "auto_init": False},
        "sms_activate": {"api_key": ""},
        "openai": {"api_key": ""}
    }

def save_config(config: Dict):
    """Save app configuration"""
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e: log_error(f"Failed to save config: {e}")

# ==================== STATISTICS ====================

def load_statistics() -> Dict:
    """Load statistics from file"""
    if STATS_FILE.exists():
        try:
            with open(STATS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return {
        "total_broadcasts": 0,
        "total_messages_sent": 0,
        "total_messages_failed": 0,
        "total_groups_joined": 0,
        "total_members_scraped": 0,
        "success_rate": 0.0,
        "last_broadcast": None
    }

def save_statistics(stats: Dict):
    """Save statistics to file"""
    try:
        STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
    except Exception as e: log_error(f"Failed to save statistics: {e}")

def update_statistics(**kwargs):
    """Update specific statistics fields"""
    stats = load_statistics()
    for key, value in kwargs.items():
        if key in stats:
            if isinstance(value, int) and isinstance(stats[key], int):
                stats[key] += value
            else:
                stats[key] = value
    
    # Calculate success rate
    total = stats["total_messages_sent"] + stats["total_messages_failed"]
    if total > 0:
        stats["success_rate"] = round(stats["total_messages_sent"] / total * 100, 2)
    
    save_statistics(stats)
    return stats

# ==================== EXPORTS ====================

__all__ = [
    # Version & Paths
    'version', 'BASE_DIR', 'SESSIONS_DIR', 'DATA_DIR', 'LOGS_DIR', 'BACKUPS_DIR',
    'ACCOUNTS_FILE', 'MESSAGE_FILE', 'GROUPS_VALID_FILE', 'GROUPS_JOINED_FILE',
    'GROUPS_BLOCKED_FILE', 'REPORT_FILE', 'CONFIG_FILE', 'STATS_FILE',
    
    # Logging
    'ensure_dirs', 'set_logger', 'log', 'log_error', 'log_success', 'log_warning',
    
    # Message
    'load_message', 'save_message',
    
    # Groups
    'load_groups', 'save_group',
    'load_joined_groups', 'save_joined_group',
    'load_blocked_groups', 'save_blocked_group',
    
    # Accounts
    'load_accounts', 'save_accounts',
    
    # Scraped Members
    'save_scraped_members', 'load_scraped_members',
    
    # Config
    'load_config', 'save_config',
    
    # Statistics
    'load_statistics', 'save_statistics', 'update_statistics',
]