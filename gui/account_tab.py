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

# OTP dialog status colours
OTP_COLOR_WAITING = "#FFC107"   # Yellow – waiting for OTP
OTP_COLOR_SUCCESS = "#4CAF50"   # Green  – verified
OTP_COLOR_ERROR   = "#F44336"   # Red    – error / invalid code
OTP_COLOR_INFO    = "#00BCD4"   # Cyan   – normal / info

STATUS_COLORS = {
    "active":  GREEN,
    "expired": ORANGE,
    "error":   RED,
}


class AccountTab:
    title = "👤 Accounts"
    _COL_PHONE = 2  # index of the Phone column in the Treeview (after ☑, Name)

    def __init__(self, parent, main_window=None):
        self.parent = parent
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        self._checked_phones: set[str] = set()
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
        make_btn(btn_row, "☑ Select All", command=self._select_all,
                 color=PANEL).pack(side="left", padx=4)
        make_btn(btn_row, "🩺 Health Check", command=self._health_check,
                 color=ORANGE, fg="#000").pack(side="left", padx=4)
        make_btn(btn_row, "🗑️ Delete", command=self._delete,
                 color=RED).pack(side="left", padx=4)

        # Status bar
        self._status_var = tk.StringVar(value="")
        tk.Label(outer, textvariable=self._status_var,
                 font=FONTS["normal"], fg=GREEN, bg=BG).pack(anchor="w", pady=(0, 6))

        # Table  (first column = checkbox)
        cols = ("☑", "Name", "Phone", "Status", "Session", "Created")
        self._tree = ttk.Treeview(outer, columns=cols, show="headings",
                                  height=20, selectmode="extended")
        widths = {"☑": 35, "Name": 160, "Phone": 130, "Status": 90,
                  "Session": 240, "Created": 150}
        for c in cols:
            self._tree.heading(c, text=c)
            self._tree.column(c, width=widths[c], anchor="center")
        self._tree.tag_configure("active",  foreground=GREEN)
        self._tree.tag_configure("expired", foreground=ORANGE)
        self._tree.tag_configure("error",   foreground=RED)

        # Toggle checkbox on click
        self._tree.bind("<Button-1>", self._on_tree_click)
        # Select all with Ctrl+A
        self._tree.bind("<Control-a>", lambda e: self._select_all())
        self._tree.bind("<Control-A>", lambda e: self._select_all())

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
            phone = acc["phone"]
            check = "☑" if phone in self._checked_phones else "☐"
            self._tree.insert("", "end",
                values=(check, acc["name"], phone, status, sf, created),
                tags=(status,))
        self._status_var.set(f"Loaded {len(accounts)} accounts.")

    def refresh_list(self):
        """Public method to reload the account list from outside this tab."""
        self._refresh()

    def _on_tree_click(self, event):
        """Toggle the checkbox when the ☑ column is clicked."""
        col = self._tree.identify_column(event.x)
        if col == "#1":  # first column = checkbox
            item = self._tree.identify_row(event.y)
            if item:
                vals = list(self._tree.item(item, "values"))
                phone = vals[self._COL_PHONE]
                if phone in self._checked_phones:
                    self._checked_phones.discard(phone)
                    vals[0] = "☐"
                else:
                    self._checked_phones.add(phone)
                    vals[0] = "☑"
                self._tree.item(item, values=vals)

    def _select_all(self):
        """Toggle: check all if any are unchecked, otherwise uncheck all."""
        all_items = self._tree.get_children()
        all_phones = {self._tree.item(i, "values")[self._COL_PHONE] for i in all_items}
        if all_phones == self._checked_phones:
            # Deselect all
            self._checked_phones.clear()
            mark = "☐"
        else:
            # Select all
            self._checked_phones = all_phones.copy()
            mark = "☑"
        for item in all_items:
            vals = list(self._tree.item(item, "values"))
            vals[0] = mark
            self._tree.item(item, values=vals)

    def _selected_phone(self) -> str | None:
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select an account first.")
            return None
        return self._tree.item(sel[0], "values")[self._COL_PHONE]

    # ─────────────────────────────────────────────────────────────────────────
    # OTP Add Account dialog
    # ─────────────────────────────────────────────────────────────────────────
    def _add_account(self):
        OTPDialog(self.frame, on_success=self._refresh)

    # ─────────────────────────────────────────────────────────────────────────
    def _delete(self):
        if self._checked_phones:
            phones = list(self._checked_phones)
            n = len(phones)
            if not messagebox.askyesno(
                "Confirm",
                f"Delete {n} account{'s' if n > 1 else ''}? Confirm?"
            ):
                return
            for phone in phones:
                delete_account(phone)
            self._checked_phones.clear()
            self._status_var.set(f"Deleted {n} account{'s' if n > 1 else ''}.")
            self._refresh()
        else:
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
    """
    Multi-step dialog: enter phone → receive OTP → verify → (2FA) → done.

    Step indicators and colour-coded status make the flow obvious:
      • Yellow (#FFC107)  – waiting / sending
      • Green  (#4CAF50)  – success
      • Red    (#F44336)  – error / invalid
      • Cyan   (#00BCD4)  – neutral / info
    """

    _PLACEHOLDER_COLOR = "#9099B7"   # muted text for placeholder hints

    def __init__(self, parent, on_success=None):
        super().__init__(parent)
        self.on_success = on_success
        self.title("Add Telegram Account")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.grab_set()
        self._step = "phone"   # "phone" | "otp" | "2fa"
        self._build()
        self.update_idletasks()
        # Center with comfortable 600 px width
        w, h = 600, 500
        x = self.winfo_screenwidth()  // 2 - w // 2
        y = self.winfo_screenheight() // 2 - h // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    # ── Layout ────────────────────────────────────────────────────────────────
    def _build(self):
        self._container = tk.Frame(self, bg=BG)
        self._container.pack(fill="both", expand=True, padx=32, pady=28)

        # Title
        tk.Label(
            self._container,
            text="➕  Add Telegram Account",
            font=FONTS["heading"], fg=OTP_COLOR_INFO, bg=BG,
        ).pack(pady=(0, 4))

        # Step indicator bar
        self._step_label = tk.Label(
            self._container,
            text="Step 1 of 3 – Enter phone number",
            font=FONTS["small"], fg=MUTED, bg=BG,
        )
        self._step_label.pack(pady=(0, 16))

        # ── Phone number ──────────────────────────────────────────────────────
        tk.Label(
            self._container,
            text="📱  Phone number  (include country code)",
            font=FONTS["normal"], fg=TEXT, bg=BG, anchor="w",
        ).pack(fill="x")

        self._phone_var = tk.StringVar()
        self._phone_entry = tk.Entry(
            self._container, textvariable=self._phone_var,
            bg=CARD, fg=self._PLACEHOLDER_COLOR,
            insertbackground=TEXT,
            font=FONTS["subheading"], relief="flat",
        )
        self._phone_entry.pack(fill="x", ipady=7, pady=(4, 2))
        self._phone_entry.insert(0, "+6281234567")
        self._phone_entry.bind("<FocusIn>",  self._phone_focus_in)
        self._phone_entry.bind("<FocusOut>", self._phone_focus_out)

        tk.Label(
            self._container, text="Example: +6281234567890  or  +19175550100",
            font=FONTS["small"], fg=MUTED, bg=BG, anchor="w",
        ).pack(fill="x", pady=(0, 12))

        # ── Display name (optional) ───────────────────────────────────────────
        name_row = tk.Frame(self._container, bg=BG)
        name_row.pack(fill="x")
        tk.Label(
            name_row,
            text="🏷️  Display name",
            font=FONTS["normal"], fg=TEXT, bg=BG,
        ).pack(side="left")
        tk.Label(
            name_row,
            text="  (optional – defaults to Telegram first name)",
            font=FONTS["small"], fg=MUTED, bg=BG,
        ).pack(side="left")

        self._name_var = tk.StringVar()
        self._name_entry = tk.Entry(
            self._container, textvariable=self._name_var,
            bg=CARD, fg=TEXT, insertbackground=TEXT,
            font=FONTS["subheading"], relief="flat",
        )
        self._name_entry.pack(fill="x", ipady=7, pady=(4, 16))

        # ── OTP section (hidden until OTP is sent) ────────────────────────────
        self._otp_frame = tk.Frame(self._container, bg=BG)

        otp_title_row = tk.Frame(self._otp_frame, bg=BG)
        otp_title_row.pack(fill="x")
        tk.Label(
            otp_title_row,
            text="🔑  OTP Code",
            font=FONTS["normal"], fg=TEXT, bg=BG,
        ).pack(side="left")
        self._otp_hint = tk.Label(
            otp_title_row,
            text="  Enter the 5–6 digit code sent to your phone",
            font=FONTS["small"], fg=MUTED, bg=BG,
        )
        self._otp_hint.pack(side="left")

        self._otp_var = tk.StringVar()
        self._otp_entry = tk.Entry(
            self._otp_frame, textvariable=self._otp_var,
            bg=CARD, fg=TEXT, insertbackground=TEXT,
            font=("Consolas", 18, "bold"), relief="flat",
            justify="center",
        )
        self._otp_entry.pack(fill="x", ipady=10, pady=(4, 4))

        # OTP status badge (Waiting / Received / Error)
        self._otp_status = tk.Label(
            self._otp_frame,
            text="⏳  Waiting for OTP code…",
            font=FONTS["bold"], fg=OTP_COLOR_WAITING, bg=BG,
        )
        self._otp_status.pack(anchor="w", pady=(0, 12))

        # ── 2FA section (hidden until 2FA required) ───────────────────────────
        self._twofa_frame = tk.Frame(self._container, bg=BG)

        tk.Label(
            self._twofa_frame,
            text="🔐  Two-Factor Authentication (2FA)",
            font=FONTS["normal"], fg=TEXT, bg=BG, anchor="w",
        ).pack(fill="x")
        tk.Label(
            self._twofa_frame,
            text="Your account has 2FA enabled. Enter your Telegram password below.",
            font=FONTS["small"], fg=MUTED, bg=BG, anchor="w",
        ).pack(fill="x", pady=(2, 4))

        self._pass_var = tk.StringVar()
        self._pass_entry = tk.Entry(
            self._twofa_frame, textvariable=self._pass_var,
            show="*",
            bg=CARD, fg=TEXT, insertbackground=TEXT,
            font=FONTS["subheading"], relief="flat",
        )
        self._pass_entry.pack(fill="x", ipady=7, pady=(0, 12))

        # ── Status message (colour changes per state) ─────────────────────────
        self._status_var = tk.StringVar(value="")
        self._status_lbl = tk.Label(
            self._container, textvariable=self._status_var,
            font=FONTS["normal"], fg=OTP_COLOR_INFO, bg=BG,
            wraplength=530, justify="left", anchor="w",
        )
        self._status_lbl.pack(fill="x", pady=(0, 12))

        # ── Button row: Action | Retry | Cancel ───────────────────────────────
        btn_row = tk.Frame(self._container, bg=BG)
        btn_row.pack(fill="x")

        self._action_btn = make_btn(
            btn_row, "📤  Send OTP", command=self._on_action,
            color=OTP_COLOR_INFO, fg="#000",
        )
        self._action_btn.pack(side="left", padx=(0, 8))

        self._retry_btn = make_btn(
            btn_row, "🔄  Retry", command=self._on_retry,
            color=ORANGE, fg="#000",
        )
        # Retry is always created but only shown when needed
        self._retry_btn.pack_forget()

        make_btn(
            btn_row, "✖  Cancel", command=self.destroy,
            color=CARD, fg=TEXT,
        ).pack(side="left")

    # ── Placeholder helpers ───────────────────────────────────────────────────
    def _phone_focus_in(self, _event=None):
        if self._phone_entry.cget("fg") == self._PLACEHOLDER_COLOR:
            self._phone_entry.delete(0, "end")
            self._phone_entry.config(fg=TEXT)

    def _phone_focus_out(self, _event=None):
        if not self._phone_var.get().strip():
            self._phone_entry.config(fg=self._PLACEHOLDER_COLOR)
            self._phone_entry.insert(0, "+6281234567")

    # ── Status helper ─────────────────────────────────────────────────────────
    def _set_status(self, text: str, color: str = OTP_COLOR_INFO):
        self._status_var.set(text)
        self._status_lbl.config(fg=color)

    def _set_otp_status(self, text: str, color: str = OTP_COLOR_WAITING):
        self._otp_status.config(text=text, fg=color)

    # ── Step transitions ──────────────────────────────────────────────────────
    def _go_to_otp_step(self):
        self._step = "otp"
        self._step_label.config(text="Step 2 of 3 – Enter OTP code")
        self._otp_frame.pack(fill="x", pady=(0, 4))
        self._set_otp_status("✅  OTP sent!  Check your phone for the code.", OTP_COLOR_SUCCESS)
        self._action_btn.config(text="✅  Verify OTP", bg=OTP_COLOR_SUCCESS, fg="#000")
        self._retry_btn.pack(side="left", padx=(0, 8))
        self._otp_entry.focus()
        self._set_status("Enter the code you received, then click Verify OTP.", OTP_COLOR_INFO)

    def _go_to_2fa_step(self):
        self._step = "2fa"
        self._step_label.config(text="Step 3 of 3 – Enter 2FA password")
        self._twofa_frame.pack(fill="x", pady=(0, 4))
        self._action_btn.config(text="🔓  Verify 2FA", bg=OTP_COLOR_INFO, fg="#000", state="normal")
        self._pass_entry.focus()
        self._set_status("🔐  2FA password required.  Enter your Telegram password below.", OTP_COLOR_WAITING)

    # ── Action dispatch ───────────────────────────────────────────────────────
    def _on_action(self):
        if self._step == "phone":
            self._do_send_otp()
        elif self._step == "otp":
            self._do_verify_otp()
        elif self._step == "2fa":
            self._do_verify_2fa()

    # ── Send OTP ──────────────────────────────────────────────────────────────
    def _do_send_otp(self):
        phone = self._phone_var.get().strip()
        # Treat placeholder value as empty
        if not phone or phone == "+6281234567":
            messagebox.showwarning("Missing", "Please enter your phone number.", parent=self)
            self._phone_entry.focus()
            return
        self._set_status("⏳  Sending OTP…  Please wait.", OTP_COLOR_WAITING)
        self._action_btn.config(text="Sending…", state="disabled")

        def task():
            ok, msg = run_async(send_otp(phone))

            def after():
                self._action_btn.config(state="normal")
                if not ok:
                    self._set_status(f"❌  {msg}", OTP_COLOR_ERROR)
                    self._action_btn.config(text="📤  Send OTP")
                    return
                if msg == "already_authorized":
                    name = self._name_var.get().strip() or phone
                    from core.account import _upsert_account, _session_path
                    sf = _session_path(phone) + ".session"
                    _upsert_account(name, phone, sf, "active")
                    self._set_status(f"✅  Account '{name}' added (already authorised).", OTP_COLOR_SUCCESS)
                    self.after(1400, self._finish)
                    return
                self._go_to_otp_step()

            self.after(0, after)

        threading.Thread(target=task, daemon=True).start()

    # ── Verify OTP ────────────────────────────────────────────────────────────
    def _do_verify_otp(self):
        phone = self._phone_var.get().strip()
        code  = self._otp_var.get().strip()
        name  = self._name_var.get().strip()
        if not code:
            messagebox.showwarning("Missing", "Please enter the OTP code.", parent=self)
            self._otp_entry.focus()
            return
        self._set_otp_status("⏳  Verifying OTP code…", OTP_COLOR_WAITING)
        self._set_status("Verifying…", OTP_COLOR_WAITING)
        self._action_btn.config(state="disabled")

        def task():
            ok, msg = run_async(verify_otp(phone, code, name))

            def after():
                self._action_btn.config(state="normal")
                if not ok:
                    if msg == "2FA_required":
                        self._set_otp_status("✅  OTP verified.", OTP_COLOR_SUCCESS)
                        self._go_to_2fa_step()
                    else:
                        self._set_otp_status(
                            "❌  Invalid OTP code.  Try again or request a new code.",
                            OTP_COLOR_ERROR,
                        )
                        self._set_status(
                            f"❌  {msg}  —  Clear the field and try a different code, or click Retry to resend.",
                            OTP_COLOR_ERROR,
                        )
                        self._otp_var.set("")
                        self._otp_entry.focus()
                    return
                self._set_otp_status("✅  OTP verified successfully!", OTP_COLOR_SUCCESS)
                self._set_status(f"✅  {msg}", OTP_COLOR_SUCCESS)
                self.after(1400, self._finish)

            self.after(0, after)

        threading.Thread(target=task, daemon=True).start()

    # ── Verify 2FA ────────────────────────────────────────────────────────────
    def _do_verify_2fa(self):
        phone    = self._phone_var.get().strip()
        code     = self._otp_var.get().strip()
        name     = self._name_var.get().strip()
        password = self._pass_var.get().strip()
        if not password:
            messagebox.showwarning("Missing", "Please enter your 2FA password.", parent=self)
            self._pass_entry.focus()
            return
        self._set_status("⏳  Verifying 2FA password…", OTP_COLOR_WAITING)
        self._action_btn.config(state="disabled")

        def task():
            ok, msg = run_async(verify_otp(phone, code, name, password))

            def after():
                self._action_btn.config(state="normal")
                if not ok:
                    self._set_status(
                        f"❌  {msg}  —  Check your password and try again, or click Retry to go back.",
                        OTP_COLOR_ERROR,
                    )
                    return
                self._set_status(f"✅  {msg}", OTP_COLOR_SUCCESS)
                self.after(1400, self._finish)

            self.after(0, after)

        threading.Thread(target=task, daemon=True).start()

    # ── Retry ─────────────────────────────────────────────────────────────────
    def _on_retry(self):
        """Retry: in OTP step → resend OTP from phone; in 2FA step → back to OTP."""
        if self._step == "2fa":
            self._twofa_frame.pack_forget()
            self._pass_var.set("")
            self._step = "otp"
            self._step_label.config(text="Step 2 of 3 – Enter OTP code")
            self._action_btn.config(text="✅  Verify OTP", bg=OTP_COLOR_SUCCESS, state="normal")
            self._otp_var.set("")
            self._otp_entry.focus()
            self._set_otp_status("⏳  Enter a new OTP code.", OTP_COLOR_WAITING)
            self._set_status("Enter a new OTP code or click Retry again to resend.", OTP_COLOR_INFO)
        else:
            # Back to phone step to allow re-send
            self._otp_frame.pack_forget()
            self._otp_var.set("")
            self._step = "phone"
            self._step_label.config(text="Step 1 of 3 – Enter phone number")
            self._action_btn.config(text="📤  Send OTP", bg=OTP_COLOR_INFO, state="normal")
            self._retry_btn.pack_forget()
            self._phone_entry.focus()
            self._set_status("Enter your phone number and click Send OTP to request a new code.", OTP_COLOR_INFO)

    # ── Finish ────────────────────────────────────────────────────────────────
    def _finish(self):
        if self.on_success:
            self.on_success()
        self.destroy()
