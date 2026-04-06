"""
gui/finder_tab.py - Member scraping + keyword-based group search
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import asyncio
import csv

from gui.styles import COLORS, FONTS, make_btn
from core.account import list_accounts
from core.finder import (
    scrape_group, list_groups, delete_group, export_csv,
    search_groups_batch, list_found_groups, export_found_groups_txt,
)
from core.keyword_generator import generate_combinations
from core.config import mark_group_search_joined

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

    # ─────────────────────────────────────────────────────────────────────────
    def _build(self):
        nb = ttk.Notebook(self.frame)
        nb.pack(fill="both", expand=True)

        self._build_scrape_tab(nb)
        self._build_search_tab(nb)

    # ─────────────────────────────────────────────────────────────────────────
    # Sub-tab A: Member Scraper
    # ─────────────────────────────────────────────────────────────────────────
    def _build_scrape_tab(self, nb):
        outer = tk.Frame(nb, bg=BG)
        nb.add(outer, text="  👥 Scrape Members  ")

        tk.Label(outer, text="👥 Member Scraper",
                 font=FONTS["heading"], fg=CYAN, bg=BG).pack(anchor="w", padx=20, pady=(12, 4))

        top = tk.LabelFrame(outer, text=" 🎯 Scrape Settings ",
                            bg=PANEL, fg=CYAN, font=FONTS["subheading"])
        top.pack(fill="x", padx=20, pady=(0, 12))

        ctrl = tk.Frame(top, bg=PANEL)
        ctrl.pack(fill="x", padx=16, pady=12)

        row1 = tk.Frame(ctrl, bg=PANEL)
        row1.pack(fill="x", pady=4)
        tk.Label(row1, text="Group Link / Username:", width=24, anchor="w",
                 font=FONTS["normal"], fg=TEXT, bg=PANEL).pack(side="left")
        self._group_var = tk.StringVar()
        tk.Entry(row1, textvariable=self._group_var,
                 bg=CARD, fg=TEXT, insertbackground=TEXT,
                 font=FONTS["normal"], width=40, relief="flat").pack(side="left")

        row2 = tk.Frame(ctrl, bg=PANEL)
        row2.pack(fill="x", pady=4)
        tk.Label(row2, text="Use Account:", width=24, anchor="w",
                 font=FONTS["normal"], fg=TEXT, bg=PANEL).pack(side="left")
        self._scrape_account_var = tk.StringVar()
        self._scrape_account_combo = ttk.Combobox(
            row2, textvariable=self._scrape_account_var,
            font=FONTS["normal"], width=30, state="readonly"
        )
        self._scrape_account_combo.pack(side="left")
        make_btn(row2, "🔄", command=self._reload_scrape_accounts,
                 color=CARD).pack(side="left", padx=4)

        btn_row = tk.Frame(ctrl, bg=PANEL)
        btn_row.pack(fill="x", pady=(12, 0))
        self._scrape_start_btn = make_btn(btn_row, "▶ Start Scrape",
                                          command=self._start_scrape, color=GREEN, fg="#000")
        self._scrape_start_btn.pack(side="left", padx=(0, 8))
        self._scrape_stop_btn = make_btn(btn_row, "⏹ Stop", command=self._stop_scrape, color=RED)
        self._scrape_stop_btn.pack(side="left", padx=(0, 8))
        self._scrape_stop_btn.config(state="disabled")

        self._scrape_progress_var = tk.StringVar(value="")
        tk.Label(ctrl, textvariable=self._scrape_progress_var,
                 font=FONTS["normal"], fg=GREEN, bg=PANEL).pack(anchor="w", pady=(8, 0))
        self._scrape_bar = ttk.Progressbar(ctrl, mode="indeterminate", length=400)
        self._scrape_bar.pack(anchor="w", pady=(4, 0))

        bot = tk.LabelFrame(outer, text=" 📋 Saved Groups ",
                            bg=PANEL, fg=CYAN, font=FONTS["subheading"])
        bot.pack(fill="both", expand=True, padx=20, pady=(0, 12))

        btn_row2 = tk.Frame(bot, bg=PANEL)
        btn_row2.pack(fill="x", padx=16, pady=8)
        make_btn(btn_row2, "💾 Export CSV", command=self._export_csv,
                 color=CYAN, fg="#000").pack(side="left", padx=(0, 8))
        make_btn(btn_row2, "🗑 Delete", command=self._delete_group, color=RED).pack(side="left", padx=(0, 8))
        make_btn(btn_row2, "🔄 Refresh", command=self._refresh_scrape_groups, color=CARD).pack(side="left")

        cols = ("Group", "Members", "Scraped At")
        self._scrape_tree = ttk.Treeview(bot, columns=cols, show="headings", height=8)
        for c, w in zip(cols, [320, 100, 160]):
            self._scrape_tree.heading(c, text=c)
            self._scrape_tree.column(c, width=w, anchor="center")
        sb = ttk.Scrollbar(bot, orient="vertical", command=self._scrape_tree.yview)
        self._scrape_tree.configure(yscrollcommand=sb.set)
        inner = tk.Frame(bot, bg=PANEL)
        inner.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._scrape_tree.pack(side="left", fill="both", expand=True, in_=inner)
        sb.pack(side="right", fill="y", in_=inner)

        self._reload_scrape_accounts()
        self._refresh_scrape_groups()

    def _reload_scrape_accounts(self):
        accounts = list_accounts()
        options = [f"{a['name']} ({a['phone']})" for a in accounts]
        self._scrape_accounts_map = {f"{a['name']} ({a['phone']})": a["phone"] for a in accounts}
        self._scrape_account_combo["values"] = options
        if options:
            self._scrape_account_combo.set(options[0])

    def _refresh_scrape_groups(self):
        for row in self._scrape_tree.get_children():
            self._scrape_tree.delete(row)
        for grp in list_groups():
            self._scrape_tree.insert("", "end", values=(
                grp["group_link"],
                grp["member_count"],
                (grp.get("created_at") or "")[:16],
            ))

    def _selected_scrape_group(self) -> str | None:
        sel = self._scrape_tree.selection()
        return self._scrape_tree.item(sel[0], "values")[0] if sel else None

    def _start_scrape(self):
        group = self._group_var.get().strip()
        phone = self._scrape_accounts_map.get(self._scrape_account_var.get())
        if not group:
            messagebox.showwarning("Missing", "Enter a group link.")
            return
        if not phone:
            messagebox.showwarning("Missing", "Select an account.")
            return

        self._stop_flag = [False]
        self._scrape_start_btn.config(state="disabled")
        self._scrape_stop_btn.config(state="normal")
        self._scrape_bar.start(10)
        self._scrape_progress_var.set("Starting scrape...")

        def on_progress(current, total, msg):
            self.frame.after(0, lambda: self._scrape_progress_var.set(msg))

        def task():
            loop = asyncio.new_event_loop()
            ok, msg, _ = loop.run_until_complete(
                scrape_group(group=group, phone=phone,
                             on_progress=on_progress, stop_flag=self._stop_flag)
            )
            loop.close()

            def after():
                self._scrape_start_btn.config(state="normal")
                self._scrape_stop_btn.config(state="disabled")
                self._scrape_bar.stop()
                self._scrape_progress_var.set(msg)
                self._refresh_scrape_groups()
                if ok:
                    messagebox.showinfo("Done", msg)
                else:
                    messagebox.showerror("Error", msg)

            self.frame.after(0, after)

        threading.Thread(target=task, daemon=True).start()

    def _stop_scrape(self):
        self._stop_flag[0] = True
        self._scrape_stop_btn.config(state="disabled")

    def _export_csv(self):
        group = self._selected_scrape_group()
        if not group:
            messagebox.showwarning("Select", "Select a group to export.")
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
        )
        if not file_path:
            return
        ok, msg = export_csv(group, file_path)
        if ok:
            messagebox.showinfo("Exported", msg)
        else:
            messagebox.showerror("Error", msg)

    def _delete_group(self):
        group = self._selected_scrape_group()
        if not group:
            messagebox.showwarning("Select", "Select a group to delete.")
            return
        if messagebox.askyesno("Confirm", f"Delete group '{group}'?"):
            delete_group(group)
            self._refresh_scrape_groups()

    # ─────────────────────────────────────────────────────────────────────────
    # Sub-tab B: Group Search
    # ─────────────────────────────────────────────────────────────────────────
    def _build_search_tab(self, nb):
        outer = tk.Frame(nb, bg=BG)
        nb.add(outer, text="  🌐 Search Groups  ")

        tk.Label(outer, text="🌐 Keyword Group Search",
                 font=FONTS["heading"], fg=CYAN, bg=BG).pack(anchor="w", padx=20, pady=(12, 4))

        top = tk.LabelFrame(outer, text=" ⚙ Search Settings ",
                            bg=PANEL, fg=CYAN, font=FONTS["subheading"])
        top.pack(fill="x", padx=20, pady=(0, 8))

        ctrl = tk.Frame(top, bg=PANEL)
        ctrl.pack(fill="x", padx=16, pady=10)

        r1 = tk.Frame(ctrl, bg=PANEL)
        r1.pack(fill="x", pady=4)
        tk.Label(r1, text="Keyword:", width=18, anchor="w",
                 font=FONTS["normal"], fg=TEXT, bg=PANEL).pack(side="left")
        self._search_kw_var = tk.StringVar()
        tk.Entry(r1, textvariable=self._search_kw_var,
                 bg=CARD, fg=TEXT, insertbackground=TEXT,
                 font=FONTS["normal"], width=30, relief="flat").pack(side="left")
        self._kw_count_label = tk.Label(r1, text="", font=FONTS["small"], fg=MUTED, bg=PANEL)
        self._kw_count_label.pack(side="left", padx=8)
        make_btn(r1, "Generate Keywords", command=self._generate_keywords,
                 color=COLORS["accent"], fg="#000").pack(side="left", padx=8)

        r2 = tk.Frame(ctrl, bg=PANEL)
        r2.pack(fill="x", pady=4)
        tk.Label(r2, text="Account:", width=18, anchor="w",
                 font=FONTS["normal"], fg=TEXT, bg=PANEL).pack(side="left")
        self._search_account_var = tk.StringVar()
        self._search_account_combo = ttk.Combobox(
            r2, textvariable=self._search_account_var,
            font=FONTS["normal"], width=28, state="readonly"
        )
        self._search_account_combo.pack(side="left")
        make_btn(r2, "🔄", command=self._reload_search_accounts, color=CARD).pack(side="left", padx=4)

        self._groups_only_var = tk.BooleanVar(value=True)
        tk.Checkbutton(ctrl, text="Groups only (exclude channels)",
                       variable=self._groups_only_var,
                       bg=PANEL, fg=TEXT, selectcolor=CARD,
                       font=FONTS["normal"],
                       activebackground=PANEL).pack(anchor="w", pady=4)

        btn_row = tk.Frame(ctrl, bg=PANEL)
        btn_row.pack(fill="x", pady=(8, 0))
        self._search_start_btn = make_btn(btn_row, "▶ Start Search",
                                          command=self._start_search, color=GREEN, fg="#000")
        self._search_start_btn.pack(side="left", padx=(0, 8))
        self._search_stop_btn = make_btn(btn_row, "⏹ Stop",
                                         command=self._stop_search, color=RED)
        self._search_stop_btn.pack(side="left", padx=(0, 8))
        self._search_stop_btn.config(state="disabled")

        prog_frame = tk.Frame(ctrl, bg=PANEL)
        prog_frame.pack(fill="x", pady=(8, 0))
        self._search_progress_var = tk.StringVar(value="")
        tk.Label(prog_frame, textvariable=self._search_progress_var,
                 font=FONTS["normal"], fg=GREEN, bg=PANEL).pack(anchor="w")
        self._search_bar = ttk.Progressbar(prog_frame, mode="determinate", length=500)
        self._search_bar.pack(anchor="w", pady=(4, 0))

        bot = tk.LabelFrame(outer, text=" 📋 Found Groups ",
                            bg=PANEL, fg=CYAN, font=FONTS["subheading"])
        bot.pack(fill="both", expand=True, padx=20, pady=(0, 12))

        btn_row2 = tk.Frame(bot, bg=PANEL)
        btn_row2.pack(fill="x", padx=16, pady=8)
        make_btn(btn_row2, "📄 Export TXT", command=self._export_txt,
                 color=CYAN, fg="#000").pack(side="left", padx=(0, 8))
        make_btn(btn_row2, "📊 Export CSV", command=self._export_search_csv,
                 color=COLORS["accent"], fg="#000").pack(side="left", padx=(0, 8))
        make_btn(btn_row2, "✅ Mark Joined", command=self._mark_joined,
                 color=GREEN, fg="#000").pack(side="left", padx=(0, 8))
        make_btn(btn_row2, "🔄 Refresh", command=self._refresh_search_results,
                 color=CARD).pack(side="left")

        cols = ("Title", "Link", "Members", "Type", "Joined")
        self._search_tree = ttk.Treeview(bot, columns=cols, show="headings", height=10)
        widths = {"Title": 200, "Link": 260, "Members": 90, "Type": 70, "Joined": 70}
        for c in cols:
            self._search_tree.heading(c, text=c)
            self._search_tree.column(c, width=widths[c], anchor="center")
        sb = ttk.Scrollbar(bot, orient="vertical", command=self._search_tree.yview)
        self._search_tree.configure(yscrollcommand=sb.set)
        inner = tk.Frame(bot, bg=PANEL)
        inner.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._search_tree.pack(side="left", fill="both", expand=True, in_=inner)
        sb.pack(side="right", fill="y", in_=inner)

        self._search_keywords: list[str] = []
        self._search_stop_flag = [False]
        self._reload_search_accounts()
        self._refresh_search_results()

    def _reload_search_accounts(self):
        accounts = list_accounts()
        options = [f"{a['name']} ({a['phone']})" for a in accounts]
        self._search_accounts_map = {f"{a['name']} ({a['phone']})": a["phone"] for a in accounts}
        self._search_account_combo["values"] = options
        if options:
            self._search_account_combo.set(options[0])

    def _generate_keywords(self):
        kw = self._search_kw_var.get().strip()
        if not kw:
            messagebox.showwarning("Keyword", "Enter a keyword first.")
            return
        self._search_keywords = generate_combinations(kw)
        self._kw_count_label.config(
            text=f"→ {len(self._search_keywords)} keywords generated", fg=GREEN
        )

    def _refresh_search_results(self):
        for row in self._search_tree.get_children():
            self._search_tree.delete(row)
        groups_only = self._groups_only_var.get() if hasattr(self, "_groups_only_var") else True
        for g in list_found_groups():
            if groups_only and not g.get("is_group", True):
                continue
            entity_type = "Group" if g.get("is_group", True) else "Channel"
            joined_str = "✅" if g.get("joined") else "—"
            self._search_tree.insert("", "end", values=(
                g.get("group_title", ""),
                g.get("group_link", ""),
                g.get("member_count", 0),
                entity_type,
                joined_str,
            ))

    def _start_search(self):
        phone = self._search_accounts_map.get(self._search_account_var.get())
        if not phone:
            messagebox.showwarning("Account", "Select an account first.")
            return

        if not self._search_keywords:
            kw = self._search_kw_var.get().strip()
            if not kw:
                messagebox.showwarning("Keyword", "Enter a keyword or generate keywords first.")
                return
            self._search_keywords = generate_combinations(kw)

        self._search_stop_flag = [False]
        self._search_start_btn.config(state="disabled")
        self._search_stop_btn.config(state="normal")
        self._search_bar["value"] = 0
        self._search_bar["maximum"] = max(len(self._search_keywords), 1)

        def on_progress(i, total, msg):
            def _update():
                self._search_progress_var.set(msg)
                self._search_bar["value"] = i
                self._search_bar["maximum"] = max(total, 1)
            self.frame.after(0, _update)

        keywords = list(self._search_keywords)

        def task():
            loop = asyncio.new_event_loop()
            total_found, searched = loop.run_until_complete(
                search_groups_batch(phone, keywords,
                                    on_progress=on_progress,
                                    stop_flag=self._search_stop_flag)
            )
            loop.close()

            def after():
                self._search_start_btn.config(state="normal")
                self._search_stop_btn.config(state="disabled")
                self._search_progress_var.set(
                    f"Done: found {total_found} groups across {searched} keywords."
                )
                self._refresh_search_results()

            self.frame.after(0, after)

        threading.Thread(target=task, daemon=True).start()

    def _stop_search(self):
        self._search_stop_flag[0] = True
        self._search_stop_btn.config(state="disabled")

    def _selected_search_group(self) -> dict | None:
        sel = self._search_tree.selection()
        if not sel:
            return None
        vals = self._search_tree.item(sel[0], "values")
        return {"title": vals[0], "group_link": vals[1]}

    def _export_txt(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            initialfile="found_groups.txt",
        )
        if not file_path:
            return
        ok, msg = export_found_groups_txt(file_path)
        if ok:
            messagebox.showinfo("Exported", msg)
        else:
            messagebox.showerror("Error", msg)

    def _export_search_csv(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="found_groups.csv",
        )
        if not file_path:
            return
        groups = list_found_groups()
        if not groups:
            messagebox.showinfo("Export", "No groups to export.")
            return
        try:
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=["group_link", "group_title", "member_count", "is_group", "joined", "found_at"],
                )
                writer.writeheader()
                writer.writerows(groups)
            messagebox.showinfo("Exported", f"Exported {len(groups)} groups.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _mark_joined(self):
        grp = self._selected_search_group()
        if not grp:
            messagebox.showwarning("Select", "Select a group to mark as joined.")
            return
        mark_group_search_joined(grp["group_link"])
        self._refresh_search_results()

