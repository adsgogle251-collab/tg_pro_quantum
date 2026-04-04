"""Clients Tab - Complete with Scrollable Content (Phase 7 - Polish)"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, scrolledtext
from core import log, client_manager, account_manager
from gui.styles import COLORS, FONTS
from core.localization import t

class ClientsTab:
    title = "👥 Clients"
    
    def __init__(self, parent, main_window=None):
        self.parent = parent
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        self._create_widgets()
        self._load_clients()
    
    def _create_widgets(self):
        # Header
        tk.Label(self.frame, text=f"👥 {t('Client Management')}", font=("Segoe UI", 24, "bold"),
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
        
        # === 1. TOOLBAR ===
        toolbar = tk.Frame(self.scrollable_frame, bg=COLORS["bg_dark"])
        toolbar.pack(fill="x", padx=10, pady=10)
        
        tk.Button(toolbar, text="➕ New Client", command=self._create_client,
                  bg=COLORS["success"], fg="white", font=FONTS["bold"]).pack(side="left", padx=5)
        tk.Button(toolbar, text="🔄 Refresh", command=self._load_clients,
                  bg=COLORS["bg_light"], fg=COLORS["text"], font=FONTS["bold"]).pack(side="left", padx=5)
        
        # === 2. SEARCH ===
        search_frame = tk.Frame(self.scrollable_frame, bg=COLORS["bg_dark"])
        search_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(search_frame, text="🔍 Search:", fg=COLORS["text"], bg=COLORS["bg_dark"]).pack(side="left", padx=5)
        self.search_entry = tk.Entry(search_frame, width=40, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<KeyRelease>", lambda e: self._filter_clients())
        
        # === 3. CLIENT LIST ===
        list_frame = tk.LabelFrame(self.scrollable_frame, text="📋 All Clients",
                                   fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                   font=FONTS["heading"])
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        columns = ("ID", "Name", "Email", "Company", "Broadcasts", "Status")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=12)
        
        for col in columns:
            self.tree.heading(col, text=col)
            width = 150 if col not in ["Name", "Email"] else 200
            self.tree.column(col, width=width)
        
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        self.tree.bind("<Double-1>", lambda e: self._view_client_details())
        
        # === 4. STATS ===
        self.stats_label = tk.Label(self.scrollable_frame, text="", fg=COLORS["text_muted"],
                                     bg=COLORS["bg_dark"], font=FONTS["bold"])
        self.stats_label.pack(pady=5)
        
        # === 5. ACTION BUTTONS ===
        action_frame = tk.Frame(self.scrollable_frame, bg=COLORS["bg_dark"])
        action_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Button(action_frame, text="👁️ View Details", command=self._view_client_details,
                  bg=COLORS["info"], fg="white", font=FONTS["bold"]).pack(side="left", padx=5)
        tk.Button(action_frame, text="✏️ Edit", command=self._edit_client,
                  bg=COLORS["warning"], fg="white", font=FONTS["bold"]).pack(side="left", padx=5)
        tk.Button(action_frame, text="🗑️ Delete", command=self._delete_client,
                  bg=COLORS["error"], fg="white", font=FONTS["bold"]).pack(side="left", padx=5)
        tk.Button(action_frame, text="📊 Export Report", command=self._export_client_report,
                  bg=COLORS["success"], fg="white", font=FONTS["bold"]).pack(side="left", padx=5)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _load_clients(self):
        """Load all clients"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        clients = client_manager.get_all_clients()
        for client in clients:
            self.tree.insert("", "end", values=(
                client["id"],
                client["name"],
                client["email"],
                client.get("company", ""),
                client.get("total_broadcasts", 0),
                client.get("status", "active")
            ))
        
        self.stats_label.config(text=f"Total Clients: {len(clients)}")
    
    def _filter_clients(self):
        """Filter clients by search query"""
        query = self.search_entry.get().lower()
        
        for item in self.tree.get_children():
            values = self.tree.item(item)["values"]
            if query in str(values).lower():
                self.tree.reattach(item, "", "end")
            else:
                self.tree.detach(item)
    
    def _create_client(self):
        """Create new client"""
        dialog = tk.Toplevel(self.frame)
        dialog.title("➕ New Client")
        dialog.geometry("500x500")
        dialog.configure(bg=COLORS["bg_dark"])
        
        tk.Label(dialog, text="➕ New Client", font=("Segoe UI", 18, "bold"),
                 fg=COLORS["primary"], bg=COLORS["bg_dark"]).pack(pady=15)
        
        # Scrollable form
        form_canvas = tk.Canvas(dialog, bg=COLORS["bg_dark"], highlightthickness=0)
        form_scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=form_canvas.yview)
        form_frame = tk.Frame(form_canvas, bg=COLORS["bg_medium"])
        
        form_frame.bind("<Configure>", lambda e: form_canvas.configure(scrollregion=form_canvas.bbox("all")))
        form_canvas.create_window((0, 0), window=form_frame, anchor="nw")
        form_canvas.configure(yscrollcommand=form_scrollbar.set)
        
        tk.Label(form_frame, text="Name:", fg=COLORS["text"], bg=COLORS["bg_medium"]).grid(row=0, column=0, padx=10, pady=8, sticky="w")
        name_entry = tk.Entry(form_frame, width=35, bg=COLORS["bg_light"], fg=COLORS["text"])
        name_entry.grid(row=0, column=1, padx=10, pady=8)
        
        tk.Label(form_frame, text="Email:", fg=COLORS["text"], bg=COLORS["bg_medium"]).grid(row=1, column=0, padx=10, pady=8, sticky="w")
        email_entry = tk.Entry(form_frame, width=35, bg=COLORS["bg_light"], fg=COLORS["text"])
        email_entry.grid(row=1, column=1, padx=10, pady=8)
        
        tk.Label(form_frame, text="Company:", fg=COLORS["text"], bg=COLORS["bg_medium"]).grid(row=2, column=0, padx=10, pady=8, sticky="w")
        company_entry = tk.Entry(form_frame, width=35, bg=COLORS["bg_light"], fg=COLORS["text"])
        company_entry.grid(row=2, column=1, padx=10, pady=8)
        
        tk.Label(form_frame, text="Phone:", fg=COLORS["text"], bg=COLORS["bg_medium"]).grid(row=3, column=0, padx=10, pady=8, sticky="w")
        phone_entry = tk.Entry(form_frame, width=35, bg=COLORS["bg_light"], fg=COLORS["text"])
        phone_entry.grid(row=3, column=1, padx=10, pady=8)
        
        tk.Label(form_frame, text="Notes:", fg=COLORS["text"], bg=COLORS["bg_medium"]).grid(row=4, column=0, padx=10, pady=8, sticky="nw")
        notes_text = scrolledtext.ScrolledText(form_frame, height=5, width=35, bg=COLORS["bg_light"], fg=COLORS["text"])
        notes_text.grid(row=4, column=1, padx=10, pady=8)
        
        form_canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        form_scrollbar.pack(side="right", fill="y", pady=10)
        
        def save():
            name = name_entry.get().strip()
            email = email_entry.get().strip()
            company = company_entry.get().strip()
            phone = phone_entry.get().strip()
            notes = notes_text.get("1.0", "end-1c").strip()
            
            if not name or not email:
                messagebox.showerror("Error", "Name and email required!")
                return
            
            client_id = client_manager.create_client(name, email, company, phone, notes)
            messagebox.showinfo("Success", f"Client created: {client_id}")
            self._load_clients()
            dialog.destroy()
        
        tk.Button(dialog, text="💾 Save Client", command=save,
                  bg=COLORS["success"], fg="white", font=FONTS["bold"],
                  padx=30, pady=10).pack(pady=10)
    
    def _view_client_details(self):
        """View client details"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Select a client first!")
            return
        
        client_id = self.tree.item(selection[0])["values"][0]
        client = client_manager.get_client(client_id)
        
        if not client:
            return
        
        dialog = tk.Toplevel(self.frame)
        dialog.title(f"👤 Client: {client['name']}")
        dialog.geometry("650x550")
        dialog.configure(bg=COLORS["bg_dark"])
        
        # Info
        info_frame = tk.LabelFrame(dialog, text="📋 Client Information",
                                   fg=COLORS["accent"], bg=COLORS["bg_medium"])
        info_frame.pack(fill="x", padx=20, pady=10)
        
        info_text = f"""
Name: {client['name']}
Email: {client['email']}
Company: {client.get('company', 'N/A')}
Phone: {client.get('phone', 'N/A')}
Status: {client.get('status', 'active')}
Created: {client['created_at'][:10]}
Total Broadcasts: {client.get('total_broadcasts', 0)}
        """
        tk.Label(info_frame, text=info_text, fg=COLORS["text"],
                bg=COLORS["bg_medium"], justify="left").pack(padx=20, pady=20)
        
        # Stats
        stats = client_manager.get_client_stats(client_id)
        stats_frame = tk.LabelFrame(dialog, text="📊 Broadcast Statistics",
                                    fg=COLORS["accent"], bg=COLORS["bg_medium"])
        stats_frame.pack(fill="x", padx=20, pady=10)
        
        stats_text = f"""
Total Broadcasts: {stats['total_broadcasts']}
Total Sent: {stats['total_sent']}
Total Failed: {stats['total_failed']}
Avg Success Rate: {stats['avg_success_rate']}%
        """
        tk.Label(stats_frame, text=stats_text, fg=COLORS["text"],
                bg=COLORS["bg_medium"]).pack(padx=20, pady=20)
        
        # Account Groups
        groups_frame = tk.LabelFrame(dialog, text="📱 Account Groups",
                                     fg=COLORS["accent"], bg=COLORS["bg_medium"])
        groups_frame.pack(fill="x", padx=20, pady=10)
        
        groups = client.get("account_groups", [])
        if groups:
            tk.Label(groups_frame, text="\n".join(groups), fg=COLORS["text"],
                    bg=COLORS["bg_medium"]).pack(padx=20, pady=20)
        else:
            tk.Label(groups_frame, text="No account groups assigned",
                    fg=COLORS["text_muted"], bg=COLORS["bg_medium"]).pack(padx=20, pady=20)
    
    def _edit_client(self):
        """Edit client"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Select a client first!")
            return
        
        messagebox.showinfo("Info", "Edit client feature - implement similar to create_client")
    
    def _delete_client(self):
        """Delete client"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Select a client first!")
            return
        
        if messagebox.askyesno("Confirm", "Delete this client?"):
            client_id = self.tree.item(selection[0])["values"][0]
            client_manager.delete_client(client_id)
            self._load_clients()
    
    def _export_client_report(self):
        """Export client report"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Select a client first!")
            return
        
        client_id = self.tree.item(selection[0])["values"][0]
        client = client_manager.get_client(client_id)
        
        if not client:
            return
        
        from tkinter import filedialog
        filepath = filedialog.asksaveasfilename(defaultextension=".txt",
                                                  initialfile=f"report_{client['name']}.txt")
        if filepath:
            stats = client_manager.get_client_stats(client_id)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write(f"       CLIENT REPORT - {client['name']}\n")
                f.write("=" * 60 + "\n\n")
                f.write(f"Email: {client['email']}\n")
                f.write(f"Company: {client.get('company', 'N/A')}\n")
                f.write(f"Phone: {client.get('phone', 'N/A')}\n")
                f.write(f"Status: {client.get('status', 'active')}\n\n")
                f.write("-" * 60 + "\n")
                f.write("BROADCAST STATISTICS\n")
                f.write("-" * 60 + "\n")
                f.write(f"Total Broadcasts: {stats['total_broadcasts']}\n")
                f.write(f"Total Sent: {stats['total_sent']}\n")
                f.write(f"Total Failed: {stats['total_failed']}\n")
                f.write(f"Avg Success Rate: {stats['avg_success_rate']}%\n")
            
            messagebox.showinfo("Success", f"Report exported to {filepath}")
    
    def _refresh(self):
        self._load_clients()