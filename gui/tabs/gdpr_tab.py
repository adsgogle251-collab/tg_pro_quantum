"""GDPR Tab - Complete with Scrollable Content (Phase 8)"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from core import log
from core.gdpr_compliance import gdpr_compliance
from gui.styles import COLORS, FONTS
from core.localization import t

class GDPRTab:
    title = "📋 GDPR"
    
    def __init__(self, parent, main_window=None):
        self.parent = parent
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        self._create_widgets()
        self._update_stats()
    
    def _create_widgets(self):
        # Header
        tk.Label(self.frame, text=f"📋 {t('GDPR Compliance')}", font=("Segoe UI", 24, "bold"),
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
        
        # === 1. COMPLIANCE OVERVIEW ===
        overview_frame = tk.LabelFrame(self.scrollable_frame, text="📊 Compliance Overview",
                                       fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                       font=FONTS["heading"])
        overview_frame.pack(fill="x", padx=10, pady=10)
        
        self.compliance_status = tk.Label(overview_frame, text="Loading...", 
                                           fg=COLORS["text"], bg=COLORS["bg_medium"],
                                           font=("Segoe UI", 16, "bold"))
        self.compliance_status.pack(pady=10)
        
        # === 2. GDPR SETTINGS ===
        settings_frame = tk.LabelFrame(self.scrollable_frame, text="⚙️ GDPR Settings",
                                       fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                       font=FONTS["heading"])
        settings_frame.pack(fill="x", padx=10, pady=10)
        
        self.consent_var = tk.BooleanVar(value=True)
        tk.Checkbutton(settings_frame, text="✅ Require User Consent", variable=self.consent_var,
                      bg=COLORS["bg_medium"], fg=COLORS["text"],
                      selectcolor=COLORS["success"]).pack(anchor="w", padx=20, pady=5)
        
        self.anonymize_var = tk.BooleanVar(value=True)
        tk.Checkbutton(settings_frame, text="🔐 Anonymize Personal Data", variable=self.anonymize_var,
                      bg=COLORS["bg_medium"], fg=COLORS["text"],
                      selectcolor=COLORS["success"]).pack(anchor="w", padx=20, pady=5)
        
        self.retention_var = tk.BooleanVar(value=True)
        tk.Checkbutton(settings_frame, text="🗑️ Auto-Delete Old Data (90 days)", variable=self.retention_var,
                      bg=COLORS["bg_medium"], fg=COLORS["text"],
                      selectcolor=COLORS["success"]).pack(anchor="w", padx=20, pady=5)
        
        tk.Button(settings_frame, text="💾 Save Settings", command=self._save_settings,
                  bg=COLORS["success"], fg="white", font=FONTS["bold"],
                  padx=20, pady=8).pack(pady=10)
        
        # === 3. DATA EXPORT ===
        export_frame = tk.LabelFrame(self.scrollable_frame, text="📤 Data Export (GDPR Right)",
                                     fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                     font=FONTS["heading"])
        export_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(export_frame, text="Export user data in GDPR-compliant format:",
                fg=COLORS["text_muted"], bg=COLORS["bg_medium"]).pack(pady=5)
        
        tk.Button(export_frame, text="📊 Export All Data", command=self._export_data,
                  bg=COLORS["info"], fg="white", font=FONTS["bold"],
                  padx=20, pady=8).pack(pady=10)
        
        # === 4. COMPLIANCE REPORT ===
        report_frame = tk.LabelFrame(self.scrollable_frame, text="📋 Compliance Report",
                                     fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                     font=FONTS["heading"])
        report_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.report_text = scrolledtext.ScrolledText(report_frame, height=15,
                                                      bg=COLORS["bg_light"], fg=COLORS["text"],
                                                      font=("Consolas", 10))
        self.report_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        tk.Button(report_frame, text="🔄 Refresh Report", command=self._update_stats,
                  bg=COLORS["info"], fg="white", font=FONTS["bold"],
                  padx=20, pady=8).pack(pady=5)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _update_stats(self):
        """Update compliance stats and report"""
        try:
            report = gdpr_compliance.get_compliance_report()
            
            status = report.get("status", "unknown")
            if status == "compliant":
                self.compliance_status.config(text="✅ COMPLIANT", fg=COLORS["success"])
            elif status == "warning":
                self.compliance_status.config(text="⚠️ NEEDS ATTENTION", fg=COLORS["warning"])
            else:
                self.compliance_status.config(text="❌ NON-COMPLIANT", fg=COLORS["error"])
            
            self.report_text.delete("1.0", "end")
            self.report_text.insert("1.0", f"""
═══════════════════════════════════════
       GDPR COMPLIANCE REPORT
═══════════════════════════════════════

Status: {report.get('status', 'unknown').upper()}
Score: {report.get('score', 0)}%

───────────────────────────────────────
CHECKLIST:
───────────────────────────────────────
""")
            
            for item in report.get("checklist", []):
                icon = "✅" if item.get("passed") else "❌"
                self.report_text.insert("end", f"{icon} {item.get('name', '')}\n")
            
            self.report_text.see("1.0")
            
        except Exception as e:
            log(f"Failed to load GDPR report: {e}", "error")
            self.compliance_status.config(text="❌ Error Loading Report", fg=COLORS["error"])
    
    def _save_settings(self):
        """Save GDPR settings"""
        settings = {
            "require_consent": self.consent_var.get(),
            "anonymize_data": self.anonymize_var.get(),
            "auto_delete_days": 90 if self.retention_var.get() else 0
        }
        
        gdpr_compliance.update_settings(settings)
        messagebox.showinfo("Success", "GDPR settings saved!")
        self._update_stats()
    
    def _export_data(self):
        """Export user data"""
        from tkinter import filedialog
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filepath:
            try:
                gdpr_compliance.export_user_data(filepath)
                messagebox.showinfo("Success", f"Data exported to {filepath}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export: {e}")
    
    def _refresh(self):
        self._update_stats()