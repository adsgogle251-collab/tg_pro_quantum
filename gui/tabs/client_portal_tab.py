"""Client Portal Tab - Enhanced White-Label View (Phase 10 Week 2)"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from core import client_manager, broadcast_history
from gui.styles import COLORS, FONTS

class ClientPortalTab:
    title = "👤 Client Portal"
    
    def __init__(self, parent, main_window=None):
        self.parent = parent
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        self.selected_client = None
        self._create_widgets()
        self._load_clients()
    
    def _create_widgets(self):
        # Header
        tk.Label(self.frame, text="👤 Client Portal - Professional Reports", 
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
        
        # === 1. CLIENT SELECTION ===
        client_frame = tk.LabelFrame(self.scrollable_frame, text="👤 Select Client",
                                      fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                      font=FONTS["heading"])
        client_frame.pack(fill="x", padx=10, pady=10)
        
        self.client_var = tk.StringVar(value="")
        self.client_combo = ttk.Combobox(client_frame, textvariable=self.client_var, width=50)
        self.client_combo.pack(padx=10, pady=10)
        self.client_combo.bind("<<ComboboxSelected>>", lambda e: self._on_client_select())
        
        tk.Button(client_frame, text="👁️ View Portal", command=self._view_client_portal,
                  bg=COLORS["info"], fg="white", font=FONTS["bold"]).pack(pady=5)
        
        # === 2. CLIENT STATS (When Selected) ===
        self.stats_frame = tk.LabelFrame(self.scrollable_frame, text="📊 Client Statistics",
                                          fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                          font=FONTS["heading"])
        
        # === 3. USAGE & LIMITS ===
        self.usage_frame = tk.LabelFrame(self.scrollable_frame, text="📈 Usage & Limits",
                                          fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                          font=FONTS["heading"])
        
        # === 4. CAMPAIGN HISTORY ===
        self.campaign_frame = tk.LabelFrame(self.scrollable_frame, text="📋 Campaign History",
                                             fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                             font=FONTS["heading"])
        
        # === 5. EXPORT BUTTONS ===
        export_frame = tk.Frame(self.scrollable_frame, bg=COLORS["bg_dark"])
        export_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Button(export_frame, text="📊 Export PDF Report", command=self._export_pdf_report,
                  bg=COLORS["success"], fg="white", font=FONTS["bold"]).pack(side="left", padx=5)
        tk.Button(export_frame, text="📄 Export CSV", command=self._export_csv,
                  bg=COLORS["info"], fg="white", font=FONTS["bold"]).pack(side="left", padx=5)
        tk.Button(export_frame, text="📋 Copy Summary", command=self._copy_summary,
                  bg=COLORS["accent"], fg="white", font=FONTS["bold"]).pack(side="left", padx=5)
        tk.Button(export_frame, text="📧 Send to Client", command=self._send_to_client,
                  bg=COLORS["primary"], fg="white", font=FONTS["bold"]).pack(side="left", padx=5)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _load_clients(self):
        """Load client list"""
        clients = client_manager.get_all_clients()
        client_list = [f"{c['name']} ({c['email']}) - {c.get('tier', 'basic').upper()}" for c in clients]
        self.client_combo['values'] = [""] + client_list
    
    def _on_client_select(self):
        """When client is selected"""
        selection = self.client_var.get()
        if not selection:
            self.selected_client = None
            self._clear_client_view()
            return
        
        # Find client by email
        email = selection.split("(")[1].split(")")[0]
        client = client_manager.get_client_by_email(email)
        
        if client:
            self.selected_client = client
            self._load_client_stats()
            self._load_usage_limits()
            self._load_client_campaigns()
    
    def _clear_client_view(self):
        """Clear client view"""
        for widget in [self.stats_frame, self.usage_frame, self.campaign_frame]:
            for w in widget.winfo_children():
                w.destroy()
    
    def _load_client_stats(self):
        """Load client statistics"""
        # Clear previous
        for widget in self.stats_frame.winfo_children():
            widget.destroy()
        self.stats_frame.pack(fill="x", padx=10, pady=10)
        
        stats = client_manager.get_client_stats(self.selected_client["id"])
        
        stat_cards = [
            ("📊 Total Broadcasts", str(stats.get('total_broadcasts', 0)), COLORS["info"]),
            ("✅ Total Sent", str(stats.get('total_sent', 0)), COLORS["success"]),
            ("❌ Total Failed", str(stats.get('total_failed', 0)), COLORS["error"]),
            ("📈 Success Rate", f"{stats.get('avg_success_rate', 0)}%", COLORS["accent"]),
        ]
        
        for i, (label, value, color) in enumerate(stat_cards):
            card = tk.Frame(self.stats_frame, bg=COLORS["bg_light"], relief="raised", bd=1)
            card.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")
            self.stats_frame.grid_columnconfigure(i, weight=1)
            
            tk.Label(card, text=label, font=FONTS["small"],
                    fg=COLORS["text_muted"], bg=COLORS["bg_light"]).pack(pady=(10, 5))
            tk.Label(card, text=value, font=("Segoe UI", 18, "bold"),
                    fg=color, bg=COLORS["bg_light"]).pack(pady=5)
    
    def _load_usage_limits(self):
        """Load usage and limits"""
        # Clear previous
        for widget in self.usage_frame.winfo_children():
            widget.destroy()
        
        limits_check = client_manager.check_limits(self.selected_client["id"])
        
        tk.Label(self.usage_frame, text="Current Usage vs Limits:",
                fg=COLORS["text"], bg=COLORS["bg_medium"], font=FONTS["bold"]).pack(pady=10)
        
        usage = limits_check.get("usage", {})
        checks = limits_check.get("checks", {})
        
        for metric, value in usage.items():
            status = "✅" if checks.get(metric, False) else "⚠️"
            color = COLORS["success"] if checks.get(metric, False) else COLORS["warning"]
            
            tk.Label(self.usage_frame, text=f"{status} {metric.title()}: {value}",
                    fg=color, bg=COLORS["bg_medium"]).pack(anchor="w", padx=20, pady=3)
        
        self.usage_frame.pack(fill="x", padx=10, pady=10)
    
    def _load_client_campaigns(self):
        """Load client campaign history"""
        # Clear previous
        for widget in self.campaign_frame.winfo_children():
            widget.destroy()
        
        columns = ("Campaign", "Date", "Sent", "Failed", "Rate", "Status")
        tree = ttk.Treeview(self.campaign_frame, columns=columns, show="headings", height=8)
        
        for col in columns:
            tree.heading(col, text=col)
            width = 100 if col not in ["Campaign"] else 200
            tree.column(col, width=width)
        
        tree.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Load from broadcast history (filter by client)
        history = broadcast_history.get_history()
        for record in history:
            # TODO: Filter by client_id when history supports it
            tree.insert("", "end", values=(
                record["campaign"],
                record["timestamp"][:16],
                record["sent"],
                record["failed"],
                f"{record['success_rate']}%",
                "Completed"
            ))
        
        self.campaign_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    def _view_client_portal(self):
        """Open dedicated client portal view (white-label)"""
        if not self.selected_client:
            messagebox.showwarning("Warning", "Select a client first!")
            return
        
        # Create new window with client branding
        portal = tk.Toplevel(self.frame)
        portal.title(f"Client Portal - {self.selected_client['name']}")
        portal.geometry("800x600")
        portal.configure(bg=COLORS["bg_dark"])
        
        # Header with client branding
        tk.Label(portal, text=f"📊 {self.selected_client['name']}", 
                 font=("Segoe UI", 20, "bold"), fg=COLORS["primary"],
                 bg=COLORS["bg_dark"]).pack(pady=20)
        
        tk.Label(portal, text=f"Tier: {self.selected_client['tier'].upper()}",
                font=FONTS["normal"], fg=COLORS["text_muted"],
                bg=COLORS["bg_dark"]).pack(pady=5)
        
        # Stats
        stats = client_manager.get_client_stats(self.selected_client["id"])
        
        stats_frame = tk.Frame(portal, bg=COLORS["bg_medium"])
        stats_frame.pack(fill="x", padx=20, pady=20)
        
        tk.Label(stats_frame, text=f"Total Broadcasts: {stats['total_broadcasts']}",
                font=FONTS["heading"], fg=COLORS["text"], bg=COLORS["bg_medium"]).pack(pady=5)
        tk.Label(stats_frame, text=f"Success Rate: {stats['avg_success_rate']}%",
                font=FONTS["heading"], fg=COLORS["success"], bg=COLORS["bg_medium"]).pack(pady=5)
        tk.Label(stats_frame, text=f"Messages Today: {stats['messages_today']}",
                font=FONTS["heading"], fg=COLORS["text"], bg=COLORS["bg_medium"]).pack(pady=5)
        
        tk.Button(portal, text="📊 Export Report", command=lambda: self._export_pdf_report(),
                  bg=COLORS["success"], fg="white", font=FONTS["bold"],
                  padx=30, pady=10).pack(pady=20)
    
    def _export_pdf_report(self):
        """Export professional PDF report for client"""
        if not self.selected_client:
            messagebox.showwarning("Warning", "Select a client first!")
            return
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            initialfile=f"Report_{self.selected_client['name']}_{datetime.now().strftime('%Y%m%d')}.pdf"
        )
        
        if filepath:
            # TODO: Implement PDF generation with reportlab
            # For now, create a text report
            stats = client_manager.get_client_stats(self.selected_client["id"])
            
            report = f"""
═══════════════════════════════════════
       BROADCAST REPORT - {self.selected_client['name']}
═══════════════════════════════════════

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Tier: {self.selected_client['tier'].upper()}

───────────────────────────────────────
STATISTICS
───────────────────────────────────────
Total Broadcasts: {stats['total_broadcasts']}
Total Sent: {stats['total_sent']}
Total Failed: {stats['total_failed']}
Success Rate: {stats['avg_success_rate']}%
Messages Today: {stats['messages_today']}

───────────────────────────────────────
LIMITS
───────────────────────────────────────
{client_manager.check_limits(self.selected_client['id'])}

═══════════════════════════════════════
Thank you for using TG PRO QUANTUM!
═══════════════════════════════════════
            """
            
            # Save as TXT for now (PDF requires reportlab)
            txt_path = filepath.replace(".pdf", ".txt")
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(report)
            
            messagebox.showinfo("Success", f"Report exported to {txt_path}\n\n(PDF export requires reportlab library)")
    
    def _export_csv(self):
        """Export CSV report"""
        if not self.selected_client:
            messagebox.showwarning("Warning", "Select a client first!")
            return
        
        import csv
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=f"Report_{self.selected_client['name']}.csv"
        )
        
        if filepath:
            history = broadcast_history.get_history()
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Campaign", "Date", "Sent", "Failed", "Success Rate", "Duration"])
                for record in history:
                    writer.writerow([
                        record["campaign"],
                        record["timestamp"],
                        record["sent"],
                        record["failed"],
                        f"{record['success_rate']}%",
                        f"{record['duration_sec']}s"
                    ])
            messagebox.showinfo("Success", f"CSV exported to {filepath}")
    
    def _copy_summary(self):
        """Copy summary for WhatsApp/Telegram"""
        if not self.selected_client:
            messagebox.showwarning("Warning", "Select a client first!")
            return
        
        stats = client_manager.get_client_stats(self.selected_client["id"])
        
        summary = f"""
📊 LAPORAN BROADCAST - {self.selected_client['name']}
═══════════════════════════════════════

Total Broadcast: {stats['total_broadcasts']} kali
Total Terkirim: {stats['total_sent']} message
Total Gagal: {stats['total_failed']} message
Success Rate: {stats['avg_success_rate']}%
Messages Hari Ini: {stats['messages_today']}

═══════════════════════════════════════
Terima kasih telah menggunakan jasa kami!
        """
        
        self.frame.clipboard_clear()
        self.frame.clipboard_append(summary)
        self.frame.update()
        messagebox.showinfo("Copied!", "Summary copied to clipboard!\n\nPaste ke WhatsApp/Telegram client")
    
    def _send_to_client(self):
        """Send report to client via email/Telegram"""
        if not self.selected_client:
            messagebox.showwarning("Warning", "Select a client first!")
            return
        
        # TODO: Implement email/Telegram sending
        messagebox.showinfo("Info", 
            f"Send report to: {self.selected_client['email']}\n\n"
            f"Email/Telegram integration requires configuration in Settings.")
    
    def _refresh(self):
        self._load_clients()