"""TG PRO QUANTUM - Modern Premium Dark Theme"""
import tkinter as tk
from tkinter import ttk

# ═══════════════════════════════════════════════════════
# MODERN COLOR PALETTE
# ═══════════════════════════════════════════════════════
COLORS = {
    # Primary - Modern Cyan
    "primary": "#00D4FF",
    "primary_hover": "#00B8E6",
    "primary_light": "#0A2A3F",

    # Backgrounds - Deep Navy / Dark Blue
    "bg_dark": "#0A0E27",        # Main background
    "bg_medium": "#1A1F3A",      # Cards/panels
    "bg_light": "#252D4A",       # Inputs/buttons
    "bg_hover": "#2E3760",

    # Text
    "text": "#E0E0FF",           # Main text
    "text_muted": "#9099B7",     # Secondary text
    "text_light": "#C0C8E8",

    # Accent
    "accent": "#FFB800",         # Gold accent
    "accent_hover": "#E6A500",

    # Status Colors
    "success": "#00FF41",        # Neon Green
    "success_light": "#003D0F",
    "warning": "#FFB800",        # Gold
    "warning_light": "#3D2B00",
    "error": "#FF0055",          # Red
    "error_light": "#3D0015",
    "info": "#00D4FF",           # Cyan
    "info_light": "#002A3D",
    "secondary": "#FF006E",      # Pink

    # Feature Colors
    "broadcast": "#00FF41",      # Green
    "finder": "#00D4FF",         # Cyan
    "scrape": "#9B59FF",         # Purple
    "join": "#FFB800",           # Gold
    "cs": "#FF006E",             # Pink
    "campaign": "#FF6B35",       # Orange
    "analytics": "#3BF5E1",      # Teal

    # Borders
    "border": "#2A3550",
    "border_focus": "#00D4FF",
}

# ═══════════════════════════════════════════════════════
# FONTS
# ═══════════════════════════════════════════════════════
FONTS = {
    "heading_large": ("Segoe UI", 22, "bold"),
    "heading": ("Segoe UI", 14, "bold"),
    "subheading": ("Segoe UI", 12, "bold"),
    "normal": ("Segoe UI", 11),
    "small": ("Segoe UI", 9),
    "bold": ("Segoe UI", 11, "bold"),
    "mono": ("Consolas", 10),
    "title": ("Segoe UI", 18, "bold"),
}

# ═══════════════════════════════════════════════════════
# UI SETTINGS
# ═══════════════════════════════════════════════════════
UI_SETTINGS = {
    "button_radius": 8,
    "input_radius": 6,
    "card_radius": 12,
    "shadow_depth": 3,
    "padding": 12,
}


def setup_theme(root=None):
    """Apply modern dark theme"""
    if root is None:
        root = tk._default_root
    if root is None:
        return

    style = ttk.Style()
    try:
        style.theme_use('clam')
    except Exception:
        pass

    # Global styles
    style.configure(".",
                    background=COLORS["bg_dark"],
                    foreground=COLORS["text"],
                    font=FONTS["normal"])

    style.configure("TFrame", background=COLORS["bg_dark"])
    style.configure("TLabel", background=COLORS["bg_dark"], foreground=COLORS["text"])
    style.configure("TButton",
                    background=COLORS["primary"],
                    foreground="#000000",
                    font=FONTS["bold"],
                    padding=[10, 6])
    style.map("TButton",
              background=[("active", COLORS["primary_hover"])])
    style.configure("TEntry",
                    fieldbackground=COLORS["bg_light"],
                    foreground=COLORS["text"],
                    insertcolor=COLORS["text"])
    style.configure("TCombobox",
                    fieldbackground=COLORS["bg_light"],
                    background=COLORS["bg_light"],
                    foreground=COLORS["text"],
                    selectbackground=COLORS["primary"],
                    selectforeground="#000000")
    style.map("TCombobox",
              fieldbackground=[("readonly", COLORS["bg_light"])],
              foreground=[("readonly", COLORS["text"])])
    style.configure("Treeview",
                    background=COLORS["bg_medium"],
                    foreground=COLORS["text"],
                    fieldbackground=COLORS["bg_medium"],
                    rowheight=26)
    style.configure("Treeview.Heading",
                    background=COLORS["bg_light"],
                    foreground=COLORS["primary"],
                    font=FONTS["bold"])
    style.map("Treeview",
              background=[("selected", COLORS["primary_light"])],
              foreground=[("selected", COLORS["primary"])])
    style.configure("TNotebook", background=COLORS["bg_dark"])
    style.configure("TNotebook.Tab",
                    background=COLORS["bg_light"],
                    foreground=COLORS["text_muted"],
                    padding=[14, 8],
                    font=FONTS["normal"])
    style.map("TNotebook.Tab",
              background=[("selected", COLORS["bg_medium"])],
              foreground=[("selected", COLORS["primary"])])
    style.configure("TScrollbar",
                    background=COLORS["bg_light"],
                    troughcolor=COLORS["bg_dark"],
                    arrowcolor=COLORS["text_muted"])
    style.configure("TLabelframe",
                    background=COLORS["bg_medium"],
                    foreground=COLORS["primary"],
                    font=FONTS["subheading"])
    style.configure("TLabelframe.Label",
                    background=COLORS["bg_medium"],
                    foreground=COLORS["primary"],
                    font=FONTS["subheading"])
    style.configure("TCheckbutton",
                    background=COLORS["bg_medium"],
                    foreground=COLORS["text"])
    style.configure("TRadiobutton",
                    background=COLORS["bg_medium"],
                    foreground=COLORS["text"])
    style.configure("Horizontal.TProgressbar",
                    background=COLORS["primary"],
                    troughcolor=COLORS["bg_light"])
    style.configure("TScale",
                    background=COLORS["bg_medium"],
                    troughcolor=COLORS["bg_light"])


def make_btn(parent, text, command=None, color=None, fg=None, **kwargs):
    """Create a modern styled button"""
    bg = color or COLORS["primary"]
    _light_bg_colors = {COLORS["primary"], COLORS["success"], COLORS["accent"]}
    text_color = fg or ("#000000" if bg in _light_bg_colors else "#ffffff")
    btn = tk.Button(
        parent,
        text=text,
        command=command,
        bg=bg,
        fg=text_color,
        font=FONTS["bold"],
        relief="flat",
        cursor="hand2",
        padx=12,
        pady=6,
        **kwargs
    )

    def on_enter(event):
        btn.config(relief="groove")

    def on_leave(event):
        btn.config(relief="flat")

    btn.bind("<Enter>", on_enter)
    btn.bind("<Leave>", on_leave)
    return btn


def make_label_frame(parent, text, **kwargs):
    """Create a styled LabelFrame"""
    return tk.LabelFrame(
        parent,
        text=text,
        bg=COLORS["bg_medium"],
        fg=COLORS["primary"],
        font=FONTS["subheading"],
        **kwargs
    )


def make_header(parent, text, color=None):
    """Create a modern header label"""
    return tk.Label(
        parent,
        text=text,
        font=FONTS["title"],
        fg=color or COLORS["primary"],
        bg=COLORS["bg_dark"]
    )


__all__ = ["COLORS", "FONTS", "UI_SETTINGS", "setup_theme", "make_btn", "make_label_frame", "make_header"]