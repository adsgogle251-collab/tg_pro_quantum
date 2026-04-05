"""
TG PRO QUANTUM - Import Dialog (Sprint 3)

Tkinter dialog for importing Telegram accounts in three modes:
  1. Session Import  – paste a session string (Ctrl+A)
  2. Bulk Create     – one phone per line
  3. File Upload     – CSV or Excel

Calls the FastAPI backend REST API directly (not the local account_manager).
"""
from __future__ import annotations

import json
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Optional

import requests  # stdlib requests, already in requirements

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

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
    """Load JWT access token from wherever the desktop app stores it."""
    try:
        from core.state_manager import state_manager  # type: ignore
        return state_manager.get("access_token")
    except Exception:
        return None


def _api_headers() -> dict:
    token = _get_token()
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def _post(path: str, json_data: dict | None = None, files=None) -> dict:
    url = f"{_API_BASE}{path}"
    resp = requests.post(url, json=json_data, files=files, headers=_api_headers(), timeout=30)
    resp.raise_for_status()
    return resp.json()


def _fmt_result(result: dict) -> str:
    return (
        f"Status  : {result.get('status', '?')}\n"
        f"Imported: {result.get('imported', 0)}\n"
        f"Skipped : {result.get('skipped', 0)}\n"
        f"Failed  : {result.get('failed_rows', 0)}\n"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Import Dialog
# ─────────────────────────────────────────────────────────────────────────────

class ImportDialog(tk.Toplevel):
    """Tabbed import dialog for account importing (Session / Bulk / File)."""

    def __init__(self, parent, on_imported: Optional[Callable] = None):
        super().__init__(parent)
        self.on_imported = on_imported
        self.title("📥 Import Accounts")
        self.geometry("560x480")
        self.resizable(True, True)
        self.configure(bg=COLORS["bg_dark"])
        self._build_ui()

    # ── UI ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Header
        tk.Label(
            self, text="📥 Import Accounts",
            font=("Segoe UI", 14, "bold"), fg=COLORS["primary"], bg=COLORS["bg_dark"]
        ).pack(pady=(16, 0))

        # Notebook
        style = ttk.Style(self)
        style.configure("TNotebook", background=COLORS["bg_dark"], borderwidth=0)
        style.configure("TNotebook.Tab", background=COLORS["bg_medium"],
                        foreground=COLORS["muted"], padding=[12, 6])
        style.map("TNotebook.Tab", background=[("selected", COLORS["bg_light"])],
                  foreground=[("selected", COLORS["primary"])])

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=16, pady=16)

        self._build_session_tab(nb)
        self._build_bulk_tab(nb)
        self._build_file_tab(nb)

        # Status bar
        self._status_var = tk.StringVar(value="Ready")
        tk.Label(self, textvariable=self._status_var, font=("Segoe UI", 10),
                 fg=COLORS["muted"], bg=COLORS["bg_dark"]).pack(pady=(0, 8))

    # ── Tab 1: Session Import ───────────────────────────────────────────────

    def _build_session_tab(self, nb: ttk.Notebook):
        frame = tk.Frame(nb, bg=COLORS["bg_medium"])
        nb.add(frame, text="Session Import")

        tk.Label(frame, text="Paste session string (Ctrl+A):",
                 fg=COLORS["text"], bg=COLORS["bg_medium"],
                 font=("Segoe UI", 10)).pack(anchor="w", padx=12, pady=(12, 4))

        self._session_text = tk.Text(frame, height=8, font=("Consolas", 9),
                                     bg=COLORS["bg_light"], fg=COLORS["text"],
                                     insertbackground=COLORS["primary"], bd=0, relief="flat")
        self._session_text.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        row = tk.Frame(frame, bg=COLORS["bg_medium"])
        row.pack(fill="x", padx=12, pady=(0, 12))

        tk.Label(row, text="Phone (optional):", fg=COLORS["muted"], bg=COLORS["bg_medium"],
                 font=("Segoe UI", 9)).pack(side="left")
        self._session_phone = tk.Entry(row, width=16, bg=COLORS["bg_light"],
                                       fg=COLORS["text"], insertbackground=COLORS["primary"],
                                       relief="flat")
        self._session_phone.pack(side="left", padx=(6, 12))

        tk.Button(row, text="Import Session", command=self._import_session,
                  bg=COLORS["primary"], fg=COLORS["bg_dark"],
                  font=("Segoe UI", 10, "bold"), relief="flat",
                  cursor="hand2").pack(side="right")

    def _import_session(self):
        text = self._session_text.get("1.0", "end").strip()
        if not text:
            messagebox.showwarning("Missing", "Paste a session string first", parent=self)
            return
        phone = self._session_phone.get().strip() or None
        self._status_var.set("Importing…")
        self._run_async(self._do_import_session, text, phone)

    def _do_import_session(self, text: str, phone: Optional[str]):
        payload = {"session_text": text}
        if phone:
            payload["phone"] = phone
        result = _post("/accounts/import-session", json_data=payload)
        self._finish(result)

    # ── Tab 2: Bulk Create ──────────────────────────────────────────────────

    def _build_bulk_tab(self, nb: ttk.Notebook):
        frame = tk.Frame(nb, bg=COLORS["bg_medium"])
        nb.add(frame, text="Bulk Create")

        help_text = "One account per line. Format: phone  OR  phone | name | api_id | api_hash"
        tk.Label(frame, text=help_text, fg=COLORS["muted"], bg=COLORS["bg_medium"],
                 font=("Segoe UI", 9), wraplength=460, justify="left").pack(
            anchor="w", padx=12, pady=(12, 4))

        self._bulk_text = tk.Text(frame, height=10, font=("Consolas", 9),
                                  bg=COLORS["bg_light"], fg=COLORS["text"],
                                  insertbackground=COLORS["primary"], bd=0, relief="flat")
        self._bulk_text.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        tk.Button(frame, text="Bulk Create Accounts", command=self._bulk_create,
                  bg=COLORS["primary"], fg=COLORS["bg_dark"],
                  font=("Segoe UI", 10, "bold"), relief="flat",
                  cursor="hand2").pack(side="right", padx=12, pady=(0, 12))

    def _bulk_create(self):
        raw = self._bulk_text.get("1.0", "end").strip()
        if not raw:
            messagebox.showwarning("Missing", "Enter at least one phone", parent=self)
            return
        lines = [l.strip() for l in raw.split("\n") if l.strip()]
        accounts = []
        for line in lines:
            parts = [p.strip() for p in line.split("|")]
            acc: dict = {"phone": parts[0]}
            if len(parts) > 1:
                acc["name"] = parts[1]
            if len(parts) > 2:
                try:
                    acc["api_id"] = int(parts[2])
                except ValueError:
                    pass
            if len(parts) > 3:
                acc["api_hash"] = parts[3]
            accounts.append(acc)

        self._status_var.set(f"Creating {len(accounts)} accounts…")
        self._run_async(self._do_bulk_create, accounts)

    def _do_bulk_create(self, accounts: list):
        result = _post("/accounts/bulk-create", json_data={"accounts": accounts})
        self._finish(result)

    # ── Tab 3: File Upload ──────────────────────────────────────────────────

    def _build_file_tab(self, nb: ttk.Notebook):
        frame = tk.Frame(nb, bg=COLORS["bg_medium"])
        nb.add(frame, text="File Upload")

        self._file_path = tk.StringVar(value="No file selected")

        tk.Label(frame, text="Upload a CSV or Excel (.xlsx) file:",
                 fg=COLORS["text"], bg=COLORS["bg_medium"],
                 font=("Segoe UI", 10)).pack(anchor="w", padx=12, pady=(12, 6))

        file_row = tk.Frame(frame, bg=COLORS["bg_medium"])
        file_row.pack(fill="x", padx=12, pady=(0, 8))

        tk.Label(file_row, textvariable=self._file_path, fg=COLORS["muted"],
                 bg=COLORS["bg_medium"], font=("Segoe UI", 9),
                 width=42, anchor="w").pack(side="left")
        tk.Button(file_row, text="Browse…", command=self._browse_file,
                  bg=COLORS["bg_light"], fg=COLORS["text"], relief="flat",
                  cursor="hand2").pack(side="right")

        # Progress bar
        self._progress = ttk.Progressbar(frame, mode="indeterminate", length=430)
        self._progress.pack(padx=12, pady=4)

        tk.Button(frame, text="Upload & Import", command=self._import_file,
                  bg=COLORS["primary"], fg=COLORS["bg_dark"],
                  font=("Segoe UI", 10, "bold"), relief="flat",
                  cursor="hand2").pack(side="right", padx=12, pady=12)

        self._selected_file: Optional[str] = None

    def _browse_file(self):
        path = filedialog.askopenfilename(
            title="Select CSV or Excel file",
            filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx *.xls"), ("All files", "*.*")],
            parent=self,
        )
        if path:
            self._selected_file = path
            self._file_path.set(path.split("/")[-1])

    def _import_file(self):
        if not self._selected_file:
            messagebox.showwarning("Missing", "Select a file first", parent=self)
            return
        self._progress.start()
        self._status_var.set("Uploading…")
        self._run_async(self._do_import_file, self._selected_file)

    def _do_import_file(self, path: str):
        with open(path, "rb") as fh:
            result = _post("/accounts/import-file", files={"file": (path.split("/")[-1], fh)})
        self.after(0, self._progress.stop)
        self._finish(result)

    # ── Async helper ────────────────────────────────────────────────────────

    def _run_async(self, func, *args):
        def worker():
            try:
                func(*args)
            except Exception as exc:
                self.after(0, lambda: self._on_error(str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def _finish(self, result: dict):
        summary = _fmt_result(result)
        self.after(0, lambda: self._on_success(summary))
        if self.on_imported:
            self.after(0, lambda: self.on_imported(result))

    def _on_success(self, summary: str):
        self._progress.stop()
        self._status_var.set("Done")
        messagebox.showinfo("Import Complete", summary, parent=self)

    def _on_error(self, msg: str):
        self._progress.stop()
        self._status_var.set("Error")
        messagebox.showerror("Import Failed", msg, parent=self)
