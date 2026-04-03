"""
╔═══════════════════════════════════════════════════════════╗
║        TG PRO QUANTUM v6.0.0 - Main Application          ║
║           Professional Telegram Broadcast System          ║
║              100% REAL - NOT SIMULATION                   ║
╚═══════════════════════════════════════════════════════════╝
"""
import tkinter as tk
from pathlib import Path
import sys

# ═══════════════════════════════════════════════════════════
# SETUP PATHS
# ═══════════════════════════════════════════════════════════
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

# ═══════════════════════════════════════════════════════════
# MAIN APPLICATION
# ═══════════════════════════════════════════════════════════
def main():
    """Main application entry point - LANGSUNG JALAN!"""
    
    # ═══════════════════════════════════════════════════════
    # IMPORT CORE MODULES
    # ═══════════════════════════════════════════════════════
    try:
        from core import log, ensure_dirs, set_logger, version
        from core.config_manager import get, load_config
        from core.engine import init_engines
        from gui.main_window import MainWindow
        from gui.styles import setup_theme
    except Exception as e:
        print(f"❌ Failed to import core modules: {e}")
        print()
        print("💡 Install dependencies:")
        print("   pip install telethon cryptography pandas")
        print()
        input("Press Enter to exit...")
        sys.exit(1)
    
    # ═══════════════════════════════════════════════════════
    # SETUP DIRECTORIES
    # ═══════════════════════════════════════════════════════
    try:
        ensure_dirs()
    except Exception as e:
        print(f"⚠️ Warning: Failed to create directories: {e}")
    
    # ═══════════════════════════════════════════════════════
    # SETUP THEME
    # ═══════════════════════════════════════════════════════
    try:
        setup_theme()
    except Exception as e:
        print(f"⚠️ Warning: Failed to setup theme: {e}")
    
    # ═══════════════════════════════════════════════════════
    # LOAD CONFIGURATION
    # ═══════════════════════════════════════════════════════
    try:
        config = load_config()
        api_id = get("telegram.api_id", 0)
        api_hash = get("telegram.api_hash", "")
    except Exception as e:
        print(f"⚠️ Warning: Failed to load config: {e}")
        api_id = 0
        api_hash = ""
    
    # ═══════════════════════════════════════════════════════
    # INITIALIZE TELEGRAM ENGINES
    # ═══════════════════════════════════════════════════════
    if api_id and api_hash:
        try:
            init_engines(int(api_id), api_hash)
            log("✅ Telegram engines initialized", "success")
        except Exception as e:
            log(f"⚠️ Warning: Failed to init engines: {e}", "warning")
    else:
        log("⚠️ API not configured. Set in Settings tab.", "warning")
    
    # ═══════════════════════════════════════════════════════
    # CREATE MAIN WINDOW
    # ═══════════════════════════════════════════════════════
    try:
        root = tk.Tk()
        root.title(f"TG PRO QUANTUM v{version} - Enterprise Edition")
        root.geometry("1600x900")
        root.minsize(1400, 800)
        
        # Create application
        app = MainWindow(root)
        
        # Start main loop
        root.mainloop()
        
    except Exception as e:
        print(f"❌ Failed to start application: {e}")
        print()
        print("💡 Try:")
        print("   1. del /s /q *.pyc")
        print("   2. rmdir /s /q __pycache__")
        print("   3. pip install -r requirements.txt")
        print()
        input("Press Enter to exit...")
        sys.exit(1)

# ═══════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    main()