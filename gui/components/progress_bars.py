"""
TG PRO QUANTUM – Phase 5A Animated Progress Bar Component

``AnimatedProgressBar`` is a Canvas-based widget that smoothly animates
towards a target value and supports label overlays.
"""
from __future__ import annotations

import tkinter as tk
from typing import Optional

from gui.themes.colors import (
    PRIMARY, SUCCESS, ERROR, WARNING,
    BG_MEDIUM, TEXT, TEXT_MUTED,
)

__all__ = ["AnimatedProgressBar"]

# ── animation settings ────────────────────────────────────────────────────────
_STEP_DELAY = 16   # ms between animation frames
_STEP_SIZE  = 2    # percentage points per frame (max)


class AnimatedProgressBar(tk.Frame):
    """
    Animated canvas progress bar.

    Parameters
    ----------
    parent:
        Parent widget.
    width / height:
        Dimensions in pixels.
    maximum:
        Value that corresponds to 100 %.
    color:
        Fill colour of the bar.  Use ``"auto"`` to pick green/yellow/red
        automatically based on the current value.
    show_label:
        Display ``"XX%"`` text centred on the bar.
    **kwargs:
        Forwarded to tk.Frame.
    """

    def __init__(
        self,
        parent: tk.Widget,
        width: int = 300,
        height: int = 18,
        maximum: float = 100.0,
        color: str = PRIMARY,
        show_label: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(parent, bg=kwargs.pop("bg", BG_MEDIUM), **kwargs)
        self._width    = width
        self._height   = height
        self._maximum  = maximum if maximum > 0 else 1.0
        self._color    = color
        self._auto     = color == "auto"
        self._show_lbl = show_label

        self._current: float = 0.0
        self._target:  float = 0.0
        self._anim_id: Optional[str] = None

        self._canvas = tk.Canvas(
            self,
            width=width, height=height,
            bg=BG_MEDIUM,
            highlightthickness=0,
        )
        self._canvas.pack(fill="both", expand=True)

        self._bar_id:   int = self._canvas.create_rectangle(
            0, 0, 0, height, fill=PRIMARY, outline="", tags="bar"
        )
        self._label_id: int = self._canvas.create_text(
            width // 2, height // 2,
            text="", fill=TEXT, font=("Segoe UI", 8, "bold"), tags="lbl"
        )

        self._canvas.bind("<Configure>", self._on_resize)

    # ── public API ────────────────────────────────────────────────────────────

    def set(self, value: float) -> None:
        """Animate the bar to *value* (clamped to [0, maximum])."""
        self._target = max(0.0, min(float(value), self._maximum))
        self._start_animation()

    def set_immediate(self, value: float) -> None:
        """Jump to *value* without animation."""
        self._current = max(0.0, min(float(value), self._maximum))
        self._target  = self._current
        if self._anim_id:
            self.after_cancel(self._anim_id)
            self._anim_id = None
        self._redraw()

    @property
    def value(self) -> float:
        return self._current

    # ── internal animation ────────────────────────────────────────────────────

    def _start_animation(self) -> None:
        if self._anim_id:
            return
        self._tick()

    def _tick(self) -> None:
        diff = self._target - self._current
        if abs(diff) < 0.5:
            self._current = self._target
            self._redraw()
            self._anim_id = None
            return
        self._current += max(-_STEP_SIZE, min(_STEP_SIZE, diff))
        self._redraw()
        self._anim_id = self.after(_STEP_DELAY, self._tick)

    def _redraw(self) -> None:
        pct     = self._current / self._maximum
        bar_w   = int(self._canvas.winfo_width() * pct)
        bar_h   = self._canvas.winfo_height()
        fill    = self._resolve_color(pct)

        self._canvas.coords(self._bar_id, 0, 0, bar_w, bar_h)
        self._canvas.itemconfig(self._bar_id, fill=fill)

        if self._show_lbl:
            self._canvas.coords(
                self._label_id,
                self._canvas.winfo_width() // 2,
                bar_h // 2,
            )
            self._canvas.itemconfig(
                self._label_id,
                text=f"{int(pct * 100)}%",
            )

    def _resolve_color(self, pct: float) -> str:
        if not self._auto:
            return self._color
        if pct >= 0.75:
            return SUCCESS
        if pct >= 0.40:
            return WARNING
        return ERROR

    def _on_resize(self, _event=None) -> None:
        self._redraw()
