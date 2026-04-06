"""
gui/tabs/join_tab.py - Smart Join Engine UI
Complete professional dashboard with:
  - Account health display & rotation
  - Adaptive delay control
  - Real-time progress + ETA
  - Activity log (newest first, color-coded)
  - Pause / Resume / Stop / Retry controls
  - Persistent queue resume prompt
  - Settings panel (speed, ban handling, etc.)
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import threading
from pathlib import Path

from core import log, account_manager
from core.utils import DATA_DIR
from core.account_router import Feature
from core.state_manager import state_manager
from core.localization import t
from core.finder import list_found_groups
from core.join_engine import join_engine, JoinStats
from core.account_health import check_accounts_health, get_health, health_label
from core.persistent_queue import persistent_queue
from gui.styles import COLORS, FONTS

BG    = COLORS["bg_dark"]
PANEL = COLORS["bg_medium"]
CARD  = COLORS["bg_light"]
CYAN  = COLORS["primary"]
GREEN = COLORS["success"]
GOLD  = COLORS["warning"]
RED   = COLORS["error"]
TEXT  = COLORS["text"]
MUTED = COLORS["text_muted"]
PURPLE = COLORS.get("scrape", "#9B59FF")

LOG_COLORS = {
    "success": GREEN,
    "error":   RED,
    "ban":     GOLD,
    "warning": GOLD,
    "pause":   PURPLE,
    "info":    TEXT,
}


class JoinTab:
    title = "📤 Join"

    def __init__(self, parent, main_window=None):
        self.parent = parent
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        self._update_job = None  # after() job id for polling stats
        self._build()
        state_manager.on_state_change("account_assigned", self._on_account_changed)
        state_manager.on_state_change("refresh_all", self._on_account_changed)

    # ──────────────────────────────────────────────────────────────────────────
    # BUILD
    # ──────────────────────────────────────────────────────────────────────────

    def _build(self):
        outer = tk.Frame(self.frame, bg=BG)
        outer.pack(fill="both", expand=True, padx=14, pady=10)

        # Title row
        title_row = tk.Frame(outer, bg=BG)
        title_row.pack(fill="x", pady=(0, 8))
        tk.Label(title_row, text="🔗 Smart Join Engine",
                 font=FONTS["heading_large"], fg=CYAN, bg=BG).pack(side="left")
        self._health_check_btn = tk.Button(
            title_row, text="🩺 Check Health", command=self._run_health_check,
            bg=CARD, fg=CYAN, font=FONTS["bold"], relief="flat", padx=10, pady=4,
        )
        self._health_check_btn.pack(side="right", padx=4)
        tk.Button(
            title_row, text="⚙ Settings", command=self._toggle_settings,
            bg=CARD, fg=TEXT, font=FONTS["bold"], relief="flat", padx=10, pady=4,
        ).pack(side="right", padx=4)

        # Two-column layout
        cols = tk.Frame(outer, bg=BG)
        cols.pack(fill="both", expand=True)

        self._build_left(cols)
        self._build_right(cols)

    # ──────────────────────────────────────────────────────────────────────────
    # LEFT COLUMN
    # ──────────────────────────────────────────────────────────────────────────

    def _build_left(self, parent):
        left = tk.Frame(parent, bg=BG)
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))

        # ── Accounts ──────────────────────────────────────────────
        acc_frame = tk.LabelFrame(left, text=" 👤 Accounts (assigned to Join) ",
                                  bg=PANEL, fg=CYAN, font=FONTS["subheading"])
        acc_frame.pack(fill="both", expand=True, pady=(0, 6))

        acc_btns = tk.Frame(acc_frame, bg=PANEL)
        acc_btns.pack(fill="x", padx=8, pady=(6, 2))
        tk.Button(acc_btns, text="Select All", command=self._select_all_accounts,
                  bg=CARD, fg=TEXT, font=FONTS["small"], relief="flat", padx=6).pack(side="left", padx=2)
        tk.Button(acc_btns, text="Refresh", command=self._reload_accounts,
                  bg=CARD, fg=TEXT, font=FONTS["small"], relief="flat", padx=6).pack(side="left", padx=2)

        sb_acc = tk.Scrollbar(acc_frame)
        sb_acc.pack(side="right", fill="y")
        self._acc_listbox = tk.Listbox(
            acc_frame, selectmode="extended", yscrollcommand=sb_acc.set,
            font=FONTS["mono"], bg=CARD, fg=TEXT, relief="flat", height=7,
            selectbackground=COLORS["primary_light"], selectforeground=CYAN,
        )
        self._acc_listbox.pack(fill="both", expand=True, padx=8, pady=(0, 6))
        sb_acc.config(command=self._acc_listbox.yview)

        # ── Group source ─────────────────────────────────────────
        grp_src = tk.LabelFrame(left, text=" 🌐 Group Source ",
                                bg=PANEL, fg=CYAN, font=FONTS["subheading"])
        grp_src.pack(fill="x", pady=(0, 6))

        self._grp_source_var = tk.StringVar(value="finder")
        for lbl, val in [("From Finder Results", "finder"), ("Manual input", "manual"), ("From file (.txt)", "file")]:
            tk.Radiobutton(grp_src, text=lbl, variable=self._grp_source_var, value=val,
                           command=self._on_source_change,
                           bg=PANEL, fg=TEXT, selectcolor=CARD, activebackground=PANEL,
                           font=FONTS["normal"]).pack(anchor="w", padx=14, pady=2)

        self._manual_frame = tk.Frame(grp_src, bg=PANEL)
        self._manual_frame.pack(fill="x", padx=8, pady=(0, 6))
        self._manual_text = tk.Text(self._manual_frame, height=3, font=FONTS["mono"],
                                    bg=CARD, fg=TEXT, insertbackground=TEXT, relief="flat")
        self._manual_text.pack(fill="x")
        tk.Label(grp_src, text="One link per line (manual mode)",
                 font=FONTS["small"], fg=MUTED, bg=PANEL).pack(anchor="w", padx=14, pady=(0, 4))

        self._file_frame = tk.Frame(grp_src, bg=PANEL)
        self._file_frame.pack(fill="x", padx=8, pady=(0, 6))
        self._file_var = tk.StringVar()
        tk.Entry(self._file_frame, textvariable=self._file_var, width=28,
                 bg=CARD, fg=TEXT, font=FONTS["small"], relief="flat").pack(side="left", fill="x", expand=True)
        tk.Button(self._file_frame, text="Browse", command=self._browse_file,
                  bg=CARD, fg=TEXT, font=FONTS["small"], relief="flat", padx=6).pack(side="left", padx=4)

        # ── Group list ───────────────────────────────────────────
        grp_sel = tk.LabelFrame(left, text=" 📋 Groups (Finder results) ",
                                bg=PANEL, fg=CYAN, font=FONTS["subheading"])
        grp_sel.pack(fill="both", expand=True, pady=(0, 6))

        grp_btns = tk.Frame(grp_sel, bg=PANEL)
        grp_btns.pack(fill="x", padx=8, pady=(6, 2))
        tk.Button(grp_btns, text="Select All", command=self._select_all_groups,
                  bg=CARD, fg=TEXT, font=FONTS["small"], relief="flat", padx=6).pack(side="left", padx=2)
        tk.Button(grp_btns, text="Refresh", command=self._reload_groups,
                  bg=CARD, fg=TEXT, font=FONTS["small"], relief="flat", padx=6).pack(side="left", padx=2)
        self._grp_count_lbl = tk.Label(grp_btns, text="0 groups", font=FONTS["small"], fg=MUTED, bg=PANEL)
        self._grp_count_lbl.pack(side="right", padx=6)

        sb_grp = tk.Scrollbar(grp_sel)
        sb_grp.pack(side="right", fill="y")
        self._grp_listbox = tk.Listbox(
            grp_sel, selectmode="extended", yscrollcommand=sb_grp.set,
            font=FONTS["mono"], bg=CARD, fg=TEXT, relief="flat", height=8,
            selectbackground=COLORS["primary_light"], selectforeground=CYAN,
        )
        self._grp_listbox.pack(fill="both", expand=True, padx=8, pady=(0, 6))
        sb_grp.config(command=self._grp_listbox.yview)

        self._reload_accounts()
        self._reload_groups()
        self._on_source_change()

    # ──────────────────────────────────────────────────────────────────────────
    # RIGHT COLUMN
    # ──────────────────────────────────────────────────────────────────────────

    def _build_right(self, parent):
        right = tk.Frame(parent, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        # ── Control buttons ───────────────────────────────────────
        ctrl_frame = tk.Frame(right, bg=PANEL)
        ctrl_frame.pack(fill="x", pady=(0, 6))

        self._start_btn = tk.Button(ctrl_frame, text="▶ START JOIN",
                                    command=self._start_join,
                                    bg=GREEN, fg="#000", font=FONTS["bold"],
                                    relief="flat", padx=16, pady=8)
        self._start_btn.pack(side="left", padx=6, pady=6)

        self._pause_btn = tk.Button(ctrl_frame, text="⏸ PAUSE",
                                    command=self._pause_join,
                                    bg=GOLD, fg="#000", font=FONTS["bold"],
                                    relief="flat", padx=12, pady=8, state="disabled")
        self._pause_btn.pack(side="left", padx=4, pady=6)

        self._resume_btn = tk.Button(ctrl_frame, text="⟳ RESUME",
                                     command=self._resume_join,
                                     bg=CYAN, fg="#000", font=FONTS["bold"],
                                     relief="flat", padx=12, pady=8, state="disabled")
        self._resume_btn.pack(side="left", padx=4, pady=6)

        self._stop_btn = tk.Button(ctrl_frame, text="⏹ STOP",
                                   command=self._stop_join,
                                   bg=RED, fg="white", font=FONTS["bold"],
                                   relief="flat", padx=12, pady=8, state="disabled")
        self._stop_btn.pack(side="left", padx=4, pady=6)

        self._retry_btn = tk.Button(ctrl_frame, text="↻ RETRY FAILED",
                                    command=self._retry_failed,
                                    bg=CARD, fg=TEXT, font=FONTS["bold"],
                                    relief="flat", padx=10, pady=8, state="disabled")
        self._retry_btn.pack(side="left", padx=4, pady=6)

        # ── Progress ──────────────────────────────────────────────
        prog_frame = tk.LabelFrame(right, text=" 📊 Progress ",
                                   bg=PANEL, fg=CYAN, font=FONTS["subheading"])
        prog_frame.pack(fill="x", pady=(0, 6))

        self._progress_bar = ttk.Progressbar(prog_frame, mode="determinate", length=400)
        self._progress_bar.pack(fill="x", padx=12, pady=6)
        self._progress_pct_lbl = tk.Label(prog_frame, text="0%  (0/0)",
                                          font=FONTS["bold"], fg=CYAN, bg=PANEL)
        self._progress_pct_lbl.pack()

        # Stats row
        stats_row = tk.Frame(prog_frame, bg=PANEL)
        stats_row.pack(fill="x", padx=12, pady=4)
        self._stat_vars = {}
        for key, label, color in [
            ("joined",  "✅ Joined",  GREEN),
            ("failed",  "❌ Failed",  RED),
            ("banned",  "🚫 Banned",  GOLD),
            ("skipped", "⏭ Skipped", MUTED),
            ("pending", "⏱ Pending", TEXT),
        ]:
            col = tk.Frame(stats_row, bg=PANEL)
            col.pack(side="left", expand=True)
            tk.Label(col, text=label, font=FONTS["small"], fg=MUTED, bg=PANEL).pack()
            var = tk.StringVar(value="0")
            self._stat_vars[key] = var
            tk.Label(col, textvariable=var, font=FONTS["subheading"], fg=color, bg=PANEL).pack()

        meta_row = tk.Frame(prog_frame, bg=PANEL)
        meta_row.pack(fill="x", padx=12, pady=(2, 6))
        self._eta_lbl = tk.Label(meta_row, text="ETA: —",
                                 font=FONTS["small"], fg=MUTED, bg=PANEL)
        self._eta_lbl.pack(side="left", padx=8)
        self._speed_lbl = tk.Label(meta_row, text="Speed: —",
                                   font=FONTS["small"], fg=MUTED, bg=PANEL)
        self._speed_lbl.pack(side="left", padx=8)
        self._delay_lbl = tk.Label(meta_row, text="Delay: 3s",
                                   font=FONTS["small"], fg=MUTED, bg=PANEL)
        self._delay_lbl.pack(side="left", padx=8)
        self._current_lbl = tk.Label(meta_row, text="",
                                     font=FONTS["small"], fg=CYAN, bg=PANEL)
        self._current_lbl.pack(side="left", padx=8)

        # ── Settings panel (hidden by default) ───────────────────
        self._settings_visible = False
        self._settings_frame = tk.LabelFrame(right, text=" ⚙ Join Settings ",
                                             bg=PANEL, fg=CYAN, font=FONTS["subheading"])
        self._build_settings(self._settings_frame)

        # ── Activity log ──────────────────────────────────────────
        log_frame = tk.LabelFrame(right, text=" 📜 Activity Log (newest first) ",
                                  bg=PANEL, fg=CYAN, font=FONTS["subheading"])
        log_frame.pack(fill="both", expand=True)

        log_btn_row = tk.Frame(log_frame, bg=PANEL)
        log_btn_row.pack(fill="x", padx=8, pady=(4, 2))
        tk.Button(log_btn_row, text="📋 Copy Log", command=self._copy_log,
                  bg=CARD, fg=TEXT, font=FONTS["small"], relief="flat", padx=6).pack(side="left", padx=2)
        tk.Button(log_btn_row, text="💾 Save Log", command=self._save_log,
                  bg=CARD, fg=TEXT, font=FONTS["small"], relief="flat", padx=6).pack(side="left", padx=2)
        tk.Button(log_btn_row, text="🔄 Clear", command=self._clear_log,
                  bg=CARD, fg=TEXT, font=FONTS["small"], relief="flat", padx=6).pack(side="left", padx=2)

        self._log_text = tk.Text(
            log_frame, font=FONTS["mono"], bg=CARD, fg=TEXT,
            relief="flat", state="disabled", height=14,
            insertbackground=TEXT,
        )
        self._log_text.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        # Tag colours
        self._log_text.tag_config("success", foreground=GREEN)
        self._log_text.tag_config("error",   foreground=RED)
        self._log_text.tag_config("ban",     foreground=GOLD)
        self._log_text.tag_config("warning", foreground=GOLD)
        self._log_text.tag_config("pause",   foreground=PURPLE)
        self._log_text.tag_config("info",    foreground=TEXT)

    def _build_settings(self, parent):
        row = 0

        # Speed
        tk.Label(parent, text="Speed:", fg=TEXT, bg=PANEL, font=FONTS["normal"]).grid(
            row=row, column=0, sticky="w", padx=10, pady=4)
        self._speed_var = tk.StringVar(value="normal")
        speed_frame = tk.Frame(parent, bg=PANEL)
        speed_frame.grid(row=row, column=1, columnspan=3, sticky="w", pady=4)
        for lbl, val in [("Conservative (30s)", "conservative"), ("Normal (3s)", "normal"), ("Aggressive (1s)", "aggressive")]:
            tk.Radiobutton(speed_frame, text=lbl, variable=self._speed_var, value=val,
                           bg=PANEL, fg=TEXT, selectcolor=CARD, activebackground=PANEL,
                           font=FONTS["small"]).pack(side="left", padx=4)
        row += 1

        # Health check
        self._skip_unhealthy_var = tk.BooleanVar(value=True)
        tk.Checkbutton(parent, text="Skip accounts with health < 40 (unhealthy)",
                       variable=self._skip_unhealthy_var,
                       bg=PANEL, fg=TEXT, selectcolor=CARD, activebackground=PANEL,
                       font=FONTS["normal"]).grid(row=row, column=0, columnspan=4, sticky="w", padx=10, pady=2)
        row += 1

        # On ban
        tk.Label(parent, text="On ban:", fg=TEXT, bg=PANEL, font=FONTS["normal"]).grid(
            row=row, column=0, sticky="w", padx=10, pady=4)
        self._on_ban_var = tk.StringVar(value="auto_continue")
        ban_frame = tk.Frame(parent, bg=PANEL)
        ban_frame.grid(row=row, column=1, columnspan=3, sticky="w", pady=4)
        for lbl, val in [("Auto-continue", "auto_continue"), ("Pause", "pause"), ("Stop", "stop")]:
            tk.Radiobutton(ban_frame, text=lbl, variable=self._on_ban_var, value=val,
                           bg=PANEL, fg=TEXT, selectcolor=CARD, activebackground=PANEL,
                           font=FONTS["small"]).pack(side="left", padx=4)
        row += 1

        # Auto-leave
        self._auto_leave_var = tk.BooleanVar(value=True)
        tk.Checkbutton(parent, text="Auto-leave group if banned",
                       variable=self._auto_leave_var,
                       bg=PANEL, fg=TEXT, selectcolor=CARD, activebackground=PANEL,
                       font=FONTS["normal"]).grid(row=row, column=0, columnspan=4, sticky="w", padx=10, pady=2)
        row += 1

        # Skip already joined
        self._skip_joined_var = tk.BooleanVar(value=True)
        tk.Checkbutton(parent, text="Skip groups already joined",
                       variable=self._skip_joined_var,
                       bg=PANEL, fg=TEXT, selectcolor=CARD, activebackground=PANEL,
                       font=FONTS["normal"]).grid(row=row, column=0, columnspan=4, sticky="w", padx=10, pady=2)
        row += 1

        # Health check before start
        self._health_before_var = tk.BooleanVar(value=True)
        tk.Checkbutton(parent, text="Check account health before starting",
                       variable=self._health_before_var,
                       bg=PANEL, fg=TEXT, selectcolor=CARD, activebackground=PANEL,
                       font=FONTS["normal"]).grid(row=row, column=0, columnspan=4, sticky="w", padx=10, pady=2)
        row += 1

        save_row = tk.Frame(parent, bg=PANEL)
        save_row.grid(row=row, column=0, columnspan=4, sticky="w", padx=10, pady=6)
        tk.Button(save_row, text="💾 Save Settings", command=self._save_settings,
                  bg=GREEN, fg="#000", font=FONTS["bold"], relief="flat", padx=8).pack(side="left", padx=4)
        tk.Button(save_row, text="Default", command=self._reset_settings,
                  bg=CARD, fg=TEXT, font=FONTS["small"], relief="flat", padx=6).pack(side="left", padx=4)

    # ──────────────────────────────────────────────────────────────────────────
    # SETTINGS PANEL TOGGLE
    # ──────────────────────────────────────────────────────────────────────────

    def _toggle_settings(self):
        if self._settings_visible:
            self._settings_frame.pack_forget()
            self._settings_visible = False
        else:
            self._settings_frame.pack(fill="x", pady=(0, 6))
            self._settings_visible = True

    def _save_settings(self):
        join_engine.settings["speed_preset"]          = self._speed_var.get()
        join_engine.settings["skip_unhealthy"]        = self._skip_unhealthy_var.get()
        join_engine.settings["on_ban"]                = self._on_ban_var.get()
        join_engine.settings["auto_leave_on_ban"]     = self._auto_leave_var.get()
        join_engine.settings["skip_already_joined"]   = self._skip_joined_var.get()
        join_engine.settings["health_check_before_start"] = self._health_before_var.get()
        join_engine.delay.set_preset(self._speed_var.get())
        self._append_log("⚙ Settings saved", "info")

    def _reset_settings(self):
        self._speed_var.set("normal")
        self._skip_unhealthy_var.set(True)
        self._on_ban_var.set("auto_continue")
        self._auto_leave_var.set(True)
        self._skip_joined_var.set(True)
        self._health_before_var.set(True)
        self._save_settings()

    # ──────────────────────────────────────────────────────────────────────────
    # DATA LOADING
    # ──────────────────────────────────────────────────────────────────────────

    def _reload_accounts(self):
        self._acc_listbox.delete(0, "end")
        self._accounts_data = account_manager.get_accounts_by_feature("join")
        if not self._accounts_data:
            self._accounts_data = account_manager.get_all()
        for a in self._accounts_data:
            phone = a.get("phone") or a.get("name", "")
            name  = a.get("name", phone)
            h = get_health(phone) if phone else None
            score = h["health_score"] if h else 100
            icon  = "🟢" if score >= 70 else ("🟡" if score >= 40 else "🔴")
            self._acc_listbox.insert("end", f"{icon} {name} [{score}/100]")

    def _select_all_accounts(self):
        self._acc_listbox.select_set(0, "end")

    def _reload_groups(self):
        self._grp_listbox.delete(0, "end")
        self._groups_data = list_found_groups(only_unjoined=True)
        for g in self._groups_data:
            title = g.get("group_title") or g.get("title") or g.get("group_link", "")
            link  = g.get("group_link", "")
            members = g.get("member_count", 0)
            self._grp_listbox.insert("end", f"{title[:35]}  [{members} 👥]  {link[:30]}")
        self._grp_count_lbl.config(text=f"{len(self._groups_data)} groups")

    def _select_all_groups(self):
        self._grp_listbox.select_set(0, "end")

    def _on_source_change(self):
        src = self._grp_source_var.get()
        if src == "finder":
            self._manual_frame.pack_forget()
            self._file_frame.pack_forget()
        elif src == "manual":
            self._manual_frame.pack(fill="x", padx=8, pady=(0, 4))
            self._file_frame.pack_forget()
        else:
            self._manual_frame.pack_forget()
            self._file_frame.pack(fill="x", padx=8, pady=(0, 4))

    def _browse_file(self):
        path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All", "*.*")])
        if path:
            self._file_var.set(path)

    def _get_selected_accounts(self) -> list:
        sel = self._acc_listbox.curselection()
        if not sel:
            # fallback: all
            sel = list(range(len(self._accounts_data)))
        result = []
        for i in sel:
            if i < len(self._accounts_data):
                result.append(self._accounts_data[i])
        return result

    def _get_groups_to_join(self) -> list:
        src = self._grp_source_var.get()
        if src == "finder":
            sel = self._grp_listbox.curselection()
            if not sel:
                sel = list(range(len(self._groups_data)))
            return [
                {
                    "group_link":  self._groups_data[i].get("group_link", ""),
                    "group_title": self._groups_data[i].get("group_title") or self._groups_data[i].get("title", ""),
                    "member_count": self._groups_data[i].get("member_count", 0),
                }
                for i in sel if i < len(self._groups_data)
            ]
        if src == "manual":
            lines = self._manual_text.get("1.0", "end").strip().splitlines()
            return [{"group_link": l.strip(), "group_title": l.strip()} for l in lines if l.strip()]
        # file
        path = self._file_var.get().strip()
        if not path or not Path(path).exists():
            return []
        with open(path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        return [{"group_link": l, "group_title": l} for l in lines]

    # ──────────────────────────────────────────────────────────────────────────
    # HEALTH CHECK
    # ──────────────────────────────────────────────────────────────────────────

    def _run_health_check(self):
        accounts = self._get_selected_accounts()
        if not accounts:
            messagebox.showwarning("Health Check", "No accounts selected.")
            return
        self._health_check_btn.config(state="disabled", text="🩺 Checking…")
        phones = [a.get("phone") or a.get("name", "") for a in accounts]

        def _on_result(r):
            def _upd():
                self._append_log(
                    f"🩺 {r.get('phone','?')} → {r.get('status','?')} [{r.get('health_score',0)}/100]",
                    "success" if r.get("status") == "active" else "warning",
                )
            self.frame.after(0, _upd)

        def _on_done(results):
            def _fin():
                self._reload_accounts()
                self._health_check_btn.config(state="normal", text="🩺 Check Health")
                self._append_log(f"🩺 Health check complete ({len(results)} accounts)", "info")
            self.frame.after(0, _fin)

        check_accounts_health(phones, on_result=_on_result, on_done=_on_done)

    # ──────────────────────────────────────────────────────────────────────────
    # JOIN CONTROL
    # ──────────────────────────────────────────────────────────────────────────

    def _start_join(self):
        # Check for resumable session
        ri = persistent_queue.resume_info()
        if ri and ri.get("completed", 0) < ri.get("total", 0):
            completed = ri.get("completed", 0)
            total     = ri.get("total", 0)
            answer = messagebox.askyesnocancel(
                "Resume Session",
                f"⟳ Resume interrupted session?\n\n"
                f"Completed: {completed}/{total} groups\n"
                f"Started: {ri.get('created_at', 'unknown')}\n\n"
                "Yes = Resume   No = Start fresh   Cancel = Abort",
            )
            if answer is None:
                return
            if answer:
                self._do_start(resume=True)
                return

        # Fresh start
        accounts = self._get_selected_accounts()
        groups   = self._get_groups_to_join()

        if not accounts:
            messagebox.showwarning("Start Join", "No accounts available. Assign accounts in the Accounts tab.")
            return
        if not groups:
            messagebox.showwarning("Start Join", "No groups selected.")
            return

        self._do_start(resume=False, accounts=accounts, groups=groups)

    def _do_start(self, resume: bool, accounts=None, groups=None):
        self._save_settings()
        self._set_buttons_running()

        def _on_update(stats: JoinStats):
            self.frame.after(0, lambda s=stats: self._update_stats(s))

        def _on_done(stats: JoinStats):
            def _done():
                self._set_buttons_idle()
                self._retry_btn.config(state="normal")
                if stats:
                    self._update_stats(stats)
                    self._append_log(
                        f"✅ Session complete — {stats.joined} joined, {stats.failed} failed, {stats.banned} banned",
                        "success",
                    )
                self._reload_groups()
                self._stop_polling()
            self.frame.after(0, _done)

        if resume:
            join_engine.start(accounts=[], groups=[], on_update=_on_update, on_done=_on_done, resume=True)
        else:
            join_engine.start(
                accounts=accounts or [],
                groups=groups or [],
                on_update=_on_update,
                on_done=_on_done,
                resume=False,
            )
        self._start_polling()

    def _pause_join(self):
        join_engine.pause()
        self._pause_btn.config(state="disabled")
        self._resume_btn.config(state="normal")
        self._append_log("⏸ Session paused", "pause")

    def _resume_join(self):
        join_engine.resume()
        self._resume_btn.config(state="disabled")
        self._pause_btn.config(state="normal")
        self._append_log("▶ Session resumed", "info")

    def _stop_join(self):
        join_engine.stop()
        self._set_buttons_idle()
        self._append_log("⏹ Session stopped by user", "warning")
        self._stop_polling()

    def _retry_failed(self):
        """Reload unjoined groups and start a fresh session."""
        self._reload_groups()
        accounts = self._get_selected_accounts()
        groups   = self._get_groups_to_join()
        if not groups:
            messagebox.showinfo("Retry", "No pending groups found.")
            return
        persistent_queue.clear()
        self._do_start(resume=False, accounts=accounts, groups=groups)

    # ──────────────────────────────────────────────────────────────────────────
    # STATS POLLING
    # ──────────────────────────────────────────────────────────────────────────

    def _start_polling(self):
        self._stop_polling()
        self._poll_stats()

    def _stop_polling(self):
        if self._update_job is not None:
            try:
                self.frame.after_cancel(self._update_job)
            except Exception:
                pass
            self._update_job = None

    def _poll_stats(self):
        if join_engine.stats:
            self._update_stats(join_engine.stats)
        if join_engine.running:
            self._update_job = self.frame.after(2000, self._poll_stats)

    def _update_stats(self, stats: JoinStats):
        total     = stats.total or 1
        completed = stats.completed
        pct       = int(completed / total * 100)

        self._progress_bar["value"] = pct
        self._progress_pct_lbl.config(
            text=f"{pct}%  ({completed}/{total})"
        )

        for key in ("joined", "failed", "banned", "skipped"):
            self._stat_vars[key].set(str(getattr(stats, key, 0)))
        pending = total - completed
        self._stat_vars["pending"].set(str(max(0, pending)))

        # ETA
        eta = stats.eta_seconds
        if eta is None:
            eta_str = "—"
        elif eta <= 0:
            eta_str = "Done"
        else:
            mins = int(eta // 60)
            secs = int(eta % 60)
            eta_str = f"{mins}m {secs}s"

        self._eta_lbl.config(text=f"ETA: {eta_str}")
        self._speed_lbl.config(text=f"Speed: {stats.speed} joins/min")
        self._delay_lbl.config(text=f"Delay: {join_engine.delay.current_delay:.0f}s")
        if stats.current_account:
            self._current_lbl.config(
                text=f"→ {stats.current_account} [{stats.current_health}/100] → {stats.current_group[:30]}"
            )

        # Update log (prepend new entries)
        self._refresh_log(stats.log)

    def _refresh_log(self, log_entries: list):
        """Efficiently refresh log from stats.log list (newest first already)."""
        # We keep our own count to avoid redundant refreshes
        current_count = getattr(self, "_last_log_count", 0)
        new_entries = log_entries[:len(log_entries) - current_count]
        if not new_entries:
            return
        self._last_log_count = len(log_entries)
        self._log_text.config(state="normal")
        for entry in new_entries:
            tag   = entry.get("level", "info")
            ts    = entry.get("ts", "")
            msg   = entry.get("msg", "")
            line  = f"[{ts}] {msg}\n"
            self._log_text.insert("1.0", line, tag)
        # Trim
        lines = int(self._log_text.index("end-1c").split(".")[0])
        if lines > 800:
            self._log_text.delete(f"{800}.0", "end")
        self._log_text.config(state="disabled")

    def _append_log(self, msg: str, level: str = "info"):
        ts   = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}\n"
        self._log_text.config(state="normal")
        self._log_text.insert("1.0", line, level)
        self._log_text.config(state="disabled")

    def _clear_log(self):
        self._log_text.config(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.config(state="disabled")
        self._last_log_count = 0

    def _copy_log(self):
        content = self._log_text.get("1.0", "end")
        self.frame.clipboard_clear()
        self.frame.clipboard_append(content)
        self._append_log("📋 Log copied to clipboard", "info")

    def _save_log(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text", "*.txt"), ("All", "*.*")],
            initialfile=f"join_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        )
        if path:
            content = self._log_text.get("1.0", "end")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self._append_log(f"💾 Log saved to {path}", "info")

    # ──────────────────────────────────────────────────────────────────────────
    # BUTTON STATES
    # ──────────────────────────────────────────────────────────────────────────

    def _set_buttons_running(self):
        self._start_btn.config(state="disabled")
        self._pause_btn.config(state="normal")
        self._resume_btn.config(state="disabled")
        self._stop_btn.config(state="normal")
        self._retry_btn.config(state="disabled")

    def _set_buttons_idle(self):
        self._start_btn.config(state="normal")
        self._pause_btn.config(state="disabled")
        self._resume_btn.config(state="disabled")
        self._stop_btn.config(state="disabled")

    # ──────────────────────────────────────────────────────────────────────────
    # MISC
    # ──────────────────────────────────────────────────────────────────────────

    def _on_tab_selected(self):
        self._reload_accounts()
        self._reload_groups()

    def _on_account_changed(self, data=None):
        try:
            self._reload_accounts()
        except Exception:
            pass