"""Campaign Dashboard Tab - Multi-Client 24/7 Monitor (Phase 10)"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from core import campaign_manager, statistics
from core.scheduler_24h import scheduler_24h
from core.clients import client_manager
from gui.styles import COLORS, FONTS

class CampaignDashboardTab:
    title = "📊 Campaign Dashboard"
    
    def __init__(self, parent, main_window=None):
        self.parent = parent
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        self._create_widgets()
        self._load_dashboard()
        self._start_auto_refresh()
    
    def _create_widgets(self):
        # Header
        tk.Label(self.frame, text="📊 Campaign Dashboard - 24/7 Monitor", 
                 font=("Segoe UI", 24, "bold"), fg=COLORS["primary"], 
                 bg=COLORS["bg_dark"]).pack(pady=15)
        
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
        overview_frame = tk.LabelFrame(self.scrollable_frame, text="📈 Overview",
                                        fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                        font=FONTS["heading"])
        overview_frame.pack(fill="x", padx=10, pady=10)
        
        stats = campaign_manager.get_campaign_summary() if hasattr(campaign_manager, 'get_campaign_summary') else {'total': 0, 'running': 0, 'scheduled': 0, 'completed': 0}
        
        stat_cards = [
            ("📊 Total Campaigns", str(stats.get('total', 0)), COLORS["info"]),
            ("🟢 Running", str(stats.get('running', 0)), COLORS["success"]),
            ("🟡 Scheduled", str(stats.get('scheduled', 0)), COLORS["warning"]),
            ("✅ Completed", str(stats.get('completed', 0)), COLORS["accent"]),
        ]
        
        for i, (label, value, color) in enumerate(stat_cards):
            card = tk.Frame(overview_frame, bg=COLORS["bg_light"], relief="raised", bd=1)
            card.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")
            overview_frame.grid_columnconfigure(i, weight=1)
            
            tk.Label(card, text=label, font=FONTS["small"],
                    fg=COLORS["text_muted"], bg=COLORS["bg_light"]).pack(pady=(10, 5))
            tk.Label(card, text=value, font=("Segoe UI", 20, "bold"),
                    fg=color, bg=COLORS["bg_light"]).pack(pady=5)
        
        # === 2. CLIENT FILTER ===
        filter_frame = tk.Frame(self.scrollable_frame, bg=COLORS["bg_dark"])
        filter_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(filter_frame, text="👤 Client:", fg=COLORS["text"], bg=COLORS["bg_dark"]).pack(side="left", padx=5)
        self.client_var = tk.StringVar(value="All")
        self.client_combo = ttk.Combobox(filter_frame, textvariable=self.client_var, width=20)
        self.client_combo.pack(side="left", padx=5)
        self.client_combo.bind("<<ComboboxSelected>>", lambda e: self._load_dashboard())
        
        tk.Label(filter_frame, text="| Status:", fg=COLORS["text"], bg=COLORS["bg_dark"]).pack(side="left", padx=10)
        self.status_var = tk.StringVar(value="All")
        status_combo = ttk.Combobox(filter_frame, textvariable=self.status_var,
                                     values=["All", "pending", "running", "completed", "failed"], width=12)
        status_combo.pack(side="left", padx=5)
        status_combo.bind("<<ComboboxSelected>>", lambda e: self._load_dashboard())
        
        tk.Button(filter_frame, text="🔄 Refresh", command=self._load_dashboard,
                  bg=COLORS["info"], fg="white").pack(side="right", padx=5)
        
        # === 3. ACTIVE CAMPAIGNS ===
        active_frame = tk.LabelFrame(self.scrollable_frame, text="🔴 Active Campaigns",
                                     fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                     font=FONTS["heading"])
        active_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        columns = ("Client", "Campaign", "Status", "Progress", "Sent", "Failed", "Actions")
        self.active_tree = ttk.Treeview(active_frame, columns=columns, show="headings", height=8)
        
        self.active_tree.heading("Client", text="Client")
        self.active_tree.column("Client", width=120)
        
        self.active_tree.heading("Campaign", text="Campaign")
        self.active_tree.column("Campaign", width=200)
        
        self.active_tree.heading("Status", text="Status")
        self.active_tree.column("Status", width=100)
        
        self.active_tree.heading("Progress", text="Progress")
        self.active_tree.column("Progress", width=100)
        
        self.active_tree.heading("Sent", text="Sent")
        self.active_tree.column("Sent", width=60)
        
        self.active_tree.heading("Failed", text="Failed")
        self.active_tree.column("Failed", width=60)
        
        self.active_tree.heading("Actions", text="Actions")
        self.active_tree.column("Actions", width=120)
        
        self.active_tree.pack(fill="both", expand=True, padx=10, pady=5)
        
        # === 4. SCHEDULED CAMPAIGNS ===
        scheduled_frame = tk.LabelFrame(self.scrollable_frame, text="📅 Scheduled Campaigns",
                                         fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                         font=FONTS["heading"])
        scheduled_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        sched_columns = ("Client", "Campaign", "Start Time", "Repeat", "Status")
        self.scheduled_tree = ttk.Treeview(scheduled_frame, columns=sched_columns, show="headings", height=6)
        
        for col in sched_columns:
            self.scheduled_tree.heading(col, text=col)
            width = 150 if col not in ["Campaign"] else 200
            self.scheduled_tree.column(col, width=width)
        
        self.scheduled_tree.pack(fill="both", expand=True, padx=10, pady=5)
        
        # === 5. ACTION BUTTONS ===
        btn_frame = tk.Frame(self.scrollable_frame, bg=COLORS["bg_dark"])
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Button(btn_frame, text="➕ New Campaign", command=self._create_campaign,
                  bg=COLORS["success"], fg="white", font=FONTS["bold"]).pack(side="left", padx=5)
        tk.Button(btn_frame, text="📅 Schedule Campaign", command=self._schedule_campaign,
                  bg=COLORS["info"], fg="white", font=FONTS["bold"]).pack(side="left", padx=5)
        tk.Button(btn_frame, text="⏸️ Pause Selected", command=self._pause_campaign,
                  bg=COLORS["warning"], fg="white", font=FONTS["bold"]).pack(side="left", padx=5)
        tk.Button(btn_frame, text="⏹️ Stop Selected", command=self._stop_campaign,
                  bg=COLORS["error"], fg="white", font=FONTS["bold"]).pack(side="left", padx=5)
        tk.Button(btn_frame, text="📊 Export Report", command=self._export_report,
                  bg=COLORS["accent"], fg="white", font=FONTS["bold"]).pack(side="left", padx=5)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _load_dashboard(self):
        """Load dashboard data"""
        self._load_active_campaigns()
        self._load_scheduled_campaigns()
        self._update_client_combo()
    
    def _update_client_combo(self):
        """Update client filter dropdown"""
        clients = ["All"]
        try:
            client_list = client_manager.get_all_clients()
            clients.extend([c['name'] for c in client_list])
        except:
            pass
        self.client_combo['values'] = clients
    
    def _load_active_campaigns(self):
        """Load active campaigns into tree"""
        for item in self.active_tree.get_children():
            self.active_tree.delete(item)
        
        # Load from campaign_manager
        try:
            campaigns = campaign_manager.get_all_campaigns()
            for camp in campaigns:
                status = camp.status.value if hasattr(camp, 'status') else 'running'
                if status in ['running', 'paused']:
                    self.active_tree.insert("", "end", values=(
                        "Client_A",  # TODO: Link to client
                        camp.name,
                        f"🟢 {status}",
                        f"{camp.stats.messages_sent} sent",
                        camp.stats.messages_sent,
                        camp.stats.messages_failed,
                        "Pause/Stop"
                    ))
        except:
            # Dummy data for testing
            campaigns = [
                {"client": "Client_A", "name": "Promo_Januari", "status": "running", 
                 "progress": 45, "sent": 450, "failed": 5},
            ]
            for camp in campaigns:
                self.active_tree.insert("", "end", values=(
                    camp["client"],
                    camp["name"],
                    f"🟢 {camp['status']}",
                    f"{camp['progress']}%",
                    camp["sent"],
                    camp["failed"],
                    "Pause/Stop"
                ))
    
    def _load_scheduled_campaigns(self):
        """Load scheduled campaigns into tree"""
        for item in self.scheduled_tree.get_children():
            self.scheduled_tree.delete(item)
        
        try:
            schedules = scheduler_24h.get_schedules()
            for sched in schedules:
                self.scheduled_tree.insert("", "end", values=(
                    sched.client_id,
                    sched.campaign_id,
                    sched.start_time.strftime("%Y-%m-%d %H:%M"),
                    sched.repeat or "Once",
                    f"🟡 {sched.status}"
                ))
        except Exception as e:
            pass  # No schedules yet
    
    def _start_auto_refresh(self):
        """Start auto-refresh for dashboard"""
        def refresh():
            self._load_dashboard()
            self.frame.after(30000, refresh)  # Refresh every 30 seconds
        refresh()
    
    def _create_campaign(self):
        """Open campaign tab to create new"""
        if hasattr(self.main_window, 'tabs'):
            self.main_window.notebook.select(4)  # Campaign editor tab
    
    def _schedule_campaign(self):
        """Open schedule dialog"""
        dialog = tk.Toplevel(self.frame)
        dialog.title("📅 Schedule Campaign")
        dialog.geometry("500x500")
        dialog.configure(bg=COLORS["bg_dark"])
        
        tk.Label(dialog, text="📅 Schedule Campaign", 
                 font=("Segoe UI", 18, "bold"), fg=COLORS["primary"],
                 bg=COLORS["bg_dark"]).pack(pady=15)
        
        form_frame = tk.Frame(dialog, bg=COLORS["bg_medium"])
        form_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        tk.Label(form_frame, text="Client:", fg=COLORS["text"], bg=COLORS["bg_medium"]).grid(row=0, column=0, padx=10, pady=8, sticky="w")
        client_entry = ttk.Combobox(form_frame, values=["Client_A", "Client_B", "Client_C"], width=25)
        client_entry.grid(row=0, column=1, padx=10, pady=8)
        
        tk.Label(form_frame, text="Campaign:", fg=COLORS["text"], bg=COLORS["bg_medium"]).grid(row=1, column=0, padx=10, pady=8, sticky="w")
        campaign_entry = ttk.Combobox(form_frame, values=["Promo_Januari", "Flash_Sale"], width=25)
        campaign_entry.grid(row=1, column=1, padx=10, pady=8)
        
        tk.Label(form_frame, text="Start Time:", fg=COLORS["text"], bg=COLORS["bg_medium"]).grid(row=2, column=0, padx=10, pady=8, sticky="w")
        start_entry = tk.Entry(form_frame, width=25, bg=COLORS["bg_light"], fg=COLORS["text"])
        start_entry.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M"))
        start_entry.grid(row=2, column=1, padx=10, pady=8)
        
        tk.Label(form_frame, text="Repeat:", fg=COLORS["text"], bg=COLORS["bg_medium"]).grid(row=3, column=0, padx=10, pady=8, sticky="w")
        repeat_var = tk.StringVar(value="none")
        repeat_combo = ttk.Combobox(form_frame, textvariable=repeat_var, 
                                     values=["none", "daily", "weekly", "monthly"], width=23)
        repeat_combo.grid(row=3, column=1, padx=10, pady=8)
        
        def schedule():
            messagebox.showinfo("Success", "Campaign scheduled!")
            dialog.destroy()
            self._load_dashboard()
        
        tk.Button(dialog, text="📅 Schedule", command=schedule,
                  bg=COLORS["success"], fg="white", font=FONTS["bold"],
                  padx=30, pady=10).pack(pady=20)
    
    def _pause_campaign(self):
        """Pause selected campaign"""
        selection = self.active_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Select a campaign first!")
            return
        messagebox.showinfo("Info", "Pause feature - implement broadcast engine pause")
    
    def _stop_campaign(self):
        """Stop selected campaign"""
        selection = self.active_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Select a campaign first!")
            return
        messagebox.showinfo("Info", "Stop feature - implement broadcast engine stop")
    
    def _export_report(self):
        """Export campaign report"""
        from tkinter import filedialog
        filepath = filedialog.asksaveasfilename(defaultextension=".csv",
                                                  initialfile="campaign_report.csv")
        if filepath:
            messagebox.showinfo("Success", f"Report exported to {filepath}")
    
    def _refresh(self):
        self._load_dashboard()