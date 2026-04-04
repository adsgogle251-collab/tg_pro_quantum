"""
TG PRO QUANTUM – Phase 5B Account Management Page

Frame-overlay page for managing Telegram accounts (add, remove, status).
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional, List, Dict, Any

from gui.styles import COLORS, FONTS
from gui.components.vibrant_buttons import make_vibrant_btn

__all__ = ["AccountsPage"]

BG    = COLORS["bg_dark"]
PANEL = COLORS["bg_medium"]
CARD  = COLORS["bg_light"]
CYAN  = COLORS["primary"]
GREEN = COLORS["success"]
RED   = COLORS["error"]
TEXT  = COLORS["text"]
MUTED = COLORS["text_muted"]


class AccountsPage:
    """
    Account management overlay.

    Usage::

        page = AccountsPage(parent_frame, on_add_account=handler)
        page.show()
    """

    def __init__(
        self,
        parent: tk.Widget,
        on_add_account: Optional[Callable] = None,
        on_remove_account: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_refresh: Optional[Callable] = None,
    ) -> None:
        self.parent            = parent
        self.on_add_account    = on_add_account
        self.on_remove_account = on_remove_account
        self.on_refresh        = on_refresh

        self._accounts: List[Dict[str, Any]] = []

        self.frame = tk.Frame(parent, bg=BG)
        self._build()

    # ── public API ────────────────────────────────────────────────────────────

    def show(self) -> None:
        self.frame.place(relx=0, rely=0, relwidth=1, relheight=1)

    def hide(self) -> None:
        self.frame.place_forget()

    def set_accounts(self, accounts: List[Dict[str, Any]]) -> None:
        """Replace the accounts list and refresh the table."""
        self._accounts = accounts
        self._refresh_table()

    # ── build ─────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        f = self.frame

        # header
        hdr = tk.Frame(f, bg=PANEL, height=56)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="👤  Accounts", bg=PANEL, fg=CYAN,
                 font=FONTS["heading"]).pack(side="left", padx=20, pady=12)

        btn_frame = tk.Frame(hdr, bg=PANEL)
        btn_frame.pack(side="right", padx=16)
        make_vibrant_btn(btn_frame, "⟳ Refresh", preset="ghost",
                         command=self._on_refresh).pack(side="left", padx=4)
        make_vibrant_btn(btn_frame, "+ Add Account", preset="primary",
                         command=self._on_add).pack(side="left")

        # summary bar
        self._summary_var = tk.StringVar(value="Loading…")
        tk.Label(f, textvariable=self._summary_var, bg=BG, fg=MUTED,
                 font=FONTS["small"]).pack(anchor="w", padx=20, pady=(8, 4))

        # table
        table_frame = tk.Frame(f, bg=BG)
        table_frame.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        self._build_table(table_frame)

        # context menu
        self._ctx_menu = tk.Menu(f, tearoff=0, bg=CARD, fg=TEXT,
                                  activebackground=CYAN, activeforeground=BG)
        self._ctx_menu.add_command(label="Remove Account",
                                    command=self._on_remove_selected)

    def _build_table(self, parent: tk.Widget) -> None:
        cols = ("phone", "username", "status", "flood_wait",
                "messages_sent", "joined_groups", "last_used")
        self._tree = ttk.Treeview(parent, columns=cols, show="headings")
        headers = {
            "phone":         ("Phone",          130),
            "username":      ("Username",        140),
            "status":        ("Status",           90),
            "flood_wait":    ("Flood Wait",       90),
            "messages_sent": ("Msgs Sent",         90),
            "joined_groups": ("Groups",            70),
            "last_used":     ("Last Used",        150),
        }
        for col, (heading, width) in headers.items():
            self._tree.heading(col, text=heading)
            self._tree.column(col, width=width, minwidth=60)

        scroll_y = ttk.Scrollbar(parent, orient="vertical",
                                  command=self._tree.yview)
        self._tree.configure(yscrollcommand=scroll_y.set)
        scroll_y.pack(side="right", fill="y")
        self._tree.pack(fill="both", expand=True)

        self._tree.bind("<Button-3>", self._on_right_click)

        # tag colours for status
        self._tree.tag_configure("online",  foreground=GREEN)
        self._tree.tag_configure("offline", foreground=MUTED)
        self._tree.tag_configure("flood",   foreground=RED)

    def _refresh_table(self) -> None:
        self._tree.delete(*self._tree.get_children())
        online = flood = 0
        for acc in self._accounts:
            status = acc.get("status", "offline")
            tag = "online" if status == "online" else (
                "flood" if status == "flood" else "offline"
            )
            if status == "online":
                online += 1
            elif status == "flood":
                flood += 1
            self._tree.insert("", tk.END, tags=(tag,), values=(
                acc.get("phone",         "—"),
                acc.get("username",      "—"),
                status.capitalize(),
                acc.get("flood_wait",    "—"),
                acc.get("messages_sent", 0),
                acc.get("joined_groups", 0),
                acc.get("last_used",     "—"),
            ))
        total = len(self._accounts)
        self._summary_var.set(
            f"Total: {total}  |  Online: {online}  |  Flood: {flood}  |  Offline: {total - online - flood}"
        )

    # ── event handlers ────────────────────────────────────────────────────────

    def _on_add(self) -> None:
        if self.on_add_account:
            self.on_add_account()

    def _on_refresh(self) -> None:
        if self.on_refresh:
            self.on_refresh()

    def _on_right_click(self, event) -> None:
        row = self._tree.identify_row(event.y)
        if row:
            self._tree.selection_set(row)
            self._ctx_menu.post(event.x_root, event.y_root)

    def _on_remove_selected(self) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        idx = self._tree.index(sel[0])
        if idx < len(self._accounts) and self.on_remove_account:
            if messagebox.askyesno("Remove Account",
                                    "Remove this account from the system?"):
                self.on_remove_account(self._accounts[idx])
