"""Account Tab - Complete with Session Validation (Phase 1000)"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from core import log, account_manager, import_manager, statistics
from core.account_router import account_router, Feature
from gui.styles import COLORS, FONTS

class AccountTab:
    title = "📱 Accounts"
    
    def __init__(self, parent, main_window=None):
        self.parent = parent
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        self.selected_accounts = []
        self.all_accounts = []
        self.filtered_accounts = []
        self.current_page = 1
        self.items_per_page = 50
        self.total_pages = 1
        self.account_groups = account_manager.load_groups()
        
        self._create_widgets()
        self._load_accounts()
    
    def _create_widgets(self):
        # ═══════════════════════════════════════════════════
        # HEADER
        # ═══════════════════════════════════════════════════
        header = tk.Frame(self.frame, bg="#1a1a2e", height=50)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        tk.Label(header, text="📱 Account Management", 
                 font=("Segoe UI", 18, "bold"), fg="#00d9ff", 
                 bg="#1a1a2e").pack(side="left", padx=20, pady=15)
        
        tk.Button(header, text="📁 Manage Groups", command=self._manage_groups,
                  bg="#00d9ff", fg="#000000", font=("Segoe UI", 11, "bold")).pack(side="right", padx=10, pady=10)
        
        # ═══════════════════════════════════════════════════
        # MAIN SCROLLABLE AREA
        # ═══════════════════════════════════════════════════
        main_container = tk.Frame(self.frame, bg="#16213e")
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        canvas = tk.Canvas(main_container, bg="#16213e", highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg="#16213e")
        
        self.scrollable_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        
        # ═══════════════════════════════════════════════════
        # 1. TOOLBAR
        # ═══════════════════════════════════════════════════
        toolbar = tk.Frame(self.scrollable_frame, bg="#16213e")
        toolbar.pack(fill="x", padx=10, pady=10)
        
        tk.Button(toolbar, text="➕ Add Account", command=self._add_account,
                  bg="#00ff00", fg="#000000", font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
        
        tk.Button(toolbar, text="🔐 Check Sessions", command=self._check_all_sessions,
                  bg="#00d9ff", fg="#000000", font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
        
        tk.Button(toolbar, text="📥 Import", command=self._import_menu,
                  bg="#ffaa00", fg="#000000", font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
        
        tk.Button(toolbar, text="📤 Export", command=self._export_accounts,
                  bg="#ff6b6b", fg="#ffffff", font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
        
        tk.Button(toolbar, text="🗑️ Delete Selected", command=self._delete_selected,
                  bg="#ff0000", fg="#ffffff", font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
        
        tk.Button(toolbar, text="☑️ Select All", command=self._select_all,
                  bg="#888888", fg="#ffffff", font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
        
        tk.Button(toolbar, text="☐ Deselect All", command=self._deselect_all,
                  bg="#888888", fg="#ffffff", font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
        
        tk.Button(toolbar, text="🔄 Refresh", command=self._load_accounts,
                  bg="#00d9ff", fg="#000000", font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
        
        # ═══════════════════════════════════════════════════
        # 2. FILTER SECTION
        # ═══════════════════════════════════════════════════
        filter_frame = tk.LabelFrame(self.scrollable_frame, text="🔍 Filter", 
                                      bg="#0f3460", fg="#00d9ff",
                                      font=("Segoe UI", 11, "bold"))
        filter_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(filter_frame, text="Search:", bg="#0f3460", fg="#ffffff").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.search_entry = tk.Entry(filter_frame, width=25, bg="#1a1a2e", fg="#ffffff")
        self.search_entry.grid(row=0, column=1, padx=10, pady=5)
        self.search_entry.bind("<KeyRelease>", lambda e: self._apply_filters())
        
        tk.Label(filter_frame, text="| Level:", bg="#0f3460", fg="#ffffff").grid(row=0, column=2, padx=10, pady=5)
        self.level_var = tk.StringVar(value="All")
        level_combo = ttk.Combobox(filter_frame, textvariable=self.level_var, values=["All", "1", "2", "3", "4"], width=5)
        level_combo.grid(row=0, column=3, padx=10, pady=5)
        level_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())
        
        tk.Label(filter_frame, text="| Status:", bg="#0f3460", fg="#ffffff").grid(row=0, column=4, padx=10, pady=5)
        self.status_var = tk.StringVar(value="All")
        status_combo = ttk.Combobox(filter_frame, textvariable=self.status_var, values=["All", "active", "inactive", "session_expired", "banned"], width=15)
        status_combo.grid(row=0, column=5, padx=10, pady=5)
        status_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())
        
        tk.Label(filter_frame, text="| Group:", bg="#0f3460", fg="#ffffff").grid(row=0, column=6, padx=10, pady=5)
        self.group_var = tk.StringVar(value="All")
        self.group_combo = ttk.Combobox(filter_frame, textvariable=self.group_var, width=15)
        self.group_combo.grid(row=0, column=7, padx=10, pady=5)
        self.group_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())
        self._update_group_combo()
        
        # ═══════════════════════════════════════════════════
        # 3. ACCOUNT TABLE
        # ═══════════════════════════════════════════════════
        table_frame = tk.LabelFrame(self.scrollable_frame, text="📋 Accounts List", 
                                     bg="#0f3460", fg="#00d9ff",
                                     font=("Segoe UI", 11, "bold"))
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        columns = ("✓", "Name", "Phone", "Level", "Session", "Status", "Group", "Success Rate")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=12, selectmode="extended")
        
        self.tree.heading("✓", text="✓")
        self.tree.column("✓", width=40)
        
        self.tree.heading("Name", text="Name")
        self.tree.column("Name", width=120)
        
        self.tree.heading("Phone", text="Phone")
        self.tree.column("Phone", width=120)
        
        self.tree.heading("Level", text="Level")
        self.tree.column("Level", width=60)
        
        self.tree.heading("Session", text="Session")
        self.tree.column("Session", width=80)
        
        self.tree.heading("Status", text="Status")
        self.tree.column("Status", width=100)
        
        self.tree.heading("Group", text="Group")
        self.tree.column("Group", width=120)
        
        self.tree.heading("Success Rate", text="Success Rate")
        self.tree.column("Success Rate", width=100)
        
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)
        self.tree.bind("<Button-1>", self._on_tree_click)
        
        # ═══════════════════════════════════════════════════
        # 4. PAGINATION
        # ═══════════════════════════════════════════════════
        page_frame = tk.Frame(self.scrollable_frame, bg="#16213e")
        page_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(page_frame, text="Page:", fg="#ffffff", bg="#16213e").pack(side="left", padx=5)
        self.page_var = tk.StringVar(value="1")
        self.page_combo = ttk.Combobox(page_frame, textvariable=self.page_var, width=5)
        self.page_combo.pack(side="left", padx=5)
        self.page_combo.bind("<<ComboboxSelected>>", lambda e: self._change_page())
        
        tk.Label(page_frame, text="of", fg="#ffffff", bg="#16213e").pack(side="left", padx=5)
        self.total_pages_label = tk.Label(page_frame, text="1", fg="#ffffff", bg="#16213e")
        self.total_pages_label.pack(side="left", padx=5)
        
        tk.Button(page_frame, text="⏮️", command=self._first_page, bg="#00d9ff", fg="#000000").pack(side="left", padx=2)
        tk.Button(page_frame, text="◀️", command=self._prev_page, bg="#00d9ff", fg="#000000").pack(side="left", padx=2)
        tk.Button(page_frame, text="▶️", command=self._next_page, bg="#00d9ff", fg="#000000").pack(side="left", padx=2)
        tk.Button(page_frame, text="⏭️", command=self._last_page, bg="#00d9ff", fg="#000000").pack(side="left", padx=2)
        
        tk.Label(page_frame, text="| Per page:", fg="#ffffff", bg="#16213e").pack(side="left", padx=15)
        self.per_page_var = tk.StringVar(value="50")
        per_page_combo = ttk.Combobox(page_frame, textvariable=self.per_page_var, values=["25", "50", "100", "200"], width=5)
        per_page_combo.pack(side="left", padx=5)
        per_page_combo.bind("<<ComboboxSelected>>", lambda e: self._change_per_page())
        
        # ═══════════════════════════════════════════════════
        # 5. FEATURE ASSIGNMENT
        # ═══════════════════════════════════════════════════
        feature_frame = tk.LabelFrame(self.scrollable_frame, text="⚡ Feature Assignment", 
                                       bg="#0f3460", fg="#00d9ff",
                                       font=("Segoe UI", 11, "bold"))
        feature_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(feature_frame, text="Assign selected accounts to features:",
                bg="#0f3460", fg="#ffffff").pack(pady=5)
        
        feature_btn_frame = tk.Frame(feature_frame, bg="#0f3460")
        feature_btn_frame.pack(pady=10)
        
        tk.Button(feature_btn_frame, text="📢 Broadcast", command=self._bulk_assign_broadcast,
                  bg="#00d9ff", fg="#000000", font=("Segoe UI", 10, "bold")).pack(side="left", padx=5)
        tk.Button(feature_btn_frame, text="🔍 Finder", command=self._bulk_assign_finder,
                  bg="#00d9ff", fg="#000000", font=("Segoe UI", 10, "bold")).pack(side="left", padx=5)
        tk.Button(feature_btn_frame, text="📥 Scrape", command=self._bulk_assign_scrape,
                  bg="#00d9ff", fg="#000000", font=("Segoe UI", 10, "bold")).pack(side="left", padx=5)
        tk.Button(feature_btn_frame, text="📤 Join", command=self._bulk_assign_join,
                  bg="#00d9ff", fg="#000000", font=("Segoe UI", 10, "bold")).pack(side="left", padx=5)
        tk.Button(feature_btn_frame, text="💬 CS", command=self._bulk_assign_cs,
                  bg="#00d9ff", fg="#000000", font=("Segoe UI", 10, "bold")).pack(side="left", padx=5)
        tk.Button(feature_btn_frame, text="❌ Unassign All", command=self._bulk_unassign,
                  bg="#ff6b6b", fg="#ffffff", font=("Segoe UI", 10, "bold")).pack(side="left", padx=5)
        
        self.feature_count_label = tk.Label(feature_frame, text="Selected: 0", 
                                          bg="#0f3460", fg="#888888", font=("Segoe UI", 11, "bold"))
        self.feature_count_label.pack(pady=5)
        
        # ═══════════════════════════════════════════════════
        # 6. STATS
        # ═══════════════════════════════════════════════════
        self.stats_label = tk.Label(self.scrollable_frame, text="", 
                                     bg="#16213e", fg="#00d9ff",
                                     font=("Segoe UI", 11, "bold"))
        self.stats_label.pack(pady=10)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    # ═══════════════════════════════════════════════════════
    # SESSION CHECK - CRITICAL
    # ═══════════════════════════════════════════════════════
    
    def _check_all_sessions(self):
        """Check all account sessions"""
        log("Checking all account sessions...", "info")
        
        valid_count = 0
        invalid_count = 0
        invalid_accounts = []
        
        for acc in account_manager.get_all():
            session_check = account_manager.check_session(acc["name"])
            if session_check["valid"]:
                valid_count += 1
            else:
                invalid_count += 1
                invalid_accounts.append(acc["name"])
                # Update account status
                if acc["name"] in account_manager.accounts:
                    account_manager.accounts[acc["name"]]["status"] = "session_expired"
        
        account_manager._save_accounts()
        
        msg = f"✅ Valid sessions: {valid_count}\n❌ Invalid sessions: {invalid_count}"
        
        if invalid_accounts:
            msg += f"\n\n⚠️ Accounts need login:\n" + "\n".join(invalid_accounts[:10])
            if len(invalid_accounts) > 10:
                msg += f"\n... and {len(invalid_accounts) - 10} more"
        
        messagebox.showinfo("Session Check Complete", msg)
        self._load_accounts()
    
    # ═══════════════════════════════════════════════════════
    # SELECTION METHODS
    # ═══════════════════════════════════════════════════════
    
    def _select_all(self):
        for item in self.tree.get_children():
            self.tree.set(item, "#1", "☑")
        self._update_selected_from_checkboxes()
    
    def _deselect_all(self):
        for item in self.tree.get_children():
            self.tree.set(item, "#1", "☐")
        self._update_selected_from_checkboxes()
    
    def _on_tree_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        column = self.tree.identify_column(event.x)
        if column == "#1":
            item = self.tree.identify_row(event.y)
            if item:
                values = self.tree.item(item, "values")
                if values:
                    if values[0] == "☐":
                        self.tree.set(item, "#1", "☑")
                    else:
                        self.tree.set(item, "#1", "☐")
                self._update_selected_from_checkboxes()
                return "break"
    
    def _update_selected_from_checkboxes(self):
        self.selected_accounts = []
        for item in self.tree.get_children():
            values = self.tree.item(item, "values")
            if values and values[0] == "☑":
                self.selected_accounts.append(values[1])
        count = len(self.selected_accounts)
        self.feature_count_label.config(text=f"Selected: {count}")
    
    # ═══════════════════════════════════════════════════════
    # LOAD & FILTER ACCOUNTS
    # ═══════════════════════════════════════════════════════
    
    def _load_accounts(self):
        """Load all accounts with session status"""
        self.all_accounts = account_manager.get_accounts_with_status()
        self._update_group_combo()
        self._apply_filters()
        self._update_stats()
    
    def _apply_filters(self):
        search = self.search_entry.get().lower()
        level = self.level_var.get()
        status = self.status_var.get()
        group = self.group_var.get()
        
        self.filtered_accounts = []
        
        for acc in self.all_accounts:
            acc_group = self._get_account_group(acc['name'])
            acc_status = acc.get('status', 'active')
            
            if search and search not in acc['name'].lower() and search not in acc.get('phone', '').lower():
                continue
            if level != "All" and str(acc.get('level', 1)) != level:
                continue
            if status != "All" and acc_status != status:
                continue
            if group != "All":
                groups = account_manager.load_groups()
                if group not in groups or acc['name'] not in groups.get(group, []):
                    continue
            
            self.filtered_accounts.append({
                **acc, 
                'group': acc_group,
                'status': acc_status
            })
        
        self._setup_pagination()
        self._display_current_page()
    
    def _setup_pagination(self):
        try:
            self.items_per_page = int(self.per_page_var.get())
        except:
            self.items_per_page = 50
        
        self.total_pages = max(1, (len(self.filtered_accounts) + self.items_per_page - 1) // self.items_per_page)
        if self.current_page > self.total_pages:
            self.current_page = self.total_pages
        
        self.total_pages_label.config(text=str(self.total_pages))
        self.page_combo['values'] = [str(i) for i in range(1, self.total_pages + 1)]
        self.page_var.set(str(self.current_page))
    
    def _display_current_page(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        start_idx = (self.current_page - 1) * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(self.filtered_accounts))
        
        for i in range(start_idx, end_idx):
            acc = self.filtered_accounts[i]
            
            # Session status
            session_status = "✅" if acc.get("session_valid", False) else "❌"
            
            self.tree.insert("", "end", values=(
                "☐", 
                acc.get("name", ""), 
                acc.get("phone", ""),
                acc.get("level", 1), 
                session_status,
                acc.get('status', 'active'),
                acc.get('group', '-'),
                f"{acc.get('success_rate', 100):.1f}%"
            ))
        
        self._update_selected_from_checkboxes()
    
    # ═══════════════════════════════════════════════════════
    # PAGINATION METHODS
    # ═══════════════════════════════════════════════════════
    
    def _change_page(self):
        try:
            self.current_page = int(self.page_var.get())
            self._display_current_page()
        except:
            pass
    
    def _first_page(self):
        self.current_page = 1
        self.page_var.set("1")
        self._display_current_page()
    
    def _prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.page_var.set(str(self.current_page))
            self._display_current_page()
    
    def _next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.page_var.set(str(self.current_page))
            self._display_current_page()
    
    def _last_page(self):
        self.current_page = self.total_pages
        self.page_var.set(str(self.total_pages))
        self._display_current_page()
    
    def _change_per_page(self):
        self.current_page = 1
        self.page_var.set("1")
        self._setup_pagination()
        self._display_current_page()
    
    # ═══════════════════════════════════════════════════════
    # HELPER METHODS
    # ═══════════════════════════════════════════════════════
    
    def _update_group_combo(self):
        self.account_groups = account_manager.load_groups()
        groups = ["All"] + list(self.account_groups.keys())
        self.group_combo['values'] = groups
    
    def _get_account_group(self, account_name):
        groups = account_manager.load_groups()
        for group_name, accounts in groups.items():
            if account_name in accounts:
                return group_name
        return "-"
    
    def _update_stats(self):
        stats = account_manager.get_stats()
        self.stats_label.config(
            text=f"Total: {stats['total']} | L1: {stats['by_level'].get(1,0)} | L2: {stats['by_level'].get(2,0)} | "
                 f"L3: {stats['by_level'].get(3,0)} | L4: {stats['by_level'].get(4,0)} | "
                 f"Active: {stats['active']} | Avg Success: {stats['avg_success_rate']:.1f}%"
        )
    
    # ═══════════════════════════════════════════════════════
    # ACCOUNT OPERATIONS
    # ═══════════════════════════════════════════════════════
    
    def _add_account(self):
        dialog = tk.Toplevel(self.frame)
        dialog.title("➕ Add Account")
        dialog.geometry("400x300")
        dialog.configure(bg="#1a1a2e")
        
        tk.Label(dialog, text="➕ Add Account", font=("Segoe UI", 16, "bold"),
                 fg="#00d9ff", bg="#1a1a2e").pack(pady=15)
        
        form_frame = tk.Frame(dialog, bg="#0f3460")
        form_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        tk.Label(form_frame, text="Name:", fg="#ffffff", bg="#0f3460").grid(row=0, column=0, padx=10, pady=8, sticky="w")
        name_entry = tk.Entry(form_frame, width=30, bg="#1a1a2e", fg="#ffffff")
        name_entry.grid(row=0, column=1, padx=10, pady=8)
        
        tk.Label(form_frame, text="Phone:", fg="#ffffff", bg="#0f3460").grid(row=1, column=0, padx=10, pady=8, sticky="w")
        phone_entry = tk.Entry(form_frame, width=30, bg="#1a1a2e", fg="#ffffff")
        phone_entry.insert(0, "+62")
        phone_entry.grid(row=1, column=1, padx=10, pady=8)
        
        tk.Label(form_frame, text="Level:", fg="#ffffff", bg="#0f3460").grid(row=2, column=0, padx=10, pady=8, sticky="w")
        level_var = tk.StringVar(value="1")
        level_combo = ttk.Combobox(form_frame, textvariable=level_var, values=["1", "2", "3", "4"], width=28)
        level_combo.grid(row=2, column=1, padx=10, pady=8)
        
        def save():
            name = name_entry.get().strip()
            phone = phone_entry.get().strip()
            level = int(level_var.get())
            
            if not name or not phone:
                messagebox.showerror("Error", "Name and phone required!")
                return
            
            if account_manager.add(name, phone, level):
                messagebox.showinfo("Success", "Account added!")
                self._load_accounts()
                dialog.destroy()
            else:
                messagebox.showerror("Error", "Account already exists!")
        
        tk.Button(dialog, text="✅ Add", command=save,
                  bg="#00ff00", fg="#000000", font=("Segoe UI", 12, "bold"),
                  padx=30, pady=10).pack(pady=20)
    
    def _delete_selected(self):
        if not self.selected_accounts:
            messagebox.showwarning("Warning", "Select accounts first!")
            return
        if messagebox.askyesno("Confirm", f"Delete {len(self.selected_accounts)} accounts?"):
            for name in self.selected_accounts:
                account_manager.delete(name)
            self._load_accounts()
            messagebox.showinfo("Success", f"Deleted {len(self.selected_accounts)} accounts")
    
    def _import_menu(self):
        menu = tk.Menu(self.frame, tearoff=0)
        menu.add_command(label="📄 Session File", command=self._import_session)
        menu.add_command(label="📁 Session Folder", command=self._import_sessions_folder)
        menu.add_command(label="📞 Phones CSV", command=self._import_phones_csv)
        menu.add_command(label="📞 Phones TXT", command=self._import_phones_txt)
        menu.post(self.frame.winfo_rootx(), self.frame.winfo_rooty())
    
    def _import_session(self):
        filepath = filedialog.askopenfilename(filetypes=[("Session files", "*.session")])
        if filepath:
            name = simpledialog.askstring("Account Name", "Enter account name:")
            if name:
                result = import_manager.import_session_single(filepath, name)
                self._load_accounts()
                if result.success:
                    messagebox.showinfo("Success", f"Session imported: {name}")
    
    def _import_sessions_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            result = import_manager.import_sessions_folder(folder)
            self._load_accounts()
            messagebox.showinfo("Import", f"Imported {result.imported} sessions")
    
    def _import_phones_csv(self):
        filepath = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if filepath:
            result = import_manager.import_phones_csv(filepath)
            self._load_accounts()
            messagebox.showinfo("Import", f"Imported {result.imported} phones")
    
    def _import_phones_txt(self):
        filepath = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if filepath:
            result = import_manager.import_phones_txt(filepath, "pipe")
            self._load_accounts()
            messagebox.showinfo("Import", f"Imported {result.imported} phones")
    
    def _export_accounts(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".csv")
        if filepath:
            import_manager.export_accounts(filepath, 'csv')
            messagebox.showinfo("Success", f"Exported to {filepath}")
    
    # ═══════════════════════════════════════════════════════
    # FEATURE ASSIGNMENT
    # ═══════════════════════════════════════════════════════
    
    def _bulk_assign_broadcast(self):
        if not self.selected_accounts:
            messagebox.showwarning("Warning", "Select accounts first!")
            return
        for name in self.selected_accounts:
            account_manager.assign_feature(name, "broadcast")
        self._load_accounts()
        messagebox.showinfo("Success", f"Assigned {len(self.selected_accounts)} to Broadcast")
    
    def _bulk_assign_finder(self):
        if not self.selected_accounts:
            messagebox.showwarning("Warning", "Select accounts first!")
            return
        for name in self.selected_accounts:
            account_manager.assign_feature(name, "finder")
        self._load_accounts()
        messagebox.showinfo("Success", f"Assigned {len(self.selected_accounts)} to Finder")
    
    def _bulk_assign_scrape(self):
        if not self.selected_accounts:
            messagebox.showwarning("Warning", "Select accounts first!")
            return
        for name in self.selected_accounts:
            account_manager.assign_feature(name, "scrape")
        self._load_accounts()
        messagebox.showinfo("Success", f"Assigned {len(self.selected_accounts)} to Scrape")
    
    def _bulk_assign_join(self):
        if not self.selected_accounts:
            messagebox.showwarning("Warning", "Select accounts first!")
            return
        for name in self.selected_accounts:
            account_manager.assign_feature(name, "join")
        self._load_accounts()
        messagebox.showinfo("Success", f"Assigned {len(self.selected_accounts)} to Join")
    
    def _bulk_assign_cs(self):
        if not self.selected_accounts:
            messagebox.showwarning("Warning", "Select accounts first!")
            return
        for name in self.selected_accounts:
            account_manager.assign_feature(name, "cs")
        self._load_accounts()
        messagebox.showinfo("Success", f"Assigned {len(self.selected_accounts)} to CS")
    
    def _bulk_unassign(self):
        if not self.selected_accounts:
            messagebox.showwarning("Warning", "Select accounts first!")
            return
        if messagebox.askyesno("Confirm", f"Remove all feature assignments from {len(self.selected_accounts)} accounts?"):
            for name in self.selected_accounts:
                acc = account_manager.get(name)
                if acc:
                    acc["features"] = []
            account_manager._save_accounts()
            self._load_accounts()
            messagebox.showinfo("Success", f"Unassigned {len(self.selected_accounts)} accounts")
    
    # ═══════════════════════════════════════════════════════
    # GROUP MANAGEMENT
    # ═══════════════════════════════════════════════════════
    
    def _manage_groups(self):
        dialog = tk.Toplevel(self.frame)
        dialog.title("📁 Manage Account Groups")
        dialog.geometry("600x450")
        dialog.configure(bg="#1a1a2e")
        
        tk.Label(dialog, text="📁 Account Groups Management", 
                 font=("Segoe UI", 16, "bold"), fg="#00d9ff",
                 bg="#1a1a2e").pack(pady=15)
        
        # Create group
        create_frame = tk.Frame(dialog, bg="#0f3460")
        create_frame.pack(fill="x", padx=20, pady=10)
        
        tk.Label(create_frame, text="New Group Name:", fg="#ffffff", bg="#0f3460").pack(side="left")
        group_name_entry = tk.Entry(create_frame, width=30, bg="#1a1a2e", fg="#ffffff")
        group_name_entry.pack(side="left", padx=5)
        
        def create_group():
            name = group_name_entry.get().strip()
            if name:
                if account_manager.create_group(name):
                    self._update_group_combo()
                    self._sync_groups_to_broadcast()
                    _load_groups_list()
                    messagebox.showinfo("Success", f"Group '{name}' created!")
                else:
                    messagebox.showerror("Error", "Group already exists!")
        
        tk.Button(create_frame, text="➕ Create", command=create_group,
                  bg="#00ff00", fg="#000000", font=("Segoe UI", 10, "bold")).pack(side="left", padx=10)
        
        # Groups list
        list_frame = tk.LabelFrame(dialog, text="📋 Existing Groups",
                                   fg="#00d9ff", bg="#0f3460")
        list_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        columns = ("Group Name", "Accounts", "Actions")
        groups_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)
        
        groups_tree.heading("Group Name", text="Group Name")
        groups_tree.column("Group Name", width=200)
        
        groups_tree.heading("Accounts", text="Accounts")
        groups_tree.column("Accounts", width=150)
        
        groups_tree.heading("Actions", text="Actions")
        groups_tree.column("Actions", width=150)
        
        groups_tree.pack(fill="both", expand=True, padx=10, pady=5)
        
        def _load_groups_list():
            for item in groups_tree.get_children():
                groups_tree.delete(item)
            
            groups = account_manager.load_groups()
            for group_name, accounts in groups.items():
                groups_tree.insert("", "end", values=(
                    group_name,
                    f"{len(accounts)} accounts",
                    "View / Edit / Delete"
                ), tags=(group_name,))
        
        _load_groups_list()
        
        # Assign accounts
        assign_frame = tk.LabelFrame(dialog, text="👥 Assign Accounts to Group",
                                     fg="#00d9ff", bg="#0f3460")
        assign_frame.pack(fill="x", padx=20, pady=10)
        
        tk.Label(assign_frame, text="Select Group:", fg="#ffffff", bg="#0f3460").pack(side="left", padx=5)
        assign_group_var = tk.StringVar()
        assign_group_combo = ttk.Combobox(assign_frame, textvariable=assign_group_var, 
                                           values=list(account_manager.load_groups().keys()), width=20)
        assign_group_combo.pack(side="left", padx=5)
        
        def assign_selected():
            group = assign_group_var.get()
            if not group or not self.selected_accounts:
                messagebox.showwarning("Warning", "Select group and accounts first!")
                return
            added = account_manager.bulk_assign_to_group(group, self.selected_accounts)
            _load_groups_list()
            self._sync_groups_to_broadcast()
            messagebox.showinfo("Success", f"Assigned {added} accounts to '{group}'")
        
        tk.Button(assign_frame, text="✅ Assign Selected", command=assign_selected,
                  bg="#00ff00", fg="#000000", font=("Segoe UI", 10, "bold")).pack(side="left", padx=10)
        
        # Action buttons
        btn_frame = tk.Frame(dialog, bg="#1a1a2e")
        btn_frame.pack(fill="x", padx=20, pady=10)
        
        def view_group():
            selection = groups_tree.selection()
            if not selection:
                messagebox.showwarning("Warning", "Select a group first!")
                return
            group_name = groups_tree.item(selection[0])["tags"][0]
            groups = account_manager.load_groups()
            accounts = groups.get(group_name, [])
            
            view_dialog = tk.Toplevel(dialog)
            view_dialog.title(f"👥 {group_name} - {len(accounts)} accounts")
            view_dialog.geometry("400x400")
            view_dialog.configure(bg="#1a1a2e")
            
            tk.Label(view_dialog, text=f"Accounts in '{group_name}':", 
                    fg="#ffffff", bg="#1a1a2e", font=("Segoe UI", 12, "bold")).pack(pady=10)
            
            listbox = tk.Listbox(view_dialog, bg="#0f3460", fg="#ffffff", height=15)
            listbox.pack(fill="both", expand=True, padx=20, pady=10)
            for acc in accounts:
                listbox.insert("end", acc)
            
            tk.Button(view_dialog, text="Close", command=view_dialog.destroy,
                      bg="#888888", fg="#ffffff").pack(pady=10)
        
        def delete_group():
            selection = groups_tree.selection()
            if not selection:
                messagebox.showwarning("Warning", "Select a group first!")
                return
            group_name = groups_tree.item(selection[0])["tags"][0]
            if messagebox.askyesno("Confirm", f"Delete group '{group_name}'?"):
                if account_manager.delete_group(group_name):
                    _load_groups_list()
                    self._update_group_combo()
                    self._sync_groups_to_broadcast()
                    messagebox.showinfo("Success", f"Group '{group_name}' deleted!")
        
        tk.Button(btn_frame, text="👁️ View", command=view_group,
                  bg="#00d9ff", fg="#000000", font=("Segoe UI", 10, "bold")).pack(side="left", padx=5)
        tk.Button(btn_frame, text="🗑️ Delete", command=delete_group,
                  bg="#ff0000", fg="#ffffff", font=("Segoe UI", 10, "bold")).pack(side="left", padx=5)
        tk.Button(btn_frame, text="🔄 Refresh", command=_load_groups_list,
                  bg="#00d9ff", fg="#000000", font=("Segoe UI", 10, "bold")).pack(side="left", padx=5)
        tk.Button(btn_frame, text="✅ Done", command=dialog.destroy,
                  bg="#00ff00", fg="#000000", font=("Segoe UI", 10, "bold")).pack(side="right", padx=5)
    
    def _sync_groups_to_broadcast(self):
        if hasattr(self.main_window, 'broadcast_tab'):
            try:
                self.main_window.broadcast_tab._load_broadcast_groups()
                log("Groups synced to Broadcast tab", "success")
            except Exception as e:
                log(f"Failed to sync groups: {e}", "error")
    
    def _refresh(self):
        self._load_accounts()