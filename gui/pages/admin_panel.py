"""
TG PRO QUANTUM – Admin Panel Page (Desktop)

Frame-overlay page for system administration: user management,
license management, audit logs, and system statistics.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Dict, Any, List, Optional

from gui.styles import COLORS, FONTS
from gui.components.vibrant_buttons import make_vibrant_btn

__all__ = ["AdminPanelPage"]

BG    = COLORS["bg_dark"]
PANEL = COLORS["bg_medium"]
CARD  = COLORS["bg_light"]
CYAN  = COLORS["primary"]
GREEN = COLORS["success"]
TEXT  = COLORS["text"]
MUTED = COLORS["text_muted"]
RED   = COLORS["error"]
GOLD  = COLORS.get("accent", "#FFD700")

TABS = ["Users", "Licenses", "Audit Logs", "Statistics"]


class AdminPanelPage:
    """
    Admin panel overlay page with tabbed sections.

    Usage::

        page = AdminPanelPage(parent, on_suspend_user=handler, ...)
        page.show()
    """

    def __init__(
        self,
        parent: tk.Widget,
        on_suspend_user: Optional[Callable[[int], None]] = None,
        on_restore_user: Optional[Callable[[int], None]] = None,
        on_delete_user:  Optional[Callable[[int], None]] = None,
        on_create_user:  Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        self.parent          = parent
        self.on_suspend_user = on_suspend_user
        self.on_restore_user = on_restore_user
        self.on_delete_user  = on_delete_user
        self.on_create_user  = on_create_user

        self._users:      List[Dict[str, Any]] = []
        self._licenses:   List[Dict[str, Any]] = []
        self._audit_logs: List[Dict[str, Any]] = []
        self._stats:      Dict[str, Any]       = {}

        self.frame = tk.Frame(parent, bg=BG)
        self._build()

    # ── public API ────────────────────────────────────────────────────────────

    def show(self) -> None:
        self.frame.place(relx=0, rely=0, relwidth=1, relheight=1)

    def hide(self) -> None:
        self.frame.place_forget()

    def load_users(self, users: List[Dict[str, Any]]) -> None:
        self._users = users
        self._refresh_users_table()

    def load_licenses(self, licenses: List[Dict[str, Any]]) -> None:
        self._licenses = licenses
        self._refresh_licenses_table()

    def load_audit_logs(self, logs: List[Dict[str, Any]]) -> None:
        self._audit_logs = logs
        self._refresh_audit_table()

    def load_stats(self, stats: Dict[str, Any]) -> None:
        self._stats = stats
        self._refresh_stats()

    # ── build ─────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        f = self.frame

        # header
        hdr = tk.Frame(f, bg=PANEL, height=56)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="⚙ Admin Panel", bg=PANEL, fg=GOLD,
                 font=FONTS.get("title", ("Arial", 14, "bold"))).pack(side="left", padx=16, pady=16)
        tk.Label(hdr, text="Admin access required", bg=PANEL, fg=RED,
                 font=FONTS.get("small", ("Arial", 10))).pack(side="right", padx=16, pady=16)

        # tab bar
        tab_bar = tk.Frame(f, bg=PANEL, height=40)
        tab_bar.pack(fill="x")
        tab_bar.pack_propagate(False)
        self._tab_btns: Dict[str, tk.Label] = {}
        self._active_tab = tk.StringVar(value=TABS[0])

        for tab in TABS:
            lbl = tk.Label(
                tab_bar, text=tab, bg=PANEL, fg=MUTED, cursor="hand2",
                font=FONTS.get("body", ("Arial", 11)), padx=14,
            )
            lbl.pack(side="left", fill="y")
            lbl.bind("<Button-1>", lambda e, t=tab: self._switch_tab(t))
            self._tab_btns[tab] = lbl

        # content area
        self._content = tk.Frame(f, bg=BG)
        self._content.pack(fill="both", expand=True)

        # build all tab panels
        self._panels: Dict[str, tk.Frame] = {}
        self._build_users_tab()
        self._build_licenses_tab()
        self._build_audit_tab()
        self._build_stats_tab()

        self._switch_tab(TABS[0])

    # ── tab switch ────────────────────────────────────────────────────────────

    def _switch_tab(self, tab: str) -> None:
        self._active_tab.set(tab)
        for name, btn in self._tab_btns.items():
            btn.configure(fg=CYAN if name == tab else MUTED)
        for name, panel in self._panels.items():
            if name == tab:
                panel.pack(fill="both", expand=True)
            else:
                panel.pack_forget()

    # ── Users tab ─────────────────────────────────────────────────────────────

    def _build_users_tab(self) -> None:
        panel = tk.Frame(self._content, bg=BG)
        self._panels["Users"] = panel

        # toolbar
        toolbar = tk.Frame(panel, bg=BG)
        toolbar.pack(fill="x", padx=16, pady=12)
        tk.Label(toolbar, text="Users", bg=BG, fg=TEXT,
                 font=FONTS.get("subtitle", ("Arial", 12, "bold"))).pack(side="left")

        # table
        cols = ("ID", "Name", "Email", "Role", "Status", "Plan")
        tree = ttk.Treeview(panel, columns=cols, show="headings", selectmode="browse")
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=100 if col != "Email" else 180)
        tree.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        self._users_tree = tree

        # action buttons
        btn_row = tk.Frame(panel, bg=BG)
        btn_row.pack(fill="x", padx=16, pady=(0, 12))
        make_vibrant_btn(btn_row, text="Suspend",  command=self._suspend_selected,  color=GOLD,  width=10).pack(side="left", padx=4)
        make_vibrant_btn(btn_row, text="Restore",  command=self._restore_selected,  color=GREEN, width=10).pack(side="left", padx=4)
        make_vibrant_btn(btn_row, text="Delete",   command=self._delete_selected,   color=RED,   width=10).pack(side="left", padx=4)

    def _refresh_users_table(self) -> None:
        tree = self._users_tree
        for row in tree.get_children():
            tree.delete(row)
        for u in self._users:
            role = "Admin" if u.get("is_admin") else "User"
            tree.insert("", "end", iid=str(u.get("id", "")), values=(
                u.get("id", ""),
                u.get("name", ""),
                u.get("email", ""),
                role,
                u.get("status", ""),
                u.get("plan_type", ""),
            ))

    def _get_selected_user_id(self) -> Optional[int]:
        sel = self._users_tree.selection()
        if not sel:
            messagebox.showwarning("Selection", "Please select a user first.")
            return None
        return int(sel[0])

    def _suspend_selected(self) -> None:
        uid = self._get_selected_user_id()
        if uid and self.on_suspend_user:
            self.on_suspend_user(uid)

    def _restore_selected(self) -> None:
        uid = self._get_selected_user_id()
        if uid and self.on_restore_user:
            self.on_restore_user(uid)

    def _delete_selected(self) -> None:
        uid = self._get_selected_user_id()
        if uid:
            if messagebox.askyesno("Delete User", f"Permanently delete user #{uid}?"):
                if self.on_delete_user:
                    self.on_delete_user(uid)

    # ── Licenses tab ──────────────────────────────────────────────────────────

    def _build_licenses_tab(self) -> None:
        panel = tk.Frame(self._content, bg=BG)
        self._panels["Licenses"] = panel

        tk.Label(panel, text="Licenses", bg=BG, fg=TEXT,
                 font=FONTS.get("subtitle", ("Arial", 12, "bold"))).pack(anchor="w", padx=16, pady=12)

        cols = ("ID", "Key (preview)", "Tier", "Status", "Client", "Expires")
        tree = ttk.Treeview(panel, columns=cols, show="headings", selectmode="browse")
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=120)
        tree.column("Key (preview)", width=200)
        tree.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self._licenses_tree = tree

    def _refresh_licenses_table(self) -> None:
        tree = self._licenses_tree
        for row in tree.get_children():
            tree.delete(row)
        for lic in self._licenses:
            key = lic.get("key", "")
            preview = f"{key[:8]}..." if key else ""
            tree.insert("", "end", values=(
                lic.get("id", ""),
                preview,
                lic.get("tier", ""),
                lic.get("status", ""),
                lic.get("client_id", ""),
                lic.get("expires_at", ""),
            ))

    # ── Audit Logs tab ────────────────────────────────────────────────────────

    def _build_audit_tab(self) -> None:
        panel = tk.Frame(self._content, bg=BG)
        self._panels["Audit Logs"] = panel

        tk.Label(panel, text="Audit Logs", bg=BG, fg=TEXT,
                 font=FONTS.get("subtitle", ("Arial", 12, "bold"))).pack(anchor="w", padx=16, pady=12)

        cols = ("ID", "Date", "User", "Action", "Resource", "Details")
        tree = ttk.Treeview(panel, columns=cols, show="headings", selectmode="browse")
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=110)
        tree.column("Details", width=220)
        tree.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self._audit_tree = tree

    def _refresh_audit_table(self) -> None:
        tree = self._audit_tree
        for row in tree.get_children():
            tree.delete(row)
        for log in self._audit_logs:
            tree.insert("", "end", values=(
                log.get("id", ""),
                str(log.get("created_at", ""))[:19],
                log.get("client_id", ""),
                log.get("action", ""),
                log.get("resource_type", ""),
                str(log.get("details", "") or ""),
            ))

    # ── Statistics tab ────────────────────────────────────────────────────────

    def _build_stats_tab(self) -> None:
        panel = tk.Frame(self._content, bg=BG)
        self._panels["Statistics"] = panel

        tk.Label(panel, text="System Statistics", bg=BG, fg=TEXT,
                 font=FONTS.get("subtitle", ("Arial", 12, "bold"))).pack(anchor="w", padx=16, pady=12)

        self._stats_frame = tk.Frame(panel, bg=BG)
        self._stats_frame.pack(fill="both", expand=True, padx=16, pady=8)

    def _refresh_stats(self) -> None:
        for w in self._stats_frame.winfo_children():
            w.destroy()
        stat_items = [
            ("Total Users",     self._stats.get("total_users", 0)),
            ("Active Users",    self._stats.get("active_users", 0)),
            ("Suspended Users", self._stats.get("suspended_users", 0)),
            ("Total Campaigns", self._stats.get("total_campaigns", 0)),
            ("Total Accounts",  self._stats.get("total_accounts", 0)),
            ("Total Licenses",  self._stats.get("total_licenses", 0)),
            ("Audit Log Entries", self._stats.get("total_audit_logs", 0)),
            ("System Health",   self._stats.get("system_health", "unknown")),
        ]
        grid = tk.Frame(self._stats_frame, bg=BG)
        grid.pack(fill="both", expand=True)
        for i, (label, value) in enumerate(stat_items):
            card = tk.Frame(grid, bg=PANEL, relief="flat", bd=0)
            card.grid(row=i // 2, column=i % 2, padx=8, pady=6, sticky="nsew")
            grid.columnconfigure(i % 2, weight=1)
            tk.Label(card, text=str(value), bg=PANEL, fg=CYAN,
                     font=FONTS.get("title", ("Arial", 18, "bold"))).pack(pady=(12, 4))
            tk.Label(card, text=label, bg=PANEL, fg=MUTED,
                     font=FONTS.get("small", ("Arial", 10))).pack(pady=(0, 12))
