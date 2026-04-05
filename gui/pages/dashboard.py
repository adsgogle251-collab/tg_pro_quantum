"""
TG PRO QUANTUM – Phase 5B Dashboard Page

Modern dashboard overlay with live stat cards, a quick-actions bar and a
mini activity feed.  Follows the same Frame-overlay pattern as
``BroadcastDetailPage``.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from datetime import datetime
from typing import Callable, Optional

from gui.styles import COLORS, FONTS
from gui.components.animated_cards import StatCard
from gui.components.vibrant_buttons import make_vibrant_btn
from gui.components.progress_bars import AnimatedProgressBar

__all__ = ["DashboardPage"]

BG    = COLORS["bg_dark"]
PANEL = COLORS["bg_medium"]
CARD  = COLORS["bg_light"]
CYAN  = COLORS["primary"]
GREEN = COLORS["success"]
TEXT  = COLORS["text"]
MUTED = COLORS["text_muted"]


class DashboardPage:
    """
    Full-screen dashboard overlay.

    Usage::

        page = DashboardPage(parent_frame, on_navigate=switch_page_fn)
        page.show()
    """

    def __init__(
        self,
        parent: tk.Widget,
        on_navigate: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.parent      = parent
        self.on_navigate = on_navigate

        self.frame = tk.Frame(parent, bg=BG)
        self._stat_cards: dict[str, StatCard] = {}
        self._activity_items: list[str] = []
        self._build()

    # ── public API ────────────────────────────────────────────────────────────

    def show(self) -> None:
        self.frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._refresh_stats()

    def hide(self) -> None:
        self.frame.place_forget()

    def update_stats(self, stats: dict) -> None:
        """Push new stats dict; keys match stat card names."""
        for key, card in self._stat_cards.items():
            if key in stats:
                card.set_value(str(stats[key]))

    def add_activity(self, text: str) -> None:
        """Prepend a line to the activity feed."""
        ts = datetime.now().strftime("%H:%M:%S")
        self._activity_items.insert(0, f"[{ts}]  {text}")
        if len(self._activity_items) > 50:
            self._activity_items = self._activity_items[:50]
        self._refresh_activity()

    # ── build ─────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        f = self.frame

        # ── header ────────────────────────────────────────────────────────────
        hdr = tk.Frame(f, bg=PANEL, height=56)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="⚡  Dashboard", bg=PANEL, fg=CYAN,
                 font=FONTS["heading"]).pack(side="left", padx=20, pady=12)
        tk.Label(hdr,
                 text=datetime.now().strftime("%A, %d %B %Y"),
                 bg=PANEL, fg=MUTED,
                 font=FONTS["small"]).pack(side="right", padx=20)

        # ── body ──────────────────────────────────────────────────────────────
        body = tk.Frame(f, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=16)

        # stat cards row
        self._build_stat_row(body)

        # middle section: progress + quick actions
        mid = tk.Frame(body, bg=BG)
        mid.pack(fill="x", pady=(16, 0))
        self._build_progress_section(mid)
        self._build_quick_actions(mid)

        # activity feed
        self._build_activity_feed(body)

    def _build_stat_row(self, parent: tk.Widget) -> None:
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x")

        specs = [
            ("campaigns",   "Active Campaigns", "0",  CYAN),
            ("accounts",    "Accounts Online",  "0",  GREEN),
            ("messages",    "Messages Sent",    "0",  COLORS["accent"]),
            ("success_rate","Success Rate",      "0%", COLORS["success"]),
        ]
        for col, (key, title, val, color) in enumerate(specs):
            card = StatCard(row, title=title, value=val, value_color=color,
                            bg=PANEL)
            card.pack(side="left", fill="x", expand=True,
                      padx=(0 if col == 0 else 8, 0))
            self._stat_cards[key] = card

    def _build_progress_section(self, parent: tk.Widget) -> None:
        pf = tk.Frame(parent, bg=PANEL, padx=16, pady=14)
        pf.pack(side="left", fill="both", expand=True)

        tk.Label(pf, text="Campaign Progress", bg=PANEL, fg=TEXT,
                 font=FONTS["subheading"]).pack(anchor="w")

        for label, pct, color in [
            ("Broadcast Alpha",  72, CYAN),
            ("Broadcast Beta",   45, COLORS["accent"]),
            ("Scrape Campaign",  91, GREEN),
        ]:
            row = tk.Frame(pf, bg=PANEL)
            row.pack(fill="x", pady=4)
            tk.Label(row, text=label, bg=PANEL, fg=MUTED,
                     font=FONTS["small"], width=18, anchor="w").pack(side="left")
            bar = AnimatedProgressBar(row, width=200, height=14, color=color,
                                      bg=PANEL)
            bar.pack(side="left", fill="x", expand=True)
            bar.set(pct)

    def _build_quick_actions(self, parent: tk.Widget) -> None:
        af = tk.Frame(parent, bg=PANEL, padx=16, pady=14)
        af.pack(side="left", fill="both", padx=(12, 0))

        tk.Label(af, text="Quick Actions", bg=PANEL, fg=TEXT,
                 font=FONTS["subheading"]).pack(anchor="w", pady=(0, 10))

        for label, preset, page in [
            ("New Campaign",  "primary",   "campaigns"),
            ("Add Account",   "success",   "accounts"),
            ("View Analytics","secondary", "analytics"),
        ]:
            make_vibrant_btn(
                af, label, preset=preset,
                command=lambda p=page: self._navigate(p),
            ).pack(fill="x", pady=3)

    def _build_activity_feed(self, parent: tk.Widget) -> None:
        ff = tk.Frame(parent, bg=PANEL, padx=12, pady=12)
        ff.pack(fill="both", expand=True, pady=(16, 0))

        tk.Label(ff, text="Recent Activity", bg=PANEL, fg=TEXT,
                 font=FONTS["subheading"]).pack(anchor="w", pady=(0, 8))

        self._activity_list = tk.Listbox(
            ff, bg=CARD, fg=MUTED,
            font=FONTS["small"],
            relief="flat", borderwidth=0,
            selectbackground=PANEL,
            highlightthickness=0,
        )
        scroll = ttk.Scrollbar(ff, orient="vertical",
                                command=self._activity_list.yview)
        self._activity_list.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self._activity_list.pack(fill="both", expand=True)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _refresh_stats(self) -> None:
        """Placeholder – real data would come from the engine."""
        pass

    def _refresh_activity(self) -> None:
        self._activity_list.delete(0, tk.END)
        for item in self._activity_items:
            self._activity_list.insert(tk.END, f"  {item}")

    def _navigate(self, page: str) -> None:
        if self.on_navigate:
            self.on_navigate(page)
