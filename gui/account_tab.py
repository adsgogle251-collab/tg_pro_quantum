"""
gui/account_tab.py - Add accounts via OTP, list and manage them
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading

from gui.styles import COLORS, FONTS, make_btn
from core.account import (
    list_accounts, delete_account, check_account_health,
    send_otp, verify_otp, run_async,
)

BG    = COLORS["bg_dark"]
PANEL = COLORS["bg_medium"]
CARD  = COLORS["bg_light"]
CYAN  = COLORS["primary"]
GREEN = COLORS["success"]
RED   = COLORS["error"]
TEXT  = COLORS["text"]
MUTED = COLORS["text_muted"]
ORANGE = COLORS["warning"]

STATUS_COLORS = {
    "active":  GREEN,
    "expired": ORANGE,
    "error":   RED,
}


class AccountTab:
    title = "👤 Accounts"

    def __init__(self, parent, main_window=None):
        self.parent = parent
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        self._build()
        self._refresh()

    # ─────────────────────────────────────────────────────────────────────────
    def _build(self):
        outer = tk.Frame(self.frame, bg=BG)
        outer.pack(fill="both", expand=True, padx=20, pady=20)

        # Title row
        hdr = tk.Frame(outer, bg=BG)
        hdr.pack(fill="x", pady=(0, 12))
        tk.Label(hdr, text="👤 Account Manager",
                 font=FONTS["heading_large"], fg=CYAN, bg=BG).pack(side="left")

        btn_row = tk.Frame(hdr, bg=BG)
        btn_row.pack(side="right")
        make_btn(btn_row, "➕ Add Account", command=self._add_account,
                 color=GREEN, fg="#000").pack(side="left", padx=4)
        make_btn(btn_row, "🔄 Refresh", command=self._refresh,
                 color=CYAN, fg="#000").pack(side="left", padx=4)
        make_btn(btn_row, "🩺 Health Check", command=self._health_check,
                 color=ORANGE, fg="#000").pack(side="left", padx=4)
        make_btn(btn_row, "🗑️ Delete", command=self._delete,
                 color=RED).pack(side="left", padx=4)

        # Status bar
        self._status_var = tk.StringVar(value="")
        tk.Label(outer, textvariable=self._status_var,
                 font=FONTS["normal"], fg=GREEN, bg=BG).pack(anchor="w", pady=(0, 6))

        # Table
        cols = ("Name", "Phone", "Status", "Session", "Created")
        self._tree = ttk.Treeview(outer, columns=cols, show="headings", height=20)
        widths = {"Name": 160, "Phone": 130, "Status": 90, "Session": 260, "Created": 150}
        for c in cols:
            self._tree.heading(c, text=c)
            self._tree.column(c, width=widths[c], anchor="center")
        self._tree.tag_configure("active",  foreground=GREEN)
        self._tree.tag_configure("expired", foreground=ORANGE)
        self._tree.tag_configure("error",   foreground=RED)

        sb = ttk.Scrollbar(outer, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)

        frame_tree = tk.Frame(outer, bg=BG)
        frame_tree.pack(fill="both", expand=True)
        self._tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    # ─────────────────────────────────────────────────────────────────────────
    def _refresh(self):
        for row in self._tree.get_children():
            self._tree.delete(row)
        accounts = list_accounts()
        for acc in accounts:
            status = acc.get("status", "active")
            sf = acc.get("session_file") or ""
            created = (acc.get("created_at") or "")[:16]
            self._tree.insert("", "end",
                values=(acc["name"], acc["phone"], status, sf, created),
                tags=(status,))
        self._status_var.set(f"Loaded {len(accounts)} accounts.")

    def _selected_phone(self) -> str | None:
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select an account first.")
            return None
        return self._tree.item(sel[0], "values")[1]

    # ─────────────────────────────────────────────────────────────────────────
    # OTP Add Account dialog
    # ─────────────────────────────────────────────────────────────────────────
    def _add_account(self):
        OTPDialog(self.frame, on_success=self._refresh)

    # ─────────────────────────────────────────────────────────────────────────
    def _delete(self):
        phone = self._selected_phone()
        if not phone:
            return
        if not messagebox.askyesno("Confirm", f"Delete account {phone}?"):
            return
        delete_account(phone)
        self._status_var.set(f"Deleted {phone}.")
        self._refresh()

    def _health_check(self):
        phone = self._selected_phone()
        if not phone:
            return
        self._status_var.set(f"Checking {phone}...")

        def do_check():
            status, msg = run_async(check_account_health(phone))
            self.frame.after(0, lambda: self._status_var.set(f"{phone}: {msg}"))
            self.frame.after(0, self._refresh)

        threading.Thread(target=do_check, daemon=True).start()


# ─────────────────────────────────────────────────────────────────────────────
# OTP Login Dialog
# ─────────────────────────────────────────────────────────────────────────────

class OTPDialog(tk.Toplevel):
    """Two-step dialog: enter phone → get OTP → verify."""

    def __init__(self, parent, on_success=None):
        super().__init__(parent)
        self.on_success = on_success
        self.title("Add Telegram Account")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.grab_set()
        self._step = "phone"  # or "otp" or "2fa"
        self._build()
        self.update_idletasks()
        # Center
        w, h = 420, 360
        x = self.winfo_screenwidth()  // 2 - w // 2
        y = self.winfo_screenheight() // 2 - h // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self):
        self._container = tk.Frame(self, bg=BG)
        self._container.pack(fill="both", expand=True, padx=24, pady=24)

        tk.Label(self._container, text="Add Telegram Account",
                 font=FONTS["heading"], fg=CYAN, bg=BG).pack(pady=(0, 16))

        # Phone
        tk.Label(self._container, text="Phone number (with country code):",
                 font=FONTS["normal"], fg=TEXT, bg=BG).pack(anchor="w")
        self._phone_var = tk.StringVar()
        self._phone_entry = tk.Entry(
            self._container, textvariable=self._phone_var,
            bg=CARD, fg=TEXT, insertbackground=TEXT,
            font=FONTS["normal"], width=30, relief="flat"
        )
        self._phone_entry.pack(fill="x", pady=(4, 12))
        self._phone_entry.focus()

        # Display name
        tk.Label(self._container, text="Display name (optional):",
                 font=FONTS["normal"], fg=TEXT, bg=BG).pack(anchor="w")
        self._name_var = tk.StringVar()
        tk.Entry(
            self._container, textvariable=self._name_var,
            bg=CARD, fg=TEXT, insertbackground=TEXT,
            font=FONTS["normal"], width=30, relief="flat"
        ).pack(fill="x", pady=(4, 12))

        # OTP frame (hidden initially)
        self._otp_frame = tk.Frame(self._container, bg=BG)
        tk.Label(self._otp_frame, text="Enter OTP code sent to your phone:",
                 font=FONTS["normal"], fg=TEXT, bg=BG).pack(anchor="w")
        self._otp_var = tk.StringVar()
        self._otp_entry = tk.Entry(
            self._otp_frame, textvariable=self._otp_var,
            bg=CARD, fg=TEXT, insertbackground=TEXT,
            font=FONTS["normal"], width=20, relief="flat"
        )
        self._otp_entry.pack(fill="x", pady=(4, 12))

        # 2FA frame (hidden initially)
        self._twofa_frame = tk.Frame(self._container, bg=BG)
        tk.Label(self._twofa_frame, text="2FA Password:",
                 font=FONTS["normal"], fg=TEXT, bg=BG).pack(anchor="w")
        self._pass_var = tk.StringVar()
        tk.Entry(
            self._twofa_frame, textvariable=self._pass_var,
            show="*",
            bg=CARD, fg=TEXT, insertbackground=TEXT,
            font=FONTS["normal"], width=30, relief="flat"
        ).pack(fill="x", pady=(4, 12))

        # Status
        self._status_var = tk.StringVar(value="")
        tk.Label(
            self._container, textvariable=self._status_var,
            font=FONTS["small"], fg=GREEN, bg=BG, wraplength=370
        ).pack(anchor="w", pady=(0, 8))

        # Button row
        btn_row = tk.Frame(self._container, bg=BG)
        btn_row.pack(fill="x")
        self._action_btn = make_btn(
            btn_row, "📤 Send OTP", command=self._on_action,
            color=CYAN, fg="#000"
        )
        self._action_btn.pack(side="left", padx=(0, 8))
        make_btn(btn_row, "Cancel", command=self.destroy,
                 color=CARD).pack(side="left")

    def _on_action(self):
        if self._step == "phone":
            self._do_send_otp()
        elif self._step == "otp":
            self._do_verify_otp()
        elif self._step == "2fa":
            self._do_verify_2fa()

    def _do_send_otp(self):
        phone = self._phone_var.get().strip()
        if not phone:
            messagebox.showwarning("Missing", "Enter phone number.", parent=self)
            return
        self._status_var.set("Sending OTP...")
        self._action_btn.config(state="disabled")

        def task():
            ok, msg = run_async(send_otp(phone))
            def after():
                self._action_btn.config(state="normal")
                if not ok:
                    self._status_var.set(f"❌ {msg}")
                    return
                if msg == "already_authorized":
                    # Already logged in — save directly
                    name = self._name_var.get().strip() or phone
                    from core.account import _upsert_account, _session_path
                    sf = _session_path(phone) + ".session"
                    _upsert_account(name, phone, sf, "active")
                    self._status_var.set(f"✅ Account {name} added (already authorized).")
                    self.after(1200, self._finish)
                    return
                # Show OTP field
                self._step = "otp"
                self._otp_frame.pack(fill="x", pady=(0, 8))
                self._otp_entry.focus()
                self._action_btn.config(text="✅ Verify OTP")
                self._status_var.set("✅ OTP sent! Check your phone.")
            self.after(0, after)

        threading.Thread(target=task, daemon=True).start()

    def _do_verify_otp(self):
        phone = self._phone_var.get().strip()
        code  = self._otp_var.get().strip()
        name  = self._name_var.get().strip()
        if not code:
            messagebox.showwarning("Missing", "Enter OTP code.", parent=self)
            return
        self._status_var.set("Verifying...")
        self._action_btn.config(state="disabled")

        def task():
            ok, msg = run_async(verify_otp(phone, code, name))
            def after():
                self._action_btn.config(state="normal")
                if not ok:
                    if msg == "2FA_required":
                        self._step = "2fa"
                        self._twofa_frame.pack(fill="x", pady=(0, 8))
                        self._action_btn.config(text="🔓 Verify 2FA")
                        self._status_var.set("🔐 2FA password required.")
                    else:
                        self._status_var.set(f"❌ {msg}")
                    return
                self._status_var.set(f"✅ {msg}")
                self.after(1200, self._finish)
            self.after(0, after)

        threading.Thread(target=task, daemon=True).start()

    def _do_verify_2fa(self):
        phone    = self._phone_var.get().strip()
        code     = self._otp_var.get().strip()
        name     = self._name_var.get().strip()
        password = self._pass_var.get().strip()
        if not password:
            messagebox.showwarning("Missing", "Enter 2FA password.", parent=self)
            return
        self._status_var.set("Verifying 2FA...")
        self._action_btn.config(state="disabled")

        def task():
            ok, msg = run_async(verify_otp(phone, code, name, password))
            def after():
                self._action_btn.config(state="normal")
                if not ok:
                    self._status_var.set(f"❌ {msg}")
                    return
                self._status_var.set(f"✅ {msg}")
                self.after(1200, self._finish)
            self.after(0, after)

        threading.Thread(target=task, daemon=True).start()

    def _finish(self):
        if self.on_success:
            self.on_success()
        self.destroy()
