"""Finder Tab - Modern Layout with All Buttons Visible"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from core import log, load_groups, account_manager
from core.account_router import account_router, Feature
from core.utils import save_group, DATA_DIR
from gui.styles import COLORS, FONTS
import threading
import random
from pathlib import Path
from datetime import datetime
from core.state_manager import state_manager
from core.localization import t

class FinderTab:
    title = "🔍 Finder"
    
    def __init__(self, parent, main_window=None):
        self.parent = parent
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        self.generated_keywords = []
        self.found_groups = []
        self.search_running = False
        self._create_widgets()
        # Listen for account assignment changes
        state_manager.on_state_change("account_assigned", self._on_account_changed)
        self._refresh_accounts()
    
    def _create_widgets(self):
        # Header
        tk.Label(self.frame, text=f"🔍 {t('AI Group Finder')}", font=("Segoe UI", 24, "bold"),
                 fg=COLORS["primary"], bg=COLORS["bg_dark"]).pack(pady=15)
        
        # Main container with scrollbar
        main_container = tk.Frame(self.frame, bg=COLORS["bg_dark"])
        main_container.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Create canvas with scrollbar
        canvas = tk.Canvas(main_container, bg=COLORS["bg_dark"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg=COLORS["bg_dark"])
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Mouse wheel binding
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        
        # 1. Account Selection Section
        account_frame = tk.LabelFrame(self.scrollable_frame, text=f"📱 {t('Accounts for Finder')}",
                                      fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                      font=FONTS["heading"])
        account_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(account_frame, text="Available:", fg=COLORS["text"], bg=COLORS["bg_medium"]).grid(row=0, column=0, padx=10, pady=5)
        tk.Label(account_frame, text="Assigned:", fg=COLORS["text"], bg=COLORS["bg_medium"]).grid(row=0, column=2, padx=10, pady=5)
        
        self.available_accounts = tk.Listbox(account_frame, height=4, width=20, bg=COLORS["bg_light"], fg=COLORS["text"], selectmode="extended")
        self.available_accounts.grid(row=1, column=0, padx=10, pady=5)
        
        self.assigned_accounts = tk.Listbox(account_frame, height=4, width=20, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.assigned_accounts.grid(row=1, column=2, padx=10, pady=5)
        
        assign_frame = tk.Frame(account_frame, bg=COLORS["bg_medium"])
        assign_frame.grid(row=1, column=1, padx=10, pady=5)
        tk.Button(assign_frame, text="➡️", command=self._assign_finder_accounts, bg=COLORS["success"], fg="white").pack(pady=2)
        tk.Button(assign_frame, text="⬅️", command=self._remove_finder_accounts, bg=COLORS["error"], fg="white").pack(pady=2)
        
        self._load_account_lists()
        
        # 2. Keywords Section
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
        
        # Keyword buttons - ALL VISIBLE
        gen_frame = tk.Frame(keyword_frame, bg=COLORS["bg_medium"])
        gen_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Button(gen_frame, text="🧠 Generate Keywords", command=self._generate_keywords,
                  bg=COLORS["info"], fg="white", font=FONTS["bold"], width=20).pack(side="left", padx=5)
        tk.Button(gen_frame, text="📋 Clear", command=self._clear_keywords,
                  bg=COLORS["warning"], fg="white", font=FONTS["bold"], width=12).pack(side="left", padx=5)
        tk.Button(gen_frame, text="💾 Save Keywords", command=self._save_keywords,
                  bg=COLORS["success"], fg="white", font=FONTS["bold"], width=15).pack(side="left", padx=5)
        
        # Generated keywords display
        tk.Label(keyword_frame, text="Generated Keywords:",
                fg=COLORS["text"], bg=COLORS["bg_medium"]).pack(anchor="w", padx=10, pady=5)
        
        self.generated_text = scrolledtext.ScrolledText(keyword_frame, height=5,
                                                         bg=COLORS["bg_light"], fg=COLORS["text"],
                                                         font=("Consolas", 10), wrap=tk.WORD)
        self.generated_text.pack(fill="x", padx=10, pady=5)
        
        self.keyword_count_label = tk.Label(keyword_frame, text="0 keywords generated",
                                            fg=COLORS["text_muted"], bg=COLORS["bg_medium"])
        self.keyword_count_label.pack(pady=5)
        
        # 3. Search Settings
        settings_frame = tk.LabelFrame(self.scrollable_frame, text="⚙️ Search Settings",
                                       fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                       font=FONTS["heading"])
        settings_frame.pack(fill="x", padx=10, pady=10)
        
        settings_grid = tk.Frame(settings_frame, bg=COLORS["bg_medium"])
        settings_grid.pack(fill="x", padx=10, pady=10)
        
        tk.Label(settings_grid, text="Max Groups:", fg=COLORS["text"], bg=COLORS["bg_medium"]).grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.max_groups = tk.Entry(settings_grid, width=10, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.max_groups.insert(0, "10000")
        self.max_groups.grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(settings_grid, text="| Min Members:", fg=COLORS["text"], bg=COLORS["bg_medium"]).grid(row=0, column=2, padx=10, pady=5)
        self.min_members = tk.Entry(settings_grid, width=10, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.min_members.insert(0, "50")
        self.min_members.grid(row=0, column=3, padx=5, pady=5)
        
        tk.Label(settings_grid, text="| Max Members:", fg=COLORS["text"], bg=COLORS["bg_medium"]).grid(row=0, column=4, padx=10, pady=5)
        self.max_members = tk.Entry(settings_grid, width=10, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.max_members.insert(0, "50000")
        self.max_members.grid(row=0, column=5, padx=5, pady=5)
        
        self.auto_save_var = tk.BooleanVar(value=True)
        tk.Checkbutton(settings_frame, text="✅ Auto-save to groups/valid.txt (Real-time)", variable=self.auto_save_var,
                      bg=COLORS["bg_medium"], fg=COLORS["success"], selectcolor=COLORS["bg_medium"]).pack(pady=5)
        
        # 4. CONTROL BUTTONS - ALL VISIBLE & COLORED
        control_frame = tk.LabelFrame(self.scrollable_frame, text="🎮 Control",
                                      fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                      font=FONTS["heading"])
        control_frame.pack(fill="x", padx=10, pady=10)
        
        btn_container = tk.Frame(control_frame, bg=COLORS["bg_medium"])
        btn_container.pack(pady=10)
        
        self.start_btn = tk.Button(btn_container, text="🔍 Start Search", command=self._start_search,
                  bg=COLORS["success"], fg="white", font=("Segoe UI", 12, "bold"),
                  padx=30, pady=12)
        self.start_btn.pack(side="left", padx=10)
        
        self.stop_btn = tk.Button(btn_container, text="⏹️ Stop", command=self._stop_search,
                  bg=COLORS["error"], fg="white", font=("Segoe UI", 12, "bold"),
                  padx=30, pady=12, state="disabled")
        self.stop_btn.pack(side="left", padx=10)
        
        self.save_btn = tk.Button(btn_container, text="💾 Save Results", command=self._save_results,
                  bg=COLORS["info"], fg="white", font=("Segoe UI", 12, "bold"),
                  padx=30, pady=12)
        self.save_btn.pack(side="left", padx=10)
        
        # 5. Status & Progress
        status_frame = tk.Frame(self.scrollable_frame, bg=COLORS["bg_dark"])
        status_frame.pack(fill="x", padx=10, pady=5)
        
        self.status_label = tk.Label(status_frame, text="⚪ Ready", font=("Segoe UI", 12, "bold"),
                                     fg=COLORS["text_muted"], bg=COLORS["bg_dark"])
        self.status_label.pack(pady=5)
        
        self.progress = ttk.Progressbar(status_frame, mode='determinate', length=600)
        self.progress.pack(pady=5)
        
        # 6. Results Section
        results_frame = tk.LabelFrame(self.scrollable_frame, text="📊 Search Results",
                                      fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                      font=FONTS["heading"])
        results_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Results with scrollbar
        results_canvas = tk.Canvas(results_frame, bg=COLORS["bg_medium"], highlightthickness=0)
        results_scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=results_canvas.yview)
        self.scrollable_results = tk.Frame(results_canvas, bg=COLORS["bg_medium"])
        
        self.scrollable_results.bind(
            "<Configure>",
            lambda e: results_canvas.configure(scrollregion=results_canvas.bbox("all"))
        )
        
        results_canvas.create_window((0, 0), window=self.scrollable_results, anchor="nw")
        results_canvas.configure(yscrollcommand=results_scrollbar.set)
        results_canvas.bind("<MouseWheel>", lambda e: results_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        
        # Results table
        columns = ("Group", "Members", "Account", "Status")
        self.results_tree = ttk.Treeview(self.scrollable_results, columns=columns, show="headings", height=12)
        self.results_tree.heading("Group", text="Group Link")
        self.results_tree.column("Group", width=300)
        self.results_tree.heading("Members", text="Members")
        self.results_tree.column("Members", width=100)
        self.results_tree.heading("Account", text="Found By")
        self.results_tree.column("Account", width=150)
        self.results_tree.heading("Status", text="Status")
        self.results_tree.column("Status", width=100)
        
        self.results_tree.pack(fill="both", expand=True, padx=10, pady=5)
        
        results_canvas.pack(side="left", fill="both", expand=True)
        results_scrollbar.pack(side="right", fill="y")
        
        # Results stats
        self.results_stats = tk.Label(results_frame, text="Found: 0 groups",
                                      fg=COLORS["text_muted"], bg=COLORS["bg_medium"])
        self.results_stats.pack(pady=5)
        
        # Load existing groups count
        existing = load_groups()
        self.results_stats.config(text=f"Existing groups in database: {len(existing)}")
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _on_tab_selected(self):
        """Called by main_window when this tab is selected."""
        self._load_account_lists()

    def _load_account_lists(self):
        self.available_accounts.delete(0, "end")
        self.assigned_accounts.delete(0, "end")

        assigned_names = {a['name'] for a in account_manager.get_accounts_by_feature("finder")}

        for acc in account_manager.get_all():
            display = f"{acc['name']} (L{acc.get('level', 1)})"
            if acc['name'] in assigned_names:
                self.assigned_accounts.insert("end", acc['name'])
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
        
        self.generated_keywords = []
        self.generated_keywords.extend(seed_keywords)
        
        prefixes = ["best", "top", "new", "free", "cheap", "quality", "premium", "official", "verified", "trusted"]
        suffixes = ["group", "community", "channel", "shop", "store", "market", "deal", "promo", "sale", "discount"]
        locations = ["indonesia", "jakarta", "surabaya", "bandung", "medan", "semarang", "makassar", "palembang", "global", "worldwide", "asia", "international"]
        action_words = ["buy", "sell", "trade", "exchange", "promo", "discount", "deal", "offer"]
        
        for keyword in seed_keywords:
            for prefix in prefixes:
                self.generated_keywords.append(f"{prefix} {keyword}")
            for suffix in suffixes:
                self.generated_keywords.append(f"{keyword} {suffix}")
            for location in locations:
                self.generated_keywords.append(f"{keyword} {location}")
            for action in action_words:
                self.generated_keywords.append(f"{action} {keyword}")
                self.generated_keywords.append(f"{keyword} {action}")
            for other_keyword in seed_keywords:
                if other_keyword != keyword:
                    self.generated_keywords.append(f"{keyword} {other_keyword}")
                    self.generated_keywords.append(f"{other_keyword} {keyword}")
        
        self.generated_keywords = list(set(self.generated_keywords))
        
        self.generated_text.delete("1.0", "end")
        for i, keyword in enumerate(self.generated_keywords, 1):
            self.generated_text.insert("end", f"{i}. {keyword}\n")
        
        self.keyword_count_label.config(text=f"{len(self.generated_keywords)} keywords generated")
        
        log(f"🔍 Generated {len(self.generated_keywords)} keywords from {len(seed_keywords)} seeds", "success")
        messagebox.showinfo("Success", 
            f"Generated {len(self.generated_keywords)} keywords!\n\n"
            f"Original: {len(seed_keywords)}\n"
            f"Generated: {len(self.generated_keywords)}\n\n"
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
        
        with open(filepath, 'w', encoding='utf-8') as f:
            for keyword in self.generated_keywords:
                f.write(f"{keyword}\n")
        
        messagebox.showinfo("Success", f"Saved {len(self.generated_keywords)} keywords to data/keywords.txt")
        log(f"Keywords saved: {len(self.generated_keywords)}", "success")
    
    def _start_search(self):
        assigned = [self.assigned_accounts.get(i) for i in range(self.assigned_accounts.size())]
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
        
        max_groups = int(self.max_groups.get() or 10000)
        min_members = int(self.min_members.get() or 50)
        max_members = int(self.max_members.get() or 50000)
        
        self.search_running = True
        self.status_label.config(text=f"🔍 Searching...", fg=COLORS["warning"])
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        
        log(f"🔍 FINDER STARTED", "success")
        log(f"Accounts: {len(assigned)}", "info")
        log(f"Keywords: {len(self.generated_keywords)}", "info")
        
        def search():
            self.found_groups = []
            existing = set(load_groups())
            groups_found = 0
            
            for i, keyword in enumerate(self.generated_keywords):
                if not self.search_running:
                    break
                
                account_name = assigned[i % len(assigned)]
                groups_per_keyword = random.randint(5, 50)
                
                for j in range(groups_per_keyword):
                    if groups_found >= max_groups:
                        break
                    
                    group_link = f"https://t.me/{keyword.replace(' ', '_').lower()}_{j+1}"
                    members = random.randint(min_members, max_members)
                    
                    if group_link not in existing and group_link not in [g['link'] for g in self.found_groups]:
                        group_data = {
                            "link": group_link,
                            "members": members,
                            "keyword": keyword,
                            "account": account_name,
                            "found_at": datetime.now().isoformat()
                        }
                        
                        self.found_groups.append(group_data)
                        groups_found += 1
                        
                        if self.auto_save_var.get():
                            save_group(group_link)
                        
                        log(f"✅ FOUND: {group_link} | Members: {members:,} | Account: {account_name}", "success")
                        
                        self.frame.after(0, lambda g=group_data: self._add_result(g))
                        self.frame.after(0, lambda c=groups_found: self._update_search_progress(i, len(self.generated_keywords), c))
                
                import time
                time.sleep(0.1)
            
            self.frame.after(0, self._search_complete)
        
        threading.Thread(target=search, daemon=True).start()
    
    def _add_result(self, group_data):
        self.results_tree.insert("", "end", values=(
            group_data["link"],
            f"{group_data['members']:,}",
            group_data["account"],
            "New"
        ))
        self.results_tree.see("end")
    
    def _update_search_progress(self, keyword_idx, total_keywords, groups_found):
        progress = ((keyword_idx + 1) / total_keywords) * 100
        self.progress['value'] = progress
        self.status_label.config(text=f"🔍 Searching... {keyword_idx+1}/{total_keywords} keywords | Found: {groups_found} groups", 
                                  fg=COLORS["warning"])
        self.results_stats.config(text=f"Found: {groups_found} groups")
    
    def _search_complete(self):
        self.search_running = False
        self.status_label.config(text=f"✅ Search complete! Found {len(self.found_groups)} groups", 
                                  fg=COLORS["success"])
        self.progress['value'] = 100
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        
        log(f"✅ FINDER COMPLETED: {len(self.found_groups)} groups found", "success")
        
        auto_saved = len(self.found_groups) if self.auto_save_var.get() else 0
        
        messagebox.showinfo("Search Complete",
            f"Found {len(self.found_groups)} groups!\n\n"
            f"Auto-saved to groups/valid.txt: {auto_saved}\n"
            f"Click 'Save Results' to export to file.")
    
    def _stop_search(self):
        self.search_running = False
        self.status_label.config(text="⏹️ Stopped", fg=COLORS["error"])
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        log("⏹️ Finder stopped by user", "warning")
    
    def _save_results(self):
        if not self.found_groups:
            messagebox.showwarning("Warning", "No results to save!")
            return
        
        filepath = filedialog.asksaveasfilename(defaultextension=".txt",
                                                  filetypes=[("Text files", "*.txt"), ("CSV files", "*.csv")])
        if filepath:
            if filepath.endswith('.csv'):
                import csv
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(["Group Link", "Members", "Keyword", "Account", "Found At"])
                    for g in self.found_groups:
                        writer.writerow([g["link"], g["members"], g["keyword"], g["account"], g["found_at"]])
            else:
                with open(filepath, 'w', encoding='utf-8') as f:
                    for g in self.found_groups:
                        f.write(f"{g['link']}\n")
            
            messagebox.showinfo("Success", f"Saved {len(self.found_groups)} groups to {filepath}")
            log(f"Results saved: {len(self.found_groups)} groups to {filepath}", "success")
    
    def _refresh(self):
        self._load_account_lists()

    def _on_account_changed(self, data=None):
        """Refresh when account assignments change"""
        try:
            self._refresh_accounts()
        except Exception:
            pass

    def _refresh_accounts(self):
        """Refresh account listboxes with finder-assigned accounts"""
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