"""
TG PRO QUANTUM – Profile Page (Desktop)

Frame-overlay page showing user profile information and allowing
password changes and API key management.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import Callable, Dict, Any, Optional

from gui.styles import COLORS, FONTS
from gui.components.vibrant_buttons import make_vibrant_btn

__all__ = ["ProfilePage"]

BG    = COLORS["bg_dark"]
PANEL = COLORS["bg_medium"]
CARD  = COLORS["bg_light"]
CYAN  = COLORS["primary"]
GREEN = COLORS["success"]
TEXT  = COLORS["text"]
MUTED = COLORS["text_muted"]
RED   = COLORS["error"]


class ProfilePage:
    """
    User profile overlay page.

    Usage::

        page = ProfilePage(parent, user_data={...}, on_update=handler, on_change_password=handler)
        page.show()
    """

    def __init__(
        self,
        parent: tk.Widget,
        user_data: Optional[Dict[str, Any]] = None,
        on_update: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_change_password: Optional[Callable[[str, str], None]] = None,
        on_regenerate_api_key: Optional[Callable[[], None]] = None,
    ) -> None:
        self.parent                = parent
        self._user                 = user_data or {}
        self.on_update             = on_update
        self.on_change_password    = on_change_password
        self.on_regenerate_api_key = on_regenerate_api_key

        self.frame = tk.Frame(parent, bg=BG)
        self._build()

    # ── public API ────────────────────────────────────────────────────────────

    def show(self) -> None:
        self.frame.place(relx=0, rely=0, relwidth=1, relheight=1)

    def hide(self) -> None:
        self.frame.place_forget()

    def load_user(self, user_data: Dict[str, Any]) -> None:
        """Populate the form with user data from the API."""
        self._user = user_data
        self._name_var.set(user_data.get("name", ""))
        self._email_var.set(user_data.get("email", ""))
        self._plan_var.set(user_data.get("plan_type", "starter"))
        api_key = user_data.get("api_key") or ""
        preview = f"{api_key[:8]}..." if api_key else "(none)"
        self._api_key_lbl.configure(text=preview)

    # ── build ─────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        f = self.frame

        # ── header ─────────────────────────────────────────────────────────
        hdr = tk.Frame(f, bg=PANEL, height=56)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="My Profile", bg=PANEL, fg=TEXT,
                 font=FONTS.get("title", ("Arial", 14, "bold"))).pack(side="left", padx=16, pady=16)

        # ── scrollable body ─────────────────────────────────────────────────
        canvas = tk.Canvas(f, bg=BG, highlightthickness=0)
        scroll = tk.Scrollbar(f, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)

        body = tk.Frame(canvas, bg=BG)
        body_id = canvas.create_window((0, 0), window=body, anchor="nw")

        def _on_frame_resize(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(body_id, width=event.width if event else canvas.winfo_width())

        body.bind("<Configure>", _on_frame_resize)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(body_id, width=e.width))

        pad = {"padx": 24, "pady": 6}

        # ── Profile Info section ────────────────────────────────────────────
        self._section(body, "Profile Information")

        self._name_var  = tk.StringVar(value=self._user.get("name", ""))
        self._email_var = tk.StringVar(value=self._user.get("email", ""))
        self._plan_var  = tk.StringVar(value=self._user.get("plan_type", "starter"))

        self._field(body, "Name",       self._name_var,  **pad)
        self._field(body, "Email",      self._email_var, **pad)
        self._field(body, "Plan",       self._plan_var,  editable=False, **pad)

        make_vibrant_btn(
            body, text="Update Profile",
            command=self._handle_update,
            color=CYAN, width=18,
        ).pack(padx=24, pady=(8, 16), anchor="w")

        # ── Change Password section ─────────────────────────────────────────
        self._section(body, "Change Password")

        self._cur_pw  = tk.StringVar()
        self._new_pw  = tk.StringVar()
        self._conf_pw = tk.StringVar()

        self._field(body, "Current Password", self._cur_pw,  show="*", **pad)
        self._field(body, "New Password",      self._new_pw,  show="*", **pad)
        self._field(body, "Confirm Password",  self._conf_pw, show="*", **pad)

        make_vibrant_btn(
            body, text="Change Password",
            command=self._handle_change_password,
            color=GREEN, width=18,
        ).pack(padx=24, pady=(8, 16), anchor="w")

        # ── API Key section ─────────────────────────────────────────────────
        self._section(body, "API Key")

        key_row = tk.Frame(body, bg=BG)
        key_row.pack(fill="x", **pad)
        tk.Label(key_row, text="Current Key:", bg=BG, fg=MUTED,
                 font=FONTS.get("body", ("Arial", 11))).pack(side="left")
        self._api_key_lbl = tk.Label(key_row, text="(none)", bg=BG, fg=TEXT,
                                     font=FONTS.get("body", ("Arial", 11)))
        self._api_key_lbl.pack(side="left", padx=8)

        make_vibrant_btn(
            body, text="Regenerate API Key",
            command=self._handle_regenerate_key,
            color=RED, width=22,
        ).pack(padx=24, pady=(8, 24), anchor="w")

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _section(parent: tk.Widget, title: str) -> None:
        sep = tk.Frame(parent, bg=COLORS.get("bg_light", "#252D4A"), height=1)
        sep.pack(fill="x", padx=24, pady=(16, 8))
        tk.Label(parent, text=title, bg=BG, fg=CYAN,
                 font=FONTS.get("subtitle", ("Arial", 12, "bold"))).pack(anchor="w", padx=24)

    def _field(
        self,
        parent: tk.Widget,
        label: str,
        var: tk.Variable,
        editable: bool = True,
        show: str = "",
        **pack_kwargs,
    ) -> None:
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", **pack_kwargs)
        tk.Label(row, text=label, bg=BG, fg=MUTED, width=18, anchor="w",
                 font=FONTS.get("body", ("Arial", 11))).pack(side="left")
        state = "normal" if editable else "readonly"
        entry = tk.Entry(row, textvariable=var, bg=PANEL, fg=TEXT, relief="flat",
                         font=FONTS.get("body", ("Arial", 11)), show=show,
                         state=state, insertbackground=TEXT)
        entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 8))

    # ── event handlers ────────────────────────────────────────────────────────

    def _handle_update(self) -> None:
        data = {"name": self._name_var.get(), "email": self._email_var.get()}
        if self.on_update:
            self.on_update(data)
        else:
            messagebox.showinfo("Profile", "Profile update saved locally.")

    def _handle_change_password(self) -> None:
        cur  = self._cur_pw.get()
        new  = self._new_pw.get()
        conf = self._conf_pw.get()
        if not cur or not new:
            messagebox.showerror("Error", "Current and new passwords are required.")
            return
        if new != conf:
            messagebox.showerror("Error", "New password and confirmation do not match.")
            return
        if len(new) < 8:
            messagebox.showerror("Error", "New password must be at least 8 characters.")
            return
        if self.on_change_password:
            self.on_change_password(cur, new)
        else:
            self._cur_pw.set("")
            self._new_pw.set("")
            self._conf_pw.set("")
            messagebox.showinfo("Password", "Password changed successfully.")

    def _handle_regenerate_key(self) -> None:
        confirmed = messagebox.askyesno(
            "Regenerate API Key",
            "Regenerating the API key will revoke the current key.\nContinue?",
        )
        if confirmed:
            if self.on_regenerate_api_key:
                self.on_regenerate_api_key()
            else:
                messagebox.showinfo("API Key", "API key regenerated.")
