"""
gui/broadcast_tab.py - Send messages with real-time progress tracking
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading

from gui.styles import COLORS, FONTS, make_btn
from core.account import list_accounts
from core.finder import list_groups
from core.broadcast import broadcast_engine, BroadcastProgress

BG    = COLORS["bg_dark"]
PANEL = COLORS["bg_medium"]
CARD  = COLORS["bg_light"]
CYAN  = COLORS["primary"]
GREEN = COLORS["success"]
RED   = COLORS["error"]
TEXT  = COLORS["text"]
MUTED = COLORS["text_muted"]
ORANGE = COLORS["warning"]


class BroadcastTab:
    title = "📢 Broadcast"

    def __init__(self, parent, main_window=None):
        self.parent = parent
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        self._build()
        self._reload_accounts()
        self._reload_groups()

    # ─────────────────────────────────────────────────────────────────────────
    def _build(self):

        outer = tk.Frame(self.frame, bg=BG)
        outer.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(outer, text="📢 Broadcast",
                 font=FONTS["heading_large"], fg=CYAN, bg=BG).pack(anchor="w", pady=(0, 12))

        # Main two-column layout
        cols = tk.Frame(outer, bg=BG)
        cols.pack(fill="both", expand=True)

        left  = tk.Frame(cols, bg=BG)
        right = tk.Frame(cols, bg=BG)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))
        right.pack(side="left", fill="both", expand=True)

        self._build_left(left)
        self._build_right(right)

    # ─────────────────────────────────────────────────────────────────────────
    def _build_left(self, parent):
        # ── Message ────────────────────────────────────────────────────────────
        msg_frame = tk.LabelFrame(parent, text=" ✏️ Message ",
                                  bg=PANEL, fg=CYAN, font=FONTS["subheading"])
        msg_frame.pack(fill="x", pady=(0, 10))
        self._msg_text = scrolledtext.ScrolledText(
            msg_frame, height=8, wrap="word",
            bg=CARD, fg=TEXT, insertbackground=TEXT,
            font=FONTS["normal"], relief="flat"
        )
        self._msg_text.pack(fill="x", padx=10, pady=10)

        # ── Delay settings ─────────────────────────────────────────────────────
        delay_frame = tk.LabelFrame(parent, text=" ⏱️ Delays (seconds) ",
                                    bg=PANEL, fg=CYAN, font=FONTS["subheading"])
        delay_frame.pack(fill="x", pady=(0, 10))
        dr = tk.Frame(delay_frame, bg=PANEL)
        dr.pack(fill="x", padx=12, pady=8)

        tk.Label(dr, text="Min:", font=FONTS["normal"], fg=TEXT, bg=PANEL).pack(side="left")
        self._min_delay_var = tk.StringVar(value="3")
        tk.Entry(dr, textvariable=self._min_delay_var, width=5,
                 bg=CARD, fg=TEXT, insertbackground=TEXT,
                 font=FONTS["normal"], relief="flat").pack(side="left", padx=(4, 16))

        tk.Label(dr, text="Max:", font=FONTS["normal"], fg=TEXT, bg=PANEL).pack(side="left")
        self._max_delay_var = tk.StringVar(value="8")
        tk.Entry(dr, textvariable=self._max_delay_var, width=5,
                 bg=CARD, fg=TEXT, insertbackground=TEXT,
                 font=FONTS["normal"], relief="flat").pack(side="left", padx=(4, 0))

        # ── Broadcast name ──────────────────────────────────────────────────────
        name_frame = tk.LabelFrame(parent, text=" 📝 Broadcast Name ",
                                   bg=PANEL, fg=CYAN, font=FONTS["subheading"])
        name_frame.pack(fill="x", pady=(0, 10))
        nr = tk.Frame(name_frame, bg=PANEL)
        nr.pack(fill="x", padx=12, pady=8)
        self._name_var = tk.StringVar(value="")
        tk.Entry(nr, textvariable=self._name_var,
                 bg=CARD, fg=TEXT, insertbackground=TEXT,
                 font=FONTS["normal"], width=35, relief="flat").pack(side="left")

        # ── Control buttons ─────────────────────────────────────────────────────
        btn_frame = tk.Frame(parent, bg=BG)
        btn_frame.pack(fill="x", pady=8)

        self._start_btn = make_btn(btn_frame, "▶️ START", command=self._start,
                                   color=GREEN, fg="#000")
        self._start_btn.pack(side="left", padx=(0, 6))

        self._pause_btn = make_btn(btn_frame, "⏸️ PAUSE", command=self._pause,
                                   color=ORANGE, fg="#000")
        self._pause_btn.pack(side="left", padx=(0, 6))
        self._pause_btn.config(state="disabled")

        self._stop_btn = make_btn(btn_frame, "⏹️ STOP", command=self._stop,
                                  color=RED)
        self._stop_btn.pack(side="left")
        self._stop_btn.config(state="disabled")

        # ── Progress ────────────────────────────────────────────────────────────
        prog_frame = tk.LabelFrame(parent, text=" 📊 Progress ",
                                   bg=PANEL, fg=CYAN, font=FONTS["subheading"])
        prog_frame.pack(fill="x", pady=(0, 0))

        stats_row = tk.Frame(prog_frame, bg=PANEL)
        stats_row.pack(fill="x", padx=12, pady=8)

        def stat_block(par, label, var, color):
            blk = tk.Frame(par, bg=PANEL)
            blk.pack(side="left", padx=12)
            tk.Label(blk, text=label, font=FONTS["small"], fg=MUTED, bg=PANEL).pack()
            tk.Label(blk, textvariable=var,  font=FONTS["heading"], fg=color, bg=PANEL).pack()

        self._sent_var    = tk.StringVar(value="0")
        self._failed_var  = tk.StringVar(value="0")
        self._pending_var = tk.StringVar(value="0")
        self._total_var   = tk.StringVar(value="0")
        stat_block(stats_row, "SENT",    self._sent_var,    GREEN)
        stat_block(stats_row, "FAILED",  self._failed_var,  RED)
        stat_block(stats_row, "PENDING", self._pending_var, ORANGE)
        stat_block(stats_row, "TOTAL",   self._total_var,   CYAN)

        self._prog_bar = ttk.Progressbar(prog_frame, length=300, mode="determinate")
        self._prog_bar.pack(fill="x", padx=12, pady=(0, 8))

    # ─────────────────────────────────────────────────────────────────────────
    def _build_right(self, parent):
        # ── Groups list ────────────────────────────────────────────────────────
        grp_frame = tk.LabelFrame(parent, text=" 📝 Target Groups ",
                                  bg=PANEL, fg=CYAN, font=FONTS["subheading"])
        grp_frame.pack(fill="both", expand=True, pady=(0, 8))

        grp_btn_row = tk.Frame(grp_frame, bg=PANEL)
        grp_btn_row.pack(fill="x", padx=10, pady=(6, 2))
        make_btn(grp_btn_row, "☑ All", command=self._select_all_groups,
                 color=CARD).pack(side="left", padx=(0, 4))
        make_btn(grp_btn_row, "☐ None", command=self._deselect_all_groups,
                 color=CARD).pack(side="left", padx=(0, 4))
        make_btn(grp_btn_row, "🔄", command=self._reload_groups,
                 color=CARD).pack(side="left")

        self._grp_listbox = tk.Listbox(
            grp_frame, selectmode="multiple",
            bg=CARD, fg=TEXT, font=FONTS["normal"],
            height=10, relief="flat", selectbackground=CYAN, selectforeground="#000"
        )
        grp_sb = ttk.Scrollbar(grp_frame, orient="vertical",
                                command=self._grp_listbox.yview)
        self._grp_listbox.config(yscrollcommand=grp_sb.set)
        grp_inner = tk.Frame(grp_frame, bg=PANEL)
        grp_inner.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._grp_listbox.pack(side="left", fill="both", expand=True, in_=grp_inner)
        grp_sb.pack(side="right", fill="y", in_=grp_inner)

        # ── Accounts list ──────────────────────────────────────────────────────
        acc_frame = tk.LabelFrame(parent, text=" 👤 Accounts ",
                                  bg=PANEL, fg=CYAN, font=FONTS["subheading"])
        acc_frame.pack(fill="both", expand=True, pady=(0, 8))

        acc_btn_row = tk.Frame(acc_frame, bg=PANEL)
        acc_btn_row.pack(fill="x", padx=10, pady=(6, 2))
        make_btn(acc_btn_row, "☑ All", command=self._select_all_accounts,
                 color=CARD).pack(side="left", padx=(0, 4))
        make_btn(acc_btn_row, "☐ None", command=self._deselect_all_accounts,
                 color=CARD).pack(side="left", padx=(0, 4))
        make_btn(acc_btn_row, "🔄", command=self._reload_accounts,
                 color=CARD).pack(side="left")

        self._acc_listbox = tk.Listbox(
            acc_frame, selectmode="multiple",
            bg=CARD, fg=TEXT, font=FONTS["normal"],
            height=8, relief="flat", selectbackground=GREEN, selectforeground="#000"
        )
        acc_sb = ttk.Scrollbar(acc_frame, orient="vertical",
                                command=self._acc_listbox.yview)
        self._acc_listbox.config(yscrollcommand=acc_sb.set)
        acc_inner = tk.Frame(acc_frame, bg=PANEL)
        acc_inner.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._acc_listbox.pack(side="left", fill="both", expand=True, in_=acc_inner)
        acc_sb.pack(side="right", fill="y", in_=acc_inner)

        # ── Activity log ───────────────────────────────────────────────────────
        log_frame = tk.LabelFrame(parent, text=" 📋 Activity Log (newest first) ",
                                  bg=PANEL, fg=CYAN, font=FONTS["subheading"])
        log_frame.pack(fill="both", expand=True)

        self._log_text = scrolledtext.ScrolledText(
            log_frame, height=10, state="disabled",
            bg=CARD, fg=GREEN, font=FONTS["mono"],
            relief="flat", wrap="word"
        )
        self._log_text.pack(fill="both", expand=True, padx=8, pady=8)

    # ─────────────────────────────────────────────────────────────────────────
    # Data loading
    # ─────────────────────────────────────────────────────────────────────────
    def _reload_accounts(self):
        self._acc_listbox.delete(0, "end")
        self._accounts_list = [(a["name"], a["phone"]) for a in list_accounts()]
        for name, phone in self._accounts_list:
            self._acc_listbox.insert("end", f"{name} ({phone})")

    def _reload_groups(self):
        self._grp_listbox.delete(0, "end")
        self._groups_list = [g["group_link"] for g in list_groups()]
        for g in self._groups_list:
            self._grp_listbox.insert("end", g)

    def _select_all_groups(self):
        self._grp_listbox.select_set(0, "end")

    def _deselect_all_groups(self):
        self._grp_listbox.selection_clear(0, "end")

    def _select_all_accounts(self):
        self._acc_listbox.select_set(0, "end")

    def _deselect_all_accounts(self):
        self._acc_listbox.selection_clear(0, "end")

    # ─────────────────────────────────────────────────────────────────────────
    # Broadcast controls
    # ─────────────────────────────────────────────────────────────────────────
    def _start(self):
        if broadcast_engine.is_running:
            messagebox.showwarning("Running", "A broadcast is already running.")
            return

        message = self._msg_text.get("1.0", "end").strip()
        if not message:
            messagebox.showwarning("Missing", "Enter a message.")
            return

        selected_grp_idx = self._grp_listbox.curselection()
        selected_acc_idx = self._acc_listbox.curselection()

        groups   = [self._groups_list[i] for i in selected_grp_idx]
        accounts = [self._accounts_list[i][1] for i in selected_acc_idx]

        if not groups:
            messagebox.showwarning("Missing", "Select at least one target group.")
            return
        if not accounts:
            messagebox.showwarning("Missing", "Select at least one account.")
            return

        try:
            min_d = float(self._min_delay_var.get())
            max_d = float(self._max_delay_var.get())
        except ValueError:
            messagebox.showerror("Invalid", "Delays must be numbers.")
            return
        if min_d > max_d:
            min_d, max_d = max_d, min_d

        name = self._name_var.get().strip() or ""
        self._total_var.set(str(len(groups)))

        broadcast_engine.start(
            message=message,
            groups=groups,
            accounts=accounts,
            min_delay=min_d,
            max_delay=max_d,
            on_update=self._on_update,
            on_done=self._on_done,
            broadcast_name=name,
        )

        self._start_btn.config(state="disabled")
        self._pause_btn.config(state="normal")
        self._stop_btn.config(state="normal")
        self._append_log("▶️ Broadcast started.")

    def _pause(self):
        if broadcast_engine.is_paused:
            broadcast_engine.resume()
            self._pause_btn.config(text="⏸️ PAUSE")
        else:
            broadcast_engine.pause()
            self._pause_btn.config(text="▶️ RESUME")

    def _stop(self):
        broadcast_engine.stop()
        self._stop_btn.config(state="disabled")

    # ─────────────────────────────────────────────────────────────────────────
    # Callbacks from broadcast engine (called from background thread)
    # ─────────────────────────────────────────────────────────────────────────
    def _on_update(self, progress: BroadcastProgress):
        self.frame.after(0, lambda: self._update_ui(progress))

    def _on_done(self, progress: BroadcastProgress):
        self.frame.after(0, lambda: self._finish_ui(progress))

    def _update_ui(self, progress: BroadcastProgress):
        self._sent_var.set(str(progress.sent))
        self._failed_var.set(str(progress.failed))
        self._pending_var.set(str(progress.pending))
        total = progress.total or 1
        pct = int((progress.done / total) * 100)
        self._prog_bar["value"] = pct

        # Update log (newest first - show newest 200 lines)
        if progress.log:
            self._set_log("\n".join(progress.log[:200]))

    def _finish_ui(self, progress: BroadcastProgress):
        self._update_ui(progress)
        self._start_btn.config(state="normal")
        self._pause_btn.config(state="disabled", text="⏸️ PAUSE")
        self._stop_btn.config(state="disabled")

    def _append_log(self, msg: str):
        self._log_text.config(state="normal")
        self._log_text.insert("1.0", msg + "\n")
        self._log_text.config(state="disabled")

    def _set_log(self, content: str):
        self._log_text.config(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.insert("1.0", content)
        self._log_text.config(state="disabled")
