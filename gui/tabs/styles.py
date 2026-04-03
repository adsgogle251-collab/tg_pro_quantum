"""
TG PRO AI QUANTUM - UI Styles & Theme
Color scheme and font definitions
"""

# ============================================================================
# COLOR SCHEME
# ============================================================================
COLORS = {
    "bg_dark": "#1a1a2e",
    "bg_medium": "#16213e",
    "bg_light": "#0f3460",
    "accent": "#e94560",
    "accent_primary": "#6366f1",
    "success": "#22c55e",
    "warning": "#f59e0b",
    "error": "#ef4444",
    "info": "#3b82f6",
    "text": "#ffffff",
    "text_muted": "#94a3b8",
    "border": "#334155",
}

# ============================================================================
# FONT DEFINITIONS
# ============================================================================
FONTS = {
    "heading": ("Inter", 16, "bold"),
    "normal": ("Inter", 11),
    "small": ("Inter", 9),
    "bold": ("Inter", 11, "bold"),
    "mono": ("Consolas", 10),
}

# ============================================================================
# THEME SETUP
# ============================================================================
def setup_theme():
    """Setup CustomTkinter dark theme"""
    try:
        import customtkinter as ctk
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
    except ImportError:
        pass

__all__ = ["COLORS", "FONTS", "setup_theme"]