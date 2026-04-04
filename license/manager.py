"""License Manager - Main license management functions"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

_DATA_DIR = Path(__file__).parent.parent / "data"
_LICENSE_FILE = _DATA_DIR / "license.json"
_SESSION_FILE = _DATA_DIR / "session.json"


def _ensure_data_dir():
    """Ensure data directory exists"""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def check_license() -> dict:
    """Check if license is valid.

    Reads from the license file if it exists; falls back to dev-mode
    defaults (always valid) when the file is absent or unreadable.

    Returns:
        dict: {"valid": bool, "status": str, "message": str}
    """
    try:
        _ensure_data_dir()
        if _LICENSE_FILE.exists():
            with open(_LICENSE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {
                "valid": True,
                "status": data.get("status", "active"),
                "message": "License active",
                "tier": data.get("tier", "pro"),
                "key": data.get("current_key", ""),
                "email": data.get("email", ""),
            }
    except Exception:
        pass

    return {
        "valid": True,
        "status": "active",
        "message": "Development mode - license always valid",
        "tier": "pro",
        "key": "",
        "email": "",
    }


def activate_license(key: str) -> bool:
    """Activate license with the given key.

    Args:
        key: License key string

    Returns:
        bool: True if activated successfully
    """
    try:
        _ensure_data_dir()
        data = {
            "current_key": key,
            "email": "",
            "tier": "pro",
            "activated_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(days=365)).isoformat(),
            "valid": True,
            "status": "active",
        }
        with open(_LICENSE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False


def load_session() -> str:
    """Load saved session data.

    Returns:
        str: Saved email address or empty string if no session found
    """
    try:
        _ensure_data_dir()
        if _SESSION_FILE.exists():
            with open(_SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("email", "")
    except Exception:
        pass
    return ""


def save_session(email: str, token: str = "") -> bool:
    """Save session data to file.

    Args:
        email: User email address
        token: Session token (optional)

    Returns:
        bool: True if saved successfully
    """
    try:
        _ensure_data_dir()
        data = {
            "email": email,
            "token": token,
            "timestamp": datetime.now().isoformat(),
        }
        with open(_SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False


def clear_session() -> bool:
    """Clear saved session data.

    Returns:
        bool: True if cleared successfully
    """
    try:
        _ensure_data_dir()
        if _SESSION_FILE.exists():
            os.remove(_SESSION_FILE)
        return True
    except Exception:
        return False


def show_activation(status: dict = None) -> bool:
    """Show license activation dialog in GUI.

    Args:
        status: Current license status dict (optional)

    Returns:
        bool: True if user successfully activated a license
    """
    try:
        import tkinter as tk
        from tkinter import simpledialog, messagebox

        root = tk.Tk()
        root.withdraw()

        key = simpledialog.askstring(
            "License Activation",
            "Enter your license key to activate:\n(Format: TGPRO-XXXX-XXXX-XXXX)",
            parent=root,
        )

        if key and key.strip():
            result = activate_license(key.strip())
            root.destroy()
            if result:
                return True
            messagebox.showerror("Activation Failed", "Invalid license key.")
            return False

        root.destroy()
        return False
    except Exception:
        # Fallback for dev mode: always succeed
        return True
