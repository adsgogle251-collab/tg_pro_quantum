"""Analytics Tab - Complete with Scrollable Content (Phase 8)"""
import tkinter as tk
from tkinter import ttk
from core import statistics, account_manager
from gui.styles import COLORS, FONTS
from core.localization import t

class AnalyticsTab:
    title = "📊 Analytics"
    
    def __init__(self, parent, main_window=None):
        self.parent = parent
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        self._create_widgets()
    
    def _create_widgets(self):
        # Header
        tk.Label(self.frame, text=f"📊 {t('Analytics Dashboard')}", font=("Segoe UI", 24, "bold"),
                 fg=COLORS["primary"], bg=COLORS["bg_dark"]).pack(pady=15)
        
        # === MAIN SCROLLABLE CONTAINER ===
        main_container = tk.Frame(self.frame, bg=COLORS["bg_dark"])
        main_container.pack(fill="both", expand=True, padx=10, pady=5)
        
        canvas = tk.Canvas(main_container, bg=COLORS["bg_dark"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg=COLORS["bg_dark"])
        
        self.scrollable_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        
        # === 1. OVERVIEW STATS ===
        overview_frame = tk.LabelFrame(self.scrollable_frame, text="📈 Overview Statistics",
                                        fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                        font=FONTS["heading"])
        overview_frame.pack(fill="x", padx=10, pady=10)
        
        stats = statistics.get_summary()
        
        stat_cards = [
            ("📊 Total Broadcasts", str(stats.get('total_broadcasts', 0)), COLORS["info"]),
            ("✅ Messages Sent", str(stats.get('total_messages_sent', 0)), COLORS["success"]),
            ("❌ Messages Failed", str(stats.get('total_failed', 0)), COLORS["error"]),
            ("📈 Success Rate", f"{stats.get('success_rate', 0)}%", COLORS["accent"]),
        ]
        
        for i, (label, value, color) in enumerate(stat_cards):
            card = tk.Frame(overview_frame, bg=COLORS["bg_light"], relief="raised", bd=1)
            card.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")
            overview_frame.grid_columnconfigure(i, weight=1)
            
            tk.Label(card, text=label, font=FONTS["small"],
                    fg=COLORS["text_muted"], bg=COLORS["bg_light"]).pack(pady=(10, 5))
            tk.Label(card, text=value, font=("Segoe UI", 20, "bold"),
                    fg=color, bg=COLORS["bg_light"]).pack(pady=5)
        
        # === 2. ACCOUNT DISTRIBUTION ===
        account_frame = tk.LabelFrame(self.scrollable_frame, text="📱 Account Distribution",
                                       fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                       font=FONTS["heading"])
        account_frame.pack(fill="x", padx=10, pady=10)
        
        accounts = account_manager.get_all()
        account_stats = account_manager.get_stats()
        
        tk.Label(account_frame, text=f"Total Accounts: {len(accounts)}",
                fg=COLORS["text"], bg=COLORS["bg_medium"], font=FONTS["bold"]).pack(pady=5)
        
        level_frame = tk.Frame(account_frame, bg=COLORS["bg_medium"])
        level_frame.pack(fill="x", padx=20, pady=10)
        
        for level in range(1, 5):
            count = account_stats['by_level'].get(level, 0)
            pct = (count / len(accounts) * 100) if accounts else 0
            
            level_row = tk.Frame(level_frame, bg=COLORS["bg_medium"])
            level_row.pack(fill="x", pady=3)
            
            tk.Label(level_row, text=f"Level {level}:", width=10,
                    fg=COLORS["text"], bg=COLORS["bg_medium"]).pack(side="left")
            
            bar = ttk.Progressbar(level_row, mode='determinate', length=300)
            bar['value'] = pct
            bar.pack(side="left", padx=10)
            
            tk.Label(level_row, text=f"{count} ({pct:.1f}%)", width=15,
                    fg=COLORS["text"], bg=COLORS["bg_medium"]).pack(side="left")
        
        # === 3. FEATURE USAGE ===
        feature_frame = tk.LabelFrame(self.scrollable_frame, text="⚡ Feature Usage",
                                       fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                       font=FONTS["heading"])
        feature_frame.pack(fill="x", padx=10, pady=10)
        
        from core.account_router import account_router
        
        try:
            assignments = account_router.get_assignments()
            feature_counts = {}
            for assignment in assignments:
                feature = assignment.feature.value
                feature_counts[feature] = feature_counts.get(feature, 0) + 1
            
            for feature, count in feature_counts.items():
                feat_row = tk.Frame(feature_frame, bg=COLORS["bg_medium"])
                feat_row.pack(fill="x", padx=20, pady=3)
                
                tk.Label(feat_row, text=f"📢 {feature.title()}:", width=15,
                        fg=COLORS["text"], bg=COLORS["bg_medium"]).pack(side="left")
                tk.Label(feat_row, text=f"{count} accounts",
                        fg=COLORS["text_muted"], bg=COLORS["bg_medium"]).pack(side="left")
        except:
            tk.Label(feature_frame, text="No feature assignments yet",
                    fg=COLORS["text_muted"], bg=COLORS["bg_medium"]).pack(pady=10)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _refresh(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self._create_widgets()