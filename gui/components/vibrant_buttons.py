"""
TG PRO QUANTUM – Phase 5A Vibrant Button Components

Provides ``VibrantButton`` (tk.Button subclass) and ``make_vibrant_btn()``
factory helper with built-in hover/press effects.
"""
from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional

from gui.themes.colors import (
    PRIMARY, SECONDARY, ACCENT, SUCCESS, ERROR, WARNING,
    BG_DARK, BG_MEDIUM, BG_LIGHT, TEXT, TEXT_MUTED,
    PRIMARY_HOVER, SECONDARY_HOVER, ACCENT_HOVER, SUCCESS_HOVER, ERROR_HOVER,
)

__all__ = ["VibrantButton", "make_vibrant_btn"]

# ── Preset colour pairs (normal, hover, pressed) ──────────────────────────────
_PRESETS: dict[str, tuple[str, str, str]] = {
    "primary":   (PRIMARY,   PRIMARY_HOVER,   "#009BBB"),
    "secondary": (SECONDARY, SECONDARY_HOVER, "#6A1FA8"),
    "accent":    (ACCENT,    ACCENT_HOVER,    "#C04010"),
    "success":   (SUCCESS,   SUCCESS_HOVER,   "#009922"),
    "error":     (ERROR,     ERROR_HOVER,     "#AA0044"),
    "warning":   (WARNING,   "#E6A500",        "#CC9000"),
    "ghost":     (BG_LIGHT,  BG_MEDIUM,        BG_DARK),
}


class VibrantButton(tk.Button):
    """
    A tk.Button with automatic hover and press colour transitions.

    Parameters
    ----------
    parent:
        Parent widget.
    text:
        Button label.
    command:
        Callback invoked on click.
    preset:
        One of ``"primary"``, ``"secondary"``, ``"accent"``, ``"success"``,
        ``"error"``, ``"warning"``, ``"ghost"``.  Defaults to ``"primary"``.
    fg:
        Override foreground colour (defaults to BG_DARK for bright presets,
        TEXT for ghost).
    **kwargs:
        Forwarded to tk.Button.
    """

    def __init__(
        self,
        parent: tk.Widget,
        text: str = "",
        command: Optional[Callable] = None,
        preset: str = "primary",
        fg: Optional[str] = None,
        **kwargs,
    ) -> None:
        normal, hover, pressed = _PRESETS.get(preset, _PRESETS["primary"])

        if fg is None:
            fg = BG_DARK if preset not in ("ghost",) else TEXT

        super().__init__(
            parent,
            text=text,
            command=command,
            bg=normal,
            fg=fg,
            activebackground=hover,
            activeforeground=fg,
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            padx=14,
            pady=7,
            **kwargs,
        )
        self._normal  = normal
        self._hover   = hover
        self._pressed = pressed
        self._fg      = fg

        self.bind("<Enter>",        self._on_enter)
        self.bind("<Leave>",        self._on_leave)
        self.bind("<ButtonPress>",  self._on_press)
        self.bind("<ButtonRelease>",self._on_release)

    # ── hover/press handlers ──────────────────────────────────────────────────

    def _on_enter(self, _event=None) -> None:
        self.configure(bg=self._hover)

    def _on_leave(self, _event=None) -> None:
        self.configure(bg=self._normal)

    def _on_press(self, _event=None) -> None:
        self.configure(bg=self._pressed)

    def _on_release(self, _event=None) -> None:
        self.configure(bg=self._hover)


def make_vibrant_btn(
    parent: tk.Widget,
    text: str,
    command: Optional[Callable] = None,
    preset: str = "primary",
    fg: Optional[str] = None,
    **kwargs,
) -> VibrantButton:
    """
    Factory helper – create and return a :class:`VibrantButton`.

    Example::

        btn = make_vibrant_btn(frame, "Launch", command=start_fn, preset="accent")
        btn.pack(padx=8, pady=4)
    """
    return VibrantButton(parent, text=text, command=command,
                         preset=preset, fg=fg, **kwargs)
