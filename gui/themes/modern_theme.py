"""
TG PRO QUANTUM – Phase 5A Modern Theme Setup
Imports vibrant colors and configures ttk styles for the application.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from gui.themes.colors import (
    PRIMARY, SECONDARY, ACCENT, SUCCESS, ERROR, WARNING,
    BG_DARK, BG_MEDIUM, BG_LIGHT, TEXT, TEXT_MUTED,
    BORDER, BORDER_FOCUS,
    PRIMARY_HOVER, COLORS,
)

__all__ = [
    "setup_modern_theme",
    "PRIMARY", "PRIMARY_HOVER",
    "SECONDARY", "ACCENT", "SUCCESS", "ERROR", "WARNING",
    "BG_DARK", "BG_MEDIUM", "BG_LIGHT", "TEXT", "TEXT_MUTED",
    "BORDER", "BORDER_FOCUS", "COLORS",
]


def setup_modern_theme(root: tk.Tk) -> ttk.Style:
    """
    Apply the Phase-5 vibrant theme to *root*.

    Returns the configured ``ttk.Style`` instance.
    """
    style = ttk.Style(root)
    style.theme_use("clam")

    # ── General frame / label ─────────────────────────────────────────────────
    style.configure(".", background=BG_DARK, foreground=TEXT,
                    font=("Segoe UI", 10), borderwidth=0)

    style.configure("TFrame", background=BG_DARK)
    style.configure("Card.TFrame", background=BG_MEDIUM)
    style.configure("Panel.TFrame", background=BG_LIGHT)

    style.configure("TLabel", background=BG_DARK, foreground=TEXT)
    style.configure("Muted.TLabel", background=BG_DARK, foreground=TEXT_MUTED)
    style.configure("Header.TLabel", background=BG_DARK, foreground=PRIMARY,
                    font=("Segoe UI", 14, "bold"))

    # ── Buttons ───────────────────────────────────────────────────────────────
    style.configure(
        "TButton",
        background=BG_LIGHT, foreground=TEXT,
        font=("Segoe UI", 10, "bold"),
        borderwidth=0, focusthickness=0, padding=(12, 6),
    )
    style.map("TButton",
              background=[("active", BG_MEDIUM), ("pressed", BORDER_FOCUS)],
              foreground=[("active", PRIMARY)])

    style.configure("Primary.TButton",
                    background=PRIMARY, foreground=BG_DARK,
                    font=("Segoe UI", 10, "bold"))
    style.map("Primary.TButton",
              background=[("active", PRIMARY_HOVER), ("pressed", PRIMARY_HOVER)])

    style.configure("Danger.TButton",
                    background=ERROR, foreground=TEXT,
                    font=("Segoe UI", 10, "bold"))
    style.map("Danger.TButton",
              background=[("active", "#CC0055"), ("pressed", "#AA0044")])

    style.configure("Success.TButton",
                    background=SUCCESS, foreground=BG_DARK,
                    font=("Segoe UI", 10, "bold"))
    style.map("Success.TButton",
              background=[("active", "#00CC33"), ("pressed", "#009922")])

    # ── Entry / Combobox ──────────────────────────────────────────────────────
    style.configure("TEntry",
                    fieldbackground=BG_LIGHT, foreground=TEXT,
                    insertcolor=PRIMARY, borderwidth=1,
                    relief="flat")
    style.map("TEntry",
              fieldbackground=[("focus", BG_MEDIUM)],
              bordercolor=[("focus", BORDER_FOCUS), ("!focus", BORDER)])

    style.configure("TCombobox",
                    fieldbackground=BG_LIGHT, foreground=TEXT,
                    selectbackground=BG_MEDIUM, selectforeground=PRIMARY,
                    arrowcolor=TEXT_MUTED, borderwidth=1)

    # ── Scrollbar ─────────────────────────────────────────────────────────────
    style.configure("TScrollbar",
                    background=BG_MEDIUM, troughcolor=BG_DARK,
                    arrowcolor=TEXT_MUTED, borderwidth=0)
    style.map("TScrollbar",
              background=[("active", BG_LIGHT)])

    # ── Progressbar ───────────────────────────────────────────────────────────
    style.configure("TProgressbar",
                    background=PRIMARY, troughcolor=BG_MEDIUM,
                    borderwidth=0, thickness=8)
    style.configure("Success.TProgressbar",
                    background=SUCCESS, troughcolor=BG_MEDIUM)
    style.configure("Danger.TProgressbar",
                    background=ERROR, troughcolor=BG_MEDIUM)

    # ── Notebook ──────────────────────────────────────────────────────────────
    style.configure("TNotebook", background=BG_DARK, borderwidth=0)
    style.configure("TNotebook.Tab",
                    background=BG_MEDIUM, foreground=TEXT_MUTED,
                    padding=(12, 6), font=("Segoe UI", 10))
    style.map("TNotebook.Tab",
              background=[("selected", BG_LIGHT)],
              foreground=[("selected", PRIMARY)])

    # ── Separator ─────────────────────────────────────────────────────────────
    style.configure("TSeparator", background=BORDER)

    return style
