"""Account Tab - Complete with Session Validation (Phase 1000)"""
import asyncio
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from core import log, account_manager, import_manager, statistics
from core.account_router import account_router, Feature
from core.state_manager import state_manager
from core.localization import t
from gui.styles import COLORS, FONTS
from gui.components.import_dialog import ImportDialog
from gui.components.otp_setup_dialog import OTPSetupDialog
from gui.components.ws_sync_client import WSSyncClient

# Timeout (seconds) waiting for the user to enter an OTP during bulk import
_BULK_OTP_TIMEOUT_SECONDS = 180

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

        # Sprint 3: WebSocket real-time sync
        client_id = state_manager.get("client_id")
        if client_id:
            self._ws_client = WSSyncClient(
                client_id=int(client_id),
                on_event=self._on_ws_event,
            )
            self._ws_client.start()
        else:
            self._ws_client = None

        self._create_widgets()
        self._load_accounts()
    
    def _create_widgets(self):
        # ═══════════════════════════════════════════════════
        # HEADER
        # ═══════════════════════════════════════════════════
        header = tk.Frame(self.frame, bg="#1a1a2e", height=50)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        tk.Label(header, text=f"📱 {t('Account Management')}", 
                 font=("Segoe UI", 18, "bold"), fg="#00d9ff", 
                 bg="#1a1a2e").pack(side="left", padx=20, pady=15)
        
        tk.Button(header, text=f"📁 {t('Manage Groups')}", command=self._manage_groups,
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
        
        tk.Button(toolbar, text=f"➕ {t('Add Account')}", command=self._add_account,
                  bg="#00ff00", fg="#000000", font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
        
        tk.Button(toolbar, text=f"🔐 {t('Check Sessions')}", command=self._check_all_sessions,
                  bg="#00d9ff", fg="#000000", font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
        
        tk.Button(toolbar, text=f"📥 {t('Import')}", command=self._import_menu,
                  bg="#ffaa00", fg="#000000", font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)

        tk.Button(toolbar, text=f"📲 {t('Session Import')}", command=self._open_import_dialog,
                  bg="#ff8800", fg="#000000", font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)

        tk.Button(toolbar, text=f"🔐 {t('Setup 2FA')}", command=self._open_otp_setup_for_selected,
                  bg="#7B2CBF", fg="#ffffff", font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
        
        tk.Button(toolbar, text=f"📤 {t('Export')}", command=self._export_accounts,
                  bg="#ff6b6b", fg="#ffffff", font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
        
        tk.Button(toolbar, text=f"🗑️ {t('Delete Selected')}", command=self._delete_selected,
                  bg="#ff0000", fg="#ffffff", font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
        
        tk.Button(toolbar, text=f"☑️ {t('Select All')}", command=self._select_all,
                  bg="#888888", fg="#ffffff", font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
        
        tk.Button(toolbar, text=f"☐ {t('Deselect All')}", command=self._deselect_all,
                  bg="#888888", fg="#ffffff", font=("Segoe UI", 11, "bold")).pack(side="left", padx=5)
        
        tk.Button(toolbar, text=f"🔄 {t('Refresh')}", command=self._load_accounts,
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
        table_frame = tk.LabelFrame(self.scrollable_frame, text=f"📋 {t('Accounts List')}", 
                                     bg="#0f3460", fg="#00d9ff",
                                     font=("Segoe UI", 11, "bold"))
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        columns = ("✓", "Nama", "Telepon", "Level", "Sesi", "Status", "Grup", "Fitur", "Tingkat")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=12, selectmode="extended")
        
        self.tree.heading("✓", text="✓")
        self.tree.column("✓", width=35, minwidth=35, stretch=False)
        
        self.tree.heading("Nama", text=t("Account Name"))
        self.tree.column("Nama", width=110, minwidth=80, stretch=True)
        
        self.tree.heading("Telepon", text=t("Phone Number"))
        self.tree.column("Telepon", width=110, minwidth=80, stretch=False)
        
        self.tree.heading("Level", text="Level")
        self.tree.column("Level", width=50, minwidth=40, stretch=False)
        
        self.tree.heading("Sesi", text=t("Session"))
        self.tree.column("Sesi", width=50, minwidth=40, stretch=False)
        
        self.tree.heading("Status", text=t("Status"))
        self.tree.column("Status", width=90, minwidth=70, stretch=False)
        
        self.tree.heading("Grup", text=t("Group"))
        self.tree.column("Grup", width=80, minwidth=60, stretch=False)
        
        self.tree.heading("Fitur", text="Fitur")
        self.tree.column("Fitur", width=130, minwidth=100, stretch=False)
        
        self.tree.heading("Tingkat", text=t("Success Rate"))
        self.tree.column("Tingkat", width=70, minwidth=60, stretch=False)
        
        # Scrollbars for the table (vertical + horizontal)
        tree_scroll_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        tree_scroll_x = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        tree_scroll_y.pack(side="right", fill="y")
        tree_scroll_x.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True, padx=(10, 0), pady=(5, 0))
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
        feature_frame = tk.LabelFrame(self.scrollable_frame, text=f"⚡ {t('Feature Assignment')}", 
                                       bg="#0f3460", fg="#00d9ff",
                                       font=("Segoe UI", 11, "bold"))
        feature_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(feature_frame, text=t("Assign selected accounts to features:"),
                bg="#0f3460", fg="#ffffff").pack(pady=5)
        
        feature_btn_frame = tk.Frame(feature_frame, bg="#0f3460")
        feature_btn_frame.pack(pady=10)
        
        tk.Button(feature_btn_frame, text=f"📢 {t('Broadcast')}", command=self._bulk_assign_broadcast,
                  bg="#00d9ff", fg="#000000", font=("Segoe UI", 10, "bold")).pack(side="left", padx=5)
        tk.Button(feature_btn_frame, text=f"🔍 {t('Finder')}", command=self._bulk_assign_finder,
                  bg="#00d9ff", fg="#000000", font=("Segoe UI", 10, "bold")).pack(side="left", padx=5)
        tk.Button(feature_btn_frame, text=f"📥 {t('Scrape')}", command=self._bulk_assign_scrape,
                  bg="#00d9ff", fg="#000000", font=("Segoe UI", 10, "bold")).pack(side="left", padx=5)
        tk.Button(feature_btn_frame, text=f"📤 {t('Join')}", command=self._bulk_assign_join,
                  bg="#00d9ff", fg="#000000", font=("Segoe UI", 10, "bold")).pack(side="left", padx=5)
        tk.Button(feature_btn_frame, text=f"💬 {t('AI CS')}", command=self._bulk_assign_cs,
                  bg="#00d9ff", fg="#000000", font=("Segoe UI", 10, "bold")).pack(side="left", padx=5)
        tk.Button(feature_btn_frame, text=f"❌ {t('Unassign All')}", command=self._bulk_unassign,
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
        for acc in self.filtered_accounts:
            account_name = acc.get("name", "")
            if account_name and account_name not in self.selected_accounts:
                self.selected_accounts.append(account_name)
        for item in self.tree.get_children():
            self.tree.set(item, "#1", "☑")
        count = len(self.selected_accounts)
        self.feature_count_label.config(text=f"Selected: {count}")
    
    def _deselect_all(self):
        self.selected_accounts = []
        for item in self.tree.get_children():
            self.tree.set(item, "#1", "☐")
        self.feature_count_label.config(text="Selected: 0")
    
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
        for item in self.tree.get_children():
            values = self.tree.item(item, "values")
            if values:
                account_name = values[1]
                if values[0] == "☑":
                    if account_name not in self.selected_accounts:
                        self.selected_accounts.append(account_name)
                else:
                    if account_name in self.selected_accounts:
                        self.selected_accounts.remove(account_name)
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
            
            # Features assigned
            features = account_manager.get_account_features(acc.get("name", ""))
            features_display = ", ".join(features) if features else "-"
            
            account_name = acc.get("name", "")
            is_selected = account_name in self.selected_accounts
            checkbox = "☑" if is_selected else "☐"

            self.tree.insert("", "end", values=(
                checkbox,
                account_name,
                acc.get("phone", ""),
                acc.get("level", 1), 
                session_status,
                acc.get('status', 'active'),
                acc.get('group', '-'),
                features_display,
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
    
    # ═══════════════════════════════════════════════════════
    # ADD ACCOUNT – Real Telegram OTP Login
    # ═══════════════════════════════════════════════════════

    def _add_account(self):
        """Open dialog to add a single account with real Telegram OTP."""
        dialog = tk.Toplevel(self.frame)
        dialog.title("➕ Add Account (Real OTP Login)")
        dialog.geometry("420x380")
        dialog.configure(bg="#1a1a2e")
        dialog.transient(self.frame)
        dialog.grab_set()

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
        level_combo = ttk.Combobox(form_frame, textvariable=level_var,
                                    values=["1", "2", "3", "4"], width=28)
        level_combo.grid(row=2, column=1, padx=10, pady=8)

        status_var = tk.StringVar(value="")
        status_label = tk.Label(dialog, textvariable=status_var, fg="#ffaa00",
                                 bg="#1a1a2e", font=("Segoe UI", 10), wraplength=380)
        status_label.pack(pady=5)

        btn_frame = tk.Frame(dialog, bg="#1a1a2e")
        btn_frame.pack(pady=10)

        send_btn = tk.Button(btn_frame, text="📱 Send OTP", command=lambda: _send_otp(),
                              bg="#00d9ff", fg="#000000", font=("Segoe UI", 11, "bold"),
                              padx=20, pady=8)
        send_btn.pack(side="left", padx=5)

        # Stored state between OTP steps
        _state = {"phone_code_hash": None}

        def _set_status(msg, color="#ffaa00"):
            status_var.set(msg)
            status_label.config(fg=color)
            dialog.update_idletasks()

        def _send_otp():
            phone = phone_entry.get().strip()
            if not phone or phone == "+62":
                messagebox.showerror("Error", "Enter a valid phone number!", parent=dialog)
                return

            send_btn.config(state="disabled", text="⏳ Sending…")
            _set_status("Connecting to Telegram…")

            def _do():
                try:
                    from core.telegram_client import request_login_code, run_async
                    result = run_async(request_login_code(phone))

                    if result.get("already_authorized"):
                        # Already logged in – just register account
                        dialog.after(0, lambda: _finish_already_authorized(phone))
                    else:
                        _state["phone_code_hash"] = result.get("phone_code_hash", "")
                        dialog.after(0, lambda: _show_otp_step(phone))
                except Exception as exc:
                    dialog.after(0, lambda: _on_error(str(exc)))

            threading.Thread(target=_do, daemon=True).start()

        def _on_error(msg):
            send_btn.config(state="normal", text="📱 Send OTP")
            _set_status(f"❌ {msg}", "#ff4444")
            messagebox.showerror("Error", msg, parent=dialog)

        def _finish_already_authorized(phone):
            name = name_entry.get().strip() or phone
            level = int(level_var.get())
            account_manager.add(name, phone, level)
            _set_status(f"✅ Account {name} already authorized and added!", "#00ff00")
            self._load_accounts()
            dialog.after(1500, dialog.destroy)

        def _show_otp_step(phone):
            send_btn.config(state="normal", text="🔄 Resend OTP")
            _set_status(f"✅ OTP sent to {phone}! Enter it below.", "#00ff00")

            otp_win = tk.Toplevel(dialog)
            otp_win.title("🔑 Enter OTP")
            otp_win.geometry("360x320")
            otp_win.configure(bg="#1a1a2e")
            otp_win.transient(dialog)
            otp_win.grab_set()

            tk.Label(otp_win, text="🔑 Enter OTP Code", font=("Segoe UI", 14, "bold"),
                     fg="#00d9ff", bg="#1a1a2e").pack(pady=12)
            tk.Label(otp_win, text=f"Code sent to: {phone}",
                     fg="#ffffff", bg="#1a1a2e").pack()
            tk.Label(otp_win, text="Check your Telegram app for the code.",
                     fg="#aaaaaa", bg="#1a1a2e", font=("Segoe UI", 9)).pack(pady=5)

            otp_frame = tk.Frame(otp_win, bg="#0f3460")
            otp_frame.pack(fill="x", padx=20, pady=10)

            tk.Label(otp_frame, text="OTP Code:", fg="#ffffff", bg="#0f3460").grid(row=0, column=0, padx=10, pady=8)
            otp_entry = tk.Entry(otp_frame, width=20, bg="#1a1a2e", fg="#ffffff",
                                  font=("Segoe UI", 14), justify="center")
            otp_entry.grid(row=0, column=1, padx=10, pady=8)
            otp_entry.focus_set()

            tk.Label(otp_frame, text="2FA Password\n(if enabled):", fg="#ffffff", bg="#0f3460").grid(row=1, column=0, padx=10, pady=8)
            pw_entry = tk.Entry(otp_frame, width=20, bg="#1a1a2e", fg="#ffffff", show="●")
            pw_entry.grid(row=1, column=1, padx=10, pady=8)

            otp_status_var = tk.StringVar(value="")
            otp_status_lbl = tk.Label(otp_win, textvariable=otp_status_var,
                                       fg="#ffaa00", bg="#1a1a2e", wraplength=320)
            otp_status_lbl.pack(pady=5)

            verify_btn = tk.Button(otp_win, text="✅ Verify OTP", command=lambda: _verify(),
                                    bg="#00ff00", fg="#000000", font=("Segoe UI", 11, "bold"),
                                    padx=20, pady=8)
            verify_btn.pack(pady=8)
            otp_entry.bind("<Return>", lambda e: _verify())

            def _verify():
                code = otp_entry.get().strip()
                password = pw_entry.get().strip()
                if not code:
                    messagebox.showerror("Error", "Enter the OTP code!", parent=otp_win)
                    return

                verify_btn.config(state="disabled", text="⏳ Verifying…")
                otp_status_var.set("Verifying OTP…")

                def _do_verify():
                    try:
                        from core.telegram_client import sign_in_with_code, run_async
                        result = run_async(sign_in_with_code(
                            phone, code, _state["phone_code_hash"], password
                        ))

                        name = name_entry.get().strip() or result["user"]["first_name"] or phone
                        level = int(level_var.get())

                        account_manager.add(name, phone, level, status="active")
                        log(f"✅ Account {name} ({phone}) added with real session", "success")

                        otp_win.after(0, lambda: _on_verify_success(name, otp_win))
                    except Exception as exc:
                        otp_win.after(0, lambda: _on_verify_error(str(exc), verify_btn, otp_status_var))

                threading.Thread(target=_do_verify, daemon=True).start()

            def _on_verify_success(name, win):
                otp_status_var.set(f"✅ Login successful! Account '{name}' added.")
                otp_status_lbl.config(fg="#00ff00")
                self._load_accounts()
                win.after(1500, win.destroy)
                dialog.after(1600, dialog.destroy)

            def _on_verify_error(msg, btn, status_sv):
                btn.config(state="normal", text="✅ Verify OTP")
                status_sv.set(f"❌ {msg}")
                otp_status_lbl.config(fg="#ff4444")
                messagebox.showerror("Error", msg, parent=otp_win)

    # ═══════════════════════════════════════════════════════
    # BULK IMPORT – CSV with real OTP login per account
    # ═══════════════════════════════════════════════════════

    def _bulk_login_csv(self):
        """Bulk-add accounts from CSV, performing real OTP for each."""
        filepath = filedialog.askopenfilename(
            title="Select CSV (phone,name,level)",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not filepath:
            return

        import csv
        rows = []
        try:
            with open(filepath, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    phone = row.get("phone", "").strip()
                    name = row.get("name", "").strip() or phone
                    level = int(row.get("level", "1").strip() or 1)
                    if phone:
                        rows.append((phone, name, level))
        except Exception as exc:
            messagebox.showerror("CSV Error", str(exc))
            return

        if not rows:
            messagebox.showwarning("Warning", "No valid phone numbers found in CSV")
            return

        # Progress window
        prog_win = tk.Toplevel(self.frame)
        prog_win.title("📥 Bulk Account Import")
        prog_win.geometry("480x400")
        prog_win.configure(bg="#1a1a2e")

        tk.Label(prog_win, text="📥 Bulk Import Progress",
                 font=("Segoe UI", 14, "bold"), fg="#00d9ff", bg="#1a1a2e").pack(pady=10)

        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(prog_win, variable=progress_var,
                                        maximum=len(rows), length=400)
        progress_bar.pack(pady=5)

        status_text = tk.Text(prog_win, height=15, bg="#0f3460", fg="#ffffff",
                               font=("Consolas", 9), state="disabled")
        status_text.pack(fill="both", expand=True, padx=10, pady=5)

        tk.Button(prog_win, text="Close", command=prog_win.destroy,
                  bg="#888888", fg="#ffffff").pack(pady=5)

        def _append(msg):
            status_text.config(state="normal")
            status_text.insert("end", msg + "\n")
            status_text.see("end")
            status_text.config(state="disabled")
            prog_win.update_idletasks()

        def _run():
            from core.telegram_client import request_login_code, sign_in_with_code, run_async

            for idx, (phone, name, level) in enumerate(rows):
                progress_var.set(idx + 1)

                # Check if already in accounts with valid session
                existing = account_manager.get(name) or next(
                    (a for a in account_manager.get_all() if a.get("phone") == phone), None
                )
                if existing:
                    session_check = account_manager.check_session(existing["name"])
                    if session_check["valid"]:
                        _append(f"⏭️  {phone} – already authorized (session exists)")
                        continue

                try:
                    result = run_async(request_login_code(phone))
                    if result.get("already_authorized"):
                        account_manager.add(name, phone, level)
                        _append(f"✅ {phone} ({name}) – already authorized, added")
                        continue

                    phone_code_hash = result.get("phone_code_hash", "")
                    _append(f"📱 {phone} – OTP sent. Waiting for user input…")

                    # Ask user for OTP in GUI thread
                    code_holder = [None]
                    pw_holder = [""]
                    event = threading.Event()

                    def _ask_code(ph=phone, holder=code_holder, pw_h=pw_holder, ev=event):
                        self._otp_input_dialog(ph, holder, pw_h, ev)

                    prog_win.after(0, _ask_code)
                    event.wait(timeout=_BULK_OTP_TIMEOUT_SECONDS)

                    code = code_holder[0]
                    password = pw_holder[0]

                    if not code:
                        _append(f"⏭️  {phone} – OTP skipped or timed out")
                        continue

                    sign_result = run_async(sign_in_with_code(phone, code, phone_code_hash, password))
                    real_name = name or sign_result["user"]["first_name"] or phone
                    account_manager.add(real_name, phone, level)
                    _append(f"✅ {phone} ({real_name}) – login successful!")

                except Exception as exc:
                    _append(f"❌ {phone} – error: {exc}")

            prog_win.after(0, lambda: (self._load_accounts(), _append("✅ Bulk import complete!")))

        threading.Thread(target=_run, daemon=True).start()

    def _otp_input_dialog(self, phone: str, code_holder: list, pw_holder: list, event: threading.Event):
        """Show a modal OTP input dialog for *phone* during bulk import."""
        otp_win = tk.Toplevel(self.frame)
        otp_win.title(f"🔑 OTP for {phone}")
        otp_win.geometry("360x280")
        otp_win.configure(bg="#1a1a2e")
        otp_win.transient(self.frame)
        otp_win.grab_set()

        tk.Label(otp_win, text=f"Enter OTP for\n{phone}",
                 font=("Segoe UI", 12, "bold"), fg="#00d9ff", bg="#1a1a2e").pack(pady=10)
        tk.Label(otp_win, text="Check your Telegram app",
                 fg="#aaaaaa", bg="#1a1a2e").pack()

        frm = tk.Frame(otp_win, bg="#0f3460")
        frm.pack(fill="x", padx=20, pady=10)

        tk.Label(frm, text="OTP Code:", fg="#ffffff", bg="#0f3460").grid(row=0, column=0, padx=10, pady=6)
        otp_entry = tk.Entry(frm, width=18, bg="#1a1a2e", fg="#ffffff",
                              font=("Segoe UI", 13), justify="center")
        otp_entry.grid(row=0, column=1, padx=10, pady=6)
        otp_entry.focus_set()

        tk.Label(frm, text="2FA Password:", fg="#ffffff", bg="#0f3460").grid(row=1, column=0, padx=10, pady=6)
        pw_entry = tk.Entry(frm, width=18, bg="#1a1a2e", fg="#ffffff", show="●")
        pw_entry.grid(row=1, column=1, padx=10, pady=6)

        def _submit():
            code_holder[0] = otp_entry.get().strip()
            pw_holder[0] = pw_entry.get().strip()
            otp_win.destroy()
            event.set()

        def _skip():
            otp_win.destroy()
            event.set()

        btn_frm = tk.Frame(otp_win, bg="#1a1a2e")
        btn_frm.pack(pady=8)
        tk.Button(btn_frm, text="✅ Submit", command=_submit,
                  bg="#00ff00", fg="#000000", font=("Segoe UI", 11, "bold"),
                  padx=15).pack(side="left", padx=5)
        tk.Button(btn_frm, text="⏭️ Skip", command=_skip,
                  bg="#888888", fg="#ffffff").pack(side="left", padx=5)
        otp_entry.bind("<Return>", lambda e: _submit())
    
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
        menu.add_command(label="📞 Phones CSV (no OTP)", command=self._import_phones_csv)
        menu.add_command(label="📞 Phones TXT", command=self._import_phones_txt)
        menu.add_separator()
        menu.add_command(label="🔐 Bulk Login CSV (with OTP)", command=self._bulk_login_csv)
        menu.post(self.frame.winfo_rootx(), self.frame.winfo_rooty())
    
    def _import_session(self):
        filepath = filedialog.askopenfilename(filetypes=[("Session files", "*.session")])
        if filepath:
            name = simpledialog.askstring("Account Name", "Enter account name:")
            if name:
                try:
                    result = import_manager.import_session_single(filepath, name)
                    self._load_accounts()
                    if result.success:
                        messagebox.showinfo("Success", f"Session imported: {name}")
                    else:
                        messagebox.showerror("Import Error", f"Failed to import: {getattr(result, 'error', 'Unknown error')}")
                except Exception as e:
                    log(f"Import session error: {e}", "error")
                    messagebox.showerror("Import Error", str(e))
    
    def _import_sessions_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            try:
                result = import_manager.import_sessions_folder(folder)
                self._load_accounts()
                messagebox.showinfo("Import", f"Imported {result.imported} sessions")
            except Exception as e:
                log(f"Import folder error: {e}", "error")
                messagebox.showerror("Import Error", str(e))
    
    def _import_phones_csv(self):
        filepath = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if filepath:
            try:
                result = import_manager.import_phones_csv(filepath)
                self._load_accounts()
                messagebox.showinfo("Import", f"Imported {result.imported} phones")
            except Exception as e:
                log(f"Import CSV error: {e}", "error")
                messagebox.showerror("Import Error", str(e))
    
    def _import_phones_txt(self):
        filepath = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if filepath:
            try:
                result = import_manager.import_phones_txt(filepath, "pipe")
                self._load_accounts()
                messagebox.showinfo("Import", f"Imported {result.imported} phones")
            except Exception as e:
                log(f"Import TXT error: {e}", "error")
                messagebox.showerror("Import Error", str(e))
    
    def _export_accounts(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".csv")
        if filepath:
            try:
                import_manager.export_accounts(filepath, 'csv')
                messagebox.showinfo("Success", f"Exported to {filepath}")
            except Exception as e:
                log(f"Export error: {e}", "error")
                messagebox.showerror("Export Error", str(e))
    
    # ═══════════════════════════════════════════════════════
    # FEATURE ASSIGNMENT
    # ═══════════════════════════════════════════════════════
    
    def _bulk_assign_broadcast(self):
        if not self.selected_accounts:
            messagebox.showwarning(t("Warning"), "Pilih akun terlebih dahulu!")
            return
        try:
            for name in self.selected_accounts:
                account_manager.assign_feature(name, "broadcast")
            self._load_accounts()
            self._sync_feature_tabs()
            messagebox.showinfo("Success", f"Assigned {len(self.selected_accounts)} to Broadcast")
        except Exception as e:
            log(f"Assign broadcast error: {e}", "error")
            messagebox.showerror("Error", str(e))

    def _bulk_assign_finder(self):
        if not self.selected_accounts:
            messagebox.showwarning("Peringatan", "Pilih akun terlebih dahulu!")
            return
        try:
            for name in self.selected_accounts:
                account_manager.assign_feature(name, "finder")
            self._load_accounts()
            self._sync_feature_tabs()
            messagebox.showinfo("Success", f"Assigned {len(self.selected_accounts)} to Finder")
        except Exception as e:
            log(f"Assign finder error: {e}", "error")
            messagebox.showerror("Error", str(e))

    def _bulk_assign_scrape(self):
        if not self.selected_accounts:
            messagebox.showwarning("Peringatan", "Pilih akun terlebih dahulu!")
            return
        try:
            for name in self.selected_accounts:
                account_manager.assign_feature(name, "scrape")
            self._load_accounts()
            self._sync_feature_tabs()
            messagebox.showinfo("Success", f"Assigned {len(self.selected_accounts)} to Scrape")
        except Exception as e:
            log(f"Assign scrape error: {e}", "error")
            messagebox.showerror("Error", str(e))

    def _bulk_assign_join(self):
        if not self.selected_accounts:
            messagebox.showwarning("Peringatan", "Pilih akun terlebih dahulu!")
            return
        try:
            for name in self.selected_accounts:
                account_manager.assign_feature(name, "join")
            self._load_accounts()
            self._sync_feature_tabs()
            messagebox.showinfo("Success", f"Assigned {len(self.selected_accounts)} to Join")
        except Exception as e:
            log(f"Assign join error: {e}", "error")
            messagebox.showerror("Error", str(e))

    def _bulk_assign_cs(self):
        if not self.selected_accounts:
            messagebox.showwarning("Peringatan", "Pilih akun terlebih dahulu!")
            return
        try:
            for name in self.selected_accounts:
                account_manager.assign_feature(name, "cs")
            self._load_accounts()
            self._sync_feature_tabs()
            messagebox.showinfo("Success", f"Assigned {len(self.selected_accounts)} to CS")
        except Exception as e:
            log(f"Assign CS error: {e}", "error")
            messagebox.showerror("Error", str(e))

    def _bulk_unassign(self):
        if not self.selected_accounts:
            messagebox.showwarning("Peringatan", "Pilih akun terlebih dahulu!")
            return
        if messagebox.askyesno("Konfirmasi", f"Lepas semua penetapan fitur dari {len(self.selected_accounts)} akun?"):
            try:
                for name in self.selected_accounts:
                    acc = account_manager.get(name)
                    if acc:
                        acc["features"] = []
                        acc["assigned_groups"] = []
                account_manager._save_accounts()
                self._load_accounts()
                self._sync_feature_tabs()
                messagebox.showinfo("Success", f"Unassigned {len(self.selected_accounts)} accounts")
            except Exception as e:
                log(f"Unassign error: {e}", "error")
                messagebox.showerror("Error", str(e))

    def _sync_feature_tabs(self):
        """Notify main_window to sync all feature tabs."""
        try:
            state_manager.emit_state_change("account_assigned", {"feature": "updated"})
            mw = getattr(self, 'main_window', None)
            if mw is not None and hasattr(mw, "sync_feature_tabs"):
                mw.sync_feature_tabs()
        except Exception:
            pass
    
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
                try:
                    if account_manager.create_group(name):
                        self._update_group_combo()
                        self._sync_groups_to_broadcast()
                        _load_groups_list()
                        messagebox.showinfo("Success", f"Group '{name}' created!")
                    else:
                        messagebox.showerror("Error", "Group already exists!")
                except Exception as e:
                    log(f"Create group error: {e}", "error")
                    messagebox.showerror("Error", str(e))
        
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
            try:
                added = account_manager.bulk_assign_to_group(group, self.selected_accounts)
                _load_groups_list()
                self._sync_groups_to_broadcast()
                messagebox.showinfo("Success", f"Assigned {added} accounts to '{group}'")
            except Exception as e:
                log(f"Assign to group error: {e}", "error")
                messagebox.showerror("Error", str(e))
        
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
                try:
                    if account_manager.delete_group(group_name):
                        _load_groups_list()
                        self._update_group_combo()
                        self._sync_groups_to_broadcast()
                        messagebox.showinfo("Success", f"Group '{group_name}' deleted!")
                except Exception as e:
                    log(f"Delete group error: {e}", "error")
                    messagebox.showerror("Error", str(e))
        
        tk.Button(btn_frame, text="👁️ View", command=view_group,
                  bg="#00d9ff", fg="#000000", font=("Segoe UI", 10, "bold")).pack(side="left", padx=5)
        tk.Button(btn_frame, text="🗑️ Delete", command=delete_group,
                  bg="#ff0000", fg="#ffffff", font=("Segoe UI", 10, "bold")).pack(side="left", padx=5)
        tk.Button(btn_frame, text="🔄 Refresh", command=_load_groups_list,
                  bg="#00d9ff", fg="#000000", font=("Segoe UI", 10, "bold")).pack(side="left", padx=5)
        tk.Button(btn_frame, text="✅ Done", command=dialog.destroy,
                  bg="#00ff00", fg="#000000", font=("Segoe UI", 10, "bold")).pack(side="right", padx=5)
    
    def _sync_groups_to_broadcast(self):
        # Emit state change to sync all tabs (broadcast_tab listens via state_manager)
        state_manager.emit_state_change("account_assigned", {"feature": "groups_updated"})
        if hasattr(self.main_window, 'broadcast_tab'):
            try:
                self.main_window.broadcast_tab._load_broadcast_groups()
                log("Grup disinkronkan ke tab Siaran", "success")
            except Exception as e:
                log(f"Gagal sinkronisasi grup: {e}", "error")
    
    def _refresh(self):
        self._load_accounts()
    # ── Sprint 3: Import Dialog ────────────────────────────────────────────────

    def _open_import_dialog(self):
        """Open the advanced Import dialog (Session / Bulk / File)."""
        ImportDialog(self.frame, on_imported=self._on_import_finished)

    def _on_import_finished(self, result: dict):
        """Callback when an import finishes – refresh account list."""
        self._load_accounts()
        imported = result.get("imported", 0)
        log(f"Import complete: {imported} account(s) added", "success")

    # ── Sprint 3: OTP Setup ──────────────────────────────────────────────────

    def _open_otp_setup_for_selected(self):
        """Open OTP setup for the first selected account in the tree."""
        selection = self.tree.selection() if hasattr(self, "tree") else []
        if not selection:
            messagebox.showwarning(
                "No Selection",
                "Select an account from the list first",
                parent=self.frame,
            )
            return
        item = self.tree.item(selection[0])
        tags = item.get("tags", [])
        # tags[0] is expected to be the account name
        account_name = tags[0] if tags else ""
        # Find account_id via local account_manager
        accounts = account_manager.load_accounts()
        acct = accounts.get(account_name, {})
        account_id = acct.get("id")
        if not account_id:
            messagebox.showwarning(
                "No ID",
                "Account does not have a server ID. Sync with backend first.",
                parent=self.frame,
            )
            return
        OTPSetupDialog(
            self.frame,
            account_id=int(account_id),
            account_phone=acct.get("phone", account_name),
            on_enabled=lambda _: self._load_accounts(),
        )

    # ── Sprint 3: WebSocket event handler ────────────────────────────────────

    def _on_ws_event(self, payload: dict):
        """
        Called from the WSSyncClient background thread when an account event
        arrives.  Schedules a UI refresh on the Tkinter main thread.
        """
        event = payload.get("event", "")
        if event in {
            "account.imported", "account.bulk_created", "account.file_imported",
            "account.updated", "account.deleted",
        }:
            self.frame.after(0, self._load_accounts)
            self.frame.after(0, lambda: log(f"Real-time sync: {event}", "info"))
