#!/usr/bin/env python3
"""TG PRO QUANTUM - Admin Panel (Complete Phase 2)"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
from pathlib import Path
import sys
import platform
import hashlib
import json
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from license.generator import LicenseGenerator
from core.user_manager import user_manager
from gui.styles import COLORS, FONTS

ADMIN_CONFIG = Path("license/admin_config.json")

class AdminPanel:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🔐 TG PRO QUANTUM - Admin Panel")
        self.root.geometry("1300x800")
        self.root.configure(bg=COLORS["bg_dark"])
        self.generator = LicenseGenerator()
        self.admin_config = self._load_admin_config()
        self._create_widgets()
    
    def _load_admin_config(self):
        if ADMIN_CONFIG.exists():
            with open(ADMIN_CONFIG, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "contact_email": "admin@tgproquantum.com",
            "contact_whatsapp": "+62 812-3456-7890",
            "contact_telegram": "@tgproquantum"
        }
    
    def _save_admin_config(self):
        ADMIN_CONFIG.parent.mkdir(parents=True, exist_ok=True)
        with open(ADMIN_CONFIG, 'w', encoding='utf-8') as f:
            json.dump(self.admin_config, f, indent=2)
    
    def _create_widgets(self):
        # Header
        header = tk.Frame(self.root, bg=COLORS["primary"], height=80)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="🔐 TG PRO QUANTUM - Admin Panel", 
                 font=("Segoe UI", 24, "bold"), fg="white", bg=COLORS["primary"]).pack(pady=20)
        
        # Notebook
        style = ttk.Style()
        style.theme_use('clam')
        
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Dashboard Tab
        dash_frame = ttk.Frame(notebook)
        notebook.add(dash_frame, text="📊 Dashboard")
        self._create_dashboard_tab(dash_frame)
        
        # Generate License Tab
        gen_frame = ttk.Frame(notebook)
        notebook.add(gen_frame, text="➕ Generate License")
        self._create_generate_tab(gen_frame)
        
        # Owner Lifetime Tab
        owner_frame = ttk.Frame(notebook)
        notebook.add(owner_frame, text="👑 Owner License")
        self._create_owner_tab(owner_frame)
        
        # Customers Tab (PHASE 2 - ENHANCED)
        cust_frame = ttk.Frame(notebook)
        notebook.add(cust_frame, text="👥 Customers")
        self._create_customers_tab(cust_frame)
        
        # Licenses Tab
        lic_frame = ttk.Frame(notebook)
        notebook.add(lic_frame, text="🔑 Licenses")
        self._create_licenses_tab(lic_frame)
        
        # Settings Tab
        settings_frame = ttk.Frame(notebook)
        notebook.add(settings_frame, text="⚙️ Settings")
        self._create_settings_tab(settings_frame)
    
    def _create_dashboard_tab(self, parent):
        """Dashboard with statistics"""
        stats_frame = tk.Frame(parent, bg=COLORS["bg_dark"])
        stats_frame.pack(fill="x", padx=20, pady=10)
        
        stats = [
            ("👥 Total Users", len(user_manager.get_all_users()), COLORS["info"]),
            ("🔑 Active Licenses", len(self.generator.get_all_licenses()), COLORS["success"]),
            ("💰 Revenue", "$0", COLORS["warning"]),
            ("⚠️ Expired", "0", COLORS["error"]),
        ]
        
        for i, (label, value, color) in enumerate(stats):
            card = tk.Frame(stats_frame, bg=COLORS["bg_medium"], relief="raised", bd=1)
            card.grid(row=0, column=i, padx=10, sticky="nsew")
            stats_frame.grid_columnconfigure(i, weight=1)
            
            tk.Label(card, text=label, font=FONTS["small"],
                    fg=COLORS["text_muted"], bg=COLORS["bg_medium"]).pack(pady=(15, 5))
            tk.Label(card, text=str(value), font=("Segoe UI", 24, "bold"),
                    fg=color, bg=COLORS["bg_medium"]).pack(pady=5)
        
        # Recent activity
        activity_frame = tk.LabelFrame(parent, text="📋 Recent Activity",
                                       fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                       font=FONTS["heading"])
        activity_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        activity_text = scrolledtext.ScrolledText(activity_frame, height=10,
                                                   bg=COLORS["bg_light"], fg=COLORS["text"])
        activity_text.pack(fill="both", expand=True, padx=10, pady=10)
        activity_text.insert("1.0", "• System initialized\n• Admin panel opened\n")
    
    def _create_generate_tab(self, parent):
        tk.Label(parent, text="Generate Member License", font=("Segoe UI", 18, "bold"),
                 fg=COLORS["primary"], bg=COLORS["bg_dark"]).pack(pady=20)
        
        form_frame = tk.Frame(parent, bg=COLORS["bg_medium"])
        form_frame.pack(pady=20, padx=30, fill="x")
        
        tk.Label(form_frame, text="Customer Email:", fg=COLORS["text"],
                bg=COLORS["bg_medium"]).grid(row=0, column=0, padx=10, pady=8, sticky="w")
        self.gen_email = tk.Entry(form_frame, width=40, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.gen_email.grid(row=0, column=1, padx=10, pady=8)
        
        tk.Label(form_frame, text="Customer Name:", fg=COLORS["text"],
                bg=COLORS["bg_medium"]).grid(row=1, column=0, padx=10, pady=8, sticky="w")
        self.gen_name = tk.Entry(form_frame, width=40, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.gen_name.grid(row=1, column=1, padx=10, pady=8)
        
        tk.Label(form_frame, text="Password:", fg=COLORS["text"],
                bg=COLORS["bg_medium"]).grid(row=2, column=0, padx=10, pady=8, sticky="w")
        self.gen_password = tk.Entry(form_frame, width=40, bg=COLORS["bg_light"], 
                                      fg=COLORS["text"], show="•")
        self.gen_password.grid(row=2, column=1, padx=10, pady=8)
        
        tk.Label(form_frame, text="Duration:", fg=COLORS["text"],
                bg=COLORS["bg_medium"]).grid(row=3, column=0, padx=10, pady=8, sticky="w")
        self.gen_duration = ttk.Combobox(form_frame, 
            values=["30 days", "6 months", "1 year", "Lifetime", "Custom"], width=37)
        self.gen_duration.set("1 year")
        self.gen_duration.grid(row=3, column=1, padx=10, pady=8)
        
        self.custom_days = tk.Entry(form_frame, width=15, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.custom_days.grid(row=3, column=2, padx=5, pady=8)
        self.custom_days.insert(0, "365")
        
        tk.Label(form_frame, text="Tier:", fg=COLORS["text"],
                bg=COLORS["bg_medium"]).grid(row=4, column=0, padx=10, pady=8, sticky="w")
        self.gen_tier = ttk.Combobox(form_frame, values=["basic", "premium", "enterprise"], width=37)
        self.gen_tier.set("premium")
        self.gen_tier.grid(row=4, column=1, padx=10, pady=8)
        
        tk.Button(parent, text="🔑 Generate License", command=self._generate_license,
                  bg=COLORS["success"], fg="white", font=("Segoe UI", 12, "bold"),
                  padx=30, pady=12).pack(pady=20)
        
        # Result
        result_frame = tk.LabelFrame(parent, text="📋 Generated License",
                                     fg=COLORS["accent"], bg=COLORS["bg_medium"])
        result_frame.pack(fill="x", padx=30, pady=10)
        
        self.gen_result = scrolledtext.ScrolledText(result_frame, height=10, width=80,
                                                     bg=COLORS["bg_light"], fg=COLORS["text"])
        self.gen_result.pack(fill="x", padx=10, pady=10)
        
        tk.Button(parent, text="📋 Copy License Key", command=self._copy_generated_license,
                  bg=COLORS["info"], fg="white", font=FONTS["bold"],
                  padx=20, pady=8).pack(pady=5)
        
        self.last_generated_key = ""
    
    def _generate_license(self):
        email = self.gen_email.get().strip()
        name = self.gen_name.get().strip()
        password = self.gen_password.get().strip()
        tier = self.gen_tier.get()
        
        duration = self.gen_duration.get()
        if duration == "Custom":
            days = int(self.custom_days.get() or 365)
        elif duration == "30 days":
            days = 30
        elif duration == "6 months":
            days = 180
        elif duration == "1 year":
            days = 365
        elif duration == "Lifetime":
            days = 36500
            tier = "lifetime"
        else:
            days = 365
        
        if not email or not password:
            messagebox.showerror("Error", "Email and password required!")
            return
        
        user_manager.add_user(email, password, name, "member")
        license_data = self.generator.generate_key(email, days, tier)
        self.last_generated_key = license_data['key']
        
        self.gen_result.delete("1.0", "end")
        result = f"""
═══════════════════════════════════════
       ✅ LICENSE GENERATED
═══════════════════════════════════════

👤 Customer: {name}
📧 Email: {email}
🔑 License: {license_data['key']}
📦 Tier: {license_data['tier']}
⏰ Duration: {days} days
📅 Expires: {license_data['expires'][:10]}
🔒 Device Lock: 1 PC (HWID)

═══════════════════════════════════════
Click "Copy License Key" button below!
═══════════════════════════════════════
        """
        self.gen_result.insert("1.0", result)
        messagebox.showinfo("Success", "License generated!")
    
    def _copy_generated_license(self):
        if self.last_generated_key:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.last_generated_key)
            self.root.update()
            messagebox.showinfo("Copied!", f"License key copied:\n\n{self.last_generated_key}")
        else:
            messagebox.showwarning("Warning", "Generate a license first!")
    
    def _create_owner_tab(self, parent):
        tk.Label(parent, text="👑 Owner Lifetime License", 
                 font=("Segoe UI", 18, "bold"), fg="#FFD700", bg=COLORS["bg_dark"]).pack(pady=20)
        
        tk.Label(parent, text="✨ NEVER expires • 🌍 Any device • 🔓 All features",
                 fg="gray", bg=COLORS["bg_dark"]).pack(pady=5)
        
        form_frame = tk.Frame(parent, bg=COLORS["bg_medium"])
        form_frame.pack(pady=20, padx=30)
        
        tk.Label(form_frame, text="Owner Name:", fg=COLORS["text"],
                bg=COLORS["bg_medium"]).grid(row=0, column=0, padx=10, pady=8)
        self.owner_name = tk.Entry(form_frame, width=40, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.owner_name.insert(0, "Admin")
        self.owner_name.grid(row=0, column=1, padx=10, pady=8)
        
        tk.Label(form_frame, text="Owner Email:", fg=COLORS["text"],
                bg=COLORS["bg_medium"]).grid(row=1, column=0, padx=10, pady=8)
        self.owner_email = tk.Entry(form_frame, width=40, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.owner_email.insert(0, "owner@tgproquantum.com")
        self.owner_email.grid(row=1, column=1, padx=10, pady=8)
        
        tk.Button(parent, text="👑 Generate Owner License", command=self._generate_owner,
                  bg="#FFD700", fg="black", font=("Segoe UI", 12, "bold"),
                  padx=30, pady=12).pack(pady=20)
        
        # Result
        result_frame = tk.LabelFrame(parent, text="📋 Owner License",
                                     fg=COLORS["accent"], bg=COLORS["bg_medium"])
        result_frame.pack(fill="x", padx=30, pady=10)
        
        self.owner_result = scrolledtext.ScrolledText(result_frame, height=10, width=80,
                                                       bg=COLORS["bg_light"], fg=COLORS["text"])
        self.owner_result.pack(fill="x", padx=10, pady=10)
        
        tk.Button(parent, text="📋 Copy Owner License", command=self._copy_owner_license,
                  bg=COLORS["info"], fg="white", font=FONTS["bold"],
                  padx=20, pady=8).pack(pady=5)
        
        self.last_owner_key = ""
    
    def _generate_owner(self):
        name = self.owner_name.get().strip()
        email = self.owner_email.get().strip()
        
        unique_id = str(hashlib.md5(f"{email}{datetime.now()}".encode()).hexdigest())[:8].upper()
        license_key = f"OWNER-{unique_id[:4]}-{unique_id[4:8]}-{unique_id[8:12]}-LIFETIME"
        
        self.last_owner_key = license_key
        
        # Save to database
        from license.generator import LICENSE_DB
        if LICENSE_DB.exists():
            with open(LICENSE_DB, 'r', encoding='utf-8') as f:
                db = json.load(f)
        else:
            db = {"licenses": [], "customers": []}
        
        db["licenses"].append({
            "key": license_key, "email": email, "tier": "owner",
            "created": datetime.now().isoformat(),
            "expires": (datetime.now() + timedelta(days=36500)).isoformat(),
            "status": "active", "activated": True,
            "activated_at": datetime.now().isoformat(), "hwid": None
        })
        with open(LICENSE_DB, 'w', encoding='utf-8') as f:
            json.dump(db, f, indent=2)
        
        self.owner_result.delete("1.0", "end")
        result = f"""
╔═══════════════════════════════════════╗
║    👑 OWNER LIFETIME LICENSE         ║
╠═══════════════════════════════════════╣
║  Name:  {name}
║  Email: {email}
║  Key:   {license_key}
║  ✨ NEVER EXPIRES
║  🌍 ANY DEVICE
║  🔓 ALL FEATURES
╚═══════════════════════════════════════╝
⚠️ KEEP SECRET - DO NOT SHARE!
        """
        self.owner_result.insert("1.0", result)
        messagebox.showinfo("Generated", f"Owner license: {license_key}")
    
    def _copy_owner_license(self):
        if self.last_owner_key:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.last_owner_key)
            self.root.update()
            messagebox.showinfo("Copied!", f"Owner license copied:\n\n{self.last_owner_key}")
        else:
            messagebox.showwarning("Warning", "Generate owner license first!")
    
    def _create_customers_tab(self, parent):
        """PHASE 2: Enhanced customers tab with license management"""
        tk.Label(parent, text="Customer List", font=("Segoe UI", 18, "bold"),
                 fg=COLORS["primary"], bg=COLORS["bg_dark"]).pack(pady=20)
        
        # Table with action buttons
        columns = ("Email", "Name", "Created", "Licenses", "Actions")
        tree = ttk.Treeview(parent, columns=columns, show="headings", height=15)
        for col in columns:
            tree.heading(col, text=col)
            width = 150 if col != "Actions" else 150
            tree.column(col, width=width)
        tree.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Load customers
        customers = user_manager.get_all_users()
        for cust in customers:
            licenses = len([l for l in self.generator.get_all_licenses() if l["email"] == cust["email"]])
            tree.insert("", "end", values=(
                cust["email"],
                cust["name"],
                cust["created"][:10] if cust.get("created") else "N/A",
                licenses,
                "View"
            ))
        
        # Action handler
        def on_tree_double_click(event):
            selection = tree.selection()
            if selection:
                email = tree.item(selection[0])["values"][0]
                self._show_customer_licenses(email)
        
        tree.bind("<Double-1>", on_tree_double_click)
        
        tk.Button(parent, text="🔄 Refresh", command=lambda: self._create_customers_tab(parent),
                  bg=COLORS["info"], fg="white", font=FONTS["bold"],
                  padx=20, pady=8).pack(pady=10)
        
        tk.Label(parent, text="💡 Double-click on a customer to view/manage licenses",
                fg=COLORS["text_muted"], bg=COLORS["bg_dark"]).pack(pady=5)
    
    def _show_customer_licenses(self, email):
        """Show customer licenses in popup with management options"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Licenses for {email}")
        dialog.geometry("700x500")
        dialog.configure(bg=COLORS["bg_dark"])
        
        tk.Label(dialog, text=f"Licenses for {email}", font=("Segoe UI", 16, "bold"),
                 fg=COLORS["primary"], bg=COLORS["bg_dark"]).pack(pady=10)
        
        licenses = [l for l in self.generator.get_all_licenses() if l["email"] == email]
        
        if not licenses:
            tk.Label(dialog, text="No licenses found", fg=COLORS["text_muted"],
                    bg=COLORS["bg_dark"]).pack(pady=20)
            return
        
        # License list
        list_frame = tk.Frame(dialog, bg=COLORS["bg_dark"])
        list_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        for lic in licenses:
            lic_frame = tk.Frame(list_frame, bg=COLORS["bg_medium"], relief="raised", bd=1)
            lic_frame.pack(fill="x", pady=5)
            
            info_frame = tk.Frame(lic_frame, bg=COLORS["bg_medium"])
            info_frame.pack(fill="x", padx=10, pady=10)
            
            tk.Label(info_frame, text=f"Key: {lic['key']}", fg=COLORS["text"],
                    bg=COLORS["bg_medium"], font=("Consolas", 10)).pack(anchor="w", pady=2)
            tk.Label(info_frame, text=f"Tier: {lic['tier']} | Expires: {lic['expires'][:10]} | Status: {lic['status']}",
                    fg=COLORS["text_muted"], bg=COLORS["bg_medium"]).pack(anchor="w", pady=2)
            
            # Action buttons
            btn_frame = tk.Frame(lic_frame, bg=COLORS["bg_medium"])
            btn_frame.pack(anchor="e", padx=10, pady=5)
            
            def extend(lic_key=lic["key"]):
                days = simpledialog.askinteger("Extend", "Days to extend:")
                if days:
                    self.generator.extend_license(lic_key, days)
                    messagebox.showinfo("Success", f"Extended by {days} days!")
                    dialog.destroy()
                    self._show_customer_licenses(email)
            
            def revoke(lic_key=lic["key"]):
                if messagebox.askyesno("Confirm", "Revoke this license?"):
                    self.generator.revoke_license(lic_key)
                    messagebox.showinfo("Success", "License revoked!")
                    dialog.destroy()
                    self._show_customer_licenses(email)
            
            tk.Button(btn_frame, text="⏰ Extend", command=extend,
                      bg=COLORS["warning"], fg="white", font=FONTS["small"],
                      padx=15, pady=5).pack(side="left", padx=5)
            tk.Button(btn_frame, text="❌ Revoke", command=revoke,
                      bg=COLORS["error"], fg="white", font=FONTS["small"],
                      padx=15, pady=5).pack(side="left", padx=5)
    
    def _create_licenses_tab(self, parent):
        tk.Label(parent, text="All Licenses", font=("Segoe UI", 18, "bold"),
                 fg=COLORS["primary"], bg=COLORS["bg_dark"]).pack(pady=20)
        
        columns = ("Key", "Email", "Tier", "Status", "Expires", "Device")
        tree = ttk.Treeview(parent, columns=columns, show="headings", height=15)
        for col in columns:
            tree.heading(col, text=col)
            width = 200 if col != "Key" else 280
            tree.column(col, width=width)
        tree.pack(fill="both", expand=True, padx=20, pady=10)
        
        for lic in self.generator.get_all_licenses():
            tree.insert("", "end", values=(
                lic["key"],
                lic["email"],
                lic["tier"],
                lic["status"],
                lic["expires"][:10],
                "🔓 Any" if not lic.get("hwid") else "🔒 Locked"
            ))
        
        tk.Button(parent, text="🔄 Refresh", command=lambda: self._create_licenses_tab(parent),
                  bg=COLORS["info"], fg="white", font=FONTS["bold"],
                  padx=20, pady=8).pack(pady=10)
    
    def _create_settings_tab(self, parent):
        tk.Label(parent, text="⚙️ Admin Settings", font=("Segoe UI", 18, "bold"),
                 fg=COLORS["primary"], bg=COLORS["bg_dark"]).pack(pady=20)
        
        form_frame = tk.Frame(parent, bg=COLORS["bg_medium"])
        form_frame.pack(pady=20, padx=30, fill="x")
        
        tk.Label(form_frame, text="Contact Email:", fg=COLORS["text"],
                bg=COLORS["bg_medium"]).grid(row=0, column=0, padx=10, pady=8, sticky="w")
        self.contact_email = tk.Entry(form_frame, width=50, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.contact_email.insert(0, self.admin_config.get("contact_email", ""))
        self.contact_email.grid(row=0, column=1, padx=10, pady=8)
        
        tk.Label(form_frame, text="WhatsApp:", fg=COLORS["text"],
                bg=COLORS["bg_medium"]).grid(row=1, column=0, padx=10, pady=8, sticky="w")
        self.contact_whatsapp = tk.Entry(form_frame, width=50, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.contact_whatsapp.insert(0, self.admin_config.get("contact_whatsapp", ""))
        self.contact_whatsapp.grid(row=1, column=1, padx=10, pady=8)
        
        tk.Label(form_frame, text="Telegram:", fg=COLORS["text"],
                bg=COLORS["bg_medium"]).grid(row=2, column=0, padx=10, pady=8, sticky="w")
        self.contact_telegram = tk.Entry(form_frame, width=50, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.contact_telegram.insert(0, self.admin_config.get("contact_telegram", ""))
        self.contact_telegram.grid(row=2, column=1, padx=10, pady=8)
        
        tk.Button(parent, text="💾 Save Settings", command=self._save_settings,
                  bg=COLORS["success"], fg="white", font=("Segoe UI", 12, "bold"),
                  padx=30, pady=12).pack(pady=20)
        
        # Preview
        preview = tk.LabelFrame(parent, text="Preview (Shown to expired users)",
                               bg=COLORS["bg_medium"], fg=COLORS["accent"])
        preview.pack(fill="x", padx=50, pady=20)
        self.preview_text = tk.Text(preview, height=6, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.preview_text.pack(fill="x", padx=10, pady=10)
        self._update_preview()
    
    def _update_preview(self):
        preview = f"""⚠️ License Expired

Contact Admin:
📧 {self.contact_email.get()}
📱 {self.contact_whatsapp.get()}
💬 {self.contact_telegram.get()}

Or enter new license key below."""
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("1.0", preview)
    
    def _save_settings(self):
        self.admin_config["contact_email"] = self.contact_email.get()
        self.admin_config["contact_whatsapp"] = self.contact_whatsapp.get()
        self.admin_config["contact_telegram"] = self.contact_telegram.get()
        self._save_admin_config()
        self._update_preview()
        messagebox.showinfo("Success", "Settings saved!")
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = AdminPanel()
    app.run()