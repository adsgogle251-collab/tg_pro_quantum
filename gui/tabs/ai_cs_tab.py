"""AI CS Tab - Scrollable Content Fix"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from core import log, ai_cs_engine, account_manager, config_manager
from core.account_router import account_router, Feature
from gui.styles import COLORS, FONTS

class AICSTab:
    title = "💬 AI CS"
    
    def __init__(self, parent, main_window=None):
        self.parent = parent
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        self.cs_account_count = None
        self._create_widgets()
        self._load_assigned_accounts()
    
    def _create_widgets(self):
        # Header
        tk.Label(self.frame, text="💬 AI Customer Service", font=("Segoe UI", 24, "bold"),
                 fg=COLORS["primary"], bg=COLORS["bg_dark"]).pack(pady=15)
        
        # Main scrollable container
        main_container = tk.Frame(self.frame, bg=COLORS["bg_dark"])
        main_container.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Canvas with scrollbar
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
        
        # 1. AI Model Selection
        model_frame = tk.LabelFrame(self.scrollable_frame, text="🤖 AI Model Selection",
                                    fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                    font=FONTS["heading"])
        model_frame.pack(fill="x", padx=10, pady=10)
        
        self.ai_model_var = tk.StringVar(value="gpt-3.5-turbo")
        
        models = [
            ("OpenAI GPT-3.5", "gpt-3.5-turbo"),
            ("OpenAI GPT-4", "gpt-4"),
            ("Claude (Anthropic)", "claude-3"),
            ("Google Gemini", "gemini-pro"),
        ]
        
        for text, value in models:
            tk.Radiobutton(model_frame, text=text, variable=self.ai_model_var,
                          value=value, bg=COLORS["bg_medium"], fg=COLORS["text"],
                          selectcolor=COLORS["bg_medium"]).pack(anchor="w", padx=20, pady=3)
        
        # 2. Response Mode
        mode_frame = tk.LabelFrame(self.scrollable_frame, text="📝 Response Mode",
                                   fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                   font=FONTS["heading"])
        mode_frame.pack(fill="x", padx=10, pady=10)
        
        self.response_mode_var = tk.StringVar(value="support")
        
        modes = [
            ("🤝 Support (Helpful)", "support"),
            ("💼 Formal (Business)", "formal"),
            ("😊 Casual (Friendly)", "casual"),
            ("💰 Sales (Persuasive)", "sales"),
        ]
        
        for text, value in modes:
            tk.Radiobutton(mode_frame, text=text, variable=self.response_mode_var,
                          value=value, bg=COLORS["bg_medium"], fg=COLORS["text"],
                          selectcolor=COLORS["bg_medium"]).pack(anchor="w", padx=20, pady=3)
        
        # 3. Account Assignment
        account_frame = tk.LabelFrame(self.scrollable_frame, text="📱 CS Accounts",
                                      fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                      font=FONTS["heading"])
        account_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(account_frame, text="Available:", fg=COLORS["text"], bg=COLORS["bg_medium"]).grid(row=0, column=0, padx=10, pady=5)
        tk.Label(account_frame, text="Assigned to CS:", fg=COLORS["text"], bg=COLORS["bg_medium"]).grid(row=0, column=2, padx=10, pady=5)
        
        self.available_accounts = tk.Listbox(account_frame, height=4, width=25, bg=COLORS["bg_light"], fg=COLORS["text"], selectmode="extended")
        self.available_accounts.grid(row=1, column=0, padx=10, pady=5)
        
        self.assigned_accounts = tk.Listbox(account_frame, height=4, width=25, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.assigned_accounts.grid(row=1, column=2, padx=10, pady=5)
        
        assign_frame = tk.Frame(account_frame, bg=COLORS["bg_medium"])
        assign_frame.grid(row=1, column=1, padx=10, pady=5)
        tk.Button(assign_frame, text="➡️ Assign", command=self._assign_cs_accounts, bg=COLORS["success"], fg="white").pack(pady=2)
        tk.Button(assign_frame, text="⬅️ Remove", command=self._remove_cs_accounts, bg=COLORS["error"], fg="white").pack(pady=2)
        
        self.cs_account_count = tk.Label(account_frame, text="0 accounts assigned to CS",
                                         fg=COLORS["text_muted"], bg=COLORS["bg_medium"])
        self.cs_account_count.grid(row=2, column=0, columnspan=3, padx=10, pady=5)
        
        # 4. Settings
        settings_frame = tk.LabelFrame(self.scrollable_frame, text="⚙️ AI CS Settings",
                                       fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                       font=FONTS["heading"])
        settings_frame.pack(fill="x", padx=10, pady=10)
        
        self.enabled_var = tk.BooleanVar(value=True)
        tk.Checkbutton(settings_frame, text="🤖 Auto-Reply Enabled", variable=self.enabled_var,
                      bg=COLORS["bg_medium"], fg=COLORS["success"], selectcolor=COLORS["bg_medium"]).pack(pady=5)
        
        self.multi_media_var = tk.BooleanVar(value=True)
        tk.Checkbutton(settings_frame, text="🖼️ Multi-Media Support (Image/Voice)", variable=self.multi_media_var,
                      bg=COLORS["bg_medium"], fg=COLORS["text"], selectcolor=COLORS["bg_medium"]).pack(pady=5)
        
        self.learn_var = tk.BooleanVar(value=True)
        tk.Checkbutton(settings_frame, text="📚 Auto-Learn from Conversations", variable=self.learn_var,
                      bg=COLORS["bg_medium"], fg=COLORS["text"], selectcolor=COLORS["bg_medium"]).pack(pady=5)
        
        # 5. Chat Display
        chat_frame = tk.LabelFrame(self.scrollable_frame, text="💬 Active Conversations",
                                   fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                   font=FONTS["heading"])
        chat_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.chat_display = scrolledtext.ScrolledText(chat_frame, height=12,
                                                       bg=COLORS["bg_light"], fg=COLORS["text"],
                                                       font=("Consolas", 10))
        self.chat_display.pack(fill="both", expand=True, padx=10, pady=5)
        
        # 6. Input
        input_frame = tk.Frame(self.scrollable_frame, bg=COLORS["bg_medium"])
        input_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(input_frame, text="Your Reply:", fg=COLORS["text"],
                bg=COLORS["bg_medium"]).pack(side="left", padx=5)
        self.reply_entry = tk.Entry(input_frame, width=50, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.reply_entry.pack(side="left", padx=5)
        
        tk.Button(input_frame, text="Send", command=self._send_reply,
                  bg=COLORS["success"], fg="white").pack(side="left", padx=5)
        tk.Button(input_frame, text="🖼️ Image", command=self._send_image,
                  bg=COLORS["info"], fg="white").pack(side="left", padx=5)
        tk.Button(input_frame, text="🎤 Voice", command=self._send_voice,
                  bg=COLORS["accent"], fg="white").pack(side="left", padx=5)
        tk.Button(input_frame, text="📚 Add to KB", command=self._add_to_kb,
                  bg=COLORS["warning"], fg="white").pack(side="left", padx=5)
        
        # 7. Stats
        stats_frame = tk.Frame(self.scrollable_frame, bg=COLORS["bg_medium"])
        stats_frame.pack(fill="x", padx=10, pady=10)
        
        self.stats_label = tk.Label(stats_frame, text="", fg=COLORS["text_muted"],
                                     bg=COLORS["bg_medium"], font=FONTS["bold"])
        self.stats_label.pack()
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _on_tab_selected(self):
        """Called by main_window when this tab is selected."""
        self._load_assigned_accounts()

    def _load_assigned_accounts(self):
        if not hasattr(self, 'available_accounts'):
            return

        self.available_accounts.delete(0, "end")
        self.assigned_accounts.delete(0, "end")

        assigned_names = {a['name'] for a in account_manager.get_accounts_by_feature("cs")}

        for acc in account_manager.get_all():
            display = f"{acc['name']} (L{acc.get('level', 1)})"
            if acc['name'] in assigned_names:
                self.assigned_accounts.insert("end", acc['name'])
            else:
                self.available_accounts.insert("end", display)

        count = self.assigned_accounts.size()
        if self.cs_account_count:
            self.cs_account_count.config(text=f"{count} accounts assigned to CS")

    def _assign_cs_accounts(self):
        selection = self.available_accounts.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Select accounts first!")
            return

        for i in selection:
            display = self.available_accounts.get(i)
            name = display.split(" (")[0]
            account_manager.assign_feature(name, "cs")

        self._load_assigned_accounts()
        messagebox.showinfo("Success", "Accounts assigned to CS")

    def _remove_cs_accounts(self):
        selection = self.assigned_accounts.curselection()
        if not selection:
            return

        for i in reversed(selection):
            name = self.assigned_accounts.get(i)
            account_manager.remove_feature(name, "cs")

        self._load_assigned_accounts()
    
    def _send_reply(self):
        reply = self.reply_entry.get().strip()
        if reply:
            self.chat_display.insert("end", f"\n[You]: {reply}")
            self.reply_entry.delete(0, "end")
            self.chat_display.insert("end", f"\n[AI]: Response sent...")
            self.chat_display.see("end")
            log(f"CS reply sent: {reply[:50]}...", "info")
    
    def _send_image(self):
        filepath = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg")])
        if filepath:
            self.chat_display.insert("end", f"\n[Image Sent]: {filepath}\n")
            self.chat_display.see("end")
    
    def _send_voice(self):
        filepath = filedialog.askopenfilename(filetypes=[("Audio", "*.mp3 *.wav")])
        if filepath:
            self.chat_display.insert("end", f"\n[Voice Sent]: {filepath}\n")
            self.chat_display.see("end")
    
    def _add_to_kb(self):
        messagebox.showinfo("Info", "Add to knowledge base feature")
    
    def _update_stats(self):
        try:
            stats = ai_cs_engine.get_conversation_stats()
            self.stats_label.config(
                text=f"Active: {stats.get('active_conversations', 0)} | "
                     f"By Intent: {stats.get('by_intent', {})}"
            )
        except:
            self.stats_label.config(text="CS Stats: Not available")
    
    def _refresh(self):
        self._load_assigned_accounts()
        self._update_stats()