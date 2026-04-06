"""
gui/broadcast_tab.py - Advanced round-robin broadcast with 24/7 operation
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading

from gui.styles import COLORS, FONTS, make_btn
from core.account import list_accounts
from core.finder import list_groups, list_found_groups
from core.config import list_account_groups
from core.broadcaster import advanced_broadcaster, BroadcastStats

BG    = COLORS["bg_dark"]
PANEL = COLORS["bg_medium"]
CARD  = COLORS["bg_light"]
CYAN  = COLORS["primary"]
GREEN = COLORS["success"]
RED   = COLORS["error"]
TEXT  = COLORS["text"]
MUTED = COLORS["text_muted"]
GOLD  = COLORS["accent"]


class BroadcastTab:
    title = "📢 Broadcast"

    def __init__(self, parent, main_window=None):
        self.parent = parent
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        self._accounts_data: list = []
        self._groups_data: list = []
        self._build()
        self._reload_accounts()
        self._reload_groups()

    # ─────────────────────────────────────────────────────────────────────────
    def _build(self):
        outer = tk.Frame(self.frame, bg=BG)
        outer.pack(fill="both", expand=True, padx=16, pady=12)

        tk.Label(outer, text="📢 Advanced Broadcast",
                 font=FONTS["heading"], fg=CYAN, bg=BG).pack(anchor="w", pady=(0, 8))

        cols = tk.Frame(outer, bg=BG)
        cols.pack(fill="both", expand=True)

        left = tk.Frame(cols, bg=BG)
        right = tk.Frame(cols, bg=BG)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))
        right.pack(side="left", fill="both", expand=True)

        self._build_left(left)
        self._build_right(right)

    # ─────────────────────────────────────────────────────────────────────────
    def _build_left(self, parent):
        # Message
        msg_frame = tk.LabelFrame(parent, text=" ✏ Message ",
                                  bg=PANEL, fg=CYAN, font=FONTS["subheading"])
        msg_frame.pack(fill="x", pady=(0, 8))
        self._msg_text = scrolledtext.ScrolledText(
            msg_frame, height=7, wrap="word",
            bg=CARD, fg=TEXT, insertbackground=TEXT,
            font=FONTS["normal"], relief="flat",
        )
        self._msg_text.pack(fill="x", padx=10, pady=10)

        # Account selection
        acc_frame = tk.LabelFrame(parent, text=" 👤 Accounts (multi-select) ",
                                  bg=PANEL, fg=CYAN, font=FONTS["subheading"])
        acc_frame.pack(fill="both", expand=True, pady=(0, 8))

        acc_btn_row = tk.Frame(acc_frame, bg=PANEL)
        acc_btn_row.pack(fill="x", padx=8, pady=(6, 2))
        make_btn(acc_btn_row, "Select All", command=self._select_all_accounts, color=CARD).pack(side="left", padx=2)
        make_btn(acc_btn_row, "🔄 Refresh", command=self._reload_accounts, color=CARD).pack(side="left", padx=2)

        sb_acc = tk.Scrollbar(acc_frame)
        sb_acc.pack(side="right", fill="y")
        self._acc_listbox = tk.Listbox(
            acc_frame,
            selectmode="extended",
            yscrollcommand=sb_acc.set,
            font=FONTS["normal"],
            bg=CARD, fg=TEXT,
            selectbackground=COLORS["primary_light"],
            selectforeground=CYAN,
            relief="flat",
            height=6,
        )
        self._acc_listbox.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        sb_acc.config(command=self._acc_listbox.yview)

        # Group source
        src_frame = tk.LabelFrame(parent, text=" 🌐 Group Source ",
                                  bg=PANEL, fg=CYAN, font=FONTS["subheading"])
        src_frame.pack(fill="x", pady=(0, 8))

        self._group_source_var = tk.StringVar(value="account_groups")
        tk.Radiobutton(src_frame, text="From Account Groups",
                       variable=self._group_source_var, value="account_groups",
                       command=self._reload_groups,
                       bg=PANEL, fg=TEXT, selectcolor=CARD, activebackground=PANEL,
                       font=FONTS["normal"]).pack(anchor="w", padx=12, pady=4)
        tk.Radiobutton(src_frame, text="From Finder Results",
                       variable=self._group_source_var, value="finder_results",
                       command=self._reload_groups,
                       bg=PANEL, fg=TEXT, selectcolor=CARD, activebackground=PANEL,
                       font=FONTS["normal"]).pack(anchor="w", padx=12, pady=(0, 8))

        # Groups list
        grp_frame = tk.LabelFrame(parent, text=" 📋 Groups ",
                                  bg=PANEL, fg=CYAN, font=FONTS["subheading"])
        grp_frame.pack(fill="both", expand=True, pady=(0, 8))

        grp_btn_row = tk.Frame(grp_frame, bg=PANEL)
        grp_btn_row.pack(fill="x", padx=8, pady=(6, 2))
        make_btn(grp_btn_row, "Select All", command=self._select_all_groups, color=CARD).pack(side="left", padx=2)
        make_btn(grp_btn_row, "🔄 Refresh", command=self._reload_groups, color=CARD).pack(side="left", padx=2)

        sb_grp = tk.Scrollbar(grp_frame)
        sb_grp.pack(side="right", fill="y")
        self._grp_listbox = tk.Listbox(
            grp_frame,
            selectmode="extended",
            yscrollcommand=sb_grp.set,
            font=FONTS["normal"],
            bg=CARD, fg=TEXT,
            selectbackground=COLORS["primary_light"],
            selectforeground=CYAN,
            relief="flat",
            height=6,
        )
        self._grp_listbox.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        sb_grp.config(command=self._grp_listbox.yview)

        # Control buttons
        btn_row = tk.Frame(parent, bg=BG)
        btn_row.pack(fill="x", pady=4)
        self._start_btn = make_btn(btn_row, "▶ Start", command=self._start, color=GREEN, fg="#000")
        self._start_btn.pack(side="left", padx=(0, 6))
        self._pause_btn = make_btn(btn_row, "⏸ Pause", command=self._pause, color=GOLD, fg="#000")
        self._pause_btn.pack(side="left", padx=(0, 6))
        self._pause_btn.config(state="disabled")
        self._resume_btn = make_btn(btn_row, "▶▶ Resume", command=self._resume, color=CYAN, fg="#000")
        self._resume_btn.pack(side="left", padx=(0, 6))
        self._resume_btn.config(state="disabled")
        self._stop_btn = make_btn(btn_row, "⏹ Stop", command=self._stop, color=RED)
        self._stop_btn.pack(side="left")
        self._stop_btn.config(state="disabled")

    # ─────────────────────────────────────────────────────────────────────────
    def _build_right(self, parent):
        # Stats
        stats_frame = tk.LabelFrame(parent, text=" 📊 Statistics ",
                                    bg=PANEL, fg=CYAN, font=FONTS["subheading"])
        stats_frame.pack(fill="x", pady=(0, 8))

        stats_inner = tk.Frame(stats_frame, bg=PANEL)
        stats_inner.pack(fill="x", padx=16, pady=8)

        self._stat_vars = {}
        stat_defs = [
            ("✅ Sent", "sent", GREEN),
            ("❌ Failed", "failed", RED),
            ("🚫 Banned", "banned", COLORS["error"]),
            ("⏳ Pending", "pending", MUTED),
            ("🔄 Rounds", "rounds", CYAN),
        ]
        for label, key, color in stat_defs:
            col = tk.Frame(stats_inner, bg=PANEL)
            col.pack(side="left", expand=True)
            tk.Label(col, text=label, font=FONTS["small"], fg=MUTED, bg=PANEL).pack()
            var = tk.StringVar(value="0")
            self._stat_vars[key] = var
            tk.Label(col, textvariable=var, font=FONTS["heading"], fg=color, bg=PANEL).pack()

        # Log
        log_frame = tk.LabelFrame(parent, text=" 📜 Activity Log (newest first) ",
                                  bg=PANEL, fg=CYAN, font=FONTS["subheading"])
        log_frame.pack(fill="both", expand=True)

        sb_log = tk.Scrollbar(log_frame)
        sb_log.pack(side="right", fill="y")
        self._log_box = tk.Listbox(
            log_frame,
            yscrollcommand=sb_log.set,
            font=FONTS["mono"],
            bg=CARD, fg=TEXT,
            selectbackground=COLORS["primary_light"],
            relief="flat",
        )
        self._log_box.pack(fill="both", expand=True, padx=8, pady=8)
        sb_log.config(command=self._log_box.yview)

    # ─────────────────────────────────────────────────────────────────────────
    def _reload_accounts(self):
        self._acc_listbox.delete(0, "end")
        self._accounts_data = [a for a in list_accounts() if a.get("status") == "active"]
        for a in self._accounts_data:
            self._acc_listbox.insert("end", f"{a['name']} ({a['phone']})")

    def _select_all_accounts(self):
        self._acc_listbox.select_set(0, "end")

    def _reload_groups(self):
        self._grp_listbox.delete(0, "end")
        source = self._group_source_var.get()

        if source == "account_groups":
            groups = []
            seen = set()
            for acct in self._accounts_data:
                for ag in list_account_groups(acct["phone"]):
                    link = ag.get("group_link", "")
                    if link and link not in seen:
                        groups.append(link)
                        seen.add(link)
            self._groups_data = groups
        else:
            groups = [g.get("group_link", "") for g in list_found_groups()]
            self._groups_data = [g for g in groups if g]

        for link in self._groups_data:
            self._grp_listbox.insert("end", link)

    def _select_all_groups(self):
        self._grp_listbox.select_set(0, "end")

    def _get_selected_accounts(self) -> list[str]:
        return [
            self._accounts_data[i]["phone"]
            for i in self._acc_listbox.curselection()
        ]

    def _get_selected_groups(self) -> list[str]:
        return [
            self._groups_data[i]
            for i in self._grp_listbox.curselection()
        ]

    def _start(self):
        message = self._msg_text.get("1.0", "end").strip()
        if not message:
            messagebox.showwarning("Broadcast", "Enter a message first.")
            return
        accounts = self._get_selected_accounts()
        groups = self._get_selected_groups()
        if not accounts:
            messagebox.showwarning("Broadcast", "Select at least one account.")
            return
        if not groups:
            messagebox.showwarning("Broadcast", "Select at least one group.")
            return

        self._start_btn.config(state="disabled")
        self._pause_btn.config(state="normal")
        self._stop_btn.config(state="normal")
        self._log_box.delete(0, "end")
        for key in self._stat_vars:
            self._stat_vars[key].set("0")

        advanced_broadcaster.start(
            message=message,
            accounts=accounts,
            groups=groups,
            on_update=self._on_update,
            on_done=self._on_done,
        )

    def _pause(self):
        advanced_broadcaster.pause()
        self._pause_btn.config(state="disabled")
        self._resume_btn.config(state="normal")

    def _resume(self):
        advanced_broadcaster.resume()
        self._pause_btn.config(state="normal")
        self._resume_btn.config(state="disabled")

    def _stop(self):
        advanced_broadcaster.stop()
        self._stop_btn.config(state="disabled")
        self._pause_btn.config(state="disabled")
        self._resume_btn.config(state="disabled")

    def _on_update(self, stats: BroadcastStats):
        def _update():
            self._stat_vars["sent"].set(str(stats.sent))
            self._stat_vars["failed"].set(str(stats.failed))
            self._stat_vars["banned"].set(str(stats.banned))
            self._stat_vars["pending"].set(str(stats.pending))
            self._stat_vars["rounds"].set(str(stats.rounds))
            self._log_box.delete(0, "end")
            for entry in stats.log:
                self._log_box.insert("end", entry)

        self.frame.after(0, _update)

    def _on_done(self, stats: BroadcastStats):
        def _done():
            self._start_btn.config(state="normal")
            self._pause_btn.config(state="disabled")
            self._resume_btn.config(state="disabled")
            self._stop_btn.config(state="disabled")
            if stats:
                self._stat_vars["sent"].set(str(stats.sent))
                self._stat_vars["failed"].set(str(stats.failed))
                self._stat_vars["banned"].set(str(stats.banned))
                self._stat_vars["rounds"].set(str(stats.rounds))

        self.frame.after(0, _done)
