"""Log Tab - Complete with System Log & Broadcast History (Phase 8)"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from core import log
from core.broadcast_history import broadcast_history
from gui.styles import COLORS, FONTS
from core.localization import t

class LogTab:
    title = "📝 LOG"
    
    def __init__(self, parent, main_window=None):
        self.parent = parent
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        self._create_widgets()
    
    def _create_widgets(self):
        # Header
        tk.Label(self.frame, text=f"📝 {t('System Logs & Broadcast History')}", 
                 font=("Segoe UI", 24, "bold"), fg=COLORS["primary"], 
                 bg=COLORS["bg_dark"]).pack(pady=15)
        
        # Create notebook for Logs and History
        notebook = ttk.Notebook(self.frame)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # System Logs Tab
        logs_frame = ttk.Frame(notebook)
        notebook.add(logs_frame, text="📋 System Logs")
        self._create_logs_panel(logs_frame)
        
        # Broadcast History Tab
        history_frame = ttk.Frame(notebook)
        notebook.add(history_frame, text="📊 Broadcast History")
        self._create_broadcast_history_tab(history_frame)
    
    def _create_logs_panel(self, parent):
        """Create system logs panel"""
        # Toolbar
        toolbar = tk.Frame(parent, bg=COLORS["bg_dark"])
        toolbar.pack(fill="x", padx=10, pady=5)
        
        tk.Button(toolbar, text="🔄 Refresh", command=self._refresh_logs,
                  bg=COLORS["info"], fg="white").pack(side="left", padx=2)
        tk.Button(toolbar, text="🗑️ Clear", command=self._clear_logs,
                  bg=COLORS["error"], fg="white").pack(side="left", padx=2)
        tk.Button(toolbar, text="💾 Export", command=self._export_logs,
                  bg=COLORS["success"], fg="white").pack(side="left", padx=2)
        
        # Log display
        self.log_text = scrolledtext.ScrolledText(parent, height=30,
                                                   bg=COLORS["bg_light"], 
                                                   fg=COLORS["text"],
                                                   font=("Consolas", 10))
        self.log_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Load logs
        self._refresh_logs()
    
    def _create_broadcast_history_tab(self, parent):
        """Show broadcast history"""
        # Stats
        stats_frame = tk.Frame(parent, bg=COLORS["bg_dark"])
        stats_frame.pack(fill="x", padx=10, pady=10)
        
        stats = broadcast_history.get_stats()
        
        stat_cards = [
            ("📊 Total Broadcasts", str(stats['total_broadcasts']), COLORS["info"]),
            ("✅ Total Sent", str(stats['total_sent']), COLORS["success"]),
            ("❌ Total Failed", str(stats['total_failed']), COLORS["error"]),
            ("📈 Avg Success Rate", f"{stats['avg_success_rate']}%", COLORS["accent"]),
        ]
        
        for i, (label, value, color) in enumerate(stat_cards):
            card = tk.Frame(stats_frame, bg=COLORS["bg_medium"], relief="raised", bd=1)
            card.grid(row=0, column=i, padx=10, sticky="nsew")
            stats_frame.grid_columnconfigure(i, weight=1)
            
            tk.Label(card, text=label, font=FONTS["small"],
                    fg=COLORS["text_muted"], bg=COLORS["bg_medium"]).pack(pady=(10, 3))
            tk.Label(card, text=value, font=("Segoe UI", 18, "bold"),
                    fg=color, bg=COLORS["bg_medium"]).pack(pady=3)
        
        # History table
        hist_frame = tk.LabelFrame(parent, text="📋 Recent Broadcasts",
                                   fg=COLORS["accent"], bg=COLORS["bg_medium"])
        hist_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        columns = ("ID", "Campaign", "Date", "Sent", "Failed", "Rate", "Duration")
        tree = ttk.Treeview(hist_frame, columns=columns, show="headings", height=12)
        
        for col in columns:
            tree.heading(col, text=col)
            width = 100 if col not in ["ID", "Campaign"] else 150
            tree.column(col, width=width)
        
        tree.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Load history
        history = broadcast_history.get_history()
        for record in history:
            tree.insert("", "end", values=(
                record["id"],
                record["campaign"],
                record["timestamp"][:16],
                record["sent"],
                record["failed"],
                f"{record['success_rate']}%",
                f"{record['duration_sec']}s"
            ))
        
        # Toolbar
        btn_frame = tk.Frame(parent, bg=COLORS["bg_dark"])
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Button(btn_frame, text="🔄 Refresh", command=lambda: self._create_broadcast_history_tab(parent),
                  bg=COLORS["info"], fg="white").pack(side="left", padx=5)
        tk.Button(btn_frame, text="📊 Export History", command=self._export_history,
                  bg=COLORS["success"], fg="white").pack(side="left", padx=5)
    
    def add_log(self, msg, level):
        """Add log entry"""
        self.log_text.insert("end", f"{msg}\n")
        self.log_text.see("end")
        
        # Color code
        if "ERROR" in msg or "❌" in msg:
            self.log_text.tag_configure("error", foreground=COLORS["error"])
            self.log_text.tag_add("error", "end-2c", "end-1c")
        elif "SUCCESS" in msg or "✅" in msg:
            self.log_text.tag_configure("success", foreground=COLORS["success"])
            self.log_text.tag_add("success", "end-2c", "end-1c")
        elif "WARNING" in msg or "⚠️" in msg:
            self.log_text.tag_configure("warning", foreground=COLORS["warning"])
            self.log_text.tag_add("warning", "end-2c", "end-1c")
    
    def _refresh_logs(self):
        """Refresh logs from file"""
        self.log_text.delete("1.0", "end")
        
        from pathlib import Path
        log_file = Path("logs/app.log")
        if log_file.exists():
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    self.add_log(line.strip(), "info")
    
    def _clear_logs(self):
        """Clear logs"""
        if messagebox.askyesno("Confirm", "Clear all logs?"):
            self.log_text.delete("1.0", "end")
            from pathlib import Path
            log_file = Path("logs/app.log")
            if log_file.exists():
                log_file.unlink()
    
    def _export_logs(self):
        """Export logs"""
        from pathlib import Path
        from tkinter import filedialog
        
        filepath = filedialog.asksaveasfilename(defaultextension=".txt",
                                                  filetypes=[("Text files", "*.txt")])
        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(self.log_text.get("1.0", "end"))
            messagebox.showinfo("Success", f"Logs exported to {filepath}")
    
    def _export_history(self):
        """Export broadcast history"""
        from tkinter import filedialog
        import csv
        
        filepath = filedialog.asksaveasfilename(defaultextension=".csv",
                                                  filetypes=[("CSV files", "*.csv")])
        if filepath:
            history = broadcast_history.get_history()
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Campaign", "Timestamp", "Sent", "Failed", 
                               "Success Rate", "Duration"])
                for record in history:
                    writer.writerow([
                        record["id"],
                        record["campaign"],
                        record["timestamp"],
                        record["sent"],
                        record["failed"],
                        f"{record['success_rate']}%",
                        f"{record['duration_sec']}s"
                    ])
            messagebox.showinfo("Success", f"History exported to {filepath}")
    
    def _refresh(self):
        self._refresh_logs()