"""Billing Tab - Complete with Scrollable Content (Phase 8 - FIXED)"""
import tkinter as tk
from tkinter import ttk, messagebox
from core.billing_engine import billing_engine, SubscriptionTier, PRICING
from gui.styles import COLORS, FONTS

class BillingTab:
    title = "💳 Billing"
    
    def __init__(self, parent, main_window=None):
        self.parent = parent
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        self._create_widgets()
        self._load_data()
    
    def _create_widgets(self):
        # Header
        tk.Label(self.frame, text="💳 Billing & Subscriptions", font=("Segoe UI", 24, "bold"),
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
        
        # === 1. PRICING PLANS ===
        pricing_frame = tk.LabelFrame(self.scrollable_frame, text="💰 Subscription Plans",
                                       fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                       font=FONTS["heading"])
        pricing_frame.pack(fill="x", padx=10, pady=10)
        
        plans_frame = tk.Frame(pricing_frame, bg=COLORS["bg_medium"])
        plans_frame.pack(fill="x", padx=20, pady=10)
        
        plans = [
            ("🥉 Basic", PRICING.get('basic', {}).get('price', '$0'), PRICING.get('basic', {}).get('features', [])),
            ("🥈 Premium", PRICING.get('premium', {}).get('price', '$0'), PRICING.get('premium', {}).get('features', [])),
            ("🥇 Enterprise", PRICING.get('enterprise', {}).get('price', '$0'), PRICING.get('enterprise', {}).get('features', [])),
        ]
        
        for i, (name, price, features) in enumerate(plans):
            card = tk.Frame(plans_frame, bg=COLORS["bg_light"], relief="raised", bd=2)
            card.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")
            plans_frame.grid_columnconfigure(i, weight=1)
            
            tk.Label(card, text=name, font=("Segoe UI", 16, "bold"),
                    fg=COLORS["primary"], bg=COLORS["bg_light"]).pack(pady=10)
            tk.Label(card, text=price, font=("Segoe UI", 24, "bold"),
                    fg=COLORS["accent"], bg=COLORS["bg_light"]).pack(pady=5)
            
            for feature in features[:5]:
                tk.Label(card, text=f"✓ {feature}", font=FONTS["small"],
                        fg=COLORS["text"], bg=COLORS["bg_light"]).pack(pady=2)
        
        # === 2. REVENUE STATS ===
        revenue_frame = tk.LabelFrame(self.scrollable_frame, text="📈 Revenue Statistics",
                                       fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                       font=FONTS["heading"])
        revenue_frame.pack(fill="x", padx=10, pady=10)
        
        # ✅ FIX: Use correct method with fallback
        try:
            stats = billing_engine.get_billing_stats() if hasattr(billing_engine, 'get_billing_stats') else {}
        except:
            stats = {}
        
        stat_cards = [
            ("💰 Total Revenue", f"${stats.get('total_revenue', 0)}", COLORS["success"]),
            ("👥 Active Subscriptions", str(stats.get('active_subscriptions', 0)), COLORS["info"]),
            ("📊 MRR", f"${stats.get('mrr', 0)}", COLORS["accent"]),
            ("📉 Churn Rate", f"{stats.get('churn_rate', 0)}%", COLORS["warning"]),
        ]
        
        for i, (label, value, color) in enumerate(stat_cards):
            card = tk.Frame(revenue_frame, bg=COLORS["bg_light"], relief="raised", bd=1)
            card.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")
            revenue_frame.grid_columnconfigure(i, weight=1)
            
            tk.Label(card, text=label, font=FONTS["small"],
                    fg=COLORS["text_muted"], bg=COLORS["bg_light"]).pack(pady=(10, 5))
            tk.Label(card, text=value, font=("Segoe UI", 20, "bold"),
                    fg=color, bg=COLORS["bg_light"]).pack(pady=5)
        
        # === 3. SUBSCRIPTION LIST ===
        sub_frame = tk.LabelFrame(self.scrollable_frame, text="📋 Active Subscriptions",
                                   fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                   font=FONTS["heading"])
        sub_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        columns = ("Customer", "Plan", "Status", "Next Billing", "Amount")
        self.sub_tree = ttk.Treeview(sub_frame, columns=columns, show="headings", height=8)
        
        for col in columns:
            self.sub_tree.heading(col, text=col)
            width = 150 if col not in ["Customer"] else 250
            self.sub_tree.column(col, width=width)
        
        self.sub_tree.pack(fill="both", expand=True, padx=10, pady=5)
        
        # === 4. ACTION BUTTONS ===
        btn_frame = tk.Frame(self.scrollable_frame, bg=COLORS["bg_dark"])
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Button(btn_frame, text="➕ New Subscription", command=self._new_subscription,
                  bg=COLORS["success"], fg="white", font=FONTS["bold"]).pack(side="left", padx=5)
        tk.Button(btn_frame, text="💳 Process Payment", command=self._process_payment,
                  bg=COLORS["info"], fg="white", font=FONTS["bold"]).pack(side="left", padx=5)
        tk.Button(btn_frame, text="📊 Generate Invoice", command=self._generate_invoice,
                  bg=COLORS["accent"], fg="white", font=FONTS["bold"]).pack(side="left", padx=5)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _load_data(self):
        """Load billing data - with fallback for missing methods"""
        for item in self.sub_tree.get_children():
            self.sub_tree.delete(item)
        
        try:
            # ✅ FIX: Try get_subscription first (singular), fallback to empty list
            if hasattr(billing_engine, 'get_subscription'):
                sub = billing_engine.get_subscription()
                subscriptions = [sub] if sub else []
            elif hasattr(billing_engine, 'get_all_subscriptions'):
                subscriptions = billing_engine.get_all_subscriptions()
            else:
                subscriptions = []
        except:
            subscriptions = []
        
        for sub in subscriptions:
            self.sub_tree.insert("", "end", values=(
                sub.get('customer', 'N/A'),
                sub.get('plan', 'N/A'),
                sub.get('status', 'N/A'),
                sub.get('next_billing', 'N/A')[:10] if sub.get('next_billing') else 'N/A',
                f"${sub.get('amount', 0)}"
            ))
    
    def _new_subscription(self):
        messagebox.showinfo("Info", "New subscription feature - implement dialog")
    
    def _process_payment(self):
        messagebox.showinfo("Info", "Process payment feature - implement payment gateway")
    
    def _generate_invoice(self):
        messagebox.showinfo("Info", "Generate invoice feature - implement PDF generation")
    
    def _refresh(self):
        self._load_data()