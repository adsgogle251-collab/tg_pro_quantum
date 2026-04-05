"""
╔═══════════════════════════════════════════════════════════╗
║     TG PRO QUANTUM v6.0.0 - Clean UI (Sidebar Only)      ║
║           Professional Telegram Broadcast System          ║
╚═══════════════════════════════════════════════════════════╝
"""
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import threading
import asyncio
from datetime import datetime
from core import log, ensure_dirs, config_manager, statistics, health_checker, backup_manager, set_logger, version, scheduler
from core.engine import broadcast_engine, init_engines
from core import notification_manager
from core import auto_backup
from core import scheduler_24h
from core.state_manager import state_manager
from core.localization import t
from gui.styles import COLORS, FONTS, setup_theme

# Import Login System
from gui.tabs.login_tab import LoginDialog, get_current_user, set_current_user

# Import ALL Tabs
from gui.tabs.dashboard_tab import DashboardTab
from gui.tabs.campaign_dashboard_tab import CampaignDashboardTab
from gui.tabs.broadcast_tab import BroadcastTab
from gui.tabs.account_tab import AccountTab
from gui.tabs.campaign_tab import CampaignTab
from gui.tabs.finder_tab import FinderTab
from gui.tabs.scrape_tab import ScrapeTab
from gui.tabs.join_tab import JoinTab
from gui.tabs.ai_cs_tab import AICSTab
from gui.tabs.analytics_tab import AnalyticsTab
from gui.tabs.crm_tab import CRMTab
from gui.tabs.billing_tab import BillingTab
from gui.tabs.security_tab import SecurityTab
from gui.tabs.users_tab import UsersTab
from gui.tabs.whitelabel_tab import WhiteLabelTab
from gui.tabs.gdpr_tab import GDPRTab
from gui.tabs.settings_tab import SettingsTab
from gui.tabs.log_tab import LogTab
from gui.tabs.tools_tab import ToolsTab
from gui.tabs.clients_tab import ClientsTab
from gui.tabs.client_portal_tab import ClientPortalTab
from gui.tabs.help_tab import HelpTab
from gui.tabs.account_groups_tab import AccountGroupsTab


class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title(f"TG PRO QUANTUM v{version}")
        self.root.geometry("1600x900")
        self.root.minsize(1400, 800)
        self.root.configure(bg=COLORS["bg_dark"])
        
        # Setup
        ensure_dirs()
        set_logger(self._add_log_to_gui)
        
        # Initialize Telegram engines
        api_id = config_manager.get("telegram.api_id", 0)
        api_hash = config_manager.get("telegram.api_hash", "")
        
        if api_id and api_hash:
            init_engines(int(api_id), api_hash)
            log("✅ Telegram engines initialized", "success")
        else:
            log("⚠️ API not configured. Set in Settings tab.", "warning")
        
        # Create UI
        self._tab_btn_map = {}
        self._create_sidebar()
        self._create_notebook()
        self._create_statusbar()
        self._start_services()
        
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _add_log_to_gui(self, msg, level):
        if hasattr(self, 'log_tab') and self.log_tab:
            self.log_tab.add_log(msg, level)
    
    # ═══════════════════════════════════════════════════════
    # LEFT SIDEBAR - ONLY MENU (NO TOP MENU)
    # ═══════════════════════════════════════════════════════
    
    def _create_sidebar(self):
        """Create left sidebar with all navigation"""
        sidebar = tk.Frame(self.root, bg="#0f3460", width=220)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        
        # Logo/Header
        header_frame = tk.Frame(sidebar, bg="#1a1a2e", height=100)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        tk.Label(header_frame, text="TG PRO\nQUANTUM", 
                 font=("Segoe UI", 22, "bold"), fg="#00d9ff", 
                 bg="#1a1a2e").pack(pady=20)
        
        tk.Label(header_frame, text=f"v{version}", 
                 font=("Segoe UI", 9), fg="#888888", 
                 bg="#1a1a2e").pack(pady=5)
        
        # Scrollable button area
        btn_container = tk.Frame(sidebar, bg="#0f3460")
        btn_container.pack(fill="both", expand=True)
        
        canvas = tk.Canvas(btn_container, bg="#0f3460", highlightthickness=0)
        scrollbar = ttk.Scrollbar(btn_container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#0f3460")
        
        scrollable_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        
        # All tabs (23 total) - (label, notebook_tab_index)
        buttons = [
            ("📊 Dasbor", 0),
            ("📂 Account Groups", 22),
            ("👥 Klien", 19),
            ("📢 Siaran", 2),
            ("📱 Akun", 3),
            ("📈 Kampanye", 4),
            ("🔍 Pencari", 5),
            ("📥 Ambil Data", 6),
            ("📤 Bergabung", 7),
            ("💬 AI Layanan", 8),
            ("📊 Analitik", 9),
            ("🤝 CRM", 10),
            ("💳 Tagihan", 11),
            ("📈 Kamp. Dashboard", 1),
            ("🔒 Keamanan", 12),
            ("👥 Pengguna", 13),
            ("🎨 Label Putih", 14),
            ("📋 GDPR", 15),
            ("⚙️ Pengaturan", 16),
            ("📝 Log", 17),
            ("🛠️ Alat", 18),
            ("👤 Portal", 20),
            ("❓ Bantuan", 21),
        ]
        
        # Map from notebook tab index → sidebar button widget
        self._tab_btn_map = {}
        self.nav_buttons = []
        for text, tab_index in buttons:
            btn_frame = tk.Frame(scrollable_frame, bg="#0f3460")
            btn_frame.pack(fill="x", pady=1)
            
            btn = tk.Button(btn_frame, text=f"  {text}", 
                            font=("Segoe UI", 11),
                            bg="#0f3460", fg="#888888",
                            activebackground="#00d9ff", 
                            activeforeground="#000000",
                            bd=0, anchor="w", padx=20, pady=12,
                            command=lambda i=tab_index: self._switch_tab(i))
            btn.pack(fill="x")
            self.nav_buttons.append(btn)
            self._tab_btn_map[tab_index] = btn
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Footer with connection status
        status_frame = tk.Frame(sidebar, bg="#1a1a2e", height=50)
        status_frame.pack(side="bottom", fill="x")
        status_frame.pack_propagate(False)
        
        self.connection_indicator = tk.Label(status_frame, text="●", 
                                              fg="#00ff00", bg="#1a1a2e", 
                                              font=("Segoe UI", 12))
        self.connection_indicator.pack(side="left", padx=15, pady=10)
        
        self.connection_label = tk.Label(status_frame, text="Terhubung",
                                          fg="#888888", bg="#1a1a2e",
                                          font=("Segoe UI", 9))
        self.connection_label.pack(side="left")
    
    # ═══════════════════════════════════════════════════════
    # TAB CONTENT AREA
    # ═══════════════════════════════════════════════════════
    
    def _create_notebook(self):
        """Create content area using Frames instead of ttk.Notebook (no visible tabs)"""

        # Create main content frame (replaces Notebook)
        self.content_frame = tk.Frame(self.root, bg=COLORS["bg_dark"])
        self.content_frame.pack(side="right", fill="both", expand=True, padx=0, pady=0)

        self.tabs = {
            "dashboard": DashboardTab(self.content_frame, self),
            "campaign_dashboard": CampaignDashboardTab(self.content_frame, self),
            "broadcast": BroadcastTab(self.content_frame, self),
            "account": AccountTab(self.content_frame, self),
            "campaign": CampaignTab(self.content_frame, self),
            "finder": FinderTab(self.content_frame, self),
            "scrape": ScrapeTab(self.content_frame, self),
            "join": JoinTab(self.content_frame, self),
            "ai_cs": AICSTab(self.content_frame, self),
            "analytics": AnalyticsTab(self.content_frame, self),
            "crm": CRMTab(self.content_frame, self),
            "billing": BillingTab(self.content_frame, self),
            "security": SecurityTab(self.content_frame, self),
            "users": UsersTab(self.content_frame, self),
            "whitelabel": WhiteLabelTab(self.content_frame, self),
            "gdpr": GDPRTab(self.content_frame, self),
            "settings": SettingsTab(self.content_frame, self),
            "log": LogTab(self.content_frame, self),
            "tools": ToolsTab(self.content_frame, self),
            "clients": ClientsTab(self.content_frame, self),
            "client_portal": ClientPortalTab(self.content_frame, self),
            "help": HelpTab(self.content_frame, self),
            "account_groups": AccountGroupsTab(self.content_frame, self),
        }

        self.account_tab = self.tabs["account"]
        self.broadcast_tab = self.tabs["broadcast"]
        self.campaign_tab = self.tabs["campaign"]
        self.log_tab = self.tabs["log"]

        # Pack all tab frames then hide them; show one at a time
        for name, tab in self.tabs.items():
            tab.frame.pack(fill="both", expand=True)
            tab.frame.pack_forget()

        # Show first tab (dashboard) by default
        self.tabs["dashboard"].frame.pack(fill="both", expand=True)
        self.current_tab_index = 0
    
    # ═══════════════════════════════════════════════════════
    # STATUS BAR (BOTTOM)
    # ═══════════════════════════════════════════════════════
    
    def _create_statusbar(self):
        """Create bottom status bar"""
        statusbar = tk.Frame(self.root, bg="#0f3460", height=30)
        statusbar.pack(side="bottom", fill="x")
        
        self.status_label = tk.Label(statusbar, text="Siap", 
                                      bg="#0f3460", fg="#888888", 
                                      anchor="w", padx=15,
                                      font=("Segoe UI", 9))
        self.status_label.pack(side="left", fill="x", expand=True)
        
        self.stats_label = tk.Label(statusbar, text="Siaran: 0 | Berhasil: 0%",
                                     bg="#0f3460", fg="#00d9ff", 
                                     padx=15,
                                     font=("Segoe UI", 9))
        self.stats_label.pack(side="right")
        
        version_label = tk.Label(statusbar, text=f"v{version}", 
                                  bg="#0f3460", fg="#00d9ff", 
                                  padx=15,
                                  font=("Segoe UI", 9))
        version_label.pack(side="right")
        
        self._update_statusbar_stats()
    
    # ═══════════════════════════════════════════════════════
    # TAB SWITCHING
    # ═══════════════════════════════════════════════════════
    
    def _switch_tab(self, index):
        """Switch tab by hiding current frame and showing the selected one"""

        # Hide all tab frames
        for tab in self.tabs.values():
            tab.frame.pack_forget()

        # Show the tab at the requested index
        tab_names = list(self.tabs.keys())
        if index < len(tab_names):
            self.tabs[tab_names[index]].frame.pack(fill="both", expand=True)
            self.current_tab_index = index

        # Update button colors using tab_index → button map
        for tab_idx, btn in self._tab_btn_map.items():
            if tab_idx == index:
                btn.config(bg="#00d9ff", fg="#000000", font=("Segoe UI", 11, "bold"))
            else:
                btn.config(bg="#0f3460", fg="#888888", font=("Segoe UI", 11))

        # Refresh tab data
        try:
            if index == 2 and hasattr(self, 'broadcast_tab'):
                self.broadcast_tab._on_tab_selected()
            elif index == 3 and hasattr(self, 'account_tab'):
                self.account_tab._load_accounts()
            elif index == 4 and hasattr(self, 'campaign_tab'):
                self.campaign_tab._refresh()
            elif index == 5 and "finder" in self.tabs:
                self.tabs["finder"]._on_tab_selected()
            elif index == 6 and "scrape" in self.tabs:
                self.tabs["scrape"]._on_tab_selected()
            elif index == 7 and "join" in self.tabs:
                self.tabs["join"]._on_tab_selected()
            elif index == 8 and "ai_cs" in self.tabs:
                self.tabs["ai_cs"]._on_tab_selected()
            elif index == 17 and hasattr(self, 'log_tab'):
                self.log_tab._refresh()
            elif index == 22 and "account_groups" in self.tabs:
                self.tabs["account_groups"]._on_tab_selected()
        except Exception as e:
            log(f"Error refreshing tab {index}: {e}", "warning")

    def sync_feature_tabs(self):
        """Refresh all feature tabs after account/feature changes."""
        try:
            if "broadcast" in self.tabs:
                self.tabs["broadcast"].refresh_assigned_accounts()
        except Exception:
            pass
        for name in ("finder", "scrape", "join", "ai_cs"):
            try:
                tab = self.tabs.get(name)
                if tab and hasattr(tab, "_on_tab_selected"):
                    tab._on_tab_selected()
            except Exception:
                pass

    # ═══════════════════════════════════════════════════════
    # SERVICES
    # ═══════════════════════════════════════════════════════
    
    def _start_services(self):
        """Start background services"""
        scheduler.start()
        scheduler_24h.start()
        auto_backup.start()
        log("Services started", "success")
        self._update_status()
    
    def _update_status(self):
        """Update connection status"""
        try:
            stats = statistics.get_summary()
            health = health_checker.get_health_summary()
            self.stats_label.config(text=f"📊 {stats['total_broadcasts']} | ✅ {stats['success_rate']}%")
            
            if health["status"] == "healthy":
                self.connection_indicator.config(fg="#00ff00")
            elif health["status"] == "warning":
                self.connection_indicator.config(fg="#ffaa00")
            else:
                self.connection_indicator.config(fg="#ff0000")
        except: 
            pass
        
        self.root.after(5000, self._update_status)
    
    def _update_statusbar_stats(self):
        """Update statusbar statistics"""
        stats = statistics.get_summary()
        self.stats_label.config(text=f"📊 {stats['total_broadcasts']} | ✅ {stats['success_rate']}%")
        self.root.after(10000, self._update_statusbar_stats)
    
    # ═══════════════════════════════════════════════════════
    # CLOSE HANDLER
    # ═══════════════════════════════════════════════════════
    
    def _on_close(self):
        """Handle application close"""
        if messagebox.askyesno("Exit", "Exit TG PRO QUANTUM?"):
            broadcast_engine.stop()
            auto_backup.stop()
            scheduler_24h.stop()
            log("Application closing...", "info")
            self.root.quit()
            self.root.destroy()


def main():
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()