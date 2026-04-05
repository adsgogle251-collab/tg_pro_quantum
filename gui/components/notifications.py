"""
TG PRO QUANTUM – Phase 5A Toast Notification System

``ToastNotification`` renders small popup banners in a corner of the root
window.  Call ``show_success()``, ``show_error()``, or ``show_info()``.
"""
from __future__ import annotations

import tkinter as tk
from typing import Optional

from gui.themes.colors import (
    SUCCESS, ERROR, PRIMARY, WARNING,
    BG_MEDIUM, BG_LIGHT, TEXT, BG_DARK,
)

__all__ = ["ToastNotification"]

# ── defaults ──────────────────────────────────────────────────────────────────
_DEFAULT_DURATION = 3500   # ms the toast is visible
_FADE_STEPS       = 20
_FADE_DELAY       = 30     # ms per fade step
_TOAST_WIDTH      = 300
_TOAST_HEIGHT     = 60
_MARGIN           = 16     # px from window edge


class ToastNotification:
    """
    Manager for on-screen toast notifications.

    Parameters
    ----------
    root:
        The application root ``tk.Tk`` (or any Toplevel) used to anchor
        positions and drive ``after`` loops.
    """

    def __init__(self, root: tk.Tk) -> None:
        self._root    = root
        self._queue:  list[dict] = []
        self._active: list[tk.Toplevel] = []

    # ── public API ────────────────────────────────────────────────────────────

    def show_success(self, message: str, title: str = "Success",
                     duration: int = _DEFAULT_DURATION) -> None:
        """Show a green success toast."""
        self._enqueue(title, message, SUCCESS, "✔", duration)

    def show_error(self, message: str, title: str = "Error",
                   duration: int = _DEFAULT_DURATION) -> None:
        """Show a red/pink error toast."""
        self._enqueue(title, message, ERROR, "✖", duration)

    def show_info(self, message: str, title: str = "Info",
                  duration: int = _DEFAULT_DURATION) -> None:
        """Show a cyan info toast."""
        self._enqueue(title, message, PRIMARY, "ℹ", duration)

    def show_warning(self, message: str, title: str = "Warning",
                     duration: int = _DEFAULT_DURATION) -> None:
        """Show a gold warning toast."""
        self._enqueue(title, message, WARNING, "⚠", duration)

    # ── internal ──────────────────────────────────────────────────────────────

    def _enqueue(self, title: str, message: str, color: str,
                 icon: str, duration: int) -> None:
        self._show_toast(title, message, color, icon, duration)

    def _show_toast(self, title: str, message: str, color: str,
                    icon: str, duration: int) -> None:
        root = self._root
        root.update_idletasks()

        rx = root.winfo_x() + root.winfo_width()  - _TOAST_WIDTH  - _MARGIN
        ry = root.winfo_y() + root.winfo_height() - _TOAST_HEIGHT - _MARGIN
        # Stack active toasts upward
        offset = len(self._active) * (_TOAST_HEIGHT + 8)
        ry -= offset

        win = tk.Toplevel(root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.geometry(f"{_TOAST_WIDTH}x{_TOAST_HEIGHT}+{rx}+{ry}")
        win.configure(bg=BG_MEDIUM)

        # Coloured accent stripe on the left
        stripe = tk.Frame(win, bg=color, width=5)
        stripe.pack(side="left", fill="y")

        body = tk.Frame(win, bg=BG_MEDIUM, padx=10, pady=8)
        body.pack(side="left", fill="both", expand=True)

        tk.Label(body, text=f"{icon}  {title}",
                 bg=BG_MEDIUM, fg=color,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")
        tk.Label(body, text=message,
                 bg=BG_MEDIUM, fg=TEXT,
                 font=("Segoe UI", 9),
                 wraplength=_TOAST_WIDTH - 40,
                 justify="left").pack(anchor="w")

        close_btn = tk.Label(win, text="✕", bg=BG_MEDIUM, fg=TEXT,
                              font=("Segoe UI", 9), cursor="hand2")
        close_btn.place(relx=1.0, rely=0.0, x=-8, y=6, anchor="ne")
        close_btn.bind("<Button-1>", lambda _e: self._dismiss(win))

        self._active.append(win)
        win.after(duration, lambda: self._fade_out(win))

    def _fade_out(self, win: tk.Toplevel) -> None:
        self._fade_step(win, _FADE_STEPS)

    def _fade_step(self, win: tk.Toplevel, steps: int) -> None:
        try:
            alpha = steps / _FADE_STEPS
            win.attributes("-alpha", alpha)
            if steps <= 0:
                self._dismiss(win)
            else:
                win.after(_FADE_DELAY, lambda: self._fade_step(win, steps - 1))
        except tk.TclError:
            pass

    def _dismiss(self, win: tk.Toplevel) -> None:
        try:
            win.destroy()
        except tk.TclError:
            pass
        if win in self._active:
            self._active.remove(win)
