"""
TG PRO QUANTUM – AccountSelectorWidget

A Tkinter widget that lets the user select accounts for broadcast while
showing their health status (session valid, feature assigned, status).

Usage::

    selector = AccountSelectorWidget(parent_frame)
    selector.pack(fill="both", expand=True)

    selected = selector.get_selected()   # → list[str] of account names
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import List

from gui.styles import COLORS, FONTS

BG    = COLORS["bg_medium"]
CARD  = COLORS["bg_light"]
CYAN  = COLORS["primary"]
GREEN = COLORS["success"]
ORANGE = COLORS["warning"]
RED   = COLORS["error"]
TEXT  = COLORS["text"]
MUTED = COLORS["text_muted"]


class AccountSelectorWidget(tk.Frame):
    """
    Displays all accounts with health indicators.  The user can:
    * Select / deselect individual accounts via checkboxes
    * Filter by feature assignment
    * Use "Select All Broadcast" to quickly pick broadcast accounts
    """

    def __init__(self, parent: tk.Widget, **kwargs):
        super().__init__(parent, bg=BG, **kwargs)
        self._vars: dict[str, tk.BooleanVar] = {}
        self._build()
        self.refresh()

    # ── Build ──────────────────────────────────────────────────────────────

    def _build(self) -> None:
        # Header
        hdr = tk.Frame(self, bg=BG)
        hdr.pack(fill="x", padx=4, pady=4)

        tk.Label(hdr, text="📱 Select Accounts", fg=CYAN, bg=BG,
                 font=FONTS["heading"]).pack(side="left")

        btn_frame = tk.Frame(hdr, bg=BG)
        btn_frame.pack(side="right")

        tk.Button(btn_frame, text="✅ All Broadcast", command=self._select_broadcast,
                  bg=GREEN, fg="#000", font=FONTS["small"],
                  relief="flat", cursor="hand2", padx=6, pady=3).pack(side="left", padx=2)

        tk.Button(btn_frame, text="⬜ Clear", command=self._clear_all,
                  bg=CARD, fg=TEXT, font=FONTS["small"],
                  relief="flat", cursor="hand2", padx=6, pady=3).pack(side="left", padx=2)

        tk.Button(btn_frame, text="🔄 Refresh", command=self.refresh,
                  bg=CARD, fg=CYAN, font=FONTS["small"],
                  relief="flat", cursor="hand2", padx=6, pady=3).pack(side="left", padx=2)

        # Tree
        cols = ("Sel", "Account", "Status", "Session", "Features")
        self._tree = ttk.Treeview(self, columns=cols, show="headings", height=8)
        widths = {"Sel": 30, "Account": 140, "Status": 80, "Session": 80, "Features": 180}
        for col in cols:
            self._tree.heading(col, text=col)
            self._tree.column(col, width=widths.get(col, 100), anchor="w")
        self._tree.bind("<ButtonRelease-1>", self._on_click)

        vsb = ttk.Scrollbar(self, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._tree.pack(fill="both", expand=True, padx=4)

        # Footer counter
        self._count_lbl = tk.Label(
            self, text="0 selected", fg=MUTED, bg=BG, font=FONTS["small"]
        )
        self._count_lbl.pack(anchor="w", padx=8, pady=2)

    # ── Public API ──────────────────────────────────────────────────────────

    def get_selected(self) -> List[str]:
        """Return names of currently selected accounts."""
        return [name for name, var in self._vars.items() if var.get()]

    def refresh(self) -> None:
        """Reload account list from account_manager."""
        try:
            from core.account_manager import account_manager
            from pathlib import Path
            from core.utils import SESSIONS_DIR

            self._vars.clear()
            for item in self._tree.get_children():
                self._tree.delete(item)

            accounts = account_manager.get_all()
            for acc in accounts:
                name = acc.get("name", "?")
                status = acc.get("status", "unknown")
                features = ", ".join(acc.get("features", [])) or "—"

                session_file = SESSIONS_DIR / f"{name}.session"
                has_session = session_file.exists() and session_file.stat().st_size > 100
                session_txt = "✅ Valid" if has_session else "❌ Missing"

                is_broadcast = "broadcast" in acc.get("features", [])
                var = tk.BooleanVar(value=is_broadcast)
                self._vars[name] = var

                icon = "☑" if is_broadcast else "☐"
                status_icon = "🟢" if status == "active" else "🔴"
                tag = "active" if status == "active" else "inactive"

                self._tree.insert(
                    "", "end",
                    iid=name,
                    values=(icon, name, f"{status_icon} {status}", session_txt, features),
                    tags=(tag,),
                )

            self._tree.tag_configure("active", foreground=GREEN)
            self._tree.tag_configure("inactive", foreground=MUTED)
            self._update_count()
        except Exception as exc:
            pass  # Gracefully handle if account_manager not yet available

    # ── Event handlers ──────────────────────────────────────────────────────

    def _on_click(self, _event: tk.Event) -> None:
        """Toggle selection when user clicks a row."""
        item = self._tree.focus()
        if not item:
            return
        name = item
        if name in self._vars:
            current = self._vars[name].get()
            self._vars[name].set(not current)
            new_icon = "☑" if not current else "☐"
            values = list(self._tree.item(item, "values"))
            values[0] = new_icon
            self._tree.item(item, values=values)
        self._update_count()

    def _select_broadcast(self) -> None:
        """Select all accounts that have the broadcast feature."""
        try:
            from core.account_manager import account_manager
            broadcast_names = {a["name"] for a in account_manager.get_accounts_by_feature("broadcast")}
        except Exception:
            broadcast_names = set()

        for name, var in self._vars.items():
            selected = name in broadcast_names
            var.set(selected)
            item = name
            try:
                values = list(self._tree.item(item, "values"))
                values[0] = "☑" if selected else "☐"
                self._tree.item(item, values=values)
            except Exception:
                pass
        self._update_count()

    def _clear_all(self) -> None:
        for name, var in self._vars.items():
            var.set(False)
            try:
                values = list(self._tree.item(name, "values"))
                values[0] = "☐"
                self._tree.item(name, values=values)
            except Exception:
                pass
        self._update_count()

    def _update_count(self) -> None:
        n = len(self.get_selected())
        color = GREEN if n > 0 else ORANGE
        self._count_lbl.config(text=f"{n} account(s) selected", fg=color)


__all__ = ["AccountSelectorWidget"]
