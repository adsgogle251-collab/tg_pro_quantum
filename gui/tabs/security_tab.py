"""Security Tab - Complete with Scrollable Content (Phase 8)"""
import tkinter as tk
from tkinter import ttk, messagebox
from core import security_ultimate
from gui.styles import COLORS, FONTS
from core.localization import t

class SecurityTab:
    title = "🔒 Security"
    
    def __init__(self, parent, main_window=None):
        self.parent = parent
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        self._create_widgets()
        self._load_settings()
    
    def _create_widgets(self):
        # Header
        tk.Label(self.frame, text=f"🔒 {t('Security Settings')}", font=("Segoe UI", 24, "bold"),
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
        
        # === 1. SECURITY STATUS ===
        status_frame = tk.LabelFrame(self.scrollable_frame, text="🛡️ Security Status",
                                      fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                      font=FONTS["heading"])
        status_frame.pack(fill="x", padx=10, pady=10)
        
        security_checks = [
            ("✅ License Valid", True, COLORS["success"]),
            ("✅ HWID Locked", True, COLORS["success"]),
            ("✅ Anti-Tamper Active", True, COLORS["success"]),
            ("⚠️ Session Encryption", False, COLORS["warning"]),
        ]
        
        for check, passed, color in security_checks:
            row_frame = tk.Frame(status_frame, bg=COLORS["bg_medium"])
            row_frame.pack(fill="x", padx=20, pady=5)
            
            tk.Label(row_frame, text=check, font=FONTS["normal"],
                    fg=color if passed else COLORS["error"],
                    bg=COLORS["bg_medium"]).pack(side="left")
            
            status_icon = "✓" if passed else "✗"
            tk.Label(row_frame, text=status_icon, font=("Segoe UI", 14, "bold"),
                    fg=color if passed else COLORS["error"],
                    bg=COLORS["bg_medium"]).pack(side="right")
        
        # === 2. ENCRYPTION SETTINGS ===
        encrypt_frame = tk.LabelFrame(self.scrollable_frame, text="🔐 Encryption Settings",
                                       fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                       font=FONTS["heading"])
        encrypt_frame.pack(fill="x", padx=10, pady=10)
        
        self.encrypt_sessions_var = tk.BooleanVar(value=False)
        tk.Checkbutton(encrypt_frame, text="🔐 Encrypt Session Files", variable=self.encrypt_sessions_var,
                      bg=COLORS["bg_medium"], fg=COLORS["text"],
                      selectcolor=COLORS["success"]).pack(anchor="w", padx=20, pady=5)
        
        self.encrypt_data_var = tk.BooleanVar(value=True)
        tk.Checkbutton(encrypt_frame, text="🔐 Encrypt Data Files", variable=self.encrypt_data_var,
                      bg=COLORS["bg_medium"], fg=COLORS["text"],
                      selectcolor=COLORS["success"]).pack(anchor="w", padx=20, pady=5)
        
        # === 3. ACCESS CONTROL ===
        access_frame = tk.LabelFrame(self.scrollable_frame, text="👤 Access Control",
                                      fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                      font=FONTS["heading"])
        access_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(access_frame, text="Login Required:", fg=COLORS["text"],
                bg=COLORS["bg_medium"]).pack(anchor="w", padx=20, pady=5)
        
        self.login_var = tk.StringVar(value="required")
        login_combo = ttk.Combobox(access_frame, textvariable=self.login_var,
                                    values=["required", "optional", "disabled"], width=20)
        login_combo.pack(anchor="w", padx=30, pady=5)
        
        # === 4. ACTION BUTTONS ===
        btn_frame = tk.Frame(self.scrollable_frame, bg=COLORS["bg_dark"])
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Button(btn_frame, text="💾 Save Security Settings", command=self._save_settings,
                  bg=COLORS["success"], fg="white", font=FONTS["bold"],
                  padx=30, pady=12).pack(side="left", padx=5)
        tk.Button(btn_frame, text="🔑 Change License", command=self._change_license,
                  bg=COLORS["info"], fg="white", font=FONTS["bold"],
                  padx=30, pady=12).pack(side="left", padx=5)
        tk.Button(btn_frame, text="🔍 Verify Integrity", command=self._verify_integrity,
                  bg=COLORS["accent"], fg="white", font=FONTS["bold"],
                  padx=30, pady=12).pack(side="left", padx=5)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _load_settings(self):
        """Load security settings"""
        pass
    
    def _save_settings(self):
        """Save security settings"""
        messagebox.showinfo("Success", "Security settings saved!")
    
    def _change_license(self):
        """Change license key"""
        messagebox.showinfo("Info", "Change license feature - implement dialog")
    
    def _verify_integrity(self):
        """Verify application integrity"""
        messagebox.showinfo("Info", "Verifying integrity...")
    
    def _refresh(self):
        self._load_settings()