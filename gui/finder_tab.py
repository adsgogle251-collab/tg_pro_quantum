"""
gui/finder_tab.py - Scrape members from Telegram groups
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import asyncio

from gui.styles import COLORS, FONTS, make_btn
from core.account import list_accounts
from core.finder import scrape_group, list_groups, delete_group, export_csv

BG    = COLORS["bg_dark"]
PANEL = COLORS["bg_medium"]
CARD  = COLORS["bg_light"]
CYAN  = COLORS["primary"]
GREEN = COLORS["success"]
RED   = COLORS["error"]
TEXT  = COLORS["text"]
MUTED = COLORS["text_muted"]
ORANGE = COLORS["warning"]


class FinderTab:
    title = "🔍 Finder"

    def __init__(self, parent, main_window=None):
        self.parent = parent
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        self._stop_flag = [False]
        self._build()
        self._refresh_groups()

    # ─────────────────────────────────────────────────────────────────────────
    def _build(self):
        outer = tk.Frame(self.frame, bg=BG)
        outer.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        tk.Label(outer, text="🔍 Member Finder",
                 font=FONTS["heading_large"], fg=CYAN, bg=BG).pack(anchor="w", pady=(0, 12))

        # ── Top panel: scrape controls ─────────────────────────────────────────
        top = tk.LabelFrame(outer, text=" 🎯 Scrape Settings ",
                            bg=PANEL, fg=CYAN, font=FONTS["subheading"])
        top.pack(fill="x", pady=(0, 12))

        ctrl = tk.Frame(top, bg=PANEL)
        ctrl.pack(fill="x", padx=16, pady=12)

        # Group link
        row1 = tk.Frame(ctrl, bg=PANEL)
        row1.pack(fill="x", pady=4)
        tk.Label(row1, text="Group Link / Username:", width=22, anchor="w",
                 font=FONTS["normal"], fg=TEXT, bg=PANEL).pack(side="left")
        self._group_var = tk.StringVar()
        tk.Entry(row1, textvariable=self._group_var,
                 bg=CARD, fg=TEXT, insertbackground=TEXT,
                 font=FONTS["normal"], width=40, relief="flat").pack(side="left")
        tk.Label(row1, text="e.g. @mygroup or t.me/mygroup",
                 font=FONTS["small"], fg=MUTED, bg=PANEL).pack(side="left", padx=8)

        # Account selection
        row2 = tk.Frame(ctrl, bg=PANEL)
        row2.pack(fill="x", pady=4)
        tk.Label(row2, text="Use Account:", width=22, anchor="w",
                 font=FONTS["normal"], fg=TEXT, bg=PANEL).pack(side="left")
        self._account_var = tk.StringVar()
        self._account_combo = ttk.Combobox(
            row2, textvariable=self._account_var,
            font=FONTS["normal"], width=30, state="readonly"
        )
        self._account_combo.pack(side="left")
        make_btn(row2, "🔄", command=self._reload_accounts,
                 color=CARD).pack(side="left", padx=4)

        # Buttons
        btn_row = tk.Frame(ctrl, bg=PANEL)
        btn_row.pack(fill="x", pady=(12, 0))
        self._start_btn = make_btn(btn_row, "▶️ Start Scrape", command=self._start_scrape,
                                   color=GREEN, fg="#000")
        self._start_btn.pack(side="left", padx=(0, 8))
        self._stop_btn = make_btn(btn_row, "⏹️ Stop", command=self._stop_scrape,
                                  color=RED)
        self._stop_btn.pack(side="left", padx=(0, 8))
        self._stop_btn.config(state="disabled")

        # Progress
        self._progress_var = tk.StringVar(value="")
        tk.Label(ctrl, textvariable=self._progress_var,
                 font=FONTS["normal"], fg=GREEN, bg=PANEL).pack(anchor="w", pady=(8, 0))

        self._progress_bar = ttk.Progressbar(ctrl, mode="indeterminate", length=400)
        self._progress_bar.pack(anchor="w", pady=(4, 0))

        # ── Saved groups ───────────────────────────────────────────────────────
        bot = tk.LabelFrame(outer, text=" 📋 Saved Groups ",
                            bg=PANEL, fg=CYAN, font=FONTS["subheading"])
        bot.pack(fill="both", expand=True, pady=(0, 0))

        btn_row2 = tk.Frame(bot, bg=PANEL)
        btn_row2.pack(fill="x", padx=16, pady=8)
        make_btn(btn_row2, "💾 Export CSV", command=self._export_csv,
                 color=CYAN, fg="#000").pack(side="left", padx=(0, 8))
        make_btn(btn_row2, "🗑️ Delete Group", command=self._delete_group,
                 color=RED).pack(side="left", padx=(0, 8))
        make_btn(btn_row2, "🔄 Refresh", command=self._refresh_groups,
                 color=CARD).pack(side="left")

        cols = ("Group", "Members", "Scraped At")
        self._tree = ttk.Treeview(bot, columns=cols, show="headings", height=10)
        widths = {"Group": 280, "Members": 100, "Scraped At": 160}
        for c in cols:
            self._tree.heading(c, text=c)
            self._tree.column(c, width=widths[c], anchor="center")
        sb = ttk.Scrollbar(bot, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        inner_bot = tk.Frame(bot, bg=PANEL)
        inner_bot.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._tree.pack(side="left", fill="both", expand=True, in_=inner_bot)
        sb.pack(side="right", fill="y", in_=inner_bot)

        self._reload_accounts()

    # ─────────────────────────────────────────────────────────────────────────
    def _reload_accounts(self):
        accounts = list_accounts()
        options = [f"{a['name']} ({a['phone']})" for a in accounts]
        self._accounts_map = {f"{a['name']} ({a['phone']})": a["phone"] for a in accounts}
        self._account_combo["values"] = options
        if options:
            self._account_combo.set(options[0])

    def _refresh_groups(self):
        for row in self._tree.get_children():
            self._tree.delete(row)
        for grp in list_groups():
            self._tree.insert("", "end", values=(
                grp["group_link"],
                grp["member_count"],
                (grp.get("created_at") or "")[:16],
            ))

    def _selected_group(self) -> str | None:
        sel = self._tree.selection()
        if not sel:
            return None
        return self._tree.item(sel[0], "values")[0]

    def _start_scrape(self):
        group = self._group_var.get().strip()
        acct_label = self._account_var.get()
        if not group:
            messagebox.showwarning("Missing", "Enter a group link.")
            return
        phone = self._accounts_map.get(acct_label)
        if not phone:
            messagebox.showwarning("Missing", "Select an account.")
            return

        self._stop_flag = [False]
        self._start_btn.config(state="disabled")
        self._stop_btn.config(state="normal")
        self._progress_bar.start(10)
        self._progress_var.set("Starting scrape...")

        def on_progress(current, total, msg):
            self.frame.after(0, lambda: self._progress_var.set(msg))

        def task():
            loop = asyncio.new_event_loop()
            ok, msg, members = loop.run_until_complete(
                scrape_group(phone, group, on_progress=on_progress, stop_flag=self._stop_flag)
            )
            loop.close()
            def after():
                self._start_btn.config(state="normal")
                self._stop_btn.config(state="disabled")
                self._progress_bar.stop()
                self._progress_var.set(msg)
                self._refresh_groups()
                if ok:
                    messagebox.showinfo("Done", msg)
                else:
                    messagebox.showerror("Error", msg)
            self.frame.after(0, after)

        threading.Thread(target=task, daemon=True).start()

    def _stop_scrape(self):
        self._stop_flag[0] = True
        self._stop_btn.config(state="disabled")

    def _export_csv(self):
        group = self._selected_group()
        if not group:
            messagebox.showwarning("Select", "Select a group to export.")
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"{group.replace('@', '').replace('/', '_')}_members.csv"
        )
        if not file_path:
            return
        ok, msg = export_csv(group, file_path)
        if ok:
            messagebox.showinfo("Exported", msg)
        else:
            messagebox.showerror("Error", msg)

    def _delete_group(self):
        group = self._selected_group()
        if not group:
            messagebox.showwarning("Select", "Select a group to delete.")
            return
        if messagebox.askyesno("Confirm", f"Delete group '{group}'?"):
            delete_group(group)
            self._refresh_groups()
