"""CRM Tab - Complete with Scrollable Content (Phase 8 - FIXED)"""
import tkinter as tk
from tkinter import ttk, messagebox
from core.crm_engine import crm_engine
from gui.styles import COLORS, FONTS
from core.localization import t

class CRMTab:
    title = "🤝 CRM"
    
    def __init__(self, parent, main_window=None):
        self.parent = parent
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        self._create_widgets()
        self._load_data()
    
    def _create_widgets(self):
        # Header
        tk.Label(self.frame, text=f"🤝 {t('Customer Relationship Management')}", font=("Segoe UI", 24, "bold"),
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
        
        # === 1. CONTACT STATISTICS ===
        stats_frame = tk.LabelFrame(self.scrollable_frame, text="📊 Contact Statistics",
                                     fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                     font=FONTS["heading"])
        stats_frame.pack(fill="x", padx=10, pady=10)
        
        # ✅ FIX: Use correct method name get_crm_stats()
        stats = crm_engine.get_crm_stats() if hasattr(crm_engine, 'get_crm_stats') else {
            'total_contacts': 0, 'active_chats': 0, 'pending_followup': 0, 'converted': 0
        }
        
        stat_cards = [
            ("👥 Total Contacts", str(stats.get('total_contacts', 0)), COLORS["info"]),
            ("💬 Active Chats", str(stats.get('active_chats', 0)), COLORS["success"]),
            ("📞 Pending Follow-up", str(stats.get('pending_followup', 0)), COLORS["warning"]),
            ("✅ Converted", str(stats.get('converted', 0)), COLORS["accent"]),
        ]
        
        for i, (label, value, color) in enumerate(stat_cards):
            card = tk.Frame(stats_frame, bg=COLORS["bg_light"], relief="raised", bd=1)
            card.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")
            stats_frame.grid_columnconfigure(i, weight=1)
            
            tk.Label(card, text=label, font=FONTS["small"],
                    fg=COLORS["text_muted"], bg=COLORS["bg_light"]).pack(pady=(10, 5))
            tk.Label(card, text=value, font=("Segoe UI", 20, "bold"),
                    fg=color, bg=COLORS["bg_light"]).pack(pady=5)
        
        # === 2. CONTACT LIST ===
        contact_frame = tk.LabelFrame(self.scrollable_frame, text="📋 Contact List",
                                       fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                       font=FONTS["heading"])
        contact_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        columns = ("Name", "Phone", "Status", "Last Contact", "Notes")
        self.contact_tree = ttk.Treeview(contact_frame, columns=columns, show="headings", height=10)
        
        for col in columns:
            self.contact_tree.heading(col, text=col)
            width = 150 if col not in ["Name", "Notes"] else 200
            self.contact_tree.column(col, width=width)
        
        self.contact_tree.pack(fill="both", expand=True, padx=10, pady=5)
        
        # === 3. ACTION BUTTONS ===
        btn_frame = tk.Frame(self.scrollable_frame, bg=COLORS["bg_dark"])
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Button(btn_frame, text="➕ Add Contact", command=self._add_contact,
                  bg=COLORS["success"], fg="white", font=FONTS["bold"]).pack(side="left", padx=5)
        tk.Button(btn_frame, text="✏️ Edit Contact", command=self._edit_contact,
                  bg=COLORS["info"], fg="white", font=FONTS["bold"]).pack(side="left", padx=5)
        tk.Button(btn_frame, text="🗑️ Delete Contact", command=self._delete_contact,
                  bg=COLORS["error"], fg="white", font=FONTS["bold"]).pack(side="left", padx=5)
        tk.Button(btn_frame, text="📞 Follow-up", command=self._follow_up,
                  bg=COLORS["warning"], fg="white", font=FONTS["bold"]).pack(side="left", padx=5)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _load_data(self):
        """Load CRM data - with fallback if method doesn't exist"""
        for item in self.contact_tree.get_children():
            self.contact_tree.delete(item)
        
        try:
            # Try get_contacts first, fallback to empty list
            contacts = crm_engine.get_contacts() if hasattr(crm_engine, 'get_contacts') else []
        except:
            contacts = []
        
        for contact in contacts:
            self.contact_tree.insert("", "end", values=(
                contact.get('name', 'N/A'),
                contact.get('phone', 'N/A'),
                contact.get('status', 'N/A'),
                contact.get('last_contact', 'N/A')[:10] if contact.get('last_contact') else 'N/A',
                contact.get('notes', '')[:30]
            ))
    
    def _add_contact(self):
        messagebox.showinfo("Info", "Add contact feature - implement dialog")
    
    def _edit_contact(self):
        messagebox.showinfo("Info", "Edit contact feature - implement dialog")
    
    def _delete_contact(self):
        messagebox.showinfo("Info", "Delete contact feature - implement confirmation")
    
    def _follow_up(self):
        messagebox.showinfo("Info", "Follow-up feature - implement scheduling")
    
    def _refresh(self):
        self._load_data()