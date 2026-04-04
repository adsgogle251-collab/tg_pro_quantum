"""
TG PRO QUANTUM – Phase 5B Campaign Management Page

Frame-overlay page for creating and monitoring broadcast campaigns.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional, List, Dict, Any

from gui.styles import COLORS, FONTS
from gui.components.vibrant_buttons import make_vibrant_btn
from gui.components.progress_bars import AnimatedProgressBar
from gui.components.animated_cards import AnimatedCard

__all__ = ["CampaignsPage"]

BG    = COLORS["bg_dark"]
PANEL = COLORS["bg_medium"]
CARD  = COLORS["bg_light"]
CYAN  = COLORS["primary"]
GREEN = COLORS["success"]
TEXT  = COLORS["text"]
MUTED = COLORS["text_muted"]
RED   = COLORS["error"]


class CampaignsPage:
    """
    Campaign management overlay.

    Usage::

        page = CampaignsPage(parent_frame, on_new_campaign=handler)
        page.show()
    """

    def __init__(
        self,
        parent: tk.Widget,
        on_new_campaign: Optional[Callable] = None,
        on_open_campaign: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        self.parent          = parent
        self.on_new_campaign = on_new_campaign
        self.on_open_campaign = on_open_campaign

        self._campaigns: List[Dict[str, Any]] = []

        self.frame = tk.Frame(parent, bg=BG)
        self._build()

    # ── public API ────────────────────────────────────────────────────────────

    def show(self) -> None:
        self.frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._refresh_table()

    def hide(self) -> None:
        self.frame.place_forget()

    def set_campaigns(self, campaigns: List[Dict[str, Any]]) -> None:
        """Replace the campaign list and refresh the table."""
        self._campaigns = campaigns
        self._refresh_table()

    # ── build ─────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        f = self.frame

        # header
        hdr = tk.Frame(f, bg=PANEL, height=56)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="📡  Campaigns", bg=PANEL, fg=CYAN,
                 font=FONTS["heading"]).pack(side="left", padx=20, pady=12)
        make_vibrant_btn(hdr, "+ New Campaign", preset="primary",
                         command=self._on_new).pack(side="right", padx=16, pady=10)

        # filter bar
        fb = tk.Frame(f, bg=BG, pady=10)
        fb.pack(fill="x", padx=20)
        for label, val in [("All", "all"), ("Active", "active"),
                            ("Paused", "paused"), ("Completed", "done")]:
            btn = tk.Button(fb, text=label, bg=CARD, fg=MUTED,
                            font=FONTS["small"], relief="flat",
                            borderwidth=0, padx=10, pady=4, cursor="hand2",
                            command=lambda v=val: self._filter(v))
            btn.pack(side="left", padx=(0, 6))

        # campaign table
        table_frame = tk.Frame(f, bg=BG)
        table_frame.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        self._build_table(table_frame)

    def _build_table(self, parent: tk.Widget) -> None:
        cols = ("name", "status", "progress", "sent", "accounts", "created")
        self._tree = ttk.Treeview(parent, columns=cols, show="headings",
                                   style="Treeview")
        headers = {
            "name":     ("Campaign Name", 200),
            "status":   ("Status",         90),
            "progress": ("Progress",       110),
            "sent":     ("Sent",            80),
            "accounts": ("Accounts",        80),
            "created":  ("Created",        130),
        }
        for col, (heading, width) in headers.items():
            self._tree.heading(col, text=heading)
            self._tree.column(col, width=width, minwidth=60)

        scroll_y = ttk.Scrollbar(parent, orient="vertical",
                                  command=self._tree.yview)
        self._tree.configure(yscrollcommand=scroll_y.set)
        scroll_y.pack(side="right", fill="y")
        self._tree.pack(fill="both", expand=True)

        self._tree.bind("<Double-1>", self._on_row_double_click)

    def _refresh_table(self) -> None:
        self._tree.delete(*self._tree.get_children())
        for c in self._campaigns:
            self._tree.insert("", tk.END, values=(
                c.get("name",     "—"),
                c.get("status",   "—"),
                f"{c.get('progress', 0):.0f}%",
                c.get("sent",     0),
                c.get("accounts", 0),
                c.get("created",  "—"),
            ))

    # ── event handlers ────────────────────────────────────────────────────────

    def _on_new(self) -> None:
        if self.on_new_campaign:
            self.on_new_campaign()

    def _filter(self, status: str) -> None:
        self._tree.delete(*self._tree.get_children())
        for c in self._campaigns:
            if status == "all" or c.get("status", "").lower() == status:
                self._tree.insert("", tk.END, values=(
                    c.get("name", "—"), c.get("status", "—"),
                    f"{c.get('progress', 0):.0f}%",
                    c.get("sent", 0), c.get("accounts", 0),
                    c.get("created", "—"),
                ))

    def _on_row_double_click(self, event) -> None:
        sel = self._tree.selection()
        if not sel or not self.on_open_campaign:
            return
        idx = self._tree.index(sel[0])
        if idx < len(self._campaigns):
            self.on_open_campaign(self._campaigns[idx])
