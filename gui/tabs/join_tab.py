"""Join Tab - Scrollable Content Fix"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from core import log, load_groups, account_manager
from core.account_router import account_router, Feature
from core.utils import DATA_DIR
from gui.styles import COLORS, FONTS
import threading
from pathlib import Path
from core.state_manager import state_manager
from core.localization import t

class JoinTab:
    title = "📤 Join"
    
    def __init__(self, parent, main_window=None):
        self.parent = parent
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        self.running = False
        self.groups_to_join = []
        self._create_widgets()
        # Listen for account assignment changes
        state_manager.on_state_change("account_assigned", self._on_account_changed)
        state_manager.on_state_change("refresh_all", self._on_account_changed)

    def _create_widgets(self):
        # Header
        tk.Label(self.frame, text=f"📤 {t('Auto Join Groups')}", font=("Segoe UI", 24, "bold"),
                 fg=COLORS["primary"], bg=COLORS["bg_dark"]).pack(pady=15)
        
        # Main scrollable container
        main_container = tk.Frame(self.frame, bg=COLORS["bg_dark"])
        main_container.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Canvas with scrollbar
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
        
        # 1. Source Selection
        source_frame = tk.LabelFrame(self.scrollable_frame, text=f"📁 {t('Select Group Source')}",
                                     fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                     font=FONTS["heading"])
        source_frame.pack(fill="x", padx=10, pady=10)
        
        self.source_var = tk.StringVar(value="valid_txt")
        
        tk.Radiobutton(source_frame, text="📄 groups/valid.txt (Finder Results)", variable=self.source_var,
                      value="valid_txt", bg=COLORS["bg_medium"], fg=COLORS["text"],
                      command=self._on_source_change).pack(anchor="w", padx=20, pady=3)
        
        tk.Radiobutton(source_frame, text="📂 Import from TXT File", variable=self.source_var,
                      value="import_txt", bg=COLORS["bg_medium"], fg=COLORS["text"],
                      command=self._on_source_change).pack(anchor="w", padx=20, pady=3)
        
        tk.Radiobutton(source_frame, text="✏️ Custom List (Manual Entry)", variable=self.source_var,
                      value="custom", bg=COLORS["bg_medium"], fg=COLORS["text"],
                      command=self._on_source_change).pack(anchor="w", padx=20, pady=3)
        
        # Source options
        self.source_options_frame = tk.Frame(self.scrollable_frame, bg=COLORS["bg_medium"])
        self.source_options_frame.pack(fill="x", padx=10, pady=10)
        self._update_source_options()
        
        # 2. Account Selection
        account_frame = tk.LabelFrame(self.scrollable_frame, text="📱 Accounts for Join",
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
        tk.Button(assign_frame, text="➡️", command=self._assign_join_accounts, bg=COLORS["success"], fg="white").pack(pady=2)
        tk.Button(assign_frame, text="⬅️", command=self._remove_join_accounts, bg=COLORS["error"], fg="white").pack(pady=2)
        
        self._load_account_lists()
        
        # 3. Settings
        settings_frame = tk.LabelFrame(self.scrollable_frame, text="⚙️ Join Settings",
                                       fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                       font=FONTS["heading"])
        settings_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(settings_frame, text="Max Join/Day:", fg=COLORS["text"], bg=COLORS["bg_medium"]).grid(row=0, column=0, padx=10, pady=5)
        self.max_join = tk.Entry(settings_frame, width=10, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.max_join.insert(0, "50")
        self.max_join.grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(settings_frame, text="| Delay (sec):", fg=COLORS["text"], bg=COLORS["bg_medium"]).grid(row=0, column=2, padx=10, pady=5)
        self.delay_min = tk.Entry(settings_frame, width=6, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.delay_min.insert(0, "30")
        self.delay_min.grid(row=0, column=3, padx=5, pady=5)
        tk.Label(settings_frame, text="-", fg=COLORS["text"], bg=COLORS["bg_medium"]).grid(row=0, column=4)
        self.delay_max = tk.Entry(settings_frame, width=6, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.delay_max.insert(0, "60")
        self.delay_max.grid(row=0, column=5, padx=5, pady=5)
        
        self.smart_join_var = tk.BooleanVar(value=True)
        tk.Checkbutton(settings_frame, text="🧠 Smart Join (Skip if already joined)", variable=self.smart_join_var,
                      bg=COLORS["bg_medium"], fg=COLORS["success"], selectcolor=COLORS["bg_medium"]).grid(row=1, column=0, columnspan=6, padx=10, pady=5, sticky="w")
        
        # 4. Control Buttons
        btn_frame = tk.Frame(self.scrollable_frame, bg=COLORS["bg_medium"])
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        self.start_btn = tk.Button(btn_frame, text="▶ Start Join", command=self._start_join,
                  bg=COLORS["success"], fg="white", font=FONTS["bold"], padx=30, pady=12)
        self.start_btn.pack(side="left", padx=10)
        
        self.stop_btn = tk.Button(btn_frame, text="⏹️ Stop", command=self._stop_join,
                  bg=COLORS["error"], fg="white", font=FONTS["bold"], padx=30, pady=12, state="disabled")
        self.stop_btn.pack(side="left", padx=10)
        
        self.view_btn = tk.Button(btn_frame, text="📊 View Joined", command=self._view_joined,
                  bg=COLORS["info"], fg="white", font=FONTS["bold"], padx=30, pady=12)
        self.view_btn.pack(side="left", padx=10)
        
        # 5. Status & Progress
        status_frame = tk.Frame(self.scrollable_frame, bg=COLORS["bg_medium"])
        status_frame.pack(fill="x", padx=10, pady=10)
        
        self.status_label = tk.Label(status_frame, text="⚪ Ready", font=FONTS["bold"],
                                     fg=COLORS["text_muted"], bg=COLORS["bg_medium"])
        self.status_label.pack(pady=5)
        
        self.progress = ttk.Progressbar(status_frame, mode='determinate', length=600)
        self.progress.pack(pady=5)
        
        # 6. Results
        results_frame = tk.LabelFrame(self.scrollable_frame, text="📊 Join Results",
                                      fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                      font=FONTS["heading"])
        results_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        columns = ("Group", "Status", "Account", "Time")
        self.results_tree = ttk.Treeview(results_frame, columns=columns, show="headings", height=10)
        self.results_tree.heading("Group", text="Group Link")
        self.results_tree.column("Group", width=300)
        self.results_tree.heading("Status", text="Status")
        self.results_tree.column("Status", width=100)
        self.results_tree.heading("Account", text="Account Used")
        self.results_tree.column("Account", width=150)
        self.results_tree.heading("Time", text="Time")
        self.results_tree.column("Time", width=150)
        
        self.results_tree.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.results_stats = tk.Label(results_frame, text="Joined: 0 | Skipped: 0 | Failed: 0",
                                      fg=COLORS["text_muted"], bg=COLORS["bg_medium"])
        self.results_stats.pack(pady=5)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _on_tab_selected(self):
        """Called by main_window when this tab is selected."""
        self._load_account_lists()

    def _on_source_change(self):
        self._update_source_options()
    
    def _update_source_options(self):
        for widget in self.source_options_frame.winfo_children():
            widget.destroy()
        
        source = self.source_var.get()
        
        if source == "valid_txt":
            valid_file = DATA_DIR / "groups" / "valid.txt"
            count = 0
            if valid_file.exists():
                with open(valid_file, 'r', encoding='utf-8') as f:
                    count = sum(1 for line in f if line.strip())
            tk.Label(self.source_options_frame, text=f"📄 groups/valid.txt contains {count} groups",
                    fg=COLORS["success"], bg=COLORS["bg_medium"]).pack(pady=10)
        
        elif source == "import_txt":
            self.import_file_var = tk.StringVar()
            file_frame = tk.Frame(self.source_options_frame, bg=COLORS["bg_medium"])
            file_frame.pack(pady=10)
            
            tk.Entry(file_frame, textvariable=self.import_file_var, width=40,
                    bg=COLORS["bg_light"], fg=COLORS["text"]).pack(side="left", padx=5)
            tk.Button(file_frame, text="📂 Browse", command=self._browse_import_file,
                     bg=COLORS["info"], fg="white").pack(side="left", padx=5)
        
        elif source == "custom":
            tk.Label(self.source_options_frame, text="Enter group links (one per line):",
                    fg=COLORS["text"], bg=COLORS["bg_medium"]).pack(pady=5)
            
            self.custom_groups_text = scrolledtext.ScrolledText(self.source_options_frame,
                                                                 height=6, bg=COLORS["bg_light"],
                                                                 fg=COLORS["text"])
            self.custom_groups_text.pack(fill="x", padx=10, pady=5)
    
    def _browse_import_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if filepath:
            self.import_file_var.set(filepath)
    
    def _load_account_lists(self):
        self.available_accounts.delete(0, "end")
        self.assigned_accounts.delete(0, "end")

        assigned_names = {a['name'] for a in account_manager.get_accounts_by_feature("join")}

        for acc in account_manager.get_all():
            display = f"{acc['name']} (L{acc.get('level', 1)})"
            if acc['name'] in assigned_names:
                self.assigned_accounts.insert("end", acc['name'])
            else:
                self.available_accounts.insert("end", display)

    def _assign_join_accounts(self):
        selection = self.available_accounts.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Select accounts first!")
            return

        for i in selection:
            display = self.available_accounts.get(i)
            name = display.split(" (")[0]
            account_manager.assign_feature(name, "join")

        self._load_account_lists()
        messagebox.showinfo("Success", "Accounts assigned to Join")

    def _remove_join_accounts(self):
        selection = self.assigned_accounts.curselection()
        if not selection:
            return

        for i in reversed(selection):
            name = self.assigned_accounts.get(i)
            account_manager.remove_feature(name, "join")

        self._load_account_lists()
    
    def _load_groups_to_join(self):
        source = self.source_var.get()
        self.groups_to_join = []
        
        if source == "valid_txt":
            valid_file = DATA_DIR / "groups" / "valid.txt"
            if valid_file.exists():
                with open(valid_file, 'r', encoding='utf-8') as f:
                    self.groups_to_join = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            else:
                messagebox.showwarning("Warning", "groups/valid.txt not found!\n\nUse Finder tab first.")
                return False
        
        elif source == "import_txt":
            filepath = self.import_file_var.get()
            if not filepath:
                messagebox.showwarning("Warning", "Select a file first!")
                return False
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    self.groups_to_join = [line.strip() for line in f if line.strip()]
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file: {e}")
                return False
        
        elif source == "custom":
            if hasattr(self, 'custom_groups_text'):
                text = self.custom_groups_text.get("1.0", "end-1c")
                self.groups_to_join = [line.strip() for line in text.split("\n") if line.strip()]
            if not self.groups_to_join:
                messagebox.showwarning("Warning", "Enter group links first!")
                return False
        
        return True
    
    def _start_join(self):
        assigned = [self.assigned_accounts.get(i) for i in range(self.assigned_accounts.size())]
        if not assigned:
            messagebox.showwarning("Warning", 
                "No accounts assigned to Join!\n\n"
                "Go to Accounts tab → Select accounts → Assign Join")
            return
        
        if not self._load_groups_to_join():
            return
        
        max_join = int(self.max_join.get() or 50)
        delay_min = int(self.delay_min.get() or 30)
        delay_max = int(self.delay_max.get() or 60)
        smart_join = self.smart_join_var.get()
        
        self.running = True
        self.status_label.config(text=f"📤 Joining...", fg=COLORS["warning"])
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        
        log(f"📤 JOIN STARTED", "success")
        
        def join():
            joined = 0
            skipped = 0
            failed = 0
            
            for i, group in enumerate(self.groups_to_join[:max_join]):
                if not self.running:
                    break
                
                account_name = assigned[i % len(assigned)]
                
                try:
                    if smart_join:
                        existing = load_groups()
                        if group in existing:
                            skipped += 1
                            self.frame.after(0, lambda g=group: self._add_join_result(g, "Skipped", "-"))
                            self.frame.after(0, lambda j=joined, s=skipped, f=failed: self._update_join_stats(j, s, f))
                            continue
                    
                    log(f"📤 [{i+1}/{len(self.groups_to_join)}] {account_name} → {group}", "info")
                    
                    import time
                    import random
                    time.sleep(random.uniform(delay_min, delay_max) / 10)
                    
                    joined += 1
                    
                    self.frame.after(0, lambda g=group, a=account_name: self._add_join_result(g, "Joined", a))
                    self.frame.after(0, lambda j=joined, s=skipped, f=failed: self._update_join_stats(j, s, f))
                    
                except Exception as e:
                    failed += 1
                    self.frame.after(0, lambda g=group: self._add_join_result(g, f"Failed", "-"))
            
            self.frame.after(0, self._join_complete)
        
        threading.Thread(target=join, daemon=True).start()
    
    def _add_join_result(self, group, status, account):
        from datetime import datetime
        self.results_tree.insert("", "end", values=(
            group,
            status,
            account,
            datetime.now().strftime("%H:%M:%S")
        ))
        self.results_tree.see("end")
    
    def _update_join_stats(self, joined, skipped, failed):
        self.results_stats.config(text=f"Joined: {joined} | Skipped: {skipped} | Failed: {failed}")
        progress = (joined / len(self.groups_to_join)) * 100 if self.groups_to_join else 0
        self.progress['value'] = progress
    
    def _join_complete(self):
        self.running = False
        self.status_label.config(text="✅ Join complete!", fg=COLORS["success"])
        self.progress['value'] = 100
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        log("✅ JOIN COMPLETED", "success")
        messagebox.showinfo("Join Complete", "All groups processed!")
    
    def _stop_join(self):
        self.running = False
        self.status_label.config(text="⏹️ Stopped", fg=COLORS["error"])
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        log("⏹️ Join stopped by user", "warning")
    
    def _view_joined(self):
        existing = load_groups()
        messagebox.showinfo("Joined Groups", f"Total groups in database: {len(existing)}")
    
    def _refresh(self):
        self._load_account_lists()

    def _on_account_changed(self, data=None):
        """Refresh when account assignments change"""
        try:
            self._load_join_accounts()
        except Exception:
            pass

    def _load_join_accounts(self):
        """Load accounts assigned to join feature"""
        try:
            join_accs = account_manager.get_accounts_by_feature("join")
            if hasattr(self, 'account_combo'):
                all_accs = [a.get("name", "") for a in account_manager.get_all()]
                join_names = [a.get("name", "") for a in join_accs]
                vals = join_names if join_names else all_accs
                self.account_combo['values'] = vals
                if vals and not self.account_combo.get():
                    self.account_combo.set(vals[0])
        except Exception:
            pass