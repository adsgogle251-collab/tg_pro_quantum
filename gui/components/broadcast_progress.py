"""
TG PRO QUANTUM – BroadcastProgressWidget

A compact, self-contained Tkinter widget that shows real-time broadcast
progress.  It subscribes to BroadcastManager callbacks and updates itself
on the Tk main thread.

Usage::

    widget = BroadcastProgressWidget(parent_frame)
    widget.pack(fill="x", padx=8, pady=4)

    # Pass the widget's callback to BroadcastManager.start():
    broadcast_manager.start(
        ...,
        progress_callback=widget.on_progress,
        activity_callback=widget.on_activity,
    )
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Dict, List, Optional

from gui.styles import COLORS, FONTS

BG     = COLORS["bg_medium"]
CARD   = COLORS["bg_light"]
CYAN   = COLORS["primary"]
GREEN  = COLORS["success"]
ORANGE = COLORS["warning"]
RED    = COLORS["error"]
TEXT   = COLORS["text"]
MUTED  = COLORS["text_muted"]


class BroadcastProgressWidget(tk.Frame):
    """
    A Tkinter Frame widget that displays:
    * Progress bar with percentage
    * Sent / Failed / Total counters
    * Current active account
    * Mini activity log (last 50 events)
    """

    def __init__(self, parent: tk.Widget, **kwargs):
        super().__init__(parent, bg=BG, **kwargs)
        self._activity_rows: List[Dict[str, Any]] = []
        self._build()

    # ── Build ──────────────────────────────────────────────────────────────

    def _build(self) -> None:
        # ── Top counters ──────────────────────────────────────────────────
        counter_row = tk.Frame(self, bg=BG)
        counter_row.pack(fill="x", padx=6, pady=4)

        self._sent_lbl   = tk.Label(counter_row, text="✅ Sent: 0",   fg=GREEN,  bg=BG, font=FONTS["body"])
        self._failed_lbl = tk.Label(counter_row, text="❌ Failed: 0", fg=RED,    bg=BG, font=FONTS["body"])
        self._total_lbl  = tk.Label(counter_row, text="📋 Total: 0",  fg=TEXT,   bg=BG, font=FONTS["body"])
        self._rate_lbl   = tk.Label(counter_row, text="📊 Rate: —",   fg=CYAN,   bg=BG, font=FONTS["body"])

        for lbl in (self._sent_lbl, self._failed_lbl, self._total_lbl, self._rate_lbl):
            lbl.pack(side="left", padx=10)

        # ── Progress bar ──────────────────────────────────────────────────
        pb_row = tk.Frame(self, bg=BG)
        pb_row.pack(fill="x", padx=6, pady=2)

        self._progress_var = tk.DoubleVar(value=0.0)
        self._pb = ttk.Progressbar(pb_row, variable=self._progress_var, maximum=100, length=400)
        self._pb.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self._pct_lbl = tk.Label(pb_row, text="0%", fg=CYAN, bg=BG, font=FONTS["small"], width=6)
        self._pct_lbl.pack(side="left")

        # ── Active account ─────────────────────────────────────────────────
        self._active_lbl = tk.Label(
            self, text="📱 Active: —", fg=MUTED, bg=BG, font=FONTS["small"]
        )
        self._active_lbl.pack(anchor="w", padx=10, pady=2)

        # ── Mini activity log ─────────────────────────────────────────────
        log_frame = tk.Frame(self, bg=BG)
        log_frame.pack(fill="both", expand=True, padx=6, pady=4)

        tk.Label(
            log_frame, text="📋 Activity Log", fg=CYAN, bg=BG, font=FONTS["small"]
        ).pack(anchor="w")

        cols = ("Time", "Account", "Group", "Status")
        self._tree = ttk.Treeview(log_frame, columns=cols, show="headings", height=6)
        widths = {"Time": 70, "Account": 120, "Group": 200, "Status": 80}
        for col in cols:
            self._tree.heading(col, text=col)
            self._tree.column(col, width=widths.get(col, 100), anchor="w")

        vsb = ttk.Scrollbar(log_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._tree.pack(fill="both", expand=True)

    # ── Callbacks (called from broadcast thread, scheduled on Tk thread) ──

    def on_progress(self, **kwargs) -> None:
        """Progress callback – safe to call from any thread."""
        self.after(0, self._update_progress, kwargs)

    def on_activity(self, entry: Dict[str, Any]) -> None:
        """Activity callback – safe to call from any thread."""
        self.after(0, self._append_activity, entry)

    # ── Internal updates (always on Tk main thread) ────────────────────────

    def _update_progress(self, data: Dict[str, Any]) -> None:
        sent    = int(data.get("sent", 0))
        failed  = int(data.get("failed", 0))
        total   = int(data.get("total", 0))
        pct     = float(data.get("progress_percent", 0.0))
        done    = data.get("completed", False)
        accs    = data.get("active_accounts", [])

        self._sent_lbl.config(text=f"✅ Sent: {sent}")
        self._failed_lbl.config(text=f"❌ Failed: {failed}")
        self._total_lbl.config(text=f"📋 Total: {total}")

        attempts = sent + failed
        rate = round(sent / attempts * 100, 1) if attempts else 0.0
        rate_color = GREEN if rate >= 90 else ORANGE if rate >= 70 else RED
        self._rate_lbl.config(text=f"📊 Rate: {rate}%", fg=rate_color)

        self._progress_var.set(pct)
        self._pct_lbl.config(text=f"{pct:.0f}%")

        # Show first active account
        if accs and len(accs) > 0:
            self._active_lbl.config(text=f"📱 Active: {accs[0].get('name', '—')[:24]}")

        if done:
            self._active_lbl.config(text="📱 Active: — (COMPLETED)")

    def _append_activity(self, entry: Dict[str, Any]) -> None:
        self._activity_rows.insert(0, entry)
        if len(self._activity_rows) > 50:
            self._activity_rows = self._activity_rows[:50]

        icon = "✅" if entry.get("success") else "❌"
        self._tree.insert(
            "", 0,
            values=(
                entry.get("ts", ""),
                entry.get("account", "?")[:18],
                entry.get("group", "?")[:40],
                icon,
            ),
        )
        # Keep only 50 rows in the tree
        children = self._tree.get_children()
        for old in children[50:]:
            self._tree.delete(old)

    def reset(self) -> None:
        """Clear all counters and log entries (call before new broadcast)."""
        self._activity_rows.clear()
        for item in self._tree.get_children():
            self._tree.delete(item)
        self._sent_lbl.config(text="✅ Sent: 0")
        self._failed_lbl.config(text="❌ Failed: 0")
        self._total_lbl.config(text="📋 Total: 0")
        self._rate_lbl.config(text="📊 Rate: —", fg=CYAN)
        self._progress_var.set(0.0)
        self._pct_lbl.config(text="0%")
        self._active_lbl.config(text="📱 Active: —")


__all__ = ["BroadcastProgressWidget"]
