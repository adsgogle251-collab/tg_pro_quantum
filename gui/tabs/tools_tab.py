"""Tools Tab - Complete with Scrollable Content (Phase 7 - Polish)"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog, scrolledtext
from core import log, config_manager, backup_manager, statistics
from core import report_manager
from gui.styles import COLORS, FONTS

class ToolsTab:
    title = "🛠️ Tools"
    
    def __init__(self, parent, main_window=None):
        self.parent = parent
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        self._create_widgets()
    
    def _create_widgets(self):
        # Header
        tk.Label(self.frame, text="🛠️ Tools & Utilities", font=("Segoe UI", 24, "bold"),
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
        
        # === 1. EXPORT REPORTS ===
        export_frame = tk.LabelFrame(self.scrollable_frame, text="📊 Export Reports",
                                      fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                      font=FONTS["heading"])
        export_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(export_frame, text="Export broadcast reports for clients in multiple formats",
                fg=COLORS["text_muted"], bg=COLORS["bg_medium"], wraplength=500).pack(pady=5)
        
        export_btn_frame = tk.Frame(export_frame, bg=COLORS["bg_medium"])
        export_btn_frame.pack(pady=10)
        
        tk.Button(export_btn_frame, text="📊 Export Report", command=self._export_report,
                  bg=COLORS["success"], fg="white", font=FONTS["bold"],
                  padx=30, pady=12).pack(side="left", padx=10)
        
        tk.Button(export_btn_frame, text="📂 View Reports", command=self._view_reports,
                  bg=COLORS["info"], fg="white", font=FONTS["bold"],
                  padx=30, pady=12).pack(side="left", padx=10)
        
        # === 2. BACKUP & RESTORE ===
        backup_frame = tk.LabelFrame(self.scrollable_frame, text="💾 Backup & Restore",
                                      fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                      font=FONTS["heading"])
        backup_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(backup_frame, text="Create and restore backups of your data",
                fg=COLORS["text_muted"], bg=COLORS["bg_medium"], wraplength=500).pack(pady=5)
        
        backup_btn_frame = tk.Frame(backup_frame, bg=COLORS["bg_medium"])
        backup_btn_frame.pack(pady=10)
        
        tk.Button(backup_btn_frame, text="💾 Create Backup", command=self._create_backup,
                  bg=COLORS["success"], fg="white", font=FONTS["bold"],
                  padx=30, pady=12).pack(side="left", padx=10)
        
        tk.Button(backup_btn_frame, text="🔄 Restore Backup", command=self._restore_backup,
                  bg=COLORS["warning"], fg="white", font=FONTS["bold"],
                  padx=30, pady=12).pack(side="left", padx=10)
        
        # === 3. CACHE MANAGEMENT ===
        cache_frame = tk.LabelFrame(self.scrollable_frame, text="🗑️ Cache Management",
                                     fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                     font=FONTS["heading"])
        cache_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(cache_frame, text="Clear cache and temporary files to free up space",
                fg=COLORS["text_muted"], bg=COLORS["bg_medium"], wraplength=500).pack(pady=5)
        
        cache_btn_frame = tk.Frame(cache_frame, bg=COLORS["bg_medium"])
        cache_btn_frame.pack(pady=10)
        
        tk.Button(cache_btn_frame, text="🗑️ Clear Cache", command=self._clear_cache,
                  bg=COLORS["error"], fg="white", font=FONTS["bold"],
                  padx=30, pady=12).pack(side="left", padx=10)
        
        tk.Button(cache_btn_frame, text="🗑️ Clear Logs", command=self._clear_logs,
                  bg=COLORS["error"], fg="white", font=FONTS["bold"],
                  padx=30, pady=12).pack(side="left", padx=10)
        
        # === 4. SYSTEM UTILITIES ===
        system_frame = tk.LabelFrame(self.scrollable_frame, text="🖥️ System Utilities",
                                      fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                      font=FONTS["heading"])
        system_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(system_frame, text="System diagnostics and maintenance tools",
                fg=COLORS["text_muted"], bg=COLORS["bg_medium"], wraplength=500).pack(pady=5)
        
        system_btn_frame = tk.Frame(system_frame, bg=COLORS["bg_medium"])
        system_btn_frame.pack(pady=10)
        
        tk.Button(system_btn_frame, text="📊 System Check", command=self._system_check,
                  bg=COLORS["info"], fg="white", font=FONTS["bold"],
                  padx=30, pady=12).pack(side="left", padx=10)
        
        tk.Button(system_btn_frame, text="📝 View Logs", command=self._view_logs,
                  bg=COLORS["info"], fg="white", font=FONTS["bold"],
                  padx=30, pady=12).pack(side="left", padx=10)
        
        # === 5. RESET OPTIONS ===
        reset_frame = tk.LabelFrame(self.scrollable_frame, text="⚠️ Reset Options",
                                     fg=COLORS["error"], bg=COLORS["bg_medium"],
                                     font=FONTS["heading"])
        reset_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(reset_frame, text="Reset application data (use with caution!)",
                fg=COLORS["text_muted"], bg=COLORS["bg_medium"], wraplength=500).pack(pady=5)
        
        reset_btn_frame = tk.Frame(reset_frame, bg=COLORS["bg_medium"])
        reset_btn_frame.pack(pady=10)
        
        tk.Button(reset_btn_frame, text="🔄 Reset Statistics", command=self._reset_stats,
                  bg=COLORS["warning"], fg="white", font=FONTS["bold"],
                  padx=30, pady=12).pack(side="left", padx=10)
        
        tk.Button(reset_btn_frame, text="⚠️ Reset All Data", command=self._reset_all,
                  bg=COLORS["error"], fg="white", font=FONTS["bold"],
                  padx=30, pady=12).pack(side="left", padx=10)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _export_report(self):
        """Export broadcast report"""
        dialog = tk.Toplevel(self.frame)
        dialog.title("📊 Export Report")
        dialog.geometry("500x400")
        dialog.configure(bg=COLORS["bg_dark"])
        dialog.transient(self.frame)
        
        tk.Label(dialog, text="📊 Export Broadcast Report", 
                 font=("Segoe UI", 18, "bold"), fg=COLORS["primary"],
                 bg=COLORS["bg_dark"]).pack(pady=15)
        
        tk.Label(dialog, text="Campaign Name:", fg=COLORS["text"],
                bg=COLORS["bg_dark"]).pack(pady=5)
        campaign_entry = tk.Entry(dialog, width=50, bg=COLORS["bg_light"], fg=COLORS["text"])
        campaign_entry.pack(pady=5)
        
        tk.Label(dialog, text="Format:", fg=COLORS["text"], bg=COLORS["bg_dark"]).pack(pady=5)
        format_var = tk.StringVar(value="txt")
        format_combo = ttk.Combobox(dialog, textvariable=format_var,
                                     values=["txt", "csv", "json"], width=20)
        format_combo.pack(pady=5)
        
        def export():
            campaign = campaign_entry.get().strip()
            format_type = format_var.get()
            
            if not campaign:
                messagebox.showerror("Error", "Campaign name required!")
                return
            
            stats = statistics.get_summary()
            filepath = report_manager.generate_broadcast_report(
                campaign_name=campaign,
                stats=stats,
                format=format_type
            )
            
            if filepath:
                messagebox.showinfo("Success", f"Report exported to:\n{filepath}")
                dialog.destroy()
        
        tk.Button(dialog, text="📊 Export", command=export,
                  bg=COLORS["success"], fg="white", font=FONTS["bold"],
                  padx=30, pady=10).pack(pady=20)
    
    def _view_reports(self):
        """View all exported reports"""
        dialog = tk.Toplevel(self.frame)
        dialog.title("📂 View Reports")
        dialog.geometry("600x400")
        dialog.configure(bg=COLORS["bg_dark"])
        
        tk.Label(dialog, text="📂 Exported Reports", 
                 font=("Segoe UI", 18, "bold"), fg=COLORS["primary"],
                 bg=COLORS["bg_dark"]).pack(pady=15)
        
        reports_list = tk.Listbox(dialog, bg=COLORS["bg_light"], fg=COLORS["text"], height=15)
        reports_list.pack(fill="both", expand=True, padx=20, pady=10)
        
        reports = report_manager.get_all_reports()
        for report in reports:
            reports_list.insert("end", f"{report['filename']} - {report['created'][:10]}")
        
        def open_report():
            selection = reports_list.curselection()
            if selection:
                report = reports[selection[0]]
                import os
                os.startfile(report['path'])
        
        tk.Button(dialog, text="📂 Open Selected", command=open_report,
                  bg=COLORS["info"], fg="white", font=FONTS["bold"],
                  padx=20, pady=8).pack(pady=10)
    
    def _create_backup(self):
        """Create backup"""
        result = backup_manager.create_backup()
        if result:
            messagebox.showinfo("Success", f"Backup created:\n{result}")
        else:
            messagebox.showerror("Error", "Backup failed")
    
    def _restore_backup(self):
        """Restore backup"""
        backups = backup_manager.list_backups()
        if not backups:
            messagebox.showinfo("Info", "No backups found")
            return
        
        backup_names = [b["name"] for b in backups]
        selected = messagebox.askquestion("Restore", 
            f"Available backups:\n{chr(10).join(backup_names)}\n\nRestore latest backup?")
        
        if selected == "yes":
            backup_manager.restore_backup(backups[0]["name"])
            messagebox.showinfo("Success", "Backup restored. Restart required.")
    
    def _clear_cache(self):
        """Clear cache"""
        from core.cache_manager import cache_manager
        if messagebox.askyesno("Confirm", "Clear all cache?"):
            cache_manager.clear_all()
            messagebox.showinfo("Success", "Cache cleared")
    
    def _clear_logs(self):
        """Clear logs"""
        from pathlib import Path
        logs_dir = Path("logs")
        if logs_dir.exists():
            if messagebox.askyesno("Confirm", "Clear all logs?"):
                for f in logs_dir.glob("*.log"):
                    f.unlink()
                messagebox.showinfo("Success", "Logs cleared")
    
    def _system_check(self):
        """Run system check"""
        from core import health_checker
        health = health_checker.check_system()
        msg = f"System Status: {health['status'].upper()}\n\n"
        msg += f"Uptime: {health['uptime']}\n"
        msg += f"CPU: {health['system']['cpu_percent']}%\n"
        msg += f"Memory: {health['system']['memory_percent']}%\n"
        msg += f"Disk: {health['disk']['used_percent']}%\n"
        msg += f"Sessions: {health['sessions']['total']}"
        if health.get('alerts'):
            msg += f"\n\nAlerts:\n" + "\n".join(health['alerts'])
        messagebox.showinfo("System Check", msg)
    
    def _view_logs(self):
        """View application logs"""
        dialog = tk.Toplevel(self.frame)
        dialog.title("📝 Application Logs")
        dialog.geometry("700x500")
        dialog.configure(bg=COLORS["bg_dark"])
        
        tk.Label(dialog, text="📝 Application Logs", 
                 font=("Segoe UI", 18, "bold"), fg=COLORS["primary"],
                 bg=COLORS["bg_dark"]).pack(pady=15)
        
        log_text = scrolledtext.ScrolledText(dialog, bg=COLORS["bg_light"], 
                                              fg=COLORS["text"], font=("Consolas", 10))
        log_text.pack(fill="both", expand=True, padx=20, pady=10)
        
        from pathlib import Path
        log_file = Path("logs/app.log")
        if log_file.exists():
            with open(log_file, 'r', encoding='utf-8') as f:
                log_text.insert("1.0", f.read())
        
        def refresh():
            log_text.delete("1.0", "end")
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    log_text.insert("1.0", f.read())
        
        tk.Button(dialog, text="🔄 Refresh", command=refresh,
                  bg=COLORS["info"], fg="white", font=FONTS["bold"],
                  padx=20, pady=8).pack(pady=10)
    
    def _reset_stats(self):
        """Reset statistics"""
        if messagebox.askyesno("Confirm", "Reset all statistics?"):
            statistics.reset()
            messagebox.showinfo("Success", "Statistics reset")
    
    def _reset_all(self):
        """Reset all data"""
        if messagebox.askyesno("⚠️ WARNING", 
            "This will delete ALL data including:\n\n"
            "• All accounts\n"
            "• All campaigns\n"
            "• All groups\n"
            "• All statistics\n\n"
            "This CANNOT be undone!\n\n"
            "Continue?"):
            
            if messagebox.askyesno("⚠️ FINAL WARNING", 
                "Are you ABSOLUTELY SURE?\n\n"
                "This will delete EVERYTHING!"):
                
                from pathlib import Path
                import shutil
                
                dirs_to_reset = [
                    Path("data/accounts.json"),
                    Path("data/account_groups.json"),
                    Path("data/campaigns.json"),
                    Path("data/statistics.json"),
                    Path("data/groups"),
                    Path("data/scraped"),
                    Path("sessions")
                ]
                
                for path in dirs_to_reset:
                    if path.exists():
                        if path.is_file():
                            path.unlink()
                        else:
                            shutil.rmtree(path)
                
                messagebox.showinfo("Reset", "All data has been reset. Restart application.")
    
    def _refresh(self):
        pass