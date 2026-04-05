"""
TG PRO QUANTUM - OTP Setup Dialog (Sprint 3)

Tkinter dialog for enabling TOTP 2FA on a Telegram account.

Flow:
  1. Call /accounts/{id}/enable-otp → get secret, provisioning_uri, backup_codes
  2. Display the secret (manual entry) and a text-mode QR URL
  3. User enters first code → /accounts/{id}/verify-otp
  4. On success display backup codes for the user to save
"""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, List, Optional

import requests

_API_BASE = "http://localhost:8000/api/v1"
COLORS = {
    "bg_dark":   "#0A0E27",
    "bg_medium": "#1A1F3A",
    "bg_light":  "#252D4A",
    "primary":   "#00D9FF",
    "success":   "#00FF41",
    "error":     "#FF006E",
    "warning":   "#FFB800",
    "text":      "#E0E0FF",
    "muted":     "#9099B7",
}


def _get_token() -> Optional[str]:
    try:
        from core.state_manager import state_manager  # type: ignore
        return state_manager.get("access_token")
    except Exception:
        return None


def _api_headers() -> dict:
    token = _get_token()
    return {"Authorization": f"Bearer {token}"} if token else {}


def _post(path: str, json_data: dict | None = None) -> dict:
    url = f"{_API_BASE}{path}"
    resp = requests.post(url, json=json_data, headers=_api_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()


class OTPSetupDialog(tk.Toplevel):
    """Step-by-step TOTP setup dialog for a single TelegramAccount."""

    def __init__(self, parent, account_id: int, account_phone: str = "",
                 on_enabled: Optional[Callable] = None):
        super().__init__(parent)
        self.account_id = account_id
        self.account_phone = account_phone
        self.on_enabled = on_enabled
        self._setup_data: Optional[dict] = None

        self.title("🔐 Enable Two-Factor Authentication")
        self.geometry("480x500")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg_dark"])
        self._show_step_init()

    # ── Step 0: init ────────────────────────────────────────────────────────

    def _show_step_init(self):
        self._clear()
        tk.Label(self, text="🔐", font=("Segoe UI", 36), bg=COLORS["bg_dark"],
                 fg=COLORS["primary"]).pack(pady=(30, 8))
        tk.Label(self, text="Enable Two-Factor Authentication",
                 font=("Segoe UI", 13, "bold"), fg=COLORS["text"],
                 bg=COLORS["bg_dark"]).pack()
        tk.Label(
            self,
            text=(
                "Secure your account with a TOTP authenticator app\n"
                "(Google Authenticator, Authy, 2FAS, etc.)"
            ),
            font=("Segoe UI", 10), fg=COLORS["muted"], bg=COLORS["bg_dark"],
            justify="center",
        ).pack(pady=(8, 24))

        self._status_var = tk.StringVar()
        tk.Label(self, textvariable=self._status_var, fg=COLORS["error"],
                 bg=COLORS["bg_dark"], font=("Segoe UI", 9)).pack()

        tk.Button(
            self, text="Enable 2FA", command=self._do_enable,
            bg=COLORS["primary"], fg=COLORS["bg_dark"],
            font=("Segoe UI", 11, "bold"), relief="flat", width=20, cursor="hand2",
        ).pack(pady=12)

    def _do_enable(self):
        self._status_var.set("Setting up…")
        def worker():
            try:
                data = _post(f"/accounts/{self.account_id}/enable-otp")
                self._setup_data = data
                self.after(0, self._show_step_scan)
            except Exception as exc:
                self.after(0, lambda: self._status_var.set(str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    # ── Step 1: scan ────────────────────────────────────────────────────────

    def _show_step_scan(self):
        self._clear()
        data = self._setup_data

        tk.Label(self, text="Scan or Enter Secret",
                 font=("Segoe UI", 13, "bold"), fg=COLORS["text"],
                 bg=COLORS["bg_dark"]).pack(pady=(20, 10))

        # Secret box
        secret_frame = tk.Frame(self, bg=COLORS["bg_light"])
        secret_frame.pack(padx=30, fill="x")
        tk.Label(secret_frame, text="Secret key:", fg=COLORS["muted"],
                 bg=COLORS["bg_light"], font=("Segoe UI", 9)).pack(anchor="w", padx=8, pady=(6, 0))
        secret_var = tk.StringVar(value=data.get("secret", ""))
        tk.Entry(secret_frame, textvariable=secret_var, state="readonly",
                 font=("Consolas", 11), bg=COLORS["bg_light"], fg=COLORS["primary"],
                 relief="flat", readonlybackground=COLORS["bg_light"]).pack(
            padx=8, pady=(0, 6), fill="x")

        # QR code URL hint
        uri = data.get("provisioning_uri", "")
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={requests.utils.quote(uri)}"
        tk.Label(self, text="QR code URL (open in browser):",
                 fg=COLORS["muted"], bg=COLORS["bg_dark"],
                 font=("Segoe UI", 9)).pack(anchor="w", padx=30, pady=(12, 2))
        qr_entry = tk.Entry(self, font=("Consolas", 8), bg=COLORS["bg_light"],
                            fg=COLORS["muted"], relief="flat", width=56)
        qr_entry.insert(0, qr_url)
        qr_entry.configure(state="readonly")
        qr_entry.pack(padx=30, fill="x")

        # Code entry
        tk.Label(self, text="Enter the 6-digit code from your app:",
                 fg=COLORS["text"], bg=COLORS["bg_dark"],
                 font=("Segoe UI", 10)).pack(pady=(16, 4))
        self._code_var = tk.StringVar()
        code_entry = tk.Entry(self, textvariable=self._code_var, font=("Consolas", 16),
                              bg=COLORS["bg_light"], fg=COLORS["primary"],
                              insertbackground=COLORS["primary"], relief="flat",
                              width=10, justify="center")
        code_entry.pack(pady=4)
        code_entry.focus_set()

        self._scan_status = tk.StringVar()
        tk.Label(self, textvariable=self._scan_status, fg=COLORS["error"],
                 bg=COLORS["bg_dark"], font=("Segoe UI", 9)).pack()

        tk.Button(
            self, text="Verify & Activate", command=self._do_verify,
            bg=COLORS["primary"], fg=COLORS["bg_dark"],
            font=("Segoe UI", 11, "bold"), relief="flat", width=20, cursor="hand2",
        ).pack(pady=12)

    def _do_verify(self):
        code = self._code_var.get().strip()
        if len(code) < 6:
            self._scan_status.set("Enter a 6-digit code")
            return
        self._scan_status.set("Verifying…")
        def worker():
            try:
                resp = _post(f"/accounts/{self.account_id}/verify-otp", json_data={"code": code})
                if resp.get("verified"):
                    backup = self._setup_data.get("backup_codes", [])
                    self.after(0, lambda: self._show_step_backup(backup))
                else:
                    self.after(0, lambda: self._scan_status.set("Code is incorrect. Try again."))
            except Exception as exc:
                self.after(0, lambda: self._scan_status.set(str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    # ── Step 2: backup codes ─────────────────────────────────────────────────

    def _show_step_backup(self, backup_codes: List[str]):
        self._clear()
        tk.Label(self, text="✅ 2FA Enabled!",
                 font=("Segoe UI", 14, "bold"), fg=COLORS["success"],
                 bg=COLORS["bg_dark"]).pack(pady=(20, 6))
        tk.Label(
            self,
            text="Save these backup codes now – they won't be shown again!",
            font=("Segoe UI", 9), fg=COLORS["warning"], bg=COLORS["bg_dark"],
            wraplength=420, justify="center",
        ).pack(pady=(0, 12))

        # Grid of codes
        grid = tk.Frame(self, bg=COLORS["bg_medium"])
        grid.pack(padx=30, fill="x")
        for i, code in enumerate(backup_codes):
            row_i, col_i = divmod(i, 2)
            tk.Label(grid, text=code, font=("Consolas", 11),
                     fg=COLORS["text"], bg=COLORS["bg_light"],
                     relief="flat", padx=12, pady=6).grid(
                row=row_i, column=col_i, padx=4, pady=3, sticky="ew")
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        def copy_all():
            self.clipboard_clear()
            self.clipboard_append("\n".join(backup_codes))
            messagebox.showinfo("Copied", "Backup codes copied to clipboard", parent=self)

        btn_frame = tk.Frame(self, bg=COLORS["bg_dark"])
        btn_frame.pack(pady=16, padx=30, fill="x")
        tk.Button(btn_frame, text="📋 Copy All", command=copy_all,
                  bg=COLORS["bg_light"], fg=COLORS["text"], relief="flat",
                  cursor="hand2", width=14).pack(side="left")
        tk.Button(btn_frame, text="Done", command=self._done,
                  bg=COLORS["primary"], fg=COLORS["bg_dark"],
                  font=("Segoe UI", 10, "bold"), relief="flat",
                  cursor="hand2", width=14).pack(side="right")

    def _done(self):
        if self.on_enabled:
            self.on_enabled(self.account_id)
        self.destroy()

    # ── Utility ─────────────────────────────────────────────────────────────

    def _clear(self):
        for widget in self.winfo_children():
            widget.destroy()
