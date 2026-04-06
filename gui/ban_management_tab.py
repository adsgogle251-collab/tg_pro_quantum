"""
gui/ban_management_tab.py - Ban log review and management
"""
import tkinter as tk
from tkinter import ttk, messagebox

from gui.styles import COLORS, FONTS, make_btn
from core.ban_detector import get_ban_summary, SUGGESTIONS
from core.config import list_ban_logs, clear_ban_logs

BG    = COLORS["bg_dark"]
PANEL = COLORS["bg_medium"]
CARD  = COLORS["bg_light"]
CYAN  = COLORS["primary"]
GREEN = COLORS["success"]
RED   = COLORS["error"]
TEXT  = COLORS["text"]
MUTED = COLORS["text_muted"]
GOLD  = COLORS["accent"]


class BanManagementTab:
    title = "🚫 Bans"

    def __init__(self, parent, main_window=None):
        self.parent = parent
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        self._build()
        self._refresh()

    # ──────────────────────────────────────────────────────────────────────────
    def _build(self):
        outer = tk.Frame(self.frame, bg=BG)
        outer.pack(fill="both", expand=True, padx=16, pady=12)

        tk.Label(outer, text="🚫 Ban Management",
                 font=FONTS["heading"], fg=RED, bg=BG).pack(anchor="w", pady=(0, 8))

        # Summary bar
        self._summary_frame = tk.LabelFrame(outer, text=" 📊 Summary ",
                                            bg=PANEL, fg=CYAN, font=FONTS["subheading"])
        self._summary_frame.pack(fill="x", pady=(0, 8))

        stats_inner = tk.Frame(self._summary_frame, bg=PANEL)
        stats_inner.pack(fill="x", padx=16, pady=8)

        self._total_var   = tk.StringVar(value="0")
        self._leave_var   = tk.StringVar(value="0")
        self._wait_var    = tk.StringVar(value="0")

        for label, var, color in [
            ("📋 Total Bans", self._total_var, MUTED),
            ("🚪 Suggest Leave", self._leave_var, RED),
            ("⏳ Suggest Wait", self._wait_var, GOLD),
        ]:
            col = tk.Frame(stats_inner, bg=PANEL)
            col.pack(side="left", expand=True)
            tk.Label(col, text=label, font=FONTS["small"], fg=MUTED, bg=PANEL).pack()
            tk.Label(col, textvariable=var, font=FONTS["heading"], fg=color, bg=PANEL).pack()

        # Toolbar
        toolbar = tk.Frame(outer, bg=BG)
        toolbar.pack(fill="x", pady=(0, 6))
        make_btn(toolbar, "🔄 Refresh", command=self._refresh, color=CARD).pack(side="left", padx=(0, 6))
        make_btn(toolbar, "🗑 Clear All Logs", command=self._clear_logs, color=RED).pack(side="left")

        # Treeview
        tree_frame = tk.LabelFrame(outer, text=" 📋 Ban Logs ",
                                   bg=PANEL, fg=CYAN, font=FONTS["subheading"])
        tree_frame.pack(fill="both", expand=True)

        cols = ("Account", "Group", "Reason", "Suggestion", "Detected At")
        self._tree = ttk.Treeview(tree_frame, columns=cols, show="headings")
        widths = {"Account": 160, "Group": 240, "Reason": 180, "Suggestion": 100, "Detected At": 140}
        for c in cols:
            self._tree.heading(c, text=c)
            self._tree.column(c, width=widths[c], anchor="center")

        self._tree.tag_configure("leave", foreground=RED)
        self._tree.tag_configure("wait", foreground=GOLD)
        self._tree.tag_configure("ignore", foreground=MUTED)

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        inner = tk.Frame(tree_frame, bg=PANEL)
        inner.pack(fill="both", expand=True, padx=8, pady=8)
        self._tree.pack(side="left", fill="both", expand=True, in_=inner)
        sb.pack(side="right", fill="y", in_=inner)

    # ──────────────────────────────────────────────────────────────────────────
    def _refresh(self):
        for row in self._tree.get_children():
            self._tree.delete(row)

        logs = list_ban_logs()
        summary = get_ban_summary()

        self._total_var.set(str(summary["total"]))
        self._leave_var.set(str(summary["suggest_leave"]))
        self._wait_var.set(str(summary["suggest_wait"]))

        for log in logs:
            reason = log.get("reason", "")
            suggestion = SUGGESTIONS.get(reason, "ignore")
            detected = (log.get("detected_at") or "")[:16]
            tag = suggestion  # "leave", "wait", or "ignore"
            self._tree.insert("", "end", values=(
                log.get("account_phone", ""),
                log.get("group_link", ""),
                reason,
                suggestion.capitalize(),
                detected,
            ), tags=(tag,))

    def _clear_logs(self):
        if not messagebox.askyesno("Clear Logs", "Delete all ban log entries? This cannot be undone."):
            return
        clear_ban_logs()
        self._refresh()
        messagebox.showinfo("Cleared", "All ban logs cleared.")
