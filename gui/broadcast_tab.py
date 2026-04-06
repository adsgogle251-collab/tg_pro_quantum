"""
gui/broadcast_tab.py - Complete broadcast UI with START button, live account-group
mapping table, real-time stats, ETA, copy-link, and color-coded activity log.
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading

from gui.styles import COLORS, FONTS, make_btn
from core.account import list_accounts
from core.finder import list_groups, list_found_groups
from core.config import list_account_groups
from core.broadcaster import advanced_broadcaster, BroadcastStats

BG     = COLORS["bg_dark"]
PANEL  = COLORS["bg_medium"]
CARD   = COLORS["bg_light"]
CYAN   = COLORS["primary"]
GREEN  = COLORS["success"]
RED    = COLORS["error"]
GOLD   = COLORS["accent"]
TEXT   = COLORS["text"]
MUTED  = COLORS["text_muted"]
PURPLE = "#9B59FF"
BLUE   = COLORS.get("info", CYAN)


def _fmt_eta(seconds: int) -> str:
    """Format seconds into human-readable ETA string."""
    if seconds <= 0:
        return "—"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m}m"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def _log_fg_color(text: str) -> str:
    """Return a foreground color for a log or status entry text."""
    if "✅" in text or "sent" in text.lower():
        return GREEN
    if "🚫" in text or "banned" in text.lower() or "peerflood" in text.lower():
        return PURPLE
    if "❌" in text or "failed" in text.lower() or "expired" in text.lower():
        return RED
    if "⏳" in text or "🔄" in text or "▶" in text or "⚠️" in text or "slowmode" in text.lower():
        return GOLD
    return MUTED


class BroadcastTab:
    title = "📢 Broadcast"

    def __init__(self, parent, main_window=None):
        self.parent = parent
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        self._accounts_data: list = []
        self._groups_data: list = []
        # Cache all mapping entries for filtering without rebuilding from scratch
        self._all_mapping: list[dict] = []
        self._build()
        self._reload_accounts()
        self._reload_groups()

    # ─────────────────────────────────────────────────────────────────────────
    # BUILD LAYOUT
    # ─────────────────────────────────────────────────────────────────────────
    def _build(self):
        outer = tk.Frame(self.frame, bg=BG)
        outer.pack(fill="both", expand=True, padx=16, pady=8)

        # ── Title + Control Buttons (TOP - PROMINENT) ────────────────────────
        self._build_control_bar(outer)

        # ── Progress/Stats Bar (FULL WIDTH) ──────────────────────────────────
        self._build_stats_bar(outer)

        # ── Main two-column body ─────────────────────────────────────────────
        body = tk.Frame(outer, bg=BG)
        body.pack(fill="both", expand=True, pady=(6, 0))

        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="both", expand=False, padx=(0, 8))
        left.config(width=350)
        left.pack_propagate(False)

        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        self._build_left(left)
        self._build_right(right)

    # ── Control bar ──────────────────────────────────────────────────────────
    def _build_control_bar(self, parent):
        bar = tk.Frame(parent, bg=PANEL, pady=10)
        bar.pack(fill="x", pady=(0, 6))

        tk.Label(
            bar, text="📢 Advanced Broadcast",
            font=FONTS["heading"], fg=CYAN, bg=PANEL,
        ).pack(side="left", padx=12)

        # Buttons on the right side – ordered: START / PAUSE / RESUME / STOP / RETRY
        btn_frame = tk.Frame(bar, bg=PANEL)
        btn_frame.pack(side="right", padx=12)

        self._start_btn = tk.Button(
            btn_frame, text="▶  START BROADCAST",
            command=self._start,
            bg="#00CC44", fg="#000000",
            font=("Segoe UI", 13, "bold"),
            relief="flat", cursor="hand2",
            padx=18, pady=8,
            activebackground="#00AA33", activeforeground="#000",
        )
        self._start_btn.pack(side="left", padx=4)

        self._pause_btn = tk.Button(
            btn_frame, text="⏸  PAUSE",
            command=self._pause,
            bg=GOLD, fg="#000000",
            font=("Segoe UI", 12, "bold"),
            relief="flat", cursor="hand2",
            padx=12, pady=8,
            state="disabled",
            activebackground="#E6A500", activeforeground="#000",
        )
        self._pause_btn.pack(side="left", padx=4)

        self._resume_btn = tk.Button(
            btn_frame, text="⟳  RESUME",
            command=self._resume,
            bg=CYAN, fg="#000000",
            font=("Segoe UI", 12, "bold"),
            relief="flat", cursor="hand2",
            padx=12, pady=8,
            state="disabled",
            activebackground=COLORS["primary_hover"], activeforeground="#000",
        )
        self._resume_btn.pack(side="left", padx=4)

        self._stop_btn = tk.Button(
            btn_frame, text="⏹  STOP",
            command=self._stop,
            bg=RED, fg="#ffffff",
            font=("Segoe UI", 12, "bold"),
            relief="flat", cursor="hand2",
            padx=12, pady=8,
            state="disabled",
            activebackground="#CC0044", activeforeground="#fff",
        )
        self._stop_btn.pack(side="left", padx=4)

        self._retry_btn = tk.Button(
            btn_frame, text="↻  RETRY FAILED",
            command=self._retry_failed,
            bg=BLUE, fg="#000000",
            font=("Segoe UI", 11, "bold"),
            relief="flat", cursor="hand2",
            padx=12, pady=8,
            state="disabled",
            activebackground="#00B8E6", activeforeground="#000",
        )
        self._retry_btn.pack(side="left", padx=4)

    # ── Stats bar ─────────────────────────────────────────────────────────────
    def _build_stats_bar(self, parent):
        stats_outer = tk.Frame(parent, bg=PANEL)
        stats_outer.pack(fill="x", pady=(0, 4))

        # First row: stat cards
        row1 = tk.Frame(stats_outer, bg=PANEL)
        row1.pack(fill="x", padx=12, pady=(8, 4))

        self._stat_vars = {}
        stat_defs = [
            ("✅ Sent",    "sent",    GREEN),
            ("❌ Failed",  "failed",  RED),
            ("🚫 Banned",  "banned",  PURPLE),
            ("⏳ Pending", "pending", MUTED),
            ("🔄 Rounds",  "rounds",  CYAN),
        ]
        for label, key, color in stat_defs:
            col = tk.Frame(row1, bg=CARD, padx=10, pady=6)
            col.pack(side="left", padx=4, fill="y")
            tk.Label(col, text=label, font=FONTS["small"], fg=MUTED, bg=CARD).pack()
            var = tk.StringVar(value="0")
            self._stat_vars[key] = var
            tk.Label(col, textvariable=var, font=FONTS["heading"], fg=color, bg=CARD).pack()

        # Second row: progress bar + pct + speed + ETA
        row2 = tk.Frame(stats_outer, bg=PANEL)
        row2.pack(fill="x", padx=12, pady=(0, 8))

        self._progress_var = tk.DoubleVar(value=0)
        self._pct_var = tk.StringVar(value="0%  (0/0)")
        self._speed_var = tk.StringVar(value="Speed: —")
        self._eta_var = tk.StringVar(value="ETA: —")

        self._prog_bar = ttk.Progressbar(
            row2, variable=self._progress_var, mode="determinate", length=300,
        )
        self._prog_bar.pack(side="left", fill="x", expand=True, padx=(0, 8))

        for var, fg_color in [
            (self._pct_var, TEXT),
            (self._speed_var, CYAN),
            (self._eta_var, GOLD),
        ]:
            tk.Label(row2, textvariable=var, font=FONTS["small"],
                     fg=fg_color, bg=PANEL).pack(side="left", padx=8)

    # ── Left column ──────────────────────────────────────────────────────────
    def _build_left(self, parent):
        # Message
        msg_frame = tk.LabelFrame(
            parent, text=" ✏  Message ",
            bg=PANEL, fg=CYAN, font=FONTS["subheading"],
        )
        msg_frame.pack(fill="x", pady=(0, 8))
        self._msg_text = scrolledtext.ScrolledText(
            msg_frame, height=7, wrap="word",
            bg=CARD, fg=TEXT, insertbackground=TEXT,
            font=FONTS["normal"], relief="flat",
        )
        self._msg_text.pack(fill="x", padx=10, pady=10)

        # Account selection
        acc_frame = tk.LabelFrame(
            parent, text=" 👤  Accounts (multi-select) ",
            bg=PANEL, fg=CYAN, font=FONTS["subheading"],
        )
        acc_frame.pack(fill="both", expand=True, pady=(0, 8))

        acc_btn_row = tk.Frame(acc_frame, bg=PANEL)
        acc_btn_row.pack(fill="x", padx=8, pady=(6, 2))
        make_btn(acc_btn_row, "Select All", command=self._select_all_accounts, color=CARD).pack(side="left", padx=2)
        make_btn(acc_btn_row, "🔄 Refresh",  command=self._reload_accounts,    color=CARD).pack(side="left", padx=2)

        sb_acc = tk.Scrollbar(acc_frame)
        sb_acc.pack(side="right", fill="y")
        self._acc_listbox = tk.Listbox(
            acc_frame, selectmode="extended",
            yscrollcommand=sb_acc.set,
            font=FONTS["normal"], bg=CARD, fg=TEXT,
            selectbackground=COLORS["primary_light"], selectforeground=CYAN,
            relief="flat", height=5,
        )
        self._acc_listbox.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        sb_acc.config(command=self._acc_listbox.yview)

        # Group source
        src_frame = tk.LabelFrame(
            parent, text=" 🌐  Group Source ",
            bg=PANEL, fg=CYAN, font=FONTS["subheading"],
        )
        src_frame.pack(fill="x", pady=(0, 8))
        self._group_source_var = tk.StringVar(value="account_groups")
        for text, val in [("From Account Groups", "account_groups"),
                          ("From Finder Results",  "finder_results")]:
            tk.Radiobutton(
                src_frame, text=text,
                variable=self._group_source_var, value=val,
                command=self._reload_groups,
                bg=PANEL, fg=TEXT, selectcolor=CARD, activebackground=PANEL,
                font=FONTS["normal"],
            ).pack(anchor="w", padx=12, pady=3)

        # Groups list
        grp_frame = tk.LabelFrame(
            parent, text=" 📋  Groups ",
            bg=PANEL, fg=CYAN, font=FONTS["subheading"],
        )
        grp_frame.pack(fill="both", expand=True)
        grp_btn_row = tk.Frame(grp_frame, bg=PANEL)
        grp_btn_row.pack(fill="x", padx=8, pady=(6, 2))
        make_btn(grp_btn_row, "Select All", command=self._select_all_groups, color=CARD).pack(side="left", padx=2)
        make_btn(grp_btn_row, "🔄 Refresh",  command=self._reload_groups,    color=CARD).pack(side="left", padx=2)

        sb_grp = tk.Scrollbar(grp_frame)
        sb_grp.pack(side="right", fill="y")
        self._grp_listbox = tk.Listbox(
            grp_frame, selectmode="extended",
            yscrollcommand=sb_grp.set,
            font=FONTS["normal"], bg=CARD, fg=TEXT,
            selectbackground=COLORS["primary_light"], selectforeground=CYAN,
            relief="flat", height=5,
        )
        self._grp_listbox.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        sb_grp.config(command=self._grp_listbox.yview)

    # ── Right column ─────────────────────────────────────────────────────────
    def _build_right(self, parent):
        # ── Live Mapping Table ────────────────────────────────────────────────
        map_frame = tk.LabelFrame(
            parent, text=" 📊  Live Account-Group Mapping ",
            bg=PANEL, fg=CYAN, font=FONTS["subheading"],
        )
        map_frame.pack(fill="both", expand=True, pady=(0, 8))

        # Search / filter row
        filter_row = tk.Frame(map_frame, bg=PANEL)
        filter_row.pack(fill="x", padx=8, pady=(6, 2))

        tk.Label(filter_row, text="🔍", fg=MUTED, bg=PANEL, font=FONTS["normal"]).pack(side="left")
        self._map_search_var = tk.StringVar()
        self._map_search_var.trace_add("write", lambda *_: self._apply_mapping_filter())
        tk.Entry(
            filter_row, textvariable=self._map_search_var,
            bg=CARD, fg=TEXT, insertbackground=CYAN,
            font=FONTS["small"], width=20,
        ).pack(side="left", padx=4)

        tk.Label(filter_row, text="Status:", fg=MUTED, bg=PANEL, font=FONTS["small"]).pack(side="left", padx=(8, 2))
        self._map_status_var = tk.StringVar(value="All")
        status_cb = ttk.Combobox(
            filter_row, textvariable=self._map_status_var,
            values=["All", "✅ Sent", "⏳ Sending", "❌ Failed", "🚫 Banned"],
            width=12, state="readonly",
        )
        status_cb.pack(side="left", padx=4)
        status_cb.bind("<<ComboboxSelected>>", lambda _: self._apply_mapping_filter())

        # Copy link + clear buttons
        make_btn(filter_row, "📋 Copy Link",  command=self._copy_link,    color=CARD).pack(side="right", padx=2)
        make_btn(filter_row, "🗑 Clear",       command=self._clear_mapping, color=CARD).pack(side="right", padx=2)

        # Treeview columns – two hidden ones store full link + group for copy operations
        # Visible columns: Account, Group, Status, Link, Time, Message
        # Hidden columns:  _fulllink, _fullgroup (width=0, no heading)
        ALL_COLS = ("Account", "Group", "Status", "Link", "Time", "Message", "_fulllink", "_fullgroup")
        VIS_COLS = ALL_COLS[:6]
        tree_frame = tk.Frame(map_frame, bg=PANEL)
        tree_frame.pack(fill="both", expand=True, padx=8, pady=(2, 6))

        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")

        self._map_tree = ttk.Treeview(
            tree_frame, columns=ALL_COLS, displaycolumns=VIS_COLS, show="headings",
            yscrollcommand=vsb.set, xscrollcommand=hsb.set,
            height=8, selectmode="browse",
        )
        vsb.config(command=self._map_tree.yview)
        hsb.config(command=self._map_tree.xview)

        col_widths = {
            "Account": 110, "Group": 180, "Status": 95,
            "Link": 160, "Time": 65, "Message": 180,
        }
        for col in VIS_COLS:
            self._map_tree.heading(col, text=col,
                                   command=lambda c=col: self._sort_mapping(c))
            self._map_tree.column(col, width=col_widths[col], minwidth=60, anchor="w")
        # Hidden columns – zero width, no heading needed
        for hcol in ("_fulllink", "_fullgroup"):
            self._map_tree.column(hcol, width=0, minwidth=0, stretch=False)

        self._map_tree.pack(fill="both", expand=True)

        # Color tags for mapping status
        self._map_tree.tag_configure("sent",     foreground=GREEN,  background=COLORS.get("success_light", "#003D0F"))
        self._map_tree.tag_configure("sending",  foreground=GOLD,   background=COLORS.get("warning_light", "#3D2B00"))
        self._map_tree.tag_configure("failed",   foreground=RED,    background=COLORS.get("error_light",   "#3D0015"))
        self._map_tree.tag_configure("banned",   foreground=PURPLE, background="#1A0030")
        self._map_tree.tag_configure("pending",  foreground=CYAN,   background=COLORS.get("info_light",    "#002A3D"))

        # Right-click context menu for copy
        self._ctx_menu = tk.Menu(self._map_tree, tearoff=False, bg=CARD, fg=TEXT)
        self._ctx_menu.add_command(label="📋 Copy Link",    command=self._copy_link)
        self._ctx_menu.add_command(label="📋 Copy Group",   command=self._copy_group)
        self._ctx_menu.add_command(label="📋 Copy Account", command=self._copy_account)
        self._map_tree.bind("<Button-3>", self._show_ctx_menu)

        # Sorting state
        self._sort_col = None
        self._sort_rev = False

        # ── Activity Log ──────────────────────────────────────────────────────
        log_frame = tk.LabelFrame(
            parent, text=" 📜  Activity Log (newest first) ",
            bg=PANEL, fg=CYAN, font=FONTS["subheading"],
        )
        log_frame.pack(fill="both", expand=False, pady=(0, 0))
        log_frame.config(height=180)
        log_frame.pack_propagate(False)

        sb_log = tk.Scrollbar(log_frame)
        sb_log.pack(side="right", fill="y")
        self._log_box = tk.Listbox(
            log_frame, yscrollcommand=sb_log.set,
            font=FONTS["mono"], bg=CARD, fg=TEXT,
            selectbackground=COLORS["primary_light"],
            relief="flat",
        )
        self._log_box.pack(fill="both", expand=True, padx=8, pady=8)
        sb_log.config(command=self._log_box.yview)

    # ─────────────────────────────────────────────────────────────────────────
    # ACCOUNT / GROUP HELPERS
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

    def _get_selected_accounts(self) -> list:
        return [self._accounts_data[i]["phone"] for i in self._acc_listbox.curselection()]

    def _get_selected_groups(self) -> list:
        return [self._groups_data[i] for i in self._grp_listbox.curselection()]

    # ─────────────────────────────────────────────────────────────────────────
    # MAPPING TABLE HELPERS
    # ─────────────────────────────────────────────────────────────────────────
    def _status_tag(self, status: str) -> str:
        s = status.lower()
        if "✅" in status or "sent" in s:
            return "sent"
        if "⏳" in status or "sending" in s or "floodwait" in s:
            return "sending"
        if "🚫" in status or "banned" in s or "peerflood" in s:
            return "banned"
        if "❌" in status or "failed" in s or "expired" in s or "member" in s or "slowmode" in s:
            return "failed"
        return "pending"

    def _apply_mapping_filter(self):
        search = self._map_search_var.get().lower().strip()
        status_filter = self._map_status_var.get()

        for row in self._map_tree.get_children():
            self._map_tree.delete(row)

        for entry in self._all_mapping:
            if search:
                # Use pre-computed lowercase fields when available (avoids repeated .lower())
                acct_lc = entry.get("_account_lc") or entry["account"].lower()
                grp_lc  = entry.get("_group_lc")   or entry["group"].lower()
                if search not in acct_lc and search not in grp_lc:
                    continue
            if status_filter != "All" and status_filter not in entry["status"]:
                continue
            self._insert_mapping_row(entry)

    def _insert_mapping_row(self, entry: dict):
        disp_group = (entry["group"][:35] + "…") if len(entry["group"]) > 35 else entry["group"]
        disp_link  = (entry["link"][:28]  + "…") if len(entry["link"])  > 28 else entry["link"]
        tag = self._status_tag(entry["status"])
        self._map_tree.insert(
            "", "end",
            values=(
                entry["account"], disp_group, entry["status"],
                disp_link, entry["timestamp"], entry["msg_preview"],
                # Hidden columns store full values for O(1) copy
                entry["link"], entry["group"],
            ),
            tags=(tag,),
        )

    def _update_mapping_table(self, mapping_entries: list):
        """Rebuild mapping table from latest stats entries (filtered)."""
        self._all_mapping = mapping_entries
        self._apply_mapping_filter()

    def _sort_mapping(self, col: str):
        """Sort mapping table by the given column header."""
        if self._sort_col == col:
            self._sort_rev = not self._sort_rev
        else:
            self._sort_col = col
            self._sort_rev = False
        COL_KEYS = {
            "Account": "account", "Group": "group", "Status": "status",
            "Link": "link", "Time": "timestamp", "Message": "msg_preview",
        }
        key = COL_KEYS.get(col, col.lower())
        try:
            self._all_mapping.sort(key=lambda e: e.get(key, ""), reverse=self._sort_rev)
        except Exception:
            pass
        self._apply_mapping_filter()

    def _clear_mapping(self):
        self._all_mapping = []
        for row in self._map_tree.get_children():
            self._map_tree.delete(row)

    def _selected_row_values(self) -> tuple:
        """Return all column values (including hidden) for the selected row."""
        sel = self._map_tree.selection()
        if not sel:
            return ()
        return self._map_tree.item(sel[0], "values")

    def _copy_link(self):
        vals = self._selected_row_values()
        if vals:
            # Hidden column index 6 = _fulllink
            link = vals[6] if len(vals) > 6 else vals[3]
            self.frame.clipboard_clear()
            self.frame.clipboard_append(link)
            messagebox.showinfo("Copied", f"Group link copied:\n{link}")
        else:
            messagebox.showwarning("Copy Link", "Select a row first.")

    def _copy_group(self):
        vals = self._selected_row_values()
        if vals:
            # Hidden column index 7 = _fullgroup
            grp = vals[7] if len(vals) > 7 else vals[1]
            self.frame.clipboard_clear()
            self.frame.clipboard_append(grp)

    def _copy_account(self):
        vals = self._selected_row_values()
        if vals:
            self.frame.clipboard_clear()
            self.frame.clipboard_append(vals[0])

    def _show_ctx_menu(self, event):
        try:
            row = self._map_tree.identify_row(event.y)
            if row:
                self._map_tree.selection_set(row)
                self._ctx_menu.post(event.x_root, event.y_root)
        except tk.TclError:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # BROADCAST CONTROLS
    # ─────────────────────────────────────────────────────────────────────────
    def _start(self):
        message = self._msg_text.get("1.0", "end").strip()
        if not message:
            messagebox.showwarning("Broadcast", "Enter a message first.")
            return
        accounts = self._get_selected_accounts()
        groups   = self._get_selected_groups()
        if not accounts:
            messagebox.showwarning("Broadcast", "Select at least one account.")
            return
        if not groups:
            messagebox.showwarning("Broadcast", "Select at least one group.")
            return

        self._start_btn.config(state="disabled")
        self._pause_btn.config(state="normal")
        self._resume_btn.config(state="disabled")
        self._stop_btn.config(state="normal")
        self._retry_btn.config(state="disabled")

        # Reset UI
        self._log_box.delete(0, "end")
        self._all_mapping = []
        for row in self._map_tree.get_children():
            self._map_tree.delete(row)
        for key in self._stat_vars:
            self._stat_vars[key].set("0")
        self._progress_var.set(0)
        self._pct_var.set("0%  (0/0)")
        self._speed_var.set("Speed: —")
        self._eta_var.set("ETA: —")

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

    def _retry_failed(self):
        if advanced_broadcaster.running:
            messagebox.showinfo("Retry", "Broadcast still running. Stop it first.")
            return
        self._start_btn.config(state="disabled")
        self._pause_btn.config(state="normal")
        self._stop_btn.config(state="normal")
        self._retry_btn.config(state="disabled")
        advanced_broadcaster.retry_failed(
            on_update=self._on_update,
            on_done=self._on_done,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # CALLBACKS
    # ─────────────────────────────────────────────────────────────────────────
    def _on_update(self, stats: BroadcastStats):
        def _update():
            # Stats labels
            self._stat_vars["sent"].set(str(stats.sent))
            self._stat_vars["failed"].set(str(stats.failed))
            self._stat_vars["banned"].set(str(stats.banned))
            self._stat_vars["pending"].set(str(stats.pending))
            self._stat_vars["rounds"].set(str(stats.rounds))

            # Progress bar + pct
            pct = stats.progress_pct
            total = stats._total_groups
            done  = stats.sent + stats.failed
            self._progress_var.set(pct)
            self._pct_var.set(f"{pct:.0f}%  ({done}/{total})")

            # Speed + ETA
            spd = stats.speed_msg_per_min
            eta = stats.eta_seconds
            self._speed_var.set(f"Speed: {spd:.1f} msg/min" if spd else "Speed: —")
            self._eta_var.set(f"ETA: {_fmt_eta(eta)}")

            # Mapping table
            self._update_mapping_table(list(stats.mapping_entries))

            # Activity log (newest entries are at index 0 in stats.log)
            self._log_box.delete(0, "end")
            for entry in stats.log:
                idx = self._log_box.size()
                self._log_box.insert("end", entry)
                self._log_box.itemconfig(idx, fg=_log_fg_color(entry))
            if self._log_box.size():
                self._log_box.see(0)

        self.frame.after(0, _update)

    def _on_done(self, stats: BroadcastStats):
        def _done():
            self._start_btn.config(state="normal")
            self._pause_btn.config(state="disabled")
            self._resume_btn.config(state="disabled")
            self._stop_btn.config(state="disabled")
            # Enable retry if there are failed groups
            has_failed = bool(stats and stats.failed_groups)
            self._retry_btn.config(state="normal" if has_failed else "disabled")
            if stats:
                self._stat_vars["sent"].set(str(stats.sent))
                self._stat_vars["failed"].set(str(stats.failed))
                self._stat_vars["banned"].set(str(stats.banned))
                self._stat_vars["rounds"].set(str(stats.rounds))
                pct = stats.progress_pct
                self._progress_var.set(pct)
                self._pct_var.set(f"{pct:.0f}%  ({stats.sent + stats.failed}/{stats._total_groups})")
                self._speed_var.set("Speed: —")
                self._eta_var.set("ETA: Done ✓")

        self.frame.after(0, _done)
