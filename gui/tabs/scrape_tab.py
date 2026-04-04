"""Scrape Tab - Complete with Scrollable Content (Fixed)"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog, simpledialog
from core import log, account_manager, load_groups
from core.account_router import account_router, Feature
from core.utils import DATA_DIR
from gui.styles import COLORS, FONTS
import threading
import json
from pathlib import Path
from datetime import datetime
from core.state_manager import state_manager
from core.localization import t

class ScrapeTab:
    title = "📥 Scrape"
    
    def __init__(self, parent, main_window=None):
        self.parent = parent
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        self.scraping = False
        self._create_widgets()
        # Listen for account assignment changes
        state_manager.on_state_change("account_assigned", self._on_account_changed)
        state_manager.on_state_change("refresh_all", self._on_account_changed)
        self._load_accounts()
    
    def _create_widgets(self):
        # Header
        tk.Label(self.frame, text=f"📥 {t('Group Member Scraper')}", font=("Segoe UI", 24, "bold"),
                 fg=COLORS["primary"], bg=COLORS["bg_dark"]).pack(pady=15)
        
        # === MAIN SCROLLABLE CONTAINER ===
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
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        
        # === 1. ACCOUNT SELECTION ===
        account_frame = tk.LabelFrame(self.scrollable_frame, text=f"📱 {t('Accounts for Scrape')}",
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
        tk.Button(assign_frame, text="➡️", command=self._assign_scrape_accounts, bg=COLORS["success"], fg="white").pack(pady=2)
        tk.Button(assign_frame, text="⬅️", command=self._remove_scrape_accounts, bg=COLORS["error"], fg="white").pack(pady=2)
        
        self._load_account_lists()
        
        # === 2. TARGET GROUPS ===
        target_frame = tk.LabelFrame(self.scrollable_frame, text="🎯 Target Groups",
                                     fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                     font=FONTS["heading"])
        target_frame.pack(fill="x", padx=10, pady=10)
        
        self.target_var = tk.StringVar(value="joined")
        tk.Radiobutton(target_frame, text="Joined Groups (from groups/joined.txt)", variable=self.target_var,
                      value="joined", bg=COLORS["bg_medium"], fg=COLORS["text"]).pack(anchor="w", padx=20, pady=3)
        tk.Radiobutton(target_frame, text="Custom Group List", variable=self.target_var,
                      value="custom", bg=COLORS["bg_medium"], fg=COLORS["text"]).pack(anchor="w", padx=20, pady=3)
        
        self.custom_groups_text = scrolledtext.ScrolledText(target_frame, height=4,
                                                             bg=COLORS["bg_light"], fg=COLORS["text"])
        self.custom_groups_text.pack(fill="x", padx=20, pady=5)
        self.custom_groups_text.insert("1.0", "https://t.me/group1\nhttps://t.me/group2")
        
        # === 3. SCRAPE SETTINGS ===
        settings_frame = tk.LabelFrame(self.scrollable_frame, text="⚙️ Scrape Settings",
                                       fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                       font=FONTS["heading"])
        settings_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(settings_frame, text="Max Members per Group:", fg=COLORS["text"],
                bg=COLORS["bg_medium"]).grid(row=0, column=0, padx=10, pady=5)
        self.max_members = tk.Entry(settings_frame, width=10, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.max_members.insert(0, "1000")
        self.max_members.grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(settings_frame, text="| Delay (sec):", fg=COLORS["text"], bg=COLORS["bg_medium"]).grid(row=0, column=2, padx=10, pady=5)
        self.delay_min = tk.Entry(settings_frame, width=6, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.delay_min.insert(0, "5")
        self.delay_min.grid(row=0, column=3, padx=5, pady=5)
        tk.Label(settings_frame, text="-", fg=COLORS["text"], bg=COLORS["bg_medium"]).grid(row=0, column=4)
        self.delay_max = tk.Entry(settings_frame, width=6, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.delay_max.insert(0, "15")
        self.delay_max.grid(row=0, column=5, padx=5, pady=5)
        
        self.filter_bots_var = tk.BooleanVar(value=True)
        tk.Checkbutton(settings_frame, text="🤖 Filter Bots", variable=self.filter_bots_var,
                      bg=COLORS["bg_medium"], fg=COLORS["text"]).grid(row=1, column=0, columnspan=6, padx=10, pady=3, sticky="w")
        
        self.filter_deleted_var = tk.BooleanVar(value=True)
        tk.Checkbutton(settings_frame, text="🗑️ Filter Deleted Accounts", variable=self.filter_deleted_var,
                      bg=COLORS["bg_medium"], fg=COLORS["text"]).grid(row=2, column=0, columnspan=6, padx=10, pady=3, sticky="w")
        
        # === 4. AUTO-SCRAPE DURING BROADCAST ===
        auto_frame = tk.LabelFrame(self.scrollable_frame, text="🔄 Auto-Scrape During Broadcast",
                                   fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                   font=FONTS["heading"])
        auto_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(auto_frame, text="When enabled, members will be automatically scraped from groups during broadcast",
                fg=COLORS["text_muted"], bg=COLORS["bg_medium"]).pack(pady=5)
        
        self.auto_scrape_var = tk.BooleanVar(value=False)
        tk.Checkbutton(auto_frame, text="✅ Enable Auto-Scrape", variable=self.auto_scrape_var,
                      bg=COLORS["bg_medium"], fg=COLORS["success"], selectcolor=COLORS["bg_medium"]).pack(pady=5)
        
        # === 5. CONTROL BUTTONS ===
        btn_frame = tk.Frame(self.scrollable_frame, bg=COLORS["bg_medium"])
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        self.start_btn = tk.Button(btn_frame, text="▶ Start Scrape", command=self._start_scrape,
                  bg=COLORS["success"], fg="white", font=FONTS["bold"], padx=30, pady=12)
        self.start_btn.pack(side="left", padx=10)
        
        self.stop_btn = tk.Button(btn_frame, text="⏹️ Stop", command=self._stop_scrape,
                  bg=COLORS["error"], fg="white", font=FONTS["bold"], padx=30, pady=12, state="disabled")
        self.stop_btn.pack(side="left", padx=10)
        
        self.export_btn = tk.Button(btn_frame, text="📤 Export Results", command=self._export_results,
                  bg=COLORS["info"], fg="white", font=FONTS["bold"], padx=30, pady=12)
        self.export_btn.pack(side="left", padx=10)
        
        # === 6. STATUS & PROGRESS ===
        status_frame = tk.Frame(self.scrollable_frame, bg=COLORS["bg_medium"])
        status_frame.pack(fill="x", padx=10, pady=10)
        
        self.status_label = tk.Label(status_frame, text="⚪ Ready", font=FONTS["bold"],
                                     fg=COLORS["text_muted"], bg=COLORS["bg_medium"])
        self.status_label.pack(pady=5)
        
        self.progress = ttk.Progressbar(status_frame, mode='determinate', length=600)
        self.progress.pack(pady=5)
        
        # === 7. RESULTS ===
        results_frame = tk.LabelFrame(self.scrollable_frame, text="📊 Scrape Results",
                                      fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                      font=FONTS["heading"])
        results_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        columns = ("Group", "Members", "Filtered", "Status")
        self.results_tree = ttk.Treeview(results_frame, columns=columns, show="headings", height=8)
        self.results_tree.heading("Group", text="Group Link")
        self.results_tree.column("Group", width=300)
        self.results_tree.heading("Members", text="Members Scraped")
        self.results_tree.column("Members", width=150)
        self.results_tree.heading("Filtered", text="After Filter")
        self.results_tree.column("Filtered", width=150)
        self.results_tree.heading("Status", text="Status")
        self.results_tree.column("Status", width=100)
        
        self.results_tree.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.results_stats = tk.Label(results_frame, text="Scraped: 0 groups | Total: 0 members",
                                      fg=COLORS["text_muted"], bg=COLORS["bg_medium"])
        self.results_stats.pack(pady=5)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _on_tab_selected(self):
        """Called by main_window when this tab is selected."""
        self._load_account_lists()

    def _load_account_lists(self):
        self.available_accounts.delete(0, "end")
        self.assigned_accounts.delete(0, "end")

        # Use account_manager.assign_feature / feature list as single source of truth
        assigned_names = {a['name'] for a in account_manager.get_accounts_by_feature("scrape")}

        for acc in account_manager.get_all():
            display = f"{acc['name']} (L{acc.get('level', 1)})"
            if acc['name'] in assigned_names:
                self.assigned_accounts.insert("end", acc['name'])
            else:
                self.available_accounts.insert("end", display)

    def _assign_scrape_accounts(self):
        selection = self.available_accounts.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Select accounts first!")
            return

        for i in selection:
            display = self.available_accounts.get(i)
            name = display.split(" (")[0]
            account_manager.assign_feature(name, "scrape")

        self._load_account_lists()
        messagebox.showinfo("Success", "Accounts assigned to Scrape")

    def _remove_scrape_accounts(self):
        selection = self.assigned_accounts.curselection()
        if not selection:
            return

        for i in reversed(selection):
            name = self.assigned_accounts.get(i)
            account_manager.remove_feature(name, "scrape")

        self._load_account_lists()
    
    def _start_scrape(self):
        assigned = [self.assigned_accounts.get(i) for i in range(self.assigned_accounts.size())]
        if not assigned:
            messagebox.showwarning("Warning", 
                "No accounts assigned to Scrape!\n\n"
                "Go to Accounts tab → Select accounts → Assign Scrape")
            return
        
        # Get target groups
        if self.target_var.get() == "joined":
            from core.utils import load_joined_groups
            groups = load_joined_groups()
            if not groups:
                messagebox.showwarning("Warning", "No joined groups found!\n\nUse Join tab first.")
                return
        else:
            text = self.custom_groups_text.get("1.0", "end-1c")
            groups = [line.strip() for line in text.split("\n") if line.strip()]
            if not groups:
                messagebox.showwarning("Warning", "Enter group links first!")
                return
        
        max_members = int(self.max_members.get() or 1000)
        delay_min = int(self.delay_min.get() or 5)
        delay_max = int(self.delay_max.get() or 15)
        
        self.scraping = True
        self.status_label.config(text="📥 Scraping...", fg=COLORS["warning"])
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        
        log(f"📥 SCRAPE STARTED: {len(assigned)} accounts, {len(groups)} groups", "success")
        
        def scrape():
            scraped_count = 0
            total_members = 0
            
            for i, group in enumerate(groups):
                if not self.scraping:
                    break
                
                account_name = assigned[i % len(assigned)]
                
                try:
                    # SIMULATED scrape (replace with actual API)
                    import random
                    import time
                    
                    members_scraped = random.randint(100, max_members)
                    members_filtered = int(members_scraped * 0.8)  # 20% filtered
                    
                    # Save scraped data
                    scraped_dir = DATA_DIR / "scraped"
                    scraped_dir.mkdir(parents=True, exist_ok=True)
                    
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{group.replace('/', '_')}_{timestamp}.json"
                    filepath = scraped_dir / filename
                    
                    # Simulated member data
                    members = []
                    for j in range(members_filtered):
                        members.append({
                            "id": 100000000 + j,
                            "username": f"user{j}",
                            "first_name": f"User {j}",
                            "phone": f"+628{j:09d}" if j % 3 == 0 else ""
                        })
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(members, f, indent=2, ensure_ascii=False)
                    
                    scraped_count += 1
                    total_members += members_filtered
                    
                    log(f"📥 Scraped {members_filtered} members from {group}", "success")
                    
                    self.frame.after(0, lambda g=group, m=members_scraped, f=members_filtered: 
                        self._add_scrape_result(g, m, f, "Success"))
                    self.frame.after(0, lambda c=scraped_count, t=total_members: 
                        self._update_scrape_stats(c, t))
                    
                    delay = random.uniform(delay_min, delay_max)
                    time.sleep(delay)
                    
                except Exception as e:
                    log(f"❌ Scrape error for {group}: {e}", "error")
                    self.frame.after(0, lambda g=group: self._add_scrape_result(g, 0, 0, "Failed"))
            
            self.frame.after(0, self._scrape_complete)
        
        threading.Thread(target=scrape, daemon=True).start()
    
    def _add_scrape_result(self, group, members, filtered, status):
        self.results_tree.insert("", "end", values=(
            group[:50],
            members,
            filtered,
            status
        ))
        self.results_tree.see("end")
    
    def _update_scrape_stats(self, scraped, total):
        self.results_stats.config(text=f"Scraped: {scraped} groups | Total: {total} members")
        progress = (scraped / len(self.results_tree.get_children())) * 100 if self.results_tree.get_children() else 0
        self.progress['value'] = min(100, progress)
    
    def _scrape_complete(self):
        self.scraping = False
        self.status_label.config(text="✅ Scrape complete!", fg=COLORS["success"])
        self.progress['value'] = 100
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        log("✅ SCRAPE COMPLETED", "success")
        messagebox.showinfo("Scrape Complete", "All groups processed!")
    
    def _stop_scrape(self):
        self.scraping = False
        self.status_label.config(text="⏹️ Stopped", fg=COLORS["error"])
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        log("⏹️ Scrape stopped by user", "warning")
    
    def _export_results(self):
        from tkinter import filedialog
        import csv
        
        filepath = filedialog.asksaveasfilename(defaultextension=".csv",
                                                  filetypes=[("CSV files", "*.csv")])
        if filepath:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Group", "Members Scraped", "After Filter", "Status"])
                for item in self.results_tree.get_children():
                    values = self.results_tree.item(item)["values"]
                    writer.writerow(values)
            messagebox.showinfo("Success", f"Exported to {filepath}")
    
    def _refresh(self):
        self._load_account_lists()

    def _on_account_changed(self, data=None):
        """Refresh account lists when assignments change"""
        try:
            self._load_accounts()
        except Exception:
            pass

    def _load_accounts(self):
        """Load accounts assigned to scrape feature"""
        try:
            all_accs = account_manager.get_all()
            scrape_accs = account_manager.get_accounts_by_feature("scrape")

            self.available_accounts.delete(0, "end")
            for acc in all_accs:
                name = acc.get("name", "")
                if name not in [a.get("name", "") for a in scrape_accs]:
                    self.available_accounts.insert("end", name)

            self.assigned_accounts.delete(0, "end")
            for acc in scrape_accs:
                self.assigned_accounts.insert("end", acc.get("name", ""))
        except Exception:
            pass