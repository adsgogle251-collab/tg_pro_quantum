"""
gui/settings_tab.py - API credentials and app settings UI
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading

from gui.styles import COLORS, FONTS, make_btn
from core.config import get_setting, set_setting, get_api_id, get_api_hash
from core.account import run_async

BG    = COLORS["bg_dark"]
PANEL = COLORS["bg_medium"]
CARD  = COLORS["bg_light"]
CYAN  = COLORS["primary"]
GREEN = COLORS["success"]
TEXT  = COLORS["text"]
MUTED = COLORS["text_muted"]
RED   = COLORS["error"]


class SettingsTab:
    title = "⚙️ Settings"

    def __init__(self, parent, main_window=None):
        self.parent = parent
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        self._build()
        self._load_settings()

    def _build(self):
        outer = tk.Frame(self.frame, bg=BG)
        outer.pack(fill="both", expand=True, padx=20, pady=20)

        # ── Title ─────────────────────────────────────────────────────────────
        tk.Label(
            outer, text="⚙️ Settings",
            font=FONTS["heading_large"], fg=CYAN, bg=BG
        ).pack(anchor="w", pady=(0, 16))

        # ── API Credentials card ───────────────────────────────────────────────
        card = tk.LabelFrame(
            outer, text=" 🔑 Telegram API Credentials ",
            bg=PANEL, fg=CYAN, font=FONTS["subheading"]
        )
        card.pack(fill="x", pady=(0, 12))

        inner = tk.Frame(card, bg=PANEL)
        inner.pack(fill="x", padx=16, pady=12)

        # API ID
        row1 = tk.Frame(inner, bg=PANEL)
        row1.pack(fill="x", pady=4)
        tk.Label(row1, text="API ID:", width=16, anchor="w",
                 font=FONTS["normal"], fg=TEXT, bg=PANEL).pack(side="left")
        self._api_id_var = tk.StringVar()
        tk.Entry(
            row1, textvariable=self._api_id_var,
            bg=CARD, fg=TEXT, insertbackground=TEXT,
            font=FONTS["normal"], width=30, relief="flat"
        ).pack(side="left", padx=(0, 8))
        tk.Label(
            row1,
            text="Get from my.telegram.org",
            font=FONTS["small"], fg=MUTED, bg=PANEL
        ).pack(side="left")

        # API Hash
        row2 = tk.Frame(inner, bg=PANEL)
        row2.pack(fill="x", pady=4)
        tk.Label(row2, text="API Hash:", width=16, anchor="w",
                 font=FONTS["normal"], fg=TEXT, bg=PANEL).pack(side="left")
        self._api_hash_var = tk.StringVar()
        tk.Entry(
            row2, textvariable=self._api_hash_var,
            bg=CARD, fg=TEXT, insertbackground=TEXT,
            font=FONTS["normal"], width=40, relief="flat", show="*"
        ).pack(side="left", padx=(0, 8))

        # Show/hide hash
        self._show_hash = False
        self._hash_entry = row2.winfo_children()[1]

        def toggle_hash():
            self._show_hash = not self._show_hash
            self._hash_entry.config(show="" if self._show_hash else "*")
        tk.Button(
            row2, text="👁", command=toggle_hash,
            bg=CARD, fg=TEXT, font=FONTS["small"],
            relief="flat", cursor="hand2", padx=4
        ).pack(side="left")

        # App Version
        row3 = tk.Frame(inner, bg=PANEL)
        row3.pack(fill="x", pady=4)
        tk.Label(row3, text="App Version:", width=16, anchor="w",
                 font=FONTS["normal"], fg=TEXT, bg=PANEL).pack(side="left")
        self._version_var = tk.StringVar(value="4.16.11")
        tk.Entry(
            row3, textvariable=self._version_var,
            bg=CARD, fg=TEXT, insertbackground=TEXT,
            font=FONTS["normal"], width=15, relief="flat"
        ).pack(side="left")

        # ── Buttons ────────────────────────────────────────────────────────────
        btn_row = tk.Frame(inner, bg=PANEL)
        btn_row.pack(fill="x", pady=(12, 0))

        make_btn(btn_row, "💾 Save Settings", command=self._save,
                 color=CYAN, fg="#000").pack(side="left", padx=(0, 8))
        make_btn(btn_row, "🧪 Test Connection", command=self._test,
                 color=GREEN, fg="#000").pack(side="left")

        # ── Status label ──────────────────────────────────────────────────────
        self._status_var = tk.StringVar(value="")
        tk.Label(
            outer, textvariable=self._status_var,
            font=FONTS["normal"], fg=GREEN, bg=BG
        ).pack(anchor="w", pady=(8, 0))

        # ── Data folder card ──────────────────────────────────────────────────
        card2 = tk.LabelFrame(
            outer, text=" 📁 Data Folder ",
            bg=PANEL, fg=CYAN, font=FONTS["subheading"]
        )
        card2.pack(fill="x", pady=(0, 12))

        inner2 = tk.Frame(card2, bg=PANEL)
        inner2.pack(fill="x", padx=16, pady=12)

        from core.config import DATA_DIR
        tk.Label(
            inner2,
            text=f"Data stored in: {DATA_DIR.resolve()}",
            font=FONTS["normal"], fg=TEXT, bg=PANEL
        ).pack(anchor="w")

    def _load_settings(self):
        self._api_id_var.set(get_setting("api_id", ""))
        self._api_hash_var.set(get_setting("api_hash", ""))
        self._version_var.set(get_setting("app_version", "4.16.11"))

    def _save(self):
        api_id   = self._api_id_var.get().strip()
        api_hash = self._api_hash_var.get().strip()
        version  = self._version_var.get().strip() or "4.16.11"

        if not api_id or not api_hash:
            messagebox.showwarning("Missing", "Please fill in both API ID and API Hash.")
            return

        try:
            int(api_id)
        except ValueError:
            messagebox.showerror("Invalid", "API ID must be a number.")
            return

        set_setting("api_id",      api_id)
        set_setting("api_hash",    api_hash)
        set_setting("app_version", version)

        self._status_var.set("✅ Settings saved.")
        self.frame.after(3000, lambda: self._status_var.set(""))

    def _test(self):
        api_id   = self._api_id_var.get().strip()
        api_hash = self._api_hash_var.get().strip()
        if not api_id or not api_hash:
            messagebox.showwarning("Missing", "Save API credentials first.")
            return

        self._status_var.set("🔄 Testing connection...")

        def do_test():
            try:
                from telethon.sync import TelegramClient as SyncClient
                import tempfile, os
                # Use a secure named temp dir for the session file
                tmp_dir = tempfile.mkdtemp(prefix="tg_api_test_")
                tmp = os.path.join(tmp_dir, "test_session")
                client = SyncClient(tmp, int(api_id), api_hash)
                client.connect()
                client.disconnect()
                # Clean up temp session directory
                for ext in ("", ".session", ".session-journal"):
                    p = tmp + ext
                    if os.path.exists(p):
                        try:
                            os.unlink(p)
                        except OSError:
                            pass
                try:
                    os.rmdir(tmp_dir)
                except OSError:
                    pass
                self.frame.after(0, lambda: self._status_var.set("✅ API connection OK!"))
            except Exception as e:
                self.frame.after(0, lambda: self._status_var.set(f"❌ Error: {e}"))

        threading.Thread(target=do_test, daemon=True).start()
