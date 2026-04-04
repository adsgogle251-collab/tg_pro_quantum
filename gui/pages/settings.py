"""
TG PRO QUANTUM – Phase 5B Settings Page

Frame-overlay settings page with sections for general, notifications,
proxy, and advanced settings.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, colorchooser
from typing import Callable, Optional, Dict, Any

from gui.styles import COLORS, FONTS
from gui.components.vibrant_buttons import make_vibrant_btn

__all__ = ["SettingsPage"]

BG    = COLORS["bg_dark"]
PANEL = COLORS["bg_medium"]
CARD  = COLORS["bg_light"]
CYAN  = COLORS["primary"]
TEXT  = COLORS["text"]
MUTED = COLORS["text_muted"]


class SettingsPage:
    """
    Settings overlay page.

    Usage::

        page = SettingsPage(parent_frame, on_save=save_handler)
        page.show()
    """

    def __init__(
        self,
        parent: tk.Widget,
        on_save: Optional[Callable[[Dict[str, Any]], None]] = None,
        initial_values: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.parent         = parent
        self.on_save        = on_save
        self._values        = initial_values or {}
        self._vars: Dict[str, tk.Variable] = {}

        self.frame = tk.Frame(parent, bg=BG)
        self._build()

    # ── public API ────────────────────────────────────────────────────────────

    def show(self) -> None:
        self.frame.place(relx=0, rely=0, relwidth=1, relheight=1)

    def hide(self) -> None:
        self.frame.place_forget()

    def load_values(self, values: Dict[str, Any]) -> None:
        """Populate form fields from a settings dictionary."""
        self._values = values
        for key, var in self._vars.items():
            if key in values:
                if isinstance(var, tk.BooleanVar):
                    var.set(bool(values[key]))
                else:
                    var.set(str(values[key]))

    def get_values(self) -> Dict[str, Any]:
        """Return the current form values."""
        return {k: v.get() for k, v in self._vars.items()}

    # ── build ─────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        f = self.frame

        # header
        hdr = tk.Frame(f, bg=PANEL, height=56)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="⚙  Settings", bg=PANEL, fg=CYAN,
                 font=FONTS["heading"]).pack(side="left", padx=20, pady=12)
        make_vibrant_btn(hdr, "💾 Save", preset="primary",
                         command=self._on_save).pack(side="right", padx=16, pady=10)

        # scrollable body
        canvas = tk.Canvas(f, bg=BG, highlightthickness=0)
        vsb = ttk.Scrollbar(f, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        body = tk.Frame(canvas, bg=BG)
        body_win = canvas.create_window((0, 0), window=body, anchor="nw")

        def _resize(evt):
            canvas.itemconfig(body_win, width=evt.width)
        def _scroll_region(evt):
            canvas.configure(scrollregion=canvas.bbox("all"))

        canvas.bind("<Configure>", _resize)
        body.bind("<Configure>", _scroll_region)

        self._build_general_section(body)
        self._build_notifications_section(body)
        self._build_proxy_section(body)
        self._build_advanced_section(body)

    # ── sections ──────────────────────────────────────────────────────────────

    def _build_general_section(self, parent: tk.Widget) -> None:
        section = self._section(parent, "⚡ General")

        self._text_row(section, "App Language",  "language",  "English")
        self._text_row(section, "Log Level",      "log_level", "INFO")
        self._bool_row(section, "Auto-start on login",    "auto_start",    False)
        self._bool_row(section, "Minimize to tray",       "minimize_tray", True)
        self._text_row(section, "Data directory",  "data_dir", "data/")
        self._spin_row(section, "Max log file size (MB)", "max_log_mb", 50, 1, 500)

    def _build_notifications_section(self, parent: tk.Widget) -> None:
        section = self._section(parent, "🔔 Notifications")

        self._bool_row(section, "Desktop notifications",     "notif_desktop", True)
        self._bool_row(section, "Sound alerts",              "notif_sound",   False)
        self._bool_row(section, "Notify on campaign finish", "notif_finish",  True)
        self._bool_row(section, "Notify on account flood",   "notif_flood",   True)

    def _build_proxy_section(self, parent: tk.Widget) -> None:
        section = self._section(parent, "🌐 Proxy")

        self._bool_row(section, "Enable proxy",      "proxy_enabled", False)
        self._text_row(section, "Proxy host",         "proxy_host",    "")
        self._text_row(section, "Proxy port",         "proxy_port",    "")
        self._text_row(section, "Proxy username",     "proxy_user",    "")
        self._pass_row(section, "Proxy password",     "proxy_pass")

    def _build_advanced_section(self, parent: tk.Widget) -> None:
        section = self._section(parent, "🛠 Advanced")

        self._spin_row(section, "Request timeout (s)",    "req_timeout",  30, 5, 120)
        self._spin_row(section, "Max retries",            "max_retries",   3, 0,  10)
        self._spin_row(section, "Delay between msgs (s)", "msg_delay",     1, 0,  60)
        self._bool_row(section, "Developer mode",          "dev_mode",    False)
        self._bool_row(section, "Verbose logging",         "verbose_log", False)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _section(self, parent: tk.Widget, title: str) -> tk.Frame:
        outer = tk.Frame(parent, bg=PANEL, padx=20, pady=16)
        outer.pack(fill="x", padx=20, pady=(16, 0))
        tk.Label(outer, text=title, bg=PANEL, fg=CYAN,
                 font=FONTS["subheading"]).pack(anchor="w", pady=(0, 10))
        ttk.Separator(outer).pack(fill="x", pady=(0, 10))
        return outer

    def _row(self, parent: tk.Widget, label: str) -> tk.Frame:
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", pady=5)
        tk.Label(row, text=label, bg=PANEL, fg=TEXT,
                 font=FONTS["small"], width=28, anchor="w").pack(side="left")
        return row

    def _text_row(self, parent, label, key, default=""):
        row = self._row(parent, label)
        var = tk.StringVar(value=self._values.get(key, default))
        tk.Entry(row, textvariable=var, bg=CARD, fg=TEXT,
                 insertbackground=CYAN, relief="flat",
                 font=FONTS["small"], width=30).pack(side="left", padx=4)
        self._vars[key] = var

    def _pass_row(self, parent, label, key):
        row = self._row(parent, label)
        var = tk.StringVar(value=self._values.get(key, ""))
        tk.Entry(row, textvariable=var, show="*",
                 bg=CARD, fg=TEXT, insertbackground=CYAN,
                 relief="flat", font=FONTS["small"], width=30).pack(side="left", padx=4)
        self._vars[key] = var

    def _bool_row(self, parent, label, key, default=False):
        row = self._row(parent, label)
        var = tk.BooleanVar(value=self._values.get(key, default))
        tk.Checkbutton(row, variable=var, bg=PANEL,
                        fg=TEXT, selectcolor=CARD,
                        activebackground=PANEL,
                        highlightthickness=0).pack(side="left")
        self._vars[key] = var

    def _spin_row(self, parent, label, key, default, from_, to):
        row = self._row(parent, label)
        var = tk.StringVar(value=str(self._values.get(key, default)))
        tk.Spinbox(row, textvariable=var, from_=from_, to=to,
                    bg=CARD, fg=TEXT, buttonbackground=CARD,
                    insertbackground=CYAN, relief="flat",
                    font=FONTS["small"], width=8).pack(side="left", padx=4)
        self._vars[key] = var

    # ── save ──────────────────────────────────────────────────────────────────

    def _on_save(self) -> None:
        if self.on_save:
            self.on_save(self.get_values())
