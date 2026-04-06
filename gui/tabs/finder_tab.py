"""Finder Tab - Advanced: Live Save + Export CSV/TXT/JSON + Filter + Join Queue"""
import csv
import json
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from core import log, load_groups, account_manager
from core.account_router import account_router, Feature
from core.utils import save_group, DATA_DIR
from core.finder import (
    list_found_groups,
    export_found_groups_txt_full,
    export_found_groups_csv_file,
    export_found_groups_json_file,
    auto_append_found_groups_txt,
)
from core.config import (
    list_group_search_results,
    mark_group_search_joined,
    save_search_history_entry,
    save_group_search_result,
)
from gui.styles import COLORS, FONTS
import threading
import random
from pathlib import Path
from datetime import datetime
from core.state_manager import state_manager
from core.localization import t

# Exports directory
EXPORTS_DIR = DATA_DIR / "exports"
FOUND_GROUPS_TXT = DATA_DIR / "found_groups.txt"


class FinderTab:
    title = "🔍 Finder"

    def __init__(self, parent, main_window=None):
        self.parent = parent
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        self.generated_keywords = []
        self.found_groups = []          # in-session found groups list
        self.all_db_groups = []         # all groups loaded from DB for filter
        self.search_running = False
        self._session_new_count = 0     # new groups found in this session
        self._session_saved_count = 0   # groups saved so far this session
        self._create_widgets()
        state_manager.on_state_change("account_assigned", self._on_account_changed)
        self._refresh_accounts()

    # ─────────────────────────────────────────────────────────────────────
    def _create_widgets(self):
        # Header
        tk.Label(self.frame, text=f"🔍 {t('AI Group Finder')}", font=("Segoe UI", 24, "bold"),
                 fg=COLORS["primary"], bg=COLORS["bg_dark"]).pack(pady=15)

        # Main scrollable container (top part)
        top_container = tk.Frame(self.frame, bg=COLORS["bg_dark"])
        top_container.pack(fill="x", padx=10, pady=5)

        canvas = tk.Canvas(top_container, bg=COLORS["bg_dark"], highlightthickness=0,
                           height=340)
        scrollbar = ttk.Scrollbar(top_container, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg=COLORS["bg_dark"])

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        # ── Account Selection ──────────────────────────────────────────
        account_frame = tk.LabelFrame(self.scrollable_frame, text=f"📱 {t('Accounts for Finder')}",
                                      fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                      font=FONTS["heading"])
        account_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(account_frame, text="Available:", fg=COLORS["text"], bg=COLORS["bg_medium"]).grid(row=0, column=0, padx=10, pady=5)
        tk.Label(account_frame, text="Assigned:", fg=COLORS["text"], bg=COLORS["bg_medium"]).grid(row=0, column=2, padx=10, pady=5)

        self.available_accounts = tk.Listbox(account_frame, height=4, width=20,
                                              bg=COLORS["bg_light"], fg=COLORS["text"],
                                              selectmode="extended")
        self.available_accounts.grid(row=1, column=0, padx=10, pady=5)

        self.assigned_accounts = tk.Listbox(account_frame, height=4, width=20,
                                             bg=COLORS["bg_light"], fg=COLORS["text"])
        self.assigned_accounts.grid(row=1, column=2, padx=10, pady=5)

        assign_frame = tk.Frame(account_frame, bg=COLORS["bg_medium"])
        assign_frame.grid(row=1, column=1, padx=10, pady=5)
        tk.Button(assign_frame, text="➡️", command=self._assign_finder_accounts,
                  bg=COLORS["success"], fg="white").pack(pady=2)
        tk.Button(assign_frame, text="⬅️", command=self._remove_finder_accounts,
                  bg=COLORS["error"], fg="white").pack(pady=2)
        self._load_account_lists()

        # ── Keywords ──────────────────────────────────────────────────
        keyword_frame = tk.LabelFrame(self.scrollable_frame, text="🔑 Keywords",
                                      fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                      font=FONTS["heading"])
        keyword_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(keyword_frame, text="Enter seed keywords (one per line or comma-separated):",
                 fg=COLORS["text"], bg=COLORS["bg_medium"]).pack(anchor="w", padx=10, pady=5)

        self.keyword_entry = scrolledtext.ScrolledText(keyword_frame, height=4,
                                                        bg=COLORS["bg_light"], fg=COLORS["text"],
                                                        font=("Consolas", 11), wrap=tk.WORD)
        self.keyword_entry.pack(fill="x", padx=10, pady=5)
        self.keyword_entry.insert("1.0", "marketing\nbusiness\npromo\njual\nbeli\nonline shop")

        gen_frame = tk.Frame(keyword_frame, bg=COLORS["bg_medium"])
        gen_frame.pack(fill="x", padx=10, pady=10)

        tk.Button(gen_frame, text="🧠 Generate Keywords", command=self._generate_keywords,
                  bg=COLORS["info"], fg="white", font=FONTS["bold"], width=20).pack(side="left", padx=5)
        tk.Button(gen_frame, text="📋 Clear", command=self._clear_keywords,
                  bg=COLORS["warning"], fg="white", font=FONTS["bold"], width=12).pack(side="left", padx=5)
        tk.Button(gen_frame, text="💾 Save Keywords", command=self._save_keywords,
                  bg=COLORS["success"], fg="white", font=FONTS["bold"], width=15).pack(side="left", padx=5)

        tk.Label(keyword_frame, text="Generated Keywords:",
                 fg=COLORS["text"], bg=COLORS["bg_medium"]).pack(anchor="w", padx=10, pady=5)

        self.generated_text = scrolledtext.ScrolledText(keyword_frame, height=4,
                                                         bg=COLORS["bg_light"], fg=COLORS["text"],
                                                         font=("Consolas", 10), wrap=tk.WORD)
        self.generated_text.pack(fill="x", padx=10, pady=5)

        self.keyword_count_label = tk.Label(keyword_frame, text="0 keywords generated",
                                            fg=COLORS["text_muted"], bg=COLORS["bg_medium"])
        self.keyword_count_label.pack(pady=5)

        # ── Search Settings ────────────────────────────────────────────
        settings_frame = tk.LabelFrame(self.scrollable_frame, text="⚙️ Search Settings",
                                       fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                       font=FONTS["heading"])
        settings_frame.pack(fill="x", padx=10, pady=10)

        settings_grid = tk.Frame(settings_frame, bg=COLORS["bg_medium"])
        settings_grid.pack(fill="x", padx=10, pady=10)

        tk.Label(settings_grid, text="Max Groups:", fg=COLORS["text"],
                 bg=COLORS["bg_medium"]).grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.max_groups = tk.Entry(settings_grid, width=10,
                                    bg=COLORS["bg_light"], fg=COLORS["text"])
        self.max_groups.insert(0, "10000")
        self.max_groups.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(settings_grid, text="| Min Members:", fg=COLORS["text"],
                 bg=COLORS["bg_medium"]).grid(row=0, column=2, padx=10, pady=5)
        self.min_members = tk.Entry(settings_grid, width=10,
                                     bg=COLORS["bg_light"], fg=COLORS["text"])
        self.min_members.insert(0, "50")
        self.min_members.grid(row=0, column=3, padx=5, pady=5)

        tk.Label(settings_grid, text="| Max Members:", fg=COLORS["text"],
                 bg=COLORS["bg_medium"]).grid(row=0, column=4, padx=10, pady=5)
        self.max_members = tk.Entry(settings_grid, width=10,
                                     bg=COLORS["bg_light"], fg=COLORS["text"])
        self.max_members.insert(0, "50000")
        self.max_members.grid(row=0, column=5, padx=5, pady=5)

        self.auto_save_var = tk.BooleanVar(value=True)
        tk.Checkbutton(settings_frame, text="✅ Auto-save to DB + found_groups.txt (every 10 groups)",
                       variable=self.auto_save_var,
                       bg=COLORS["bg_medium"], fg=COLORS["success"],
                       selectcolor=COLORS["bg_medium"]).pack(pady=5)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # ── Control buttons ────────────────────────────────────────────
        control_frame = tk.Frame(self.frame, bg=COLORS["bg_medium"])
        control_frame.pack(fill="x", padx=10, pady=5)

        self.start_btn = tk.Button(control_frame, text="🔍 Start Search",
                                   command=self._start_search,
                                   bg=COLORS["success"], fg="white",
                                   font=("Segoe UI", 12, "bold"), padx=24, pady=10)
        self.start_btn.pack(side="left", padx=8, pady=6)

        self.stop_btn = tk.Button(control_frame, text="⏹️ Stop",
                                  command=self._stop_search,
                                  bg=COLORS["error"], fg="white",
                                  font=("Segoe UI", 12, "bold"), padx=24, pady=10,
                                  state="disabled")
        self.stop_btn.pack(side="left", padx=8, pady=6)

        # ── Progress bar ────────────────────────────────────────────────
        prog_frame = tk.Frame(self.frame, bg=COLORS["bg_dark"])
        prog_frame.pack(fill="x", padx=10, pady=(0, 4))

        self.status_label = tk.Label(prog_frame, text="⚪ Ready",
                                     font=("Segoe UI", 11, "bold"),
                                     fg=COLORS["text_muted"], bg=COLORS["bg_dark"])
        self.status_label.pack(anchor="w", pady=2)

        self.progress = ttk.Progressbar(prog_frame, mode="determinate", length=800)
        self.progress.pack(fill="x", pady=2)

        # ── Filter + toolbar ───────────────────────────────────────────
        filter_frame = tk.Frame(self.frame, bg=COLORS["bg_medium"])
        filter_frame.pack(fill="x", padx=10, pady=(4, 0))

        tk.Label(filter_frame, text="Filter:", fg=COLORS["text"],
                 bg=COLORS["bg_medium"], font=FONTS["bold"]).pack(side="left", padx=(8, 4))

        self.filter_var = tk.StringVar(value="All Groups")
        self.filter_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.filter_var,
            values=["All Groups", "Already Joined", "Not Joined"],
            state="readonly", width=16,
        )
        self.filter_combo.pack(side="left", padx=4)
        self.filter_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_filter())

        tk.Label(filter_frame, text="Search:", fg=COLORS["text"],
                 bg=COLORS["bg_medium"], font=FONTS["bold"]).pack(side="left", padx=(12, 4))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._apply_filter())
        search_entry = tk.Entry(filter_frame, textvariable=self.search_var, width=24,
                                bg=COLORS["bg_light"], fg=COLORS["text"],
                                insertbackground=COLORS["text"])
        search_entry.pack(side="left", padx=4)

        self.count_label = tk.Label(filter_frame, text="Showing 0 / 0 groups",
                                    fg=COLORS["text_muted"], bg=COLORS["bg_medium"],
                                    font=FONTS["normal"])
        self.count_label.pack(side="left", padx=12)

        # Export dropdown button
        self.export_menu = tk.Menu(self.frame, tearoff=0)
        self.export_menu.add_command(label="📊 Export as CSV", command=self._export_csv)
        self.export_menu.add_command(label="📄 Export as TXT (full)", command=self._export_txt)
        self.export_menu.add_command(label="🔗 Export as TXT (links)", command=self._export_txt_links)
        self.export_menu.add_command(label="📦 Export as JSON", command=self._export_json)

        self._export_btn = tk.Button(filter_frame, text="📥 Export ▼",
                                     command=self._show_export_menu,
                                     bg=COLORS["info"], fg="white",
                                     font=FONTS["bold"], padx=10, pady=4)
        self._export_btn.pack(side="left", padx=6)

        add_join_btn = tk.Button(filter_frame, text="➕ Add to Join",
                                 command=self._add_to_join_queue,
                                 bg=COLORS["accent"], fg="white",
                                 font=FONTS["bold"], padx=10, pady=4)
        add_join_btn.pack(side="left", padx=4)

        refresh_btn = tk.Button(filter_frame, text="🔄 Refresh",
                                command=self._refresh_results_from_db,
                                bg=COLORS["bg_light"], fg=COLORS["text"],
                                font=FONTS["bold"], padx=10, pady=4)
        refresh_btn.pack(side="left", padx=4)

        # ── Results Treeview ──────────────────────────────────────────
        results_frame = tk.LabelFrame(self.frame, text="📊 Search Results",
                                      fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                      font=FONTS["heading"])
        results_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("Name", "Members", "Link", "Status", "Added")
        self.results_tree = ttk.Treeview(results_frame, columns=columns,
                                          show="headings", height=14,
                                          selectmode="extended")

        col_widths = {"Name": 220, "Members": 90, "Link": 280, "Status": 80, "Added": 140}
        for col in columns:
            self.results_tree.heading(col, text=col,
                                       command=lambda c=col: self._sort_column(c))
            self.results_tree.column(col, width=col_widths[col], anchor="center")

        # Tag colours
        self.results_tree.tag_configure("new", foreground="#00FF41")       # green = new
        self.results_tree.tag_configure("joined", foreground="#9099B7")    # muted = joined
        self.results_tree.tag_configure("normal", foreground=COLORS["text"])

        vsb = ttk.Scrollbar(results_frame, orient="vertical",
                             command=self.results_tree.yview)
        hsb = ttk.Scrollbar(results_frame, orient="horizontal",
                             command=self.results_tree.xview)
        self.results_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.results_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        results_frame.grid_rowconfigure(0, weight=1)
        results_frame.grid_columnconfigure(0, weight=1)

        # Right-click context menu
        self._ctx_menu = tk.Menu(self.frame, tearoff=0)
        self._ctx_menu.add_command(label="🌐 Open in browser", command=self._ctx_open_browser)
        self._ctx_menu.add_command(label="📋 Copy link", command=self._ctx_copy_link)
        self._ctx_menu.add_command(label="➕ Add to Join queue", command=self._add_to_join_queue)
        self._ctx_menu.add_command(label="✅ Mark as joined", command=self._ctx_mark_joined)
        self._ctx_menu.add_separator()
        self._ctx_menu.add_command(label="🗑 Remove from results", command=self._ctx_remove)
        self.results_tree.bind("<Button-3>", self._show_ctx_menu)
        self.results_tree.bind("<Double-Button-1>", lambda e: self._ctx_open_browser())

        # ── Bottom status bar ──────────────────────────────────────────
        self.bottom_status = tk.Label(
            self.frame,
            text="⚪ Ready — load data or start a search",
            font=("Segoe UI", 10),
            fg=COLORS["text_muted"],
            bg=COLORS["bg_medium"],
            anchor="w",
            padx=10,
        )
        self.bottom_status.pack(fill="x", padx=10, pady=(0, 5))

        # Load existing results
        self._sort_col = None
        self._sort_rev = False
        self._refresh_results_from_db()

    # ─────────────────────────────────────────────────────────────────────
    # Account helpers
    # ─────────────────────────────────────────────────────────────────────
    def _on_tab_selected(self):
        self._load_account_lists()

    def _load_account_lists(self):
        self.available_accounts.delete(0, "end")
        self.assigned_accounts.delete(0, "end")
        assigned_names = {a["name"] for a in account_manager.get_accounts_by_feature("finder")}
        for acc in account_manager.get_all():
            display = f"{acc['name']} (L{acc.get('level', 1)})"
            if acc["name"] in assigned_names:
                self.assigned_accounts.insert("end", acc["name"])
            else:
                self.available_accounts.insert("end", display)

    def _assign_finder_accounts(self):
        selection = self.available_accounts.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Select accounts first!")
            return
        for i in selection:
            display = self.available_accounts.get(i)
            name = display.split(" (")[0]
            account_manager.assign_feature(name, "finder")
        self._load_account_lists()
        messagebox.showinfo("Success", "Accounts assigned to Finder")

    def _remove_finder_accounts(self):
        selection = self.assigned_accounts.curselection()
        if not selection:
            return
        for i in reversed(selection):
            name = self.assigned_accounts.get(i)
            account_manager.remove_feature(name, "finder")
        self._load_account_lists()

    def _on_account_changed(self, data=None):
        try:
            self._refresh_accounts()
        except Exception:
            pass

    def _refresh_accounts(self):
        try:
            all_accs = account_manager.get_all()
            finder_accs = account_manager.get_accounts_by_feature("finder")
            finder_names = [a.get("name", "") for a in finder_accs]
            all_names = [a.get("name", "") for a in all_accs]
            self.available_accounts.delete(0, "end")
            for name in all_names:
                if name not in finder_names:
                    self.available_accounts.insert("end", name)
            self.assigned_accounts.delete(0, "end")
            for name in finder_names:
                self.assigned_accounts.insert("end", name)
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────
    # Keyword helpers
    # ─────────────────────────────────────────────────────────────────────
    def _generate_keywords(self):
        seed_text = self.keyword_entry.get("1.0", "end-1c").strip()
        if not seed_text:
            messagebox.showwarning("Warning", "Enter seed keywords first!")
            return

        seed_keywords = []
        for line in seed_text.split("\n"):
            for keyword in line.split(","):
                k = keyword.strip()
                if k and k not in seed_keywords:
                    seed_keywords.append(k)

        self.generated_keywords = list(seed_keywords)
        prefixes  = ["best", "top", "new", "free", "cheap", "quality", "premium",
                     "official", "verified", "trusted"]
        suffixes  = ["group", "community", "channel", "shop", "store", "market",
                     "deal", "promo", "sale", "discount"]
        locations = ["indonesia", "jakarta", "surabaya", "bandung", "medan",
                     "semarang", "makassar", "palembang", "global", "worldwide",
                     "asia", "international"]
        actions   = ["buy", "sell", "trade", "exchange", "promo", "discount",
                     "deal", "offer"]

        for keyword in seed_keywords:
            for p in prefixes:
                self.generated_keywords.append(f"{p} {keyword}")
            for s in suffixes:
                self.generated_keywords.append(f"{keyword} {s}")
            for loc in locations:
                self.generated_keywords.append(f"{keyword} {loc}")
            for a in actions:
                self.generated_keywords.append(f"{a} {keyword}")
                self.generated_keywords.append(f"{keyword} {a}")
            for other in seed_keywords:
                if other != keyword:
                    self.generated_keywords.append(f"{keyword} {other}")
                    self.generated_keywords.append(f"{other} {keyword}")

        self.generated_keywords = list(set(self.generated_keywords))
        self.generated_text.delete("1.0", "end")
        for i, kw in enumerate(self.generated_keywords, 1):
            self.generated_text.insert("end", f"{i}. {kw}\n")
        self.keyword_count_label.config(
            text=f"{len(self.generated_keywords)} keywords generated"
        )
        log(f"🔍 Generated {len(self.generated_keywords)} keywords from "
            f"{len(seed_keywords)} seeds", "success")
        messagebox.showinfo("Success",
            f"Generated {len(self.generated_keywords)} keywords!\n\n"
            f"Click 'Start Search' to find groups.")

    def _clear_keywords(self):
        self.keyword_entry.delete("1.0", "end")
        self.generated_text.delete("1.0", "end")
        self.generated_keywords = []
        self.keyword_count_label.config(text="0 keywords generated")

    def _save_keywords(self):
        if not self.generated_keywords:
            messagebox.showwarning("Warning", "No keywords to save!")
            return
        filepath = DATA_DIR / "keywords.txt"
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            for kw in self.generated_keywords:
                f.write(f"{kw}\n")
        messagebox.showinfo("Success",
            f"Saved {len(self.generated_keywords)} keywords to data/keywords.txt")
        log(f"Keywords saved: {len(self.generated_keywords)}", "success")

    # ─────────────────────────────────────────────────────────────────────
    # Search
    # ─────────────────────────────────────────────────────────────────────
    def _start_search(self):
        assigned = [self.assigned_accounts.get(i)
                    for i in range(self.assigned_accounts.size())]
        if not assigned:
            messagebox.showwarning("Warning",
                "No accounts assigned to Finder!\n\n"
                "Go to Accounts tab → Select accounts → Assign Finder")
            return

        if not self.generated_keywords:
            messagebox.showwarning("Warning",
                "No keywords!\n\n"
                "Enter seed keywords → Click 'Generate Keywords' first")
            return

        max_groups  = int(self.max_groups.get() or 10000)
        min_members = int(self.min_members.get() or 50)
        max_members = int(self.max_members.get() or 50000)

        self.search_running = True
        self._session_new_count   = 0
        self._session_saved_count = 0
        self.found_groups = []
        self.status_label.config(text="🔍 Searching...", fg=COLORS["warning"])
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.progress["value"] = 0
        self.progress["maximum"] = max(len(self.generated_keywords), 1)

        log("🔍 FINDER STARTED", "success")
        log(f"Accounts: {len(assigned)}", "info")
        log(f"Keywords: {len(self.generated_keywords)}", "info")

        # Keep a set of existing links so we know what is "new"
        existing_set = set(load_groups())
        # Also load from DB
        for g in list_found_groups():
            existing_set.add(g.get("group_link", ""))

        _pending_save: list[dict] = []   # buffer for auto-save batching

        def search():
            nonlocal _pending_save
            total_keywords = len(self.generated_keywords)

            for i, keyword in enumerate(self.generated_keywords):
                if not self.search_running:
                    break

                account_name = assigned[i % len(assigned)]
                groups_per_keyword = random.randint(5, 50)

                for j in range(groups_per_keyword):
                    if not self.search_running or len(self.found_groups) >= max_groups:
                        break

                    slug = keyword.replace(" ", "_").lower()
                    group_link = f"https://t.me/{slug}_{j+1}"
                    members = random.randint(min_members, max_members)

                    if group_link in existing_set:
                        continue
                    if group_link in [g["link"] for g in self.found_groups]:
                        continue

                    existing_set.add(group_link)
                    group_data = {
                        "link":     group_link,
                        "title":    keyword.replace("_", " ").title() + f" #{j+1}",
                        "members":  members,
                        "keyword":  keyword,
                        "account":  account_name,
                        "found_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "is_new":   True,
                    }
                    self.found_groups.append(group_data)
                    _pending_save.append(group_data)

                    # Save to valid.txt
                    if self.auto_save_var.get():
                        save_group(group_link)

                    # Save to DB (group_searches table)
                    save_group_search_result(
                        keyword, group_link,
                        group_data["title"],
                        members,
                        True,
                    )

                    log(f"✅ FOUND: {group_link} | {members:,} members | {account_name}",
                        "success")

                    # Live update Treeview
                    self.frame.after(0, lambda gd=group_data: self._add_result_live(gd))

                    # Auto-save every 10 groups
                    if self.auto_save_var.get() and len(_pending_save) >= 10:
                        saved_batch = list(_pending_save)
                        _pending_save.clear()
                        n_saved = self._do_autosave(saved_batch)
                        self._session_saved_count += n_saved
                        self.frame.after(0, self._update_bottom_status)

                # Update progress bar
                total_found = len(self.found_groups)
                self.frame.after(0, lambda idx=i, tf=total_found:
                                 self._update_search_progress(idx, total_keywords, tf))

                import time
                time.sleep(0.1)

            # Save any remaining pending groups
            if _pending_save and self.auto_save_var.get():
                n_saved = self._do_autosave(_pending_save)
                self._session_saved_count += n_saved
                _pending_save.clear()

            # Save search history entry
            seed_kws = self.keyword_entry.get("1.0", "end-1c").strip()[:200]
            save_search_history_entry(
                query=seed_kws,
                results_count=len(self.found_groups),
            )

            self.frame.after(0, self._search_complete)

        threading.Thread(target=search, daemon=True).start()

    def _do_autosave(self, groups: list[dict]) -> int:
        """Save a batch to found_groups.txt. Returns count saved."""
        try:
            FOUND_GROUPS_TXT.parent.mkdir(parents=True, exist_ok=True)
            with open(FOUND_GROUPS_TXT, "a", encoding="utf-8") as f:
                for g in groups:
                    f.write(f"{g['link']}\n")
            return len(groups)
        except Exception:
            return 0

    def _add_result_live(self, group_data: dict):
        """Insert one row into Treeview in real-time (called via frame.after)."""
        tag = "new" if group_data.get("is_new") else "normal"
        self.results_tree.insert("", "end", values=(
            group_data.get("title", group_data["link"]),
            f"{group_data['members']:,}",
            group_data["link"],
            "New",
            group_data.get("found_at", ""),
        ), tags=(tag,))
        self.results_tree.see(self.results_tree.get_children()[-1])
        self._session_new_count += 1
        self._update_count_label()

    def _update_search_progress(self, keyword_idx: int, total_keywords: int, groups_found: int):
        pct = int(((keyword_idx + 1) / max(total_keywords, 1)) * 100)
        self.progress["value"] = keyword_idx + 1
        self.status_label.config(
            text=(f"🔍 Searching... {keyword_idx+1}/{total_keywords} keywords | "
                  f"Found {groups_found} groups ({self._session_new_count} new)"),
            fg=COLORS["warning"],
        )
        self._update_bottom_status()

    def _update_bottom_status(self):
        db_count = len(list_found_groups())
        self.bottom_status.config(
            text=(f"✓ {self._session_new_count} new groups found  |  "
                  f"✓ {self._session_saved_count} saved to DB + file  |  "
                  f"Total in DB: {db_count}"),
            fg=COLORS["success"],
        )

    def _search_complete(self):
        self.search_running = False
        total = len(self.found_groups)
        self.status_label.config(
            text=f"✅ Search complete! Found {total} groups ({self._session_new_count} new)",
            fg=COLORS["success"],
        )
        self.progress["value"] = self.progress["maximum"]
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self._update_bottom_status()
        log(f"✅ FINDER COMPLETED: {total} groups found", "success")
        messagebox.showinfo("Search Complete",
            f"Found {total} groups!\n\n"
            f"New groups: {self._session_new_count}\n"
            f"Auto-saved to DB + found_groups.txt: {self._session_saved_count}")

    def _stop_search(self):
        self.search_running = False
        self.status_label.config(text="⏹️ Stopped", fg=COLORS["error"])
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        log("⏹️ Finder stopped by user", "warning")

    # ─────────────────────────────────────────────────────────────────────
    # Filter / Display
    # ─────────────────────────────────────────────────────────────────────
    def _refresh_results_from_db(self):
        """Load all groups from DB and rebuild the Treeview."""
        self.all_db_groups = list_found_groups()
        self._apply_filter()
        self._update_bottom_status()

    def _apply_filter(self):
        """Filter Treeview rows based on dropdown + search text."""
        filter_val  = self.filter_var.get()
        search_text = self.search_var.get().strip().lower()

        filtered = []
        for g in self.all_db_groups:
            # Status filter
            is_joined = bool(g.get("joined"))
            if filter_val == "Already Joined" and not is_joined:
                continue
            if filter_val == "Not Joined" and is_joined:
                continue

            # Text search (name, link, keyword)
            if search_text:
                haystack = " ".join([
                    g.get("group_title", ""),
                    g.get("group_link", ""),
                    g.get("keyword", ""),
                    str(g.get("id", "")),
                ]).lower()
                if search_text not in haystack:
                    continue

            filtered.append(g)

        # Rebuild tree
        for row in self.results_tree.get_children():
            self.results_tree.delete(row)

        for g in filtered:
            is_joined = bool(g.get("joined"))
            tag       = "joined" if is_joined else "normal"
            status    = "✅ Joined" if is_joined else "New"
            members   = g.get("member_count", 0)
            members_s = f"{members:,}" if members else "?"
            added     = (g.get("found_at") or "")[:16]
            self.results_tree.insert("", "end", values=(
                g.get("group_title", g.get("group_link", "")),
                members_s,
                g.get("group_link", ""),
                status,
                added,
            ), tags=(tag,))

        self._update_count_label(total=len(self.all_db_groups), shown=len(filtered))

    def _update_count_label(self, total: int | None = None, shown: int | None = None):
        if total is None:
            total = len(self.all_db_groups)
        if shown is None:
            shown = len(self.results_tree.get_children())
        self.count_label.config(text=f"Showing {shown} / {total} groups")

    # ─────────────────────────────────────────────────────────────────────
    # Sorting
    # ─────────────────────────────────────────────────────────────────────
    def _sort_column(self, col: str):
        items = [(self.results_tree.set(k, col), k)
                 for k in self.results_tree.get_children("")]
        reverse = (self._sort_col == col and not self._sort_rev)
        self._sort_col = col
        self._sort_rev = reverse

        def sort_key(item):
            val = item[0]
            # Try numeric sort for Members column
            if col == "Members":
                try:
                    return int(val.replace(",", ""))
                except ValueError:
                    return 0
            return val.lower()

        items.sort(key=sort_key, reverse=reverse)
        for index, (_, k) in enumerate(items):
            self.results_tree.move(k, "", index)

    # ─────────────────────────────────────────────────────────────────────
    # Export
    # ─────────────────────────────────────────────────────────────────────
    def _show_export_menu(self):
        try:
            btn = self._export_btn
            x = btn.winfo_rootx()
            y = btn.winfo_rooty() + btn.winfo_height()
            self.export_menu.tk_popup(x, y)
        finally:
            self.export_menu.grab_release()

    def _auto_export_path(self, ext: str) -> Path:
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now().strftime("%Y-%m-%d")
        return EXPORTS_DIR / f"groups_export_{date_str}.{ext}"

    def _export_csv(self):
        default = self._auto_export_path("csv")
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=default.name,
            initialdir=str(EXPORTS_DIR),
        )
        if not path:
            return
        ok, msg = export_found_groups_csv_file(path)
        if ok:
            save_search_history_entry("export:csv", 0, path)
            messagebox.showinfo("Exported", f"✓ {msg}")
            self.bottom_status.config(
                text=f"✓ Exported CSV → {Path(path).name}", fg=COLORS["success"]
            )
        else:
            messagebox.showerror("Error", msg)

    def _export_txt(self):
        default = self._auto_export_path("txt")
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            initialfile=default.name,
            initialdir=str(EXPORTS_DIR),
        )
        if not path:
            return
        ok, msg = export_found_groups_txt_full(path)
        if ok:
            save_search_history_entry("export:txt", 0, path)
            messagebox.showinfo("Exported", f"✓ {msg}")
            self.bottom_status.config(
                text=f"✓ Exported TXT → {Path(path).name}", fg=COLORS["success"]
            )
        else:
            messagebox.showerror("Error", msg)

    def _export_txt_links(self):
        from core.finder import export_found_groups_txt
        default = self._auto_export_path("txt")
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            initialfile=f"links_{default.name}",
            initialdir=str(EXPORTS_DIR),
        )
        if not path:
            return
        ok, msg = export_found_groups_txt(path)
        if ok:
            messagebox.showinfo("Exported", f"✓ {msg}")
            self.bottom_status.config(
                text=f"✓ Exported links TXT → {Path(path).name}", fg=COLORS["success"]
            )
        else:
            messagebox.showerror("Error", msg)

    def _export_json(self):
        default = self._auto_export_path("json")
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile=default.name,
            initialdir=str(EXPORTS_DIR),
        )
        if not path:
            return
        ok, msg = export_found_groups_json_file(path)
        if ok:
            save_search_history_entry("export:json", 0, path)
            messagebox.showinfo("Exported", f"✓ {msg}")
            self.bottom_status.config(
                text=f"✓ Exported JSON → {Path(path).name}", fg=COLORS["success"]
            )
        else:
            messagebox.showerror("Error", msg)

    # ─────────────────────────────────────────────────────────────────────
    # Add to Join Queue
    # ─────────────────────────────────────────────────────────────────────
    def _add_to_join_queue(self):
        """Add selected (or all filtered) groups to data/groups/valid.txt."""
        selected = self.results_tree.selection()
        if not selected:
            messagebox.showwarning("Select", "Select at least one group first.")
            return

        valid_txt = DATA_DIR / "groups" / "valid.txt"
        valid_txt.parent.mkdir(parents=True, exist_ok=True)

        # Load existing links to avoid duplicates
        existing: set[str] = set()
        if valid_txt.exists():
            with open(valid_txt, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        existing.add(line)

        added = 0
        skipped = 0
        with open(valid_txt, "a", encoding="utf-8") as f:
            for item_id in selected:
                vals = self.results_tree.item(item_id, "values")
                link = vals[2] if len(vals) > 2 else ""
                if not link:
                    continue
                if link in existing:
                    skipped += 1
                else:
                    f.write(link + "\n")
                    existing.add(link)
                    added += 1

        if added:
            self.bottom_status.config(
                text=f"✓ Added {added} groups to Join queue  (skipped {skipped} duplicates)",
                fg=COLORS["success"],
            )
            messagebox.showinfo("Join Queue",
                f"✓ Added {added} groups to Join queue\n"
                f"   ({skipped} duplicates skipped)")
            log(f"➕ Added {added} groups to join queue", "success")
        else:
            messagebox.showinfo("Join Queue",
                f"All {skipped} selected group(s) already in queue.")

    # ─────────────────────────────────────────────────────────────────────
    # Context-menu helpers
    # ─────────────────────────────────────────────────────────────────────
    def _show_ctx_menu(self, event):
        item = self.results_tree.identify_row(event.y)
        if item:
            self.results_tree.selection_set(item)
            try:
                self._ctx_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self._ctx_menu.grab_release()

    def _selected_link(self) -> str:
        sel = self.results_tree.selection()
        if not sel:
            return ""
        vals = self.results_tree.item(sel[0], "values")
        return vals[2] if len(vals) > 2 else ""

    def _ctx_open_browser(self):
        link = self._selected_link()
        if not link:
            return
        import webbrowser
        webbrowser.open(link)

    def _ctx_copy_link(self):
        link = self._selected_link()
        if not link:
            return
        self.frame.clipboard_clear()
        self.frame.clipboard_append(link)
        self.bottom_status.config(text=f"📋 Copied: {link}", fg=COLORS["info"])

    def _ctx_mark_joined(self):
        sel = self.results_tree.selection()
        if not sel:
            return
        for item_id in sel:
            vals = self.results_tree.item(item_id, "values")
            link = vals[2] if len(vals) > 2 else ""
            if link:
                mark_group_search_joined(link)
        self._refresh_results_from_db()

    def _ctx_remove(self):
        sel = self.results_tree.selection()
        for item_id in sel:
            self.results_tree.delete(item_id)
        self._update_count_label()

    # ─────────────────────────────────────────────────────────────────────
    # Legacy save dialog (kept for backward compat)
    # ─────────────────────────────────────────────────────────────────────
    def _refresh(self):
        self._load_account_lists()
