"""TG PRO QUANTUM - Premium Dark Theme"""

# Premium Dark Theme Colors
COLORS = {
    # Primary - Modern Blue Gradient
    "primary": "#3B82F6",
    "primary_hover": "#2563EB",
    "primary_light": "#1E3A5F",
    
    # Backgrounds - Dark Professional
    "bg_dark": "#0F172A",        # Main background (dark blue-black)
    "bg_medium": "#1E293B",      # Cards/panels
    "bg_light": "#334155",       # Inputs/buttons
    "bg_hover": "#475569",
    
    # Text - High Contrast
    "text": "#F1F5F9",           # Main text (white-ish)
    "text_muted": "#94A3B8",     # Secondary text
    "text_light": "#CBD5E1",
    
    # Accent - Gold for premium feel
    "accent": "#F59E0B",         # Gold accent
    "accent_hover": "#D97706",
    
    # Status Colors - Vibrant
    "success": "#10B981",        # Green
    "success_light": "#064E3B",
    "warning": "#F59E0B",        # Orange
    "warning_light": "#78350F",
    "error": "#EF4444",          # Red
    "error_light": "#7F1D1D",
    "info": "#3B82F6",           # Blue
    "info_light": "#1E3A8A",
    
    # Feature Buttons - Distinct Colors
    "broadcast": "#10B981",      # Green
    "finder": "#3B82F6",         # Blue
    "scrape": "#8B5CF6",         # Purple
    "join": "#F59E0B",           # Orange
    "cs": "#EC4899",             # Pink
    
    # Borders & Shadows
    "border": "#334155",
    "border_focus": "#3B82F6",
    "shadow": "rgba(0, 0, 0, 0.5)",
}

# Fonts
FONTS = {
    "heading_large": ("Segoe UI", 24, "bold"),
    "heading": ("Segoe UI", 14, "bold"),
    "normal": ("Segoe UI", 11),
    "small": ("Segoe UI", 9),
    "bold": ("Segoe UI", 11, "bold"),
    "mono": ("Consolas", 10),
}

# UI Settings
UI_SETTINGS = {
    "button_radius": 8,
    "input_radius": 6,
    "card_radius": 12,
    "shadow_depth": 3,
}

def setup_theme(root=None):
    """Apply premium dark theme"""
    import tkinter as tk
    from tkinter import ttk
    
    if root is None:
        root = tk._default_root
    if root is None:
        return
    
    style = ttk.Style()
    style.theme_use('clam')
    
    # Global styles
    style.configure(".", 
                    background=COLORS["bg_dark"],
                    foreground=COLORS["text"],
                    font=FONTS["normal"])
    
    style.configure("TFrame", background=COLORS["bg_dark"])
    style.configure("TLabel", background=COLORS["bg_dark"], foreground=COLORS["text"])
    style.configure("TButton", 
                    background=COLORS["primary"],
                    foreground="white",
                    font=FONTS["normal"])
    style.configure("TEntry", 
                    fieldbackground=COLORS["bg_light"],
                    foreground=COLORS["text"])
    style.configure("Treeview",
                    background=COLORS["bg_medium"],
                    foreground=COLORS["text"],
                    fieldbackground=COLORS["bg_light"])
    style.configure("Treeview.Heading",
                    background=COLORS["bg_light"],
                    foreground=COLORS["text"])
    style.configure("TNotebook", background=COLORS["bg_dark"])
    style.configure("TNotebook.Tab",
                    background=COLORS["bg_light"],
                    foreground=COLORS["text"],
                    padding=[20, 10])
    style.map("TNotebook.Tab",
              background=[("selected", COLORS["bg_medium"])],
              foreground=[("selected", COLORS["primary"])])

__all__ = ["COLORS", "FONTS", "UI_SETTINGS", "setup_theme"]