#!/usr/bin/env python3
"""
PyInstaller build script for TG PRO QUANTUM desktop application.

Usage:
    python build_executable.py

Output:
    dist/TG-PRO-QUANTUM.exe  (standalone Windows executable)
"""

import subprocess
import sys
import shutil
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────
APP_NAME = "TG-PRO-QUANTUM"
ENTRY_POINT = "admin_panel.py"
DIST_DIR = Path("dist")
BUILD_DIR = Path("build")


def build():
    """Run PyInstaller to produce a standalone .exe."""
    args = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--console",
        f"--name={APP_NAME}",
        "--distpath=dist",
        "--workpath=build",
        "--specpath=.",
        # Hidden imports required by CustomTkinter & Telethon
        "--hidden-import=customtkinter",
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.ttk",
        "--hidden-import=tkinterdnd2",
        "--hidden-import=PIL",
        "--hidden-import=PIL._tkinter_finder",
        "--hidden-import=telethon",
        "--hidden-import=telethon.sessions",
        "--hidden-import=telethon.tl",
        "--hidden-import=telethon.tl.types",
        "--hidden-import=telethon.tl.functions",
        "--hidden-import=cryptography",
        "--hidden-import=pyotp",
        "--hidden-import=passlib",
        "--hidden-import=passlib.handlers.bcrypt",
        "--hidden-import=jose",
        "--hidden-import=aiofiles",
        "--hidden-import=aiohttp",
        "--hidden-import=pandas",
        "--hidden-import=openpyxl",
        # Collect entire CustomTkinter package (themes / assets)
        "--collect-all=customtkinter",
        "--collect-all=tkinterdnd2",
        ENTRY_POINT,
    ]

    print(f"[BUILD] Running PyInstaller for {APP_NAME}...")
    result = subprocess.run(args, check=False)

    if result.returncode != 0:
        print("[BUILD] PyInstaller failed. Check output above.")
        sys.exit(result.returncode)

    exe_path = DIST_DIR / f"{APP_NAME}.exe"
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"[BUILD] Success! {exe_path}  ({size_mb:.1f} MB)")
    else:
        print(f"[BUILD] Warning: expected output not found at {exe_path}")

    # Clean up spec & build artifacts (keep dist/)
    spec_file = Path(f"{APP_NAME}.spec")
    if spec_file.exists():
        spec_file.unlink()
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)


if __name__ == "__main__":
    build()
