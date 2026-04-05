"""TG PRO QUANTUM - Register Window (synced with backend API)"""
import tkinter as tk
from tkinter import messagebox
import threading
import re
import urllib.request
import urllib.parse
import json

from gui.styles import COLORS, FONTS

API_BASE = "http://localhost:8000/api/v1"

SPECIAL_CHARS = set("!@#$%^&*()_+-=[]{}|;':\",./<>?")


def _password_errors(password: str) -> list:
    errs = []
    if len(password) < 8:
        errs.append("At least 8 characters")
    if not any(c.isupper() for c in password):
        errs.append("At least one uppercase letter (A-Z)")
    if not any(c.islower() for c in password):
        errs.append("At least one lowercase letter (a-z)")
    if not any(c.isdigit() for c in password):
        errs.append("At least one digit (0-9)")
    if not any(c in SPECIAL_CHARS for c in password):
        errs.append("At least one special character (!@#$…)")
    return errs


def _is_valid_email(email: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$", email))


class RegisterWindow:
    """Register Window - calls backend API POST /auth/register"""

    def __init__(self, parent, on_success=None):
        self.parent = parent
        self.on_success = on_success  # callback after successful registration
        self.result = None

        self._build()

    def _build(self):
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("📝 Register - TG PRO QUANTUM")
        self.dialog.geometry("520x620")
        self.dialog.configure(bg=COLORS["bg_dark"])
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        # Center
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (520 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (620 // 2)
        self.dialog.geometry(f"520x620+{x}+{y}")

        # Header
        header = tk.Frame(self.dialog, bg=COLORS["primary"], height=90)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="📝", font=("Inter", 30), fg="white",
                 bg=COLORS["primary"]).pack(pady=(12, 0))
        tk.Label(header, text="Create Account", font=("Inter", 18, "bold"),
                 fg="white", bg=COLORS["primary"]).pack()

        # Form
        form = tk.Frame(self.dialog, bg=COLORS["bg_medium"])
        form.pack(fill="both", expand=True, padx=30, pady=20)

        def field(label_text, entry_attr, show=""):
            tk.Label(form, text=label_text, fg=COLORS["text"],
                     bg=COLORS["bg_medium"], font=FONTS["normal"]).pack(anchor="w", pady=(8, 3))
            e = tk.Entry(form, width=44, bg=COLORS["bg_light"], fg=COLORS["text"],
                         font=FONTS["normal"], show=show,
                         insertbackground=COLORS["text"])
            e.pack(fill="x", pady=2)
            setattr(self, entry_attr, e)
            return e

        field("Full Name:", "name_entry")
        field("Email:", "email_entry")
        field("Password:", "password_entry", show="•")
        field("Confirm Password:", "confirm_entry", show="•")

        # Password hint
        self.hint_label = tk.Label(form, text="", fg=COLORS["text_muted"],
                                    bg=COLORS["bg_medium"], font=FONTS["small"],
                                    wraplength=440, justify="left")
        self.hint_label.pack(anchor="w", pady=(4, 0))

        self.password_entry.bind("<KeyRelease>", self._update_hint)

        # Register button
        tk.Button(form, text="🚀 Create Account", command=self._submit,
                  bg=COLORS["primary"], fg="white",
                  font=("Inter", 13, "bold"),
                  padx=40, pady=10, bd=0,
                  activebackground=COLORS.get("primary_hover", "#00B8E6"),
                  cursor="hand2").pack(pady=18)

        # Link back to login
        link_frame = tk.Frame(form, bg=COLORS["bg_medium"])
        link_frame.pack()
        tk.Label(link_frame, text="Already have an account? ",
                 fg=COLORS["text_muted"], bg=COLORS["bg_medium"],
                 font=FONTS["small"]).pack(side="left")
        login_link = tk.Label(link_frame, text="Sign In", fg=COLORS["primary"],
                               bg=COLORS["bg_medium"], font=FONTS["small"],
                               cursor="hand2")
        login_link.pack(side="left")
        login_link.bind("<Button-1>", lambda e: self._go_login())

        self.dialog.bind("<Return>", lambda e: self._submit())
        self.name_entry.focus_set()

    def _update_hint(self, _event=None):
        pw = self.password_entry.get()
        errs = _password_errors(pw)
        if not pw:
            self.hint_label.config(text="")
        elif errs:
            self.hint_label.config(text="⚠ " + " · ".join(errs), fg=COLORS.get("warning", "#FFB800"))
        else:
            self.hint_label.config(text="✓ Strong password", fg=COLORS.get("success", "#00FF41"))

    def _submit(self):
        name = self.name_entry.get().strip()
        email = self.email_entry.get().strip()
        password = self.password_entry.get()
        confirm = self.confirm_entry.get()

        if not all([name, email, password, confirm]):
            messagebox.showerror("Error", "All fields are required.", parent=self.dialog)
            return

        if len(name) < 2:
            messagebox.showerror("Error", "Name must be at least 2 characters.", parent=self.dialog)
            return

        if not _is_valid_email(email):
            messagebox.showerror("Error", "Invalid email format.", parent=self.dialog)
            return

        errs = _password_errors(password)
        if errs:
            messagebox.showerror("Error", "Password requirements not met:\n• " + "\n• ".join(errs),
                                 parent=self.dialog)
            return

        if password != confirm:
            messagebox.showerror("Error", "Passwords do not match.", parent=self.dialog)
            return

        # Call API in background thread
        threading.Thread(target=self._call_api, args=(name, email, password), daemon=True).start()

    def _call_api(self, name, email, password):
        try:
            payload = json.dumps({"name": name, "email": email, "password": password}).encode()
            req = urllib.request.Request(
                f"{API_BASE}/auth/register",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp.read()  # consume body
            # Success
            self.dialog.after(0, self._on_success)
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            try:
                detail = json.loads(body).get("detail", body)
                if isinstance(detail, list):
                    detail = " · ".join(str(d.get("msg", d)) for d in detail)
            except Exception:
                detail = body
            self.dialog.after(0, lambda: messagebox.showerror(
                "Registration Failed", str(detail), parent=self.dialog))
        except Exception as ex:
            self.dialog.after(0, lambda: messagebox.showerror(
                "Error", f"Could not connect to server:\n{ex}", parent=self.dialog))

    def _on_success(self):
        messagebox.showinfo("Success",
                            "✅ Account created!\nYou can now sign in with your credentials.",
                            parent=self.dialog)
        self.result = {"success": True}
        self.dialog.destroy()
        if self.on_success:
            self.on_success()

    def _go_login(self):
        self.dialog.destroy()

    def show(self):
        if hasattr(self, "dialog"):
            try:
                self.parent.wait_window(self.dialog)
            except Exception:
                pass
        return self.result or {"success": False}


__all__ = ["RegisterWindow"]
