"""
TG PRO QUANTUM – Phase 5A/5B Vibrant Color Definitions
"""
from __future__ import annotations

__all__ = [
    "PRIMARY", "SECONDARY", "ACCENT", "SUCCESS", "ERROR",
    "BG_DARK", "BG_MEDIUM", "BG_LIGHT", "TEXT", "TEXT_MUTED",
    "WARNING", "INFO", "BORDER", "BORDER_FOCUS",
    "COLORS",
]

# ── Core palette ──────────────────────────────────────────────────────────────
PRIMARY      = "#00D9FF"   # Neon Cyan
SECONDARY    = "#7B2CBF"   # Electric Purple
ACCENT       = "#FF6B35"   # Vibrant Orange
SUCCESS      = "#00FF41"   # Lime Green
ERROR        = "#FF006E"   # Hot Pink
WARNING      = "#FFB800"   # Gold
INFO         = "#00D9FF"   # same as PRIMARY

# Backgrounds
BG_DARK      = "#0A0E27"   # Deep Dark
BG_MEDIUM    = "#1A1F3A"   # Medium Dark
BG_LIGHT     = "#252D4A"   # Light Dark

# Text
TEXT         = "#E0E0FF"   # Main text
TEXT_MUTED   = "#9099B7"   # Secondary text

# Borders
BORDER       = "#2A3550"
BORDER_FOCUS = "#00D9FF"

# ── Derived / hover shades ─────────────────────────────────────────────────────
PRIMARY_HOVER   = "#00BBDD"
SECONDARY_HOVER = "#9B3DE8"
ACCENT_HOVER    = "#E05520"
SUCCESS_HOVER   = "#00CC33"
ERROR_HOVER     = "#CC0055"

# ── Dict form (compatible with gui/styles.py COLORS) ─────────────────────────
COLORS: dict[str, str] = {
    "primary":        PRIMARY,
    "primary_hover":  PRIMARY_HOVER,
    "secondary":      SECONDARY,
    "secondary_hover": SECONDARY_HOVER,
    "accent":         ACCENT,
    "accent_hover":   ACCENT_HOVER,
    "success":        SUCCESS,
    "success_hover":  SUCCESS_HOVER,
    "error":          ERROR,
    "error_hover":    ERROR_HOVER,
    "warning":        WARNING,
    "info":           INFO,
    "bg_dark":        BG_DARK,
    "bg_medium":      BG_MEDIUM,
    "bg_light":       BG_LIGHT,
    "text":           TEXT,
    "text_muted":     TEXT_MUTED,
    "border":         BORDER,
    "border_focus":   BORDER_FOCUS,
}
