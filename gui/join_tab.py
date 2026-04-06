"""
gui/join_tab.py - Multi-account join automation GUI
"""
import tkinter as tk
from tkinter import ttk, messagebox

from gui.styles import COLORS, FONTS, make_btn
from core.account import list_accounts
from core.finder import list_found_groups
from core.join_manager import join_manager, JoinProgress

BG    = COLORS["bg_dark"]
PANEL = COLORS["bg_medium"]
CARD  = COLORS["bg_light"]
CYAN  = COLORS["primary"]
GREEN = COLORS["success"]
RED   = COLORS["error"]
TEXT  = COLORS["text"]
MUTED = COLORS["text_muted"]


class JoinTab:
    title = "🔗 Join"

    def __init__(self, parent, main_window=None):
        self.parent = parent
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        self._build()

    # ──────────────────────────────────────────────────────────────────────────
    def _build(self):
        outer = tk.Frame(self.frame, bg=BG)
        outer.pack(fill="both", expand=True, padx=16, pady=12)

        tk.Label(outer, text="🔗 Join Automation",
                 font=FONTS["heading"], fg=CYAN, bg=BG).pack(anchor="w", pady=(0, 8))

        main_row = tk.Frame(outer, bg=BG)
        main_row.pack(fill="both", expand=True)

        self._build_left(main_row)
        self._build_right(main_row)

    # ──────────────────────────────────────────────────────────────────────────
    def _build_left(self, parent):
        left = tk.Frame(parent, bg=BG)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        # Account multi-select
        acc_frame = tk.LabelFrame(left, text=" 👤 Accounts ",
                                  bg=PANEL, fg=CYAN, font=FONTS["subheading"])
        acc_frame.pack(fill="both", expand=True, pady=(0, 8))

        btn_row = tk.Frame(acc_frame, bg=PANEL)
        btn_row.pack(fill="x", padx=8, pady=(8, 4))
        make_btn(btn_row, "Select All", command=self._select_all_accounts, color=CARD).pack(side="left", padx=2)
        make_btn(btn_row, "Refresh", command=self._reload_accounts, color=CARD).pack(side="left", padx=2)

        sb_acc = tk.Scrollbar(acc_frame)
        sb_acc.pack(side="right", fill="y")
        self._acc_listbox = tk.Listbox(
            acc_frame,
            selectmode="extended",
            yscrollcommand=sb_acc.set,
            font=FONTS["normal"],
            bg=CARD,
            fg=TEXT,
            selectbackground=COLORS["primary_light"],
            selectforeground=CYAN,
            relief="flat",
            height=8,
        )
        self._acc_listbox.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        sb_acc.config(command=self._acc_listbox.yview)

        # Group source
        grp_src_frame = tk.LabelFrame(left, text=" 🌐 Group Source ",
                                      bg=PANEL, fg=CYAN, font=FONTS["subheading"])
        grp_src_frame.pack(fill="x", pady=(0, 8))

        self._grp_source_var = tk.StringVar(value="finder")
        tk.Radiobutton(grp_src_frame, text="From Finder Results",
                       variable=self._grp_source_var, value="finder",
                       command=self._reload_groups,
                       bg=PANEL, fg=TEXT, selectcolor=CARD, activebackground=PANEL,
                       font=FONTS["normal"]).pack(anchor="w", padx=12, pady=4)
        tk.Radiobutton(grp_src_frame, text="Manual input",
                       variable=self._grp_source_var, value="manual",
                       command=self._reload_groups,
                       bg=PANEL, fg=TEXT, selectcolor=CARD, activebackground=PANEL,
                       font=FONTS["normal"]).pack(anchor="w", padx=12)

        self._manual_groups_text = tk.Text(
            grp_src_frame,
            height=4,
            font=FONTS["mono"],
            bg=CARD,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
        )
        self._manual_groups_text.pack(fill="x", padx=8, pady=(4, 8))
        tk.Label(grp_src_frame, text="One group link per line (for manual mode)",
                 font=FONTS["small"], fg=MUTED, bg=PANEL).pack(anchor="w", padx=12, pady=(0, 8))

        # Group multiselect (for finder mode)
        grp_sel_frame = tk.LabelFrame(left, text=" 📋 Select Groups (Finder Results) ",
                                      bg=PANEL, fg=CYAN, font=FONTS["subheading"])
        grp_sel_frame.pack(fill="both", expand=True, pady=(0, 8))

        btn_row2 = tk.Frame(grp_sel_frame, bg=PANEL)
        btn_row2.pack(fill="x", padx=8, pady=(8, 4))
        make_btn(btn_row2, "Select All", command=self._select_all_groups, color=CARD).pack(side="left", padx=2)
        make_btn(btn_row2, "Refresh", command=self._reload_groups, color=CARD).pack(side="left", padx=2)

        sb_grp = tk.Scrollbar(grp_sel_frame)
        sb_grp.pack(side="right", fill="y")
        self._grp_listbox = tk.Listbox(
            grp_sel_frame,
            selectmode="extended",
            yscrollcommand=sb_grp.set,
            font=FONTS["normal"],
            bg=CARD,
            fg=TEXT,
            selectbackground=COLORS["primary_light"],
            selectforeground=CYAN,
            relief="flat",
            height=8,
        )
        self._grp_listbox.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        sb_grp.config(command=self._grp_listbox.yview)

        # Delay
        delay_frame = tk.Frame(left, bg=PANEL)
        delay_frame.pack(fill="x", pady=(0, 8))
        tk.Label(delay_frame, text="Delay between joins (s):",
                 font=FONTS["normal"], fg=TEXT, bg=PANEL).pack(side="left", padx=8)
        self._delay_var = tk.DoubleVar(value=3.0)
        tk.Spinbox(
            delay_frame,
            from_=1.0,
            to=60.0,
            increment=0.5,
            textvariable=self._delay_var,
            font=FONTS["normal"],
            bg=CARD,
            fg=TEXT,
            width=8,
        ).pack(side="left")

        # Buttons
        btn_row3 = tk.Frame(left, bg=BG)
        btn_row3.pack(fill="x", pady=4)
        self._start_btn = make_btn(btn_row3, "▶ Start", command=self._start, color=GREEN, fg="#000")
        self._start_btn.pack(side="left", padx=(0, 8))
        self._stop_btn = make_btn(btn_row3, "⏹ Stop", command=self._stop, color=RED)
        self._stop_btn.pack(side="left")
        self._stop_btn.config(state="disabled")

        self._reload_accounts()
        self._reload_groups()

    # ──────────────────────────────────────────────────────────────────────────
    def _build_right(self, parent):
        right = tk.Frame(parent, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        # Stats
        stats_frame = tk.LabelFrame(right, text=" 📊 Progress ",
                                    bg=PANEL, fg=CYAN, font=FONTS["subheading"])
        stats_frame.pack(fill="x", pady=(0, 8))

        stats_inner = tk.Frame(stats_frame, bg=PANEL)
        stats_inner.pack(fill="x", padx=16, pady=8)

        self._stat_joined_var = tk.StringVar(value="0")
        self._stat_failed_var = tk.StringVar(value="0")
        self._stat_skipped_var = tk.StringVar(value="0")

        for label, var, color in [
            ("✅ Joined", self._stat_joined_var, GREEN),
            ("❌ Failed", self._stat_failed_var, RED),
            ("ℹ Already In", self._stat_skipped_var, MUTED),
        ]:
            col = tk.Frame(stats_inner, bg=PANEL)
            col.pack(side="left", expand=True)
            tk.Label(col, text=label, font=FONTS["small"], fg=MUTED, bg=PANEL).pack()
            tk.Label(col, textvariable=var, font=FONTS["heading"], fg=color, bg=PANEL).pack()

        # Log
        log_frame = tk.LabelFrame(right, text=" 📜 Activity Log ",
                                  bg=PANEL, fg=CYAN, font=FONTS["subheading"])
        log_frame.pack(fill="both", expand=True)

        sb_log = tk.Scrollbar(log_frame)
        sb_log.pack(side="right", fill="y")
        self._log_box = tk.Listbox(
            log_frame,
            yscrollcommand=sb_log.set,
            font=FONTS["mono"],
            bg=CARD,
            fg=TEXT,
            selectbackground=COLORS["primary_light"],
            relief="flat",
        )
        self._log_box.pack(fill="both", expand=True, padx=8, pady=8)
        sb_log.config(command=self._log_box.yview)

    # ──────────────────────────────────────────────────────────────────────────
    def _reload_accounts(self):
        self._acc_listbox.delete(0, "end")
        self._accounts_data = list_accounts()
        for a in self._accounts_data:
            status = "✅" if a.get("status") == "active" else "⚠️"
            self._acc_listbox.insert("end", f"{status} {a['name']} ({a['phone']})")

    def _select_all_accounts(self):
        self._acc_listbox.select_set(0, "end")

    def _reload_groups(self):
        self._grp_listbox.delete(0, "end")
        self._groups_data = list_found_groups(only_unjoined=True)
        for g in self._groups_data:
            title = g.get("group_title") or g.get("group_link", "")
            self._grp_listbox.insert("end", f"{title[:40]} — {g.get('group_link', '')}")

    def _select_all_groups(self):
        self._grp_listbox.select_set(0, "end")

    def _get_selected_accounts(self) -> list[str]:
        selected = self._acc_listbox.curselection()
        phones = []
        for i in selected:
            acc = self._accounts_data[i]
            if acc.get("status") == "active":
                phones.append(acc["phone"])
        return phones

    def _get_selected_groups(self) -> list[dict]:
        if self._grp_source_var.get() == "manual":
            text = self._manual_groups_text.get("1.0", "end").strip()
            groups = []
            for line in text.splitlines():
                line = line.strip()
                if line:
                    groups.append({"group_link": line, "title": line})
            return groups

        selected = self._grp_listbox.curselection()
        return [
            {
                "group_link": self._groups_data[i].get("group_link", ""),
                "title": self._groups_data[i].get("group_title", ""),
            }
            for i in selected
        ]

    def _start(self):
        accounts = self._get_selected_accounts()
        groups = self._get_selected_groups()

        if not accounts:
            messagebox.showwarning("Join", "Select at least one active account.")
            return
        if not groups:
            messagebox.showwarning("Join", "Select at least one group.")
            return

        self._start_btn.config(state="disabled")
        self._stop_btn.config(state="normal")
        self._log_box.delete(0, "end")

        join_manager.start(
            accounts=accounts,
            groups=groups,
            delay_between_joins=self._delay_var.get(),
            on_update=self._on_update,
            on_done=self._on_done,
        )

    def _stop(self):
        join_manager.stop()
        self._stop_btn.config(state="disabled")

    def _on_update(self, progress: JoinProgress):
        def _update():
            self._stat_joined_var.set(str(progress.joined))
            self._stat_failed_var.set(str(progress.failed))
            self._stat_skipped_var.set(str(progress.skipped))
            self._log_box.delete(0, "end")
            for entry in progress.log:
                self._log_box.insert("end", entry)

        self.frame.after(0, _update)

    def _on_done(self, progress: JoinProgress):
        def _done():
            self._start_btn.config(state="normal")
            self._stop_btn.config(state="disabled")
            if progress:
                self._stat_joined_var.set(str(progress.joined))
                self._stat_failed_var.set(str(progress.failed))
                self._stat_skipped_var.set(str(progress.skipped))
            self._reload_groups()

        self.frame.after(0, _done)
