"""Help Tab - Complete with Scrollable Content (Phase 7 - Polish)"""
import tkinter as tk
from tkinter import ttk, messagebox
from core import help_manager
from gui.styles import COLORS, FONTS

class HelpTab:
    title = "❓ Help"
    
    def __init__(self, parent, main_window=None):
        self.parent = parent
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        self._create_widgets()
    
    def _create_widgets(self):
        # Header
        tk.Label(self.frame, text="❓ Help & Documentation", 
                 font=("Segoe UI", 24, "bold"), fg=COLORS["primary"], 
                 bg=COLORS["bg_dark"]).pack(pady=15)
        
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
        
        # === 1. QUICK START GUIDE ===
        quick_frame = tk.LabelFrame(self.scrollable_frame, text="🚀 Quick Start Guide",
                                    fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                    font=FONTS["heading"])
        quick_frame.pack(fill="x", padx=10, pady=10)
        
        steps = [
            ("1️⃣ Settings", "Configure Telegram API in Settings tab"),
            ("2️⃣ Accounts", "Add/Import your Telegram accounts"),
            ("3️⃣ Groups", "Create account groups for different clients"),
            ("4️⃣ Finder", "Search for target groups by keywords"),
            ("5️⃣ Join", "Join the groups you found"),
            ("6️⃣ Campaign", "Create your broadcast campaign"),
            ("7️⃣ Broadcast", "Start your campaign and monitor progress"),
        ]
        
        for i, (title, desc) in enumerate(steps):
            step_frame = tk.Frame(quick_frame, bg=COLORS["bg_light"])
            step_frame.pack(fill="x", padx=15, pady=3)
            
            tk.Label(step_frame, text=title, font=FONTS["bold"],
                    fg=COLORS["primary"], bg=COLORS["bg_light"]).pack(anchor="w", padx=10, pady=5)
            tk.Label(step_frame, text=desc, font=FONTS["normal"],
                    fg=COLORS["text_muted"], bg=COLORS["bg_light"]).pack(anchor="w", padx=10, pady=(0, 5))
        
        # === 2. TAB GUIDE ===
        guide_frame = tk.LabelFrame(self.scrollable_frame, text="📋 Tab Guide",
                                    fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                    font=FONTS["heading"])
        guide_frame.pack(fill="x", padx=10, pady=10)
        
        tabs = help_manager.help_data.get("tabs", {})
        
        for i, (tab_name, tab_help) in enumerate(tabs.items()):
            card = tk.Frame(guide_frame, bg=COLORS["bg_light"], relief="raised", bd=1)
            card.pack(fill="x", padx=15, pady=5)
            
            tk.Label(card, text=tab_help.get("title", tab_name), 
                    font=("Segoe UI", 13, "bold"), fg=COLORS["accent"],
                    bg=COLORS["bg_light"]).pack(padx=15, pady=(10, 5))
            
            tk.Label(card, text=tab_help.get("description", ""), 
                    font=FONTS["normal"], fg=COLORS["text_muted"],
                    bg=COLORS["bg_light"], wraplength=500, justify="left").pack(padx=15, pady=(0, 10))
            
            steps_list = tab_help.get("steps", [])
            if steps_list:
                steps_frame = tk.Frame(card, bg=COLORS["bg_medium"])
                steps_frame.pack(fill="x", padx=15, pady=10)
                
                tk.Label(steps_frame, text="Key Features:", font=FONTS["bold"],
                        fg=COLORS["text"], bg=COLORS["bg_medium"]).pack(anchor="w")
                
                for step in steps_list:
                    tk.Label(steps_frame, text=f"• {step}", font=FONTS["normal"],
                            fg=COLORS["text"], bg=COLORS["bg_medium"],
                            justify="left").pack(anchor="w", padx=10, pady=2)
        
        # === 3. FAQ ===
        faq_frame = tk.LabelFrame(self.scrollable_frame, text="❓ Frequently Asked Questions",
                                  fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                  font=FONTS["heading"])
        faq_frame.pack(fill="x", padx=10, pady=10)
        
        faqs = help_manager.get_faq()
        
        for i, faq in enumerate(faqs):
            card = tk.Frame(faq_frame, bg=COLORS["bg_light"], relief="raised", bd=1)
            card.pack(fill="x", padx=15, pady=5)
            
            tk.Label(card, text=f"Q: {faq.get('question', '')}", 
                    font=("Segoe UI", 12, "bold"), fg=COLORS["primary"],
                    bg=COLORS["bg_light"], wraplength=500, justify="left").pack(padx=15, pady=(10, 5))
            
            tk.Label(card, text=f"A: {faq.get('answer', '')}", 
                    font=FONTS["normal"], fg=COLORS["text"],
                    bg=COLORS["bg_light"], wraplength=500, justify="left").pack(padx=15, pady=(0, 10))
        
        # === 4. KEYBOARD SHORTCUTS ===
        shortcuts_frame = tk.LabelFrame(self.scrollable_frame, text="⌨️ Keyboard Shortcuts",
                                        fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                        font=FONTS["heading"])
        shortcuts_frame.pack(fill="x", padx=10, pady=10)
        
        shortcuts = help_manager.get_shortcuts()
        
        for shortcut in shortcuts:
            card = tk.Frame(shortcuts_frame, bg=COLORS["bg_light"], relief="raised", bd=1)
            card.pack(fill="x", padx=15, pady=3)
            
            tk.Label(card, text=shortcut.get("key", ""), 
                    font=("Consolas", 13, "bold"), fg=COLORS["accent"],
                    bg=COLORS["bg_light"], width=15).pack(side="left", padx=15, pady=8)
            
            tk.Label(card, text=shortcut.get("action", ""), 
                    font=FONTS["normal"], fg=COLORS["text"],
                    bg=COLORS["bg_light"]).pack(side="left", padx=15, pady=8)
        
        # === 5. SEARCH HELP ===
        search_frame = tk.LabelFrame(self.scrollable_frame, text="🔍 Search Help",
                                     fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                     font=FONTS["heading"])
        search_frame.pack(fill="x", padx=10, pady=10)
        
        search_entry_frame = tk.Frame(search_frame, bg=COLORS["bg_medium"])
        search_entry_frame.pack(fill="x", padx=15, pady=10)
        
        self.search_entry = tk.Entry(search_entry_frame, width=50, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.search_entry.pack(side="left", padx=5)
        
        tk.Button(search_entry_frame, text="🔍 Search", command=self._do_search,
                  bg=COLORS["info"], fg="white").pack(side="left", padx=5)
        
        # Results
        self.results_text = tk.Text(search_frame, height=10, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.results_text.pack(fill="x", padx=15, pady=10)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _do_search(self):
        """Perform search"""
        query = self.search_entry.get().strip()
        if not query:
            messagebox.showwarning("Warning", "Enter search query!")
            return
        
        results = help_manager.search_help(query)
        
        self.results_text.delete("1.0", "end")
        
        if not results:
            self.results_text.insert("1.0", "❌ No results found.")
            return
        
        self.results_text.insert("1.0", f"✅ Found {len(results)} result(s):\n\n")
        
        for result in results:
            if result["type"] == "tab":
                self.results_text.insert("end", f"📋 Tab: {result['data'].get('title', '')}\n")
                self.results_text.insert("end", f"   {result['data'].get('description', '')}\n\n")
            else:
                self.results_text.insert("end", f"❓ Q: {result['data'].get('question', '')}\n")
                self.results_text.insert("end", f"   A: {result['data'].get('answer', '')}\n\n")
        
        self.results_text.see("1.0")
    
    def _refresh(self):
        pass