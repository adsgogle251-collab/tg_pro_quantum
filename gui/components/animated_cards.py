"""
TG PRO QUANTUM – Phase 5A Animated Card Components

``AnimatedCard`` is a tk.Frame subclass that lifts on hover with a subtle
border-colour animation to draw focus.
"""
from __future__ import annotations

import tkinter as tk
from typing import Optional

from gui.themes.colors import (
    BG_MEDIUM, BG_LIGHT, PRIMARY, TEXT, TEXT_MUTED, BORDER,
)

__all__ = ["AnimatedCard", "StatCard"]

# ── animation constants ───────────────────────────────────────────────────────
_ANIM_STEPS  = 6
_ANIM_DELAY  = 16   # ms per step


class AnimatedCard(tk.Frame):
    """
    A rounded-look card that animates its border colour on hover.

    Parameters
    ----------
    parent:
        Parent widget.
    bg:
        Card background colour.
    hover_border:
        Border colour shown when the mouse is over the card.
    border_width:
        Border thickness in pixels.
    **kwargs:
        Forwarded to tk.Frame.
    """

    def __init__(
        self,
        parent: tk.Widget,
        bg: str = BG_MEDIUM,
        hover_border: str = PRIMARY,
        border_width: int = 2,
        **kwargs,
    ) -> None:
        # Outer border frame
        self._border_frame = tk.Frame(parent, bg=BORDER, padx=border_width,
                                      pady=border_width)
        # Inner content frame (this is the public frame)
        super().__init__(self._border_frame, bg=bg, **kwargs)
        super().pack(fill="both", expand=True)

        self._idle_border  = BORDER
        self._hover_border = hover_border
        self._current      = BORDER
        self._anim_id: Optional[str] = None

        # Propagate hover events from children
        self.bind("<Enter>", self._on_enter, add="+")
        self.bind("<Leave>", self._on_leave, add="+")
        self._border_frame.bind("<Enter>", self._on_enter, add="+")
        self._border_frame.bind("<Leave>", self._on_leave, add="+")

    # ── geometry delegation ───────────────────────────────────────────────────

    def pack(self, **kwargs):  # type: ignore[override]
        self._border_frame.pack(**kwargs)

    def grid(self, **kwargs):  # type: ignore[override]
        self._border_frame.grid(**kwargs)

    def place(self, **kwargs):  # type: ignore[override]
        self._border_frame.place(**kwargs)

    # ── animation ─────────────────────────────────────────────────────────────

    def _on_enter(self, _event=None) -> None:
        self._animate_to(self._hover_border)

    def _on_leave(self, _event=None) -> None:
        self._animate_to(self._idle_border)

    def _animate_to(self, target: str) -> None:
        if self._anim_id:
            try:
                self.after_cancel(self._anim_id)
            except Exception:
                pass
        self._step_animation(self._current, target, _ANIM_STEPS)

    def _step_animation(self, start: str, end: str, steps_left: int) -> None:
        if steps_left <= 0:
            self._current = end
            self._border_frame.configure(bg=end)
            return
        blended = _blend(start, end, 1 - steps_left / _ANIM_STEPS)
        self._border_frame.configure(bg=blended)
        self._anim_id = self.after(
            _ANIM_DELAY,
            lambda: self._step_animation(blended, end, steps_left - 1),
        )


class StatCard(AnimatedCard):
    """
    A pre-built card showing a title, large value, and optional subtitle.

    Parameters
    ----------
    parent:
        Parent widget.
    title:
        Label shown at the top of the card.
    value:
        Large central value string.
    subtitle:
        Smaller text beneath the value.
    value_color:
        Colour of the value label.
    **kwargs:
        Forwarded to :class:`AnimatedCard`.
    """

    def __init__(
        self,
        parent: tk.Widget,
        title: str = "",
        value: str = "0",
        subtitle: str = "",
        value_color: str = PRIMARY,
        **kwargs,
    ) -> None:
        super().__init__(parent, **kwargs)
        self.configure(padx=16, pady=14)

        tk.Label(self, text=title, bg=self["bg"], fg=TEXT_MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w")

        self._value_lbl = tk.Label(self, text=value, bg=self["bg"],
                                   fg=value_color,
                                   font=("Segoe UI", 22, "bold"))
        self._value_lbl.pack(anchor="w", pady=(2, 0))

        if subtitle:
            tk.Label(self, text=subtitle, bg=self["bg"], fg=TEXT_MUTED,
                     font=("Segoe UI", 8)).pack(anchor="w")

    def set_value(self, value: str) -> None:
        """Update the displayed value."""
        self._value_lbl.configure(text=value)


# ── colour blending helper ────────────────────────────────────────────────────

def _blend(c1: str, c2: str, t: float) -> str:
    """Linear-interpolate between two hex colours at position *t* (0-1)."""
    t = max(0.0, min(1.0, t))
    r1, g1, b1 = _hex_to_rgb(c1)
    r2, g2, b2 = _hex_to_rgb(c2)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02X}{g:02X}{b:02X}"


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
