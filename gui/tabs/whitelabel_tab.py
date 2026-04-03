"""WhiteLabel Tab - Complete with Scrollable Content (Phase 7 - Polish)"""
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser, filedialog
from core import log, config_manager
from core.whitelabel_manager import whitelabel_manager
from gui.styles import COLORS, FONTS

class WhiteLabelTab:
    title = "🎨 White-Label"
    
    def __init__(self, parent, main_window=None):
        self.parent = parent
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        self._create_widgets()
        self._load_branding()
    
    def _create_widgets(self):
        # Header
        tk.Label(self.frame, text="🎨 White-Label Branding", font=("Segoe UI", 24, "bold"),
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
        
        # === 1. BRANDING SETTINGS ===
        branding_frame = tk.LabelFrame(self.scrollable_frame, text="🏢 Company Branding",
                                       fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                       font=FONTS["heading"])
        branding_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(branding_frame, text="App Name:", fg=COLORS["text"],
                bg=COLORS["bg_medium"]).grid(row=0, column=0, padx=10, pady=8, sticky="w")
        self.app_name = tk.Entry(branding_frame, width=40, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.app_name.grid(row=0, column=1, padx=10, pady=8)
        
        tk.Label(branding_frame, text="Company Name:", fg=COLORS["text"],
                bg=COLORS["bg_medium"]).grid(row=1, column=0, padx=10, pady=8, sticky="w")
        self.company_name = tk.Entry(branding_frame, width=40, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.company_name.grid(row=1, column=1, padx=10, pady=8)
        
        tk.Label(branding_frame, text="Primary Color:", fg=COLORS["text"],
                bg=COLORS["bg_medium"]).grid(row=2, column=0, padx=10, pady=8, sticky="w")
        self.color_btn = tk.Button(branding_frame, text="Choose Color", command=self._choose_color, 
                                   bg=COLORS["primary"], fg="white")
        self.color_btn.grid(row=2, column=1, padx=10, pady=8, sticky="w")
        
        self.color_preview = tk.Label(branding_frame, text="", width=5, bg=COLORS["primary"])
        self.color_preview.grid(row=2, column=2, padx=5, pady=8)
        
        # === 2. LOGO ===
        logo_frame = tk.LabelFrame(self.scrollable_frame, text="🖼️ Logo",
                                   fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                   font=FONTS["heading"])
        logo_frame.pack(fill="x", padx=10, pady=10)
        
        self.logo_label = tk.Label(logo_frame, text="No logo selected", 
                                   fg=COLORS["text_muted"], bg=COLORS["bg_medium"])
        self.logo_label.pack(pady=10)
        
        logo_btn_frame = tk.Frame(logo_frame, bg=COLORS["bg_medium"])
        logo_btn_frame.pack(pady=10)
        
        tk.Button(logo_btn_frame, text="📂 Upload Logo", command=self._upload_logo,
                  bg=COLORS["info"], fg="white").pack(side="left", padx=10)
        tk.Button(logo_btn_frame, text="🗑️ Remove Logo", command=self._remove_logo,
                  bg=COLORS["error"], fg="white").pack(side="left", padx=10)
        
        # === 3. LICENSE GENERATION ===
        license_frame = tk.LabelFrame(self.scrollable_frame, text="🔑 License Generation",
                                      fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                      font=FONTS["heading"])
        license_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(license_frame, text="License Prefix:", fg=COLORS["text"],
                bg=COLORS["bg_medium"]).grid(row=0, column=0, padx=10, pady=8, sticky="w")
        self.license_prefix = tk.Entry(license_frame, width=40, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.license_prefix.insert(0, "TGPRO")
        self.license_prefix.grid(row=0, column=1, padx=10, pady=8)
        
        tk.Button(license_frame, text="🔑 Generate License Key", command=self._generate_license,
                  bg=COLORS["success"], fg="white").grid(row=1, column=0, columnspan=2, padx=10, pady=10)
        
        self.license_result = tk.Label(license_frame, text="", fg=COLORS["text_muted"],
                                        bg=COLORS["bg_medium"], font=("Consolas", 12))
        self.license_result.grid(row=2, column=0, columnspan=2, padx=10, pady=5)
        
        # === 4. SAVE BUTTON ===
        tk.Button(self.scrollable_frame, text="💾 Save Branding Settings", command=self._save_branding,
                  bg=COLORS["success"], fg="white", font=FONTS["bold"],
                  padx=40, pady=15).pack(pady=20)
        
        # === 5. PREVIEW ===
        preview_frame = tk.LabelFrame(self.scrollable_frame, text="👁️ Live Preview",
                                      fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                      font=FONTS["heading"])
        preview_frame.pack(fill="x", padx=10, pady=10)
        
        self.preview_label = tk.Label(preview_frame, text="TG PRO QUANTUM", 
                                       font=("Segoe UI", 20, "bold"),
                                       fg=COLORS["primary"], bg=COLORS["bg_light"])
        self.preview_label.pack(pady=20)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _load_branding(self):
        """Load branding settings"""
        branding = whitelabel_manager.get_branding()
        
        self.app_name.insert(0, branding.get("app_name", "TG PRO QUANTUM"))
        self.company_name.insert(0, branding.get("company_name", "TG PRO"))
        
        color = branding.get("primary_color", COLORS["primary"])
        self.color_btn.config(bg=color)
        self.color_preview.config(bg=color)
        self.preview_label.config(fg=color)
    
    def _choose_color(self):
        """Choose primary color"""
        color = colorchooser.askcolor(title="Choose Primary Color")[1]
        if color:
            self.color_btn.config(bg=color)
            self.color_preview.config(bg=color)
            self.preview_label.config(fg=color)
    
    def _upload_logo(self):
        """Upload company logo"""
        filepath = filedialog.askopenfilename(
            filetypes=[("PNG files", "*.png"), ("JPG files", "*.jpg"), ("All files", "*.*")]
        )
        if filepath:
            self.logo_label.config(text=f"Logo: {filepath.split('/')[-1]}")
            log(f"Logo uploaded: {filepath}", "success")
    
    def _remove_logo(self):
        """Remove logo"""
        self.logo_label.config(text="No logo selected")
        log("Logo removed", "info")
    
    def _generate_license(self):
        """Generate license key"""
        import hashlib
        import uuid
        from datetime import datetime
        
        prefix = self.license_prefix.get().strip() or "TGPRO"
        unique_id = str(uuid.uuid4())[:8].upper()
        hash_input = f"{prefix}{unique_id}{datetime.now().isoformat()}"
        license_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:12].upper()
        
        license_key = f"{prefix}-{license_hash[:4]}-{license_hash[4:8]}-{license_hash[8:12]}"
        
        self.license_result.config(text=license_key, fg=COLORS["success"])
        log(f"License generated: {license_key}", "success")
    
    def _save_branding(self):
        """Save branding settings"""
        branding = {
            "app_name": self.app_name.get().strip(),
            "company_name": self.company_name.get().strip(),
            "primary_color": self.color_btn.cget("bg"),
            "logo": self.logo_label.cget("text")
        }
        
        whitelabel_manager.set_branding(branding)
        
        self.preview_label.config(text=branding["app_name"])
        
        messagebox.showinfo("Success", "Branding settings saved!")
        log("Branding settings saved", "success")
    
    def _refresh(self):
        self._load_branding()