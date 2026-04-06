"""
gui/import_tab.py - 4 session/phone import methods
"""
import asyncio
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading

from gui.styles import COLORS, FONTS, make_btn
from core.session_manager import (
    import_single_session,
    import_folder_sessions,
    import_phones_txt,
    add_phones_manual,
)
from core.account import send_otp_batch, get_pending_otp_accounts

BG    = COLORS["bg_dark"]
PANEL = COLORS["bg_medium"]
CARD  = COLORS["bg_light"]
CYAN  = COLORS["primary"]
GREEN = COLORS["success"]
RED   = COLORS["error"]
TEXT  = COLORS["text"]
MUTED = COLORS["text_muted"]


class ImportTab:
    title = "📥 Import"

    def __init__(self, parent, main_window=None):
        self.parent = parent
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        self._build()

    # ──────────────────────────────────────────────────────────────────────────
    def _build(self):
        self.frame.configure(style="TFrame")
        tk.Label(
            self.frame,
            text="📥 Import Accounts",
            font=FONTS["heading"],
            fg=CYAN,
            bg=BG,
        ).pack(pady=(12, 4))

        nb = ttk.Notebook(self.frame)
        nb.pack(fill="both", expand=True, padx=12, pady=8)

        self._build_single_tab(nb)
        self._build_folder_tab(nb)
        self._build_txt_tab(nb)
        self._build_manual_tab(nb)

    # ──────────────────────────────────────────────────────────────────────────
    # Sub-tab 1: Single .session
    # ──────────────────────────────────────────────────────────────────────────
    def _build_single_tab(self, nb):
        f = tk.Frame(nb, bg=PANEL)
        nb.add(f, text="  Single .session  ")

        tk.Label(f, text="Import a single .session file", font=FONTS["subheading"],
                 fg=CYAN, bg=PANEL).pack(pady=(16, 4))
        tk.Label(f, text="File will be validated and copied to the sessions directory.",
                 font=FONTS["small"], fg=MUTED, bg=PANEL).pack()

        path_frame = tk.Frame(f, bg=PANEL)
        path_frame.pack(fill="x", padx=24, pady=(16, 4))

        self._single_path_var = tk.StringVar()
        tk.Entry(
            path_frame,
            textvariable=self._single_path_var,
            font=FONTS["normal"],
            bg=CARD,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
        ).pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 8))

        make_btn(path_frame, "Browse…", command=self._browse_single_file,
                 color=COLORS["bg_light"], fg=TEXT).pack(side="left")

        make_btn(f, "⬇ Import Session", command=self._do_single_import,
                 color=CYAN).pack(pady=(12, 4))

        self._single_status = tk.Label(f, text="", font=FONTS["normal"],
                                        fg=GREEN, bg=PANEL, wraplength=600)
        self._single_status.pack(pady=4)

    def _browse_single_file(self):
        path = filedialog.askopenfilename(
            title="Select .session file",
            filetypes=[("Telegram session", "*.session"), ("All files", "*.*")],
        )
        if path:
            self._single_path_var.set(path)

    def _do_single_import(self):
        path = self._single_path_var.get().strip()
        if not path:
            messagebox.showwarning("Import", "Please select a .session file.")
            return
        self._single_status.config(text="Validating…", fg=MUTED)
        self.frame.update_idletasks()

        def _run():
            ok, msg = import_single_session(
                path,
                on_progress=lambda m: self._single_status.config(text=m, fg=MUTED),
            )
            color = GREEN if ok else RED
            if ok and self.main_window:
                msg = f"{msg}  ✅ Account tab refreshed."
                self.frame.after(0, self.main_window.refresh_account_tab)
            self._single_status.config(text=msg, fg=color)

        threading.Thread(target=_run, daemon=True).start()

    # ──────────────────────────────────────────────────────────────────────────
    # Sub-tab 2: Folder .session
    # ──────────────────────────────────────────────────────────────────────────
    def _build_folder_tab(self, nb):
        f = tk.Frame(nb, bg=PANEL)
        nb.add(f, text="  Folder .session  ")

        tk.Label(f, text="Batch import all .session files from a folder",
                 font=FONTS["subheading"], fg=CYAN, bg=PANEL).pack(pady=(16, 4))

        path_frame = tk.Frame(f, bg=PANEL)
        path_frame.pack(fill="x", padx=24, pady=(12, 4))

        self._folder_path_var = tk.StringVar()
        tk.Entry(
            path_frame,
            textvariable=self._folder_path_var,
            font=FONTS["normal"],
            bg=CARD,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
        ).pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 8))

        make_btn(path_frame, "Browse…", command=self._browse_folder,
                 color=COLORS["bg_light"], fg=TEXT).pack(side="left")

        btn_row = tk.Frame(f, bg=PANEL)
        btn_row.pack(pady=(8, 4))
        make_btn(btn_row, "⬇ Import All", command=self._do_folder_import,
                 color=CYAN).pack(side="left", padx=4)

        self._folder_status = tk.Label(f, text="", font=FONTS["normal"],
                                        fg=GREEN, bg=PANEL)
        self._folder_status.pack(pady=4)

        log_frame = tk.Frame(f, bg=CARD)
        log_frame.pack(fill="both", expand=True, padx=24, pady=(4, 16))

        sb = tk.Scrollbar(log_frame)
        sb.pack(side="right", fill="y")
        self._folder_log = tk.Listbox(
            log_frame,
            yscrollcommand=sb.set,
            font=FONTS["small"],
            bg=CARD,
            fg=TEXT,
            selectbackground=COLORS["primary_light"],
            relief="flat",
        )
        self._folder_log.pack(fill="both", expand=True)
        sb.config(command=self._folder_log.yview)

    def _browse_folder(self):
        path = filedialog.askdirectory(title="Select folder with .session files")
        if path:
            self._folder_path_var.set(path)

    def _do_folder_import(self):
        path = self._folder_path_var.get().strip()
        if not path:
            messagebox.showwarning("Import", "Please select a folder.")
            return
        self._folder_log.delete(0, "end")
        self._folder_status.config(text="Importing…", fg=MUTED)

        def _run():
            def _progress(i, total, msg):
                self._folder_status.config(text=f"{i}/{total}: {msg}", fg=MUTED)
                self._folder_log.insert("end", msg)
                self._folder_log.see("end")

            ok, fail, messages = import_folder_sessions(path, on_progress=_progress)
            for m in messages:
                self._folder_log.insert("end", m)
            summary = f"Done: {ok} imported, {fail} failed."
            if ok > 0 and self.main_window:
                suffix = f" ({fail} failed)" if fail > 0 else ""
                summary = f"Imported {ok} accounts{suffix}! Tab refreshed."
                self.frame.after(0, self.main_window.refresh_account_tab)
            self._folder_status.config(
                text=summary,
                fg=GREEN if ok > 0 else RED,
            )

        threading.Thread(target=_run, daemon=True).start()

    # ──────────────────────────────────────────────────────────────────────────
    # Sub-tab 3: Bulk TXT (phones)
    # ──────────────────────────────────────────────────────────────────────────
    def _build_txt_tab(self, nb):
        f = tk.Frame(nb, bg=PANEL)
        nb.add(f, text="  Bulk TXT (phones)  ")

        tk.Label(f, text="Import phone numbers from a TXT file",
                 font=FONTS["subheading"], fg=CYAN, bg=PANEL).pack(pady=(16, 4))
        tk.Label(f, text="One phone per line  (e.g. +6281234567890)",
                 font=FONTS["small"], fg=MUTED, bg=PANEL).pack()

        path_frame = tk.Frame(f, bg=PANEL)
        path_frame.pack(fill="x", padx=24, pady=(12, 4))

        self._txt_path_var = tk.StringVar()
        tk.Entry(
            path_frame,
            textvariable=self._txt_path_var,
            font=FONTS["normal"],
            bg=CARD,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
        ).pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 8))

        make_btn(path_frame, "Browse…", command=self._browse_txt_file,
                 color=COLORS["bg_light"], fg=TEXT).pack(side="left")

        btn_row = tk.Frame(f, bg=PANEL)
        btn_row.pack(pady=(8, 4))
        make_btn(btn_row, "📋 Import Phones", command=self._do_txt_import,
                 color=CYAN).pack(side="left", padx=4)
        make_btn(btn_row, "📲 Start OTP All", command=self._do_otp_all,
                 color=GREEN, fg="#000000").pack(side="left", padx=4)

        self._txt_status = tk.Label(f, text="", font=FONTS["normal"],
                                     fg=GREEN, bg=PANEL, wraplength=600)
        self._txt_status.pack(pady=4)

    def _browse_txt_file(self):
        path = filedialog.askopenfilename(
            title="Select phones TXT file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if path:
            self._txt_path_var.set(path)

    def _do_txt_import(self):
        path = self._txt_path_var.get().strip()
        if not path:
            messagebox.showwarning("Import", "Please select a TXT file.")
            return
        self._txt_status.config(text="Importing…", fg=MUTED)

        def _run():
            count, phones = import_phones_txt(path)
            msg = f"Added {count} new phone(s) (status: pending_otp)."
            if count > 0 and self.main_window:
                msg = f"Imported {count} accounts! Tab refreshed."
                self.frame.after(0, self.main_window.refresh_account_tab)
            self._txt_status.config(
                text=msg,
                fg=GREEN if count > 0 else MUTED,
            )

        threading.Thread(target=_run, daemon=True).start()

    def _do_otp_all(self):
        pending = get_pending_otp_accounts()
        if not pending:
            messagebox.showinfo("OTP", "No pending accounts to send OTP to.")
            return
        phones = [a["phone"] for a in pending]
        self._send_otp_to_phones(phones, self._txt_status)

    # ──────────────────────────────────────────────────────────────────────────
    # Sub-tab 4: Manual Add
    # ──────────────────────────────────────────────────────────────────────────
    def _build_manual_tab(self, nb):
        f = tk.Frame(nb, bg=PANEL)
        nb.add(f, text="  Manual Add  ")

        tk.Label(f, text="Manually enter phone numbers",
                 font=FONTS["subheading"], fg=CYAN, bg=PANEL).pack(pady=(16, 4))
        tk.Label(f, text="One per line  (e.g. +6281234567890)",
                 font=FONTS["small"], fg=MUTED, bg=PANEL).pack()

        self._manual_text = tk.Text(
            f,
            height=10,
            font=FONTS["mono"],
            bg=CARD,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
        )
        self._manual_text.pack(fill="both", expand=True, padx=24, pady=(12, 4))

        btn_row = tk.Frame(f, bg=PANEL)
        btn_row.pack(pady=(4, 4))
        make_btn(btn_row, "➕ Add Phones", command=self._do_manual_add,
                 color=CYAN).pack(side="left", padx=4)
        make_btn(btn_row, "📲 Start OTP All", command=self._do_manual_otp,
                 color=GREEN, fg="#000000").pack(side="left", padx=4)

        self._manual_status = tk.Label(f, text="", font=FONTS["normal"],
                                        fg=GREEN, bg=PANEL, wraplength=600)
        self._manual_status.pack(pady=4)

    def _do_manual_add(self):
        text = self._manual_text.get("1.0", "end")
        if not text.strip():
            messagebox.showwarning("Add", "Please enter at least one phone number.")
            return
        count, phones = add_phones_manual(text)
        msg = f"Added {count} new phone(s) (status: pending_otp)."
        if count > 0 and self.main_window:
            msg = f"Imported {count} accounts! Tab refreshed."
            self.frame.after(0, self.main_window.refresh_account_tab)
        self._manual_status.config(
            text=msg,
            fg=GREEN if count > 0 else MUTED,
        )

    def _do_manual_otp(self):
        pending = get_pending_otp_accounts()
        if not pending:
            messagebox.showinfo("OTP", "No pending accounts.")
            return
        phones = [a["phone"] for a in pending]
        self._send_otp_to_phones(phones, self._manual_status)

    def _send_otp_to_phones(self, phones: list[str], status_label: tk.Label):
        """Shared helper: send OTP batch and update the given status label."""
        status_label.config(text=f"Sending OTP to {len(phones)} accounts…", fg=MUTED)

        def _run():
            loop = asyncio.new_event_loop()
            try:
                results = loop.run_until_complete(send_otp_batch(phones))
            finally:
                loop.close()
            ok = sum(1 for _, s, _ in results if s)
            status_label.config(
                text=f"OTP sent: {ok}/{len(results)} successful.",
                fg=GREEN if ok > 0 else RED,
            )

        threading.Thread(target=_run, daemon=True).start()
