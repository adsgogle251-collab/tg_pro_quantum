#!/usr/bin/env python3
"""PyInstaller configuration for TG PRO QUANTUM Desktop App"""
import PyInstaller.__main__
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent
output_dir = project_root / "dist"
build_dir = project_root / "build"

args = [
    str(project_root / "admin_panel.py"),
    "--onefile",
    "--windowed",
    f"--distpath={output_dir}",
    f"--buildpath={build_dir}",
    "--name=TG-PRO-QUANTUM",
    "--hidden-import=customtkinter",
    "--hidden-import=tkinter",
    "--hidden-import=telethon",
    "--hidden-import=PIL",
    "--hidden-import=aiohttp",
    "--hidden-import=cryptography",
    f"--add-data={project_root / 'gui'}{os.pathsep}gui",
    f"--add-data={project_root / 'license'}{os.pathsep}license",
    f"--add-data={project_root / 'core'}{os.pathsep}core",
    "--optimize=2",
    "--exclude-module=pytest",
    "--exclude-module=unittest",
    "--exclude-module=test",
]

print("=" * 70)
print("Building TG PRO QUANTUM - Windows .exe")
print("=" * 70)
PyInstaller.__main__.run(args)
print("=" * 70)
print("BUILD COMPLETE!")
print(f"Output: {output_dir / 'TG-PRO-QUANTUM.exe'}")
print("=" * 70)