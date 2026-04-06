"""
gui/analytics_tab.py - Stats dashboard and broadcast history
"""
import tkinter as tk
from tkinter import ttk

from gui.styles import COLORS, FONTS, make_btn
from core.analytics import account_summary, broadcast_summary, recent_broadcasts, weekly_stats

BG    = COLORS["bg_dark"]
PANEL = COLORS["bg_medium"]
CARD  = COLORS["bg_light"]
CYAN  = COLORS["primary"]
GREEN = COLORS["success"]
RED   = COLORS["error"]
TEXT  = COLORS["text"]
MUTED = COLORS["text_muted"]
ORANGE = COLORS["warning"]


class AnalyticsTab:
    title = "📊 Analytics"

    def __init__(self, parent, main_window=None):
        self.parent = parent
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        self._build()
        self._refresh()

    # ─────────────────────────────────────────────────────────────────────────
    def _build(self):
        outer = tk.Frame(self.frame, bg=BG)
        outer.pack(fill="both", expand=True, padx=20, pady=20)

        # Header
        hdr = tk.Frame(outer, bg=BG)
        hdr.pack(fill="x", pady=(0, 12))
        tk.Label(hdr, text="📊 Analytics",
                 font=FONTS["heading_large"], fg=CYAN, bg=BG).pack(side="left")
        make_btn(hdr, "🔄 Refresh", command=self._refresh,
                 color=CYAN, fg="#000").pack(side="right")

        # ── Stats cards row ────────────────────────────────────────────────────
        cards_row = tk.Frame(outer, bg=BG)
        cards_row.pack(fill="x", pady=(0, 16))

        self._stat_vars: dict[str, tk.StringVar] = {}

        stats_defs = [
            ("👤 Total Accounts", "accounts_total", CYAN),
            ("✅ Active",          "accounts_active", GREEN),
            ("📢 Broadcasts",      "broadcasts_total", ORANGE),
            ("✉️ Messages Sent",   "total_sent",       GREEN),
            ("❌ Failed",          "total_failed",     RED),
            ("📈 Success Rate",    "success_rate",     CYAN),
        ]

        for label, key, color in stats_defs:
            var = tk.StringVar(value="—")
            self._stat_vars[key] = var
            self._make_stat_card(cards_row, label, var, color)

        # ── Weekly chart (simple bar using labels) ─────────────────────────────
        chart_frame = tk.LabelFrame(outer, text=" 📈 Last 7 Days — Messages Sent ",
                                    bg=PANEL, fg=CYAN, font=FONTS["subheading"])
        chart_frame.pack(fill="x", pady=(0, 12))
        self._chart_inner = tk.Frame(chart_frame, bg=PANEL, height=80)
        self._chart_inner.pack(fill="x", padx=12, pady=12)

        # ── Recent broadcasts table ────────────────────────────────────────────
        hist_frame = tk.LabelFrame(outer, text=" 📋 Recent Broadcasts ",
                                   bg=PANEL, fg=CYAN, font=FONTS["subheading"])
        hist_frame.pack(fill="both", expand=True)

        cols = ("Name", "Sent", "Failed", "Total", "Rate %", "Duration (s)", "Date")
        self._tree = ttk.Treeview(hist_frame, columns=cols, show="headings", height=12)
        widths = {
            "Name": 200, "Sent": 70, "Failed": 70, "Total": 70,
            "Rate %": 70, "Duration (s)": 100, "Date": 150,
        }
        for c in cols:
            self._tree.heading(c, text=c)
            self._tree.column(c, width=widths[c], anchor="center")

        sb = ttk.Scrollbar(hist_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        inner = tk.Frame(hist_frame, bg=PANEL)
        inner.pack(fill="both", expand=True, padx=8, pady=8)
        self._tree.pack(side="left", fill="both", expand=True, in_=inner)
        sb.pack(side="right", fill="y", in_=inner)

    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _make_stat_card(parent, label: str, var: tk.StringVar, color: str):
        card = tk.Frame(parent, bg=PANEL, padx=14, pady=10)
        card.pack(side="left", padx=6, fill="y")
        tk.Label(card, text=label, font=FONTS["small"], fg=MUTED, bg=PANEL).pack()
        tk.Label(card, textvariable=var, font=FONTS["heading"], fg=color, bg=PANEL).pack()

    # ─────────────────────────────────────────────────────────────────────────
    def _refresh(self):
        # Account stats
        acct = account_summary()
        self._stat_vars["accounts_total"].set(str(acct["total"]))
        self._stat_vars["accounts_active"].set(str(acct["active"]))

        # Broadcast stats
        bcast = broadcast_summary()
        self._stat_vars["broadcasts_total"].set(str(bcast["total_broadcasts"]))
        self._stat_vars["total_sent"].set(str(bcast["total_sent"]))
        self._stat_vars["total_failed"].set(str(bcast["total_failed"]))
        self._stat_vars["success_rate"].set(f"{bcast['success_rate']}%")

        # Weekly chart
        self._update_chart()

        # Recent broadcasts
        self._update_history()

    def _update_chart(self):
        for w in self._chart_inner.winfo_children():
            w.destroy()

        weekly = weekly_stats()
        if not weekly:
            tk.Label(self._chart_inner, text="No data yet.",
                     font=FONTS["normal"], fg=MUTED, bg=PANEL).pack()
            return

        max_sent = max((d["sent"] for d in weekly), default=1) or 1

        for day_data in weekly:
            col = tk.Frame(self._chart_inner, bg=PANEL)
            col.pack(side="left", padx=6, fill="y", anchor="s")

            sent = day_data["sent"]
            bar_h = max(4, int((sent / max_sent) * 60))
            bar = tk.Frame(col, bg=GREEN, width=32, height=bar_h)
            bar.pack(side="top")
            bar.pack_propagate(False)

            tk.Label(col, text=str(sent), font=FONTS["small"],
                     fg=GREEN, bg=PANEL).pack()
            date_str = day_data["date"][-5:] if day_data["date"] else ""
            tk.Label(col, text=date_str, font=FONTS["small"],
                     fg=MUTED, bg=PANEL).pack()

    def _update_history(self):
        for row in self._tree.get_children():
            self._tree.delete(row)
        for b in recent_broadcasts(50):
            total = b["total"] or 0
            sent  = b["sent"]  or 0
            rate  = f"{round(sent/total*100, 1)}%" if total else "—"
            self._tree.insert("", "end", values=(
                b["name"],
                sent,
                b["failed"] or 0,
                total,
                rate,
                b.get("duration") or "—",
                (b.get("created_at") or "")[:16],
            ))
