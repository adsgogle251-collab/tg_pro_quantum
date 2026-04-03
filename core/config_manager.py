"""Config Manager - Load/Save Configuration"""
import json
from pathlib import Path
from .utils import DATA_DIR, CONFIG_FILE, log, log_error

DEFAULT_CONFIG = {
    "telegram": {
        "api_id": 0,
        "api_hash": ""
    },
    "broadcast": {
        "delay_min": 10,
        "delay_max": 30,
        "round_robin": True,
        "auto_scrape": False
    },
    "backup": {
        "enabled": True,
        "interval_hours": 24
    },
    "notifications": {
        "enabled": True,
        "email": "",
        "telegram_bot": ""
    }
}

_config_cache = None

def load_config() -> dict:
    """Load configuration from file"""
    global _config_cache
    
    if _config_cache is not None:
        return _config_cache
    
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Merge with defaults
            for key, value in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value
                elif isinstance(value, dict):
                    for k, v in value.items():
                        if k not in config[key]:
                            config[key][k] = v
            
            _config_cache = config
            log("Configuration loaded", "info")
            return config
        except Exception as e:
            log_error(f"Failed to load config: {e}")
            _config_cache = DEFAULT_CONFIG.copy()
            return _config_cache
    else:
        _config_cache = DEFAULT_CONFIG.copy()
        save_config(_config_cache)
        log("Created default configuration", "info")
        return _config_cache

def save_config(config: dict) -> bool:
    """Save configuration to file"""
    global _config_cache
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        _config_cache = config
        log("Configuration saved", "success")
        return True
    except Exception as e:
        log_error(f"Failed to save config: {e}")
        return False

def get(key: str, default=None):
    """Get config value by dot notation (e.g., 'telegram.api_id')"""
    config = load_config()
    keys = key.split('.')
    value = config
    
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default
    
    return value

def set_value(key: str, value):
    """Set config value by dot notation"""
    global _config_cache
    config = load_config()
    keys = key.split('.')
    
    current = config
    for k in keys[:-1]:
        if k not in current:
            current[k] = {}
        current = current[k]
    
    current[keys[-1]] = value
    _config_cache = config
    return save_config(config)

# ✅ CREATE config_manager OBJECT FOR IMPORT
class ConfigManager:
    """Config Manager Class"""
    @staticmethod
    def load():
        return load_config()
    
    @staticmethod
    def save(config):
        return save_config(config)
    
    @staticmethod
    def get(key, default=None):
        return get(key, default)
    
    @staticmethod
    def set(key, value):
        return set_value(key, value)

# ✅ EXPORT config_manager AS OBJECT
config_manager = ConfigManager()

# ✅ EXPORT ALL
__all__ = [
    "load_config",
    "save_config", 
    "get",
    "set_value",
    "config_manager",
    "DEFAULT_CONFIG"
]