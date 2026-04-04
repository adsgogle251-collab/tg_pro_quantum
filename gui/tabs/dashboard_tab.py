"""Dashboard Tab - Complete with Scrollable Content (Fixed)"""
import tkinter as tk
from tkinter import ttk
from core import statistics, health_checker, account_manager, load_groups, campaign_manager
from core.account_router import account_router, Feature
from gui.styles import COLORS, FONTS

class DashboardTab:
    title = "📊 Dashboard"
    
    def __init__(self, parent, main_window=None):
        self.parent = parent
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        self._create_widgets()
        self._start_realtime_updates()
    
    def _create_widgets(self):
        # Header
        tk.Label(self.frame, text="📊 Real-Time Dashboard", font=("Segoe UI", 24, "bold"),
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
        
        # === STATUS DASHBOARD ===
        status_frame = tk.LabelFrame(self.scrollable_frame, text="🎯 System Readiness",
                                      fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                      font=FONTS["heading"])
        status_frame.pack(fill="x", padx=10, pady=10)
        
        self.status_items = {}
        status_checks = [
            ("📱 Accounts", self._check_accounts, COLORS["success"]),
            ("📁 Account Groups", self._check_groups, COLORS["success"]),
            ("🎯 Joined Groups", self._check_joined, COLORS["success"]),
            ("📈 Campaigns", self._check_campaigns, COLORS["success"]),
            ("🔐 License", self._check_license, COLORS["success"]),
            ("🔌 Telegram API", self._check_api, COLORS["info"]),
        ]
        
        status_grid = tk.Frame(status_frame, bg=COLORS["bg_medium"])
        status_grid.pack(fill="x", padx=10, pady=10)
        
        for i, (label, check_func, color) in enumerate(status_checks):
            row = i // 3
            col = (i % 3) * 2
            
            status_icon = tk.Label(status_grid, text="⏳", font=("Segoe UI", 16),
                                   bg=COLORS["bg_medium"])
            status_icon.grid(row=row, column=col, padx=10, pady=5)
            
            status_label = tk.Label(status_grid, text=label, font=FONTS["normal"],
                                    fg=COLORS["text"], bg=COLORS["bg_medium"])
            status_label.grid(row=row, column=col+1, padx=5, pady=5, sticky="w")
            
            self.status_items[label] = {"icon": status_icon, "check": check_func, "color": color}
        
        # Quick Start Button
        tk.Button(status_frame, text="🚀 Setup Guide", command=self._show_setup_wizard,
                  bg=COLORS["info"], fg="white", font=FONTS["bold"],
                  padx=20, pady=8).pack(pady=10)
        
        # === TOP STATS CARDS ===
        stats_frame = tk.Frame(self.scrollable_frame, bg=COLORS["bg_dark"])
        stats_frame.pack(fill="x", padx=10, pady=10)
        
        cards = [
            ("📱 Total Accounts", "accounts_var", COLORS["info"]),
            ("📢 Active Broadcasts", "broadcasts_var", COLORS["success"]),
            ("✅ Messages Sent", "sent_var", COLORS["accent"]),
            ("📈 Success Rate", "rate_var", COLORS["warning"]),
            ("🔍 Groups Found", "groups_var", COLORS["info"]),
            ("📥 Members Scraped", "scraped_var", COLORS["success"]),
        ]
        
        self.stat_vars = {}
        for i, (label, var_name, color) in enumerate(cards):
            card = tk.Frame(stats_frame, bg=COLORS["bg_medium"], relief="raised", bd=1)
            card.grid(row=0, column=i, padx=8, sticky="nsew")
            stats_frame.grid_columnconfigure(i, weight=1)
            
            tk.Label(card, text=label, font=FONTS["small"],
                    fg=COLORS["text_muted"], bg=COLORS["bg_medium"]).pack(pady=(10, 3))
            
            var = tk.StringVar(value="0")
            tk.Label(card, textvariable=var, font=("Segoe UI", 20, "bold"),
                    fg=color, bg=COLORS["bg_medium"]).pack(pady=3)
            self.stat_vars[var_name] = var
        
        # === MIDDLE SECTION ===
        middle_frame = tk.Frame(self.scrollable_frame, bg=COLORS["bg_dark"])
        middle_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left - Account Distribution
        dist_frame = tk.LabelFrame(middle_frame, text="📊 Account Distribution by Feature",
                                   fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                   font=FONTS["heading"])
        dist_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        self.feature_bars = {}
        features = [
            ("📢 Broadcast", "broadcast", COLORS["broadcast"]),
            ("🔍 Finder", "finder", COLORS["finder"]),
            ("📥 Scrape", "scrape", COLORS["scrape"]),
            ("📤 Join", "join", COLORS["join"]),
            ("💬 CS", "cs", COLORS["cs"]),
        ]
        
        for label, feature, color in features:
            frame = tk.Frame(dist_frame, bg=COLORS["bg_medium"])
            frame.pack(fill="x", padx=15, pady=4)
            
            tk.Label(frame, text=label, width=14, anchor="w",
                    fg=COLORS["text"], bg=COLORS["bg_medium"],
                    font=FONTS["normal"]).pack(side="left")
            
            bar = ttk.Progressbar(frame, mode='determinate', length=180)
            bar.pack(side="left", padx=8, fill="x", expand=True)
            
            count_label = tk.Label(frame, text="0", width=4,
                                   fg=color, bg=COLORS["bg_medium"],
                                   font=("Segoe UI", 11, "bold"))
            count_label.pack(side="left")
            
            self.feature_bars[feature] = {"bar": bar, "label": count_label}
        
        # Right - System Health
        health_frame = tk.LabelFrame(middle_frame, text="🖥️ System Health",
                                     fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                     font=FONTS["heading"])
        health_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
        self.health_text = tk.Text(health_frame, height=6, bg=COLORS["bg_light"],
                                    fg=COLORS["text"], font=("Consolas", 9))
        self.health_text.pack(fill="both", expand=True, padx=10, pady=8)
        
        # === RECENT ACTIVITY LOG ===
        activity_frame = tk.LabelFrame(self.scrollable_frame, text="📋 Recent Activity",
                                       fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                       font=FONTS["heading"])
        activity_frame.pack(fill="x", padx=10, pady=10)
        
        self.activity_text = tk.Text(activity_frame, height=4, bg=COLORS["bg_light"],
                                      fg=COLORS["text"], font=("Consolas", 9))
        self.activity_text.pack(fill="x", padx=10, pady=8)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Initial update
        self._update_all_stats()
    
    def _check_accounts(self):
        return len(account_manager.get_all()) > 0
    
    def _check_groups(self):
        return len(account_manager.get_all_groups()) > 0
    
    def _check_joined(self):
        from core.utils import load_joined_groups
        return len(load_joined_groups()) > 0
    
    def _check_campaigns(self):
        return len(campaign_manager.get_all_campaigns()) > 0
    
    def _check_license(self):
        from license.manager import check_license
        return check_license()
    
    def _check_api(self):
        from core import config_manager
        api_id = config_manager.get("telegram.api_id", 0)
        api_hash = config_manager.get("telegram.api_hash", "")
        return api_id > 0 and api_hash != ""
    
    def _update_status_dashboard(self):
        """Update status dashboard icons"""
        for label, data in self.status_items.items():
            is_ready = data["check"]()
            if is_ready:
                data["icon"].config(text="✅", fg=data["color"])
            else:
                data["icon"].config(text="❌", fg=COLORS["error"])
    
    def _show_setup_wizard(self):
        """Show setup guide wizard"""
        wizard = tk.Toplevel(self.frame)
        wizard.title("🚀 Setup Guide")
        wizard.geometry("600x500")
        wizard.configure(bg=COLORS["bg_dark"])
        wizard.transient(self.frame)
        
        tk.Label(wizard, text="🚀 TG PRO QUANTUM Setup Guide", 
                 font=("Segoe UI", 18, "bold"), fg=COLORS["primary"],
                 bg=COLORS["bg_dark"]).pack(pady=20)
        
        steps = [
            ("1️⃣ Settings", "Configure Telegram API in Settings tab"),
            ("2️⃣ Accounts", "Add/Import your Telegram accounts"),
            ("3️⃣ Groups", "Create account groups (Client_A, Client_B)"),
            ("4️⃣ Finder", "Search for target groups"),
            ("5️⃣ Join", "Join the groups you found"),
            ("6️⃣ Campaign", "Create your broadcast campaign"),
            ("7️⃣ Broadcast", "Start your campaign!"),
        ]
        
        for i, (title, desc) in enumerate(steps):
            step_frame = tk.Frame(wizard, bg=COLORS["bg_medium"])
            step_frame.pack(fill="x", padx=20, pady=5)
            
            tk.Label(step_frame, text=title, font=FONTS["bold"],
                    fg=COLORS["primary"], bg=COLORS["bg_medium"]).pack(anchor="w", padx=10, pady=5)
            tk.Label(step_frame, text=desc, font=FONTS["normal"],
                    fg=COLORS["text_muted"], bg=COLORS["bg_medium"]).pack(anchor="w", padx=10, pady=(0, 10))
        
        def open_settings():
            wizard.destroy()
            if hasattr(self.main_window, 'tabs'):
                self.main_window.notebook.select(15)  # Settings tab
        
        tk.Button(wizard, text="⚙️ Open Settings", command=open_settings,
                  bg=COLORS["success"], fg="white", font=FONTS["bold"],
                  padx=30, pady=10).pack(pady=20)
    
    def _start_realtime_updates(self):
        def update():
            self._update_all_stats()
            self.frame.after(3000, update)
        update()
    
    def _update_all_stats(self):
        try:
            # Update status dashboard
            self._update_status_dashboard()
            
            # Get account stats
            accounts = account_manager.get_all()
            total_accounts = len(accounts)
            
            # Get broadcast stats
            stats = statistics.get_summary()
            total_sent = stats.get('total_messages_sent', 0)
            total_failed = stats.get('total_failed', 0)
            total = total_sent + total_failed
            success_rate = (total_sent / total * 100) if total > 0 else 0
            
            # Get groups
            groups = load_groups()
            
            # Get feature assignments using account_manager (single source of truth)
            feature_counts = {"broadcast": 0, "finder": 0, "scrape": 0, "join": 0, "cs": 0}
            try:
                featured = account_manager.get_featured_accounts()
                for feat, accs in featured.items():
                    feature_counts[feat] = len(accs)
            except:
                pass
            
            # Update top cards
            self.stat_vars["accounts_var"].set(str(total_accounts))
            self.stat_vars["broadcasts_var"].set("1" if stats.get('total_broadcasts', 0) > 0 else "0")
            self.stat_vars["sent_var"].set(str(total_sent))
            self.stat_vars["rate_var"].set(f"{success_rate:.1f}%")
            self.stat_vars["groups_var"].set(str(len(groups)))
            self.stat_vars["scraped_var"].set(str(stats.get('total_members_scraped', 0)))
            
            # Update feature bars
            max_accounts = max(total_accounts, 1)
            for feature, data in self.feature_bars.items():
                count = feature_counts.get(feature, 0)
                percentage = (count / max_accounts) * 100
                data["bar"]["value"] = percentage
                data["label"].config(text=str(count))
            
            # Update system health
            health = health_checker.get_health_summary()
            self.health_text.delete("1.0", "end")
            self.health_text.insert("end", f"Status: {health['status'].upper()}\n")
            self.health_text.insert("end", f"Uptime: {health['uptime']}\n")
            self.health_text.insert("end", f"CPU: {health.get('cpu', 'N/A')}\n")
            self.health_text.insert("end", f"Memory: {health.get('memory', 'N/A')}\n")
            self.health_text.insert("end", f"Disk: {health.get('disk', 'N/A')}\n")
            
            if health['status'] == 'healthy':
                self.health_text.config(fg=COLORS["success"])
            elif health['status'] == 'warning':
                self.health_text.config(fg=COLORS["warning"])
            else:
                self.health_text.config(fg=COLORS["error"])
            
        except Exception as e:
            pass
    
    def _refresh(self):
        self._update_all_stats()