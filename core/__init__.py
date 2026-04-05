"""TG PRO QUANTUM - Core Module (Phase 10 - Complete)"""
import logging
import sys
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/app.log', encoding='utf-8', mode='a')
    ]
)

logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
SESSIONS_DIR = BASE_DIR / "sessions"
LOGS_DIR = BASE_DIR / "logs"
CONFIG_FILE = DATA_DIR / "config.json"

# Version
version = "6.0.0"  # ✅ Updated for Phase 10

def log(message: str, level: str = "info"):
    """Log message with level"""
    getattr(logger, level.lower(), logger.info)(message)

def log_error(message: str, exc: Exception = None):
    """Log error with optional exception"""
    if exc:
        logger.error(f"{message}: {exc}", exc_info=True)
    else:
        logger.error(message)

def ensure_dirs():
    """Ensure required directories exist"""
    for d in [DATA_DIR, SESSIONS_DIR, LOGS_DIR]:
        d.mkdir(parents=True, exist_ok=True)

def set_logger(gui_callback):
    """Set callback for GUI log display"""
    class GUILogHandler(logging.Handler):
        def emit(self, record):
            msg = self.format(record)
            level = record.levelname.lower()
            try:
                gui_callback(msg, level)
            except:
                pass
    logger.addHandler(GUILogHandler())

# === IMPORT CORE MODULES ===
from . import utils
from . import database
from . import config_manager
from . import statistics
from . import health_checker
from . import backup_manager
from . import scheduler
from . import account_manager
from . import account_router
from . import import_manager
from . import ai_cs_engine
from . import encryption
from . import session_manager
from . import task_queue
from . import cache_manager
from . import security_ultimate
from . import crm_engine
from . import billing_engine
from . import whitelabel_manager
from . import gdpr_compliance
from . import state_manager  # ✅ State manager for tab sync
from . import localization    # ✅ Bahasa Indonesia localization

# === PHASE 4-5 MODULES ===
from . import templates
from . import group_filters
from . import clients  # ✅ Client manager module
from . import auto_reconnect
from . import broadcast_history
from . import campaign_manager
from . import auto_backup
from . import notification_manager
from . import help_manager

# === PHASE 10 NEW MODULES ===
from . import scheduler_24h  # ✅ 24/7 scheduler
from . import report_generator  # ✅ Auto report generator

# === BROADCAST MANAGER ===
from . import broadcast_manager as _broadcast_manager_module

# === ENTERPRISE MODULES ===
from . import account_group_manager  # ✅ Account group pools

# === IMPORT INSTANCES FOR EASY ACCESS ===
from .account_manager import account_manager
from .account_router import account_router
from .config_manager import config_manager
from .statistics import statistics
from .health_checker import health_checker
from .backup_manager import backup_manager
from .scheduler import scheduler
from .templates import template_manager
from .group_filters import group_filter_manager
from .clients import client_manager  # ✅ Client manager instance
from .auto_reconnect import auto_reconnect
from .broadcast_history import broadcast_history
from .campaign_manager import campaign_manager
from .crm_engine import crm_engine
from .billing_engine import billing_engine
from .whitelabel_manager import whitelabel_manager
from .gdpr_compliance import gdpr_compliance
from .state_manager import state_manager  # ✅ State manager instance
from .localization import t               # ✅ Translation function
from .auto_backup import auto_backup
from .notification_manager import notification_manager
from .help_manager import help_manager

# === MISSING INSTANCE IMPORTS ===
from .import_manager import import_manager  # override module with instance
from .ai_cs_engine import ai_cs_engine  # override module with instance
from .security_ultimate import security_ultimate  # instance

# === PHASE 10 INSTANCES ===
from .scheduler_24h import scheduler_24h  # ✅ 24/7 scheduler instance
from .report_generator import report_generator  # ✅ Report generator instance
from .account_group_manager import account_group_manager  # ✅ Account group manager instance
from .broadcast_manager import broadcast_manager  # ✅ Broadcast manager instance

# === IMPORT UTILITY FUNCTIONS ===
from .utils import (
    load_groups,
    save_group,
    load_message,
    save_message,
    load_accounts,
    save_accounts,
    load_config,
    save_config,
    load_statistics,
    save_statistics,
    update_statistics
)

# === ENGINE IMPORTS (loaded separately to avoid circular import) ===
_engine_initialized = False

def init_engines(api_id: int, api_hash: str):
    """Initialize Telegram engines"""
    global _engine_initialized
    if _engine_initialized:
        return
    try:
        from . import engine
        engine.init(api_id, api_hash)
        _engine_initialized = True
        log("✅ Telegram engines initialized", "success")
    except Exception as e:
        log_error(f"Failed to init engines: {e}")

# === EXPORT PUBLIC API ===
__all__ = [
    # === Logging ===
    "log", "log_error", "ensure_dirs", "set_logger", "version",
    
    # === Paths ===
    "BASE_DIR", "DATA_DIR", "SESSIONS_DIR", "LOGS_DIR", "CONFIG_FILE",
    
    # === Core Modules ===
    "utils", "database", "config_manager", "statistics", "health_checker",
    "backup_manager", "scheduler", "account_manager", "account_router",
    "import_manager", "ai_cs_engine", "encryption", "session_manager",
    "task_queue", "cache_manager", "init_engines",
    "state_manager", "localization", "security_ultimate",
    
    # === Engine Instances ===
    "crm_engine",
    "billing_engine",
    "whitelabel_manager",
    "gdpr_compliance",
    "t",
    
    # === PHASE 4-5 Modules & Instances ===
    "templates", "template_manager",
    "group_filters", "group_filter_manager",
    "clients", "client_manager",
    "auto_reconnect", "broadcast_history",
    "campaign_manager",
    "auto_backup",
    "notification_manager",
    "help_manager",
    
    # === PHASE 10 Modules & Instances ===
    "scheduler_24h",  # ✅ 24/7 scheduler
    "report_generator",  # ✅ Auto report generator
    "broadcast_manager",  # ✅ Broadcast manager

    # === Enterprise Modules & Instances ===
    "account_group_manager",  # ✅ Account group pools
    
    # === Utility Functions ===
    "load_groups", "save_group",
    "load_message", "save_message",
    "load_accounts", "save_accounts",
    "load_config", "save_config",
    "load_statistics", "save_statistics", "update_statistics"
]