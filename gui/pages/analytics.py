"""
TG PRO QUANTUM – Phase 5B Analytics Page

Frame-overlay page displaying campaign statistics, charts and KPI cards.
Uses StatCard and AnimatedProgressBar for a rich visual layout.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional, Dict, Any

from gui.styles import COLORS, FONTS
from gui.components.animated_cards import StatCard
from gui.components.progress_bars import AnimatedProgressBar
from gui.components.vibrant_buttons import make_vibrant_btn

__all__ = ["AnalyticsPage"]

BG    = COLORS["bg_dark"]
PANEL = COLORS["bg_medium"]
CARD  = COLORS["bg_light"]
CYAN  = COLORS["primary"]
GREEN = COLORS["success"]
TEXT  = COLORS["text"]
MUTED = COLORS["text_muted"]
ORANGE = COLORS.get("accent", COLORS["warning"])
PURPLE = COLORS.get("secondary", "#7B2CBF")


class AnalyticsPage:
    """
    Analytics overlay page.

    Usage::

        page = AnalyticsPage(parent_frame)
        page.show()
        page.update_stats({...})
    """

    def __init__(
        self,
        parent: tk.Widget,
        on_export: Optional[Callable] = None,
    ) -> None:
        self.parent    = parent
        self.on_export = on_export

        self._stat_cards: Dict[str, StatCard] = {}
        self._bars: Dict[str, AnimatedProgressBar] = {}

        self.frame = tk.Frame(parent, bg=BG)
        self._build()

    # ── public API ────────────────────────────────────────────────────────────

    def show(self) -> None:
        self.frame.place(relx=0, rely=0, relwidth=1, relheight=1)

    def hide(self) -> None:
        self.frame.place_forget()

    def update_stats(self, stats: Dict[str, Any]) -> None:
        """
        Update displayed statistics.

        Expected keys (all optional):
            total_sent, delivery_rate, open_rate, reply_rate,
            active_campaigns, total_accounts, messages_today,
            groups_reached
        """
        mapping = {
            "total_sent":        ("total_sent",       lambda v: f"{int(v):,}"),
            "delivery_rate":     ("delivery_rate",    lambda v: f"{v:.1f}%"),
            "open_rate":         ("open_rate",        lambda v: f"{v:.1f}%"),
            "reply_rate":        ("reply_rate",       lambda v: f"{v:.1f}%"),
            "active_campaigns":  ("active_campaigns", str),
            "total_accounts":    ("total_accounts",   str),
            "messages_today":    ("messages_today",   lambda v: f"{int(v):,}"),
            "groups_reached":    ("groups_reached",   str),
        }
        for key, (card_key, fmt) in mapping.items():
            if key in stats and card_key in self._stat_cards:
                self._stat_cards[card_key].set_value(fmt(stats[key]))

        # update progress bars
        bar_map = {
            "delivery_rate": "delivery_rate",
            "open_rate":     "open_rate",
            "reply_rate":    "reply_rate",
        }
        for stat_key, bar_key in bar_map.items():
            if stat_key in stats and bar_key in self._bars:
                self._bars[bar_key].set(stats[stat_key])

    # ── build ─────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        f = self.frame

        # header
        hdr = tk.Frame(f, bg=PANEL, height=56)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="📊  Analytics", bg=PANEL, fg=CYAN,
                 font=FONTS["heading"]).pack(side="left", padx=20, pady=12)
        make_vibrant_btn(hdr, "⬇ Export CSV", preset="ghost",
                         command=self._on_export).pack(side="right", padx=16)

        # scrollable body
        canvas = tk.Canvas(f, bg=BG, highlightthickness=0)
        vsb = ttk.Scrollbar(f, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        body = tk.Frame(canvas, bg=BG)
        body_win = canvas.create_window((0, 0), window=body, anchor="nw")

        def _resize(evt):
            canvas.itemconfig(body_win, width=evt.width)
        def _scroll_region(evt):
            canvas.configure(scrollregion=canvas.bbox("all"))

        canvas.bind("<Configure>", _resize)
        body.bind("<Configure>", _scroll_region)

        self._build_kpi_row(body)
        self._build_rates_section(body)
        self._build_breakdown_table(body)

    def _build_kpi_row(self, parent: tk.Widget) -> None:
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", padx=20, pady=(16, 0))

        specs = [
            ("total_sent",      "Total Messages",     "0",    CYAN),
            ("delivery_rate",   "Delivery Rate",      "0%",   GREEN),
            ("active_campaigns","Active Campaigns",   "0",    ORANGE),
            ("total_accounts",  "Total Accounts",     "0",    PURPLE),
            ("messages_today",  "Messages Today",     "0",    CYAN),
            ("groups_reached",  "Groups Reached",     "0",    GREEN),
        ]
        for col, (key, title, val, color) in enumerate(specs):
            card = StatCard(row, title=title, value=val, value_color=color,
                            bg=PANEL)
            card.pack(side="left", fill="x", expand=True,
                      padx=(0 if col == 0 else 8, 0))
            self._stat_cards[key] = card

    def _build_rates_section(self, parent: tk.Widget) -> None:
        section = tk.Frame(parent, bg=PANEL, padx=20, pady=16)
        section.pack(fill="x", padx=20, pady=(16, 0))

        tk.Label(section, text="Engagement Rates", bg=PANEL, fg=TEXT,
                 font=FONTS["subheading"]).pack(anchor="w", pady=(0, 12))

        for label, key, color in [
            ("Delivery Rate", "delivery_rate", GREEN),
            ("Open Rate",     "open_rate",     CYAN),
            ("Reply Rate",    "reply_rate",    ORANGE),
        ]:
            row = tk.Frame(section, bg=PANEL)
            row.pack(fill="x", pady=5)
            tk.Label(row, text=label, bg=PANEL, fg=TEXT,
                     font=FONTS["small"], width=16, anchor="w").pack(side="left")
            bar = AnimatedProgressBar(row, width=400, height=16, color=color,
                                       show_label=True, bg=PANEL)
            bar.pack(side="left", fill="x", expand=True, padx=(8, 0))
            bar.set(0)
            self._bars[key] = bar

    def _build_breakdown_table(self, parent: tk.Widget) -> None:
        section = tk.Frame(parent, bg=PANEL, padx=20, pady=16)
        section.pack(fill="x", padx=20, pady=(16, 20))

        tk.Label(section, text="Campaign Breakdown", bg=PANEL, fg=TEXT,
                 font=FONTS["subheading"]).pack(anchor="w", pady=(0, 8))

        cols = ("campaign", "sent", "delivered", "delivery_rate",
                "replies", "errors")
        tree = ttk.Treeview(section, columns=cols, show="headings", height=6)
        for col, heading, width in [
            ("campaign",      "Campaign",      200),
            ("sent",          "Sent",           80),
            ("delivered",     "Delivered",      90),
            ("delivery_rate", "Rate",           70),
            ("replies",       "Replies",        80),
            ("errors",        "Errors",         70),
        ]:
            tree.heading(col, text=heading)
            tree.column(col, width=width, minwidth=50)

        tree.pack(fill="x")
        self._breakdown_tree = tree

    # ── handlers ──────────────────────────────────────────────────────────────

    def _on_export(self) -> None:
        if self.on_export:
            self.on_export()
