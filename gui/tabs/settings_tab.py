"""Settings Tab - Complete Configuration (Phase 1000)"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from core import log, log_error, config_manager, backup_manager
from core.auto_backup import auto_backup
from gui.styles import COLORS, FONTS
from core.localization import t

class SettingsTab:
    title = "⚙️ Settings"
    
    def __init__(self, parent, main_window=None):
        self.parent = parent
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        self._create_widgets()
        self._load_settings()
    
    def _create_widgets(self):
        # === HEADER ===
        header_frame = tk.Frame(self.frame, bg=COLORS["bg_dark"], height=60)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        tk.Label(header_frame, text=f"⚙️ {t('Settings & Configuration')}", 
                 font=("Segoe UI", 20, "bold"), fg=COLORS["primary"], 
                 bg=COLORS["bg_dark"]).pack(side="left", padx=20, pady=15)
        
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
        
        # === 1. TELEGRAM API SETTINGS ===
        api_frame = tk.LabelFrame(self.scrollable_frame, text="🔑 Telegram API Configuration",
                                   fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                   font=FONTS["heading"])
        api_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(api_frame, text="API ID:", fg=COLORS["text"],
                bg=COLORS["bg_medium"], font=FONTS["bold"]).grid(row=0, column=0, padx=10, pady=8, sticky="w")
        self.api_id_entry = tk.Entry(api_frame, width=40, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.api_id_entry.grid(row=0, column=1, padx=10, pady=8, sticky="w")
        
        tk.Label(api_frame, text="API Hash:", fg=COLORS["text"],
                bg=COLORS["bg_medium"], font=FONTS["bold"]).grid(row=1, column=0, padx=10, pady=8, sticky="w")
        self.api_hash_entry = tk.Entry(api_frame, width=40, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.api_hash_entry.grid(row=1, column=1, padx=10, pady=8, sticky="w")
        
        tk.Label(api_frame, text="📝 Cara mendapatkan API ID & Hash:", 
                fg=COLORS["text_muted"], bg=COLORS["bg_medium"]).grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        tk.Label(api_frame, text="1. Buka https://my.telegram.org", 
                fg=COLORS["info"], bg=COLORS["bg_medium"], cursor="hand2").grid(row=3, column=0, columnspan=2, padx=10, pady=2, sticky="w")
        tk.Label(api_frame, text="2. Login dengan nomor Telegram Anda", 
                fg=COLORS["text_muted"], bg=COLORS["bg_medium"]).grid(row=4, column=0, columnspan=2, padx=10, pady=2, sticky="w")
        tk.Label(api_frame, text="3. Klik 'API development tools'", 
                fg=COLORS["text_muted"], bg=COLORS["bg_medium"]).grid(row=5, column=0, columnspan=2, padx=10, pady=2, sticky="w")
        tk.Label(api_frame, text="4. Buat aplikasi baru (bebas)", 
                fg=COLORS["text_muted"], bg=COLORS["bg_medium"]).grid(row=6, column=0, columnspan=2, padx=10, pady=2, sticky="w")
        tk.Label(api_frame, text="5. Copy API ID dan API Hash ke sini", 
                fg=COLORS["text_muted"], bg=COLORS["bg_medium"]).grid(row=7, column=0, columnspan=2, padx=10, pady=2, sticky="w")
        
        # === 2. BROADCAST SETTINGS ===
        broadcast_frame = tk.LabelFrame(self.scrollable_frame, text="📢 Broadcast Settings",
                                         fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                         font=FONTS["heading"])
        broadcast_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(broadcast_frame, text="Delay Min (seconds):", fg=COLORS["text"],
                bg=COLORS["bg_medium"]).grid(row=0, column=0, padx=10, pady=8, sticky="w")
        self.delay_min = tk.Entry(broadcast_frame, width=15, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.delay_min.grid(row=0, column=1, padx=10, pady=8, sticky="w")
        self.delay_min.insert(0, "10")
        
        tk.Label(broadcast_frame, text="Delay Max (seconds):", fg=COLORS["text"],
                bg=COLORS["bg_medium"]).grid(row=0, column=2, padx=10, pady=8, sticky="w")
        self.delay_max = tk.Entry(broadcast_frame, width=15, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.delay_max.grid(row=0, column=3, padx=10, pady=8, sticky="w")
        self.delay_max.insert(0, "30")
        
        self.round_robin_var = tk.BooleanVar(value=True)
        tk.Checkbutton(broadcast_frame, text="🔄 Round-Robin (Rotate Accounts)", 
                       variable=self.round_robin_var,
                       bg=COLORS["bg_medium"], fg=COLORS["text"],
                       selectcolor=COLORS["success"]).grid(row=1, column=0, columnspan=4, padx=10, pady=5, sticky="w")
        
        self.auto_scrape_var = tk.BooleanVar(value=False)
        tk.Checkbutton(broadcast_frame, text="📥 Auto-Scrape Members", 
                       variable=self.auto_scrape_var,
                       bg=COLORS["bg_medium"], fg=COLORS["text"],
                       selectcolor=COLORS["success"]).grid(row=2, column=0, columnspan=4, padx=10, pady=5, sticky="w")
        
        # === 3. AUTO-BACKUP SETTINGS ===
        backup_frame = tk.LabelFrame(self.scrollable_frame, text="💾 Auto-Backup Settings",
                                      fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                      font=FONTS["heading"])
        backup_frame.pack(fill="x", padx=10, pady=10)
        
        self.auto_backup_var = tk.BooleanVar(value=True)
        tk.Checkbutton(backup_frame, text="✅ Enable Auto-Backup", variable=self.auto_backup_var,
                      bg=COLORS["bg_medium"], fg=COLORS["text"],
                      selectcolor=COLORS["success"]).grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        
        tk.Label(backup_frame, text="Backup Interval (hours):", fg=COLORS["text"],
                bg=COLORS["bg_medium"]).grid(row=1, column=0, padx=10, pady=8, sticky="w")
        self.backup_interval = tk.Entry(backup_frame, width=15, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.backup_interval.grid(row=1, column=1, padx=10, pady=8, sticky="w")
        self.backup_interval.insert(0, "24")
        
        tk.Button(backup_frame, text="📦 Create Backup Now", command=self._create_backup_now,
                  bg=COLORS["success"], fg="white", font=FONTS["bold"]).grid(row=2, column=0, columnspan=2, padx=10, pady=10)
        
        # === 4. NOTIFICATION SETTINGS ===
        notif_frame = tk.LabelFrame(self.scrollable_frame, text="🔔 Notification Settings",
                                     fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                     font=FONTS["heading"])
        notif_frame.pack(fill="x", padx=10, pady=10)
        
        self.email_notif_var = tk.BooleanVar(value=False)
        tk.Checkbutton(notif_frame, text="📧 Email Notifications", variable=self.email_notif_var,
                      bg=COLORS["bg_medium"], fg=COLORS["text"],
                      selectcolor=COLORS["success"]).grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        
        tk.Label(notif_frame, text="Email Address:", fg=COLORS["text"],
                bg=COLORS["bg_medium"]).grid(row=1, column=0, padx=10, pady=8, sticky="w")
        self.email_entry = tk.Entry(notif_frame, width=40, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.email_entry.grid(row=1, column=1, padx=10, pady=8, sticky="w")
        
        # === 5. SAVE BUTTONS ===
        btn_frame = tk.Frame(self.scrollable_frame, bg=COLORS["bg_dark"])
        btn_frame.pack(fill="x", padx=10, pady=20)
        
        tk.Button(btn_frame, text=f"💾 {t('Save All Settings')}", command=self._save_all_settings,
                  bg=COLORS["success"], fg="white", font=("Segoe UI", 14, "bold"),
                  padx=40, pady=15).pack(side="left", padx=10)
        
        tk.Button(btn_frame, text="🔄 Reset to Default", command=self._reset_to_default,
                  bg=COLORS["warning"], fg="white", font=FONTS["bold"],
                  padx=30, pady=15).pack(side="left", padx=10)
        
        # === 6. STATUS INFO ===
        self.status_label = tk.Label(self.scrollable_frame, text="", 
                                      fg=COLORS["text_muted"], bg=COLORS["bg_dark"],
                                      font=FONTS["bold"])
        self.status_label.pack(pady=10)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _load_settings(self):
        """Load settings from config file"""
        try:
            # Load Telegram API
            api_id = config_manager.get("telegram.api_id", 0)
            api_hash = config_manager.get("telegram.api_hash", "")
            
            if api_id:
                self.api_id_entry.delete(0, tk.END)
                self.api_id_entry.insert(0, str(api_id))
            
            if api_hash:
                self.api_hash_entry.delete(0, tk.END)
                self.api_hash_entry.insert(0, api_hash)
            
            # Load Broadcast settings
            delay_min = config_manager.get("broadcast.delay_min", 10)
            delay_max = config_manager.get("broadcast.delay_max", 30)
            round_robin = config_manager.get("broadcast.round_robin", True)
            auto_scrape = config_manager.get("broadcast.auto_scrape", False)
            
            self.delay_min.delete(0, tk.END)
            self.delay_min.insert(0, str(delay_min))
            
            self.delay_max.delete(0, tk.END)
            self.delay_max.insert(0, str(delay_max))
            
            self.round_robin_var.set(round_robin)
            self.auto_scrape_var.set(auto_scrape)
            
            # Load Backup settings
            auto_backup_enabled = config_manager.get("backup.enabled", True)
            backup_interval = config_manager.get("backup.interval_hours", 24)
            
            self.auto_backup_var.set(auto_backup_enabled)
            self.backup_interval.delete(0, tk.END)
            self.backup_interval.insert(0, str(backup_interval))
            
            # Load Notification settings
            email_notif = config_manager.get("notifications.enabled", False)
            email = config_manager.get("notifications.email", "")
            
            self.email_notif_var.set(email_notif)
            self.email_entry.delete(0, tk.END)
            self.email_entry.insert(0, email)
            
            self.status_label.config(text="✅ Settings loaded from data/config.json", fg=COLORS["success"])
            log("Settings loaded", "info")
            
        except Exception as e:
            log_error(f"Failed to load settings: {e}")
            self.status_label.config(text="⚠️ Using default settings", fg=COLORS["warning"])
    
    def _save_all_settings(self):
        """Save all settings to config file"""
        try:
            # Validate API ID
            api_id = self.api_id_entry.get().strip()
            if not api_id or not api_id.isdigit():
                messagebox.showerror("Error", "API ID harus berupa angka!")
                return
            
            # Validate API Hash
            api_hash = self.api_hash_entry.get().strip()
            if not api_hash:
                messagebox.showerror("Error", "API Hash tidak boleh kosong!")
                return
            
            # Save Telegram API
            from core.config_manager import set_value
            set_value("telegram.api_id", int(api_id))
            set_value("telegram.api_hash", api_hash)
            
            # Save Broadcast settings
            set_value("broadcast.delay_min", int(self.delay_min.get()))
            set_value("broadcast.delay_max", int(self.delay_max.get()))
            set_value("broadcast.round_robin", self.round_robin_var.get())
            set_value("broadcast.auto_scrape", self.auto_scrape_var.get())
            
            # Save Backup settings
            set_value("backup.enabled", self.auto_backup_var.get())
            set_value("backup.interval_hours", int(self.backup_interval.get()))
            
            # Save Notification settings
            set_value("notifications.enabled", self.email_notif_var.get())
            set_value("notifications.email", self.email_entry.get().strip())
            
            # Show success message
            messagebox.showinfo("Success", 
                "✅ Settings saved successfully!\n\n"
                "Configuration saved to:\n"
                "data/config.json\n\n"
                "Restart application untuk apply changes.")
            
            self.status_label.config(text="✅ Settings saved to data/config.json", fg=COLORS["success"])
            log("✅ All settings saved successfully", "success")
            
            # Reinitialize engines if API changed
            if hasattr(self, 'main_window') and self.main_window:
                from core.engine import init_engines
                init_engines(int(api_id), api_hash)
                log("Telegram engines reinitialized", "success")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings:\n{e}")
            log_error(f"Failed to save settings: {e}")
            self.status_label.config(text="❌ Failed to save settings", fg=COLORS["error"])
    
    def _create_backup_now(self):
        """Create backup immediately"""
        try:
            result = backup_manager.create_backup()
            if result:
                messagebox.showinfo("Success", f"✅ Backup created:\n{result}")
                log(f"Manual backup created: {result}", "success")
            else:
                messagebox.showerror("Error", "Failed to create backup")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create backup:\n{e}")
            log_error(f"Failed to create backup: {e}")
    
    def _reset_to_default(self):
        """Reset all settings to default"""
        if messagebox.askyesno("Confirm", "Reset all settings to default?"):
            try:
                from core.config_manager import save_config, DEFAULT_CONFIG
                save_config(DEFAULT_CONFIG)
                self._load_settings()
                messagebox.showinfo("Success", "Settings reset to default")
                log("Settings reset to default", "info")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to reset settings:\n{e}")
                log_error(f"Failed to reset settings: {e}")
    
    def _refresh(self):
        """Refresh settings from file"""
        self._load_settings()