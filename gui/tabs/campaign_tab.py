"""Campaign Tab - Complete with Templates, Scheduling & Real-time Sync (Phase 4)"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog, simpledialog
from datetime import datetime, timedelta

# ✅ FIX: Import instances & functions separately
from core import log, account_manager, template_manager, scheduler, load_groups  # ← HAPUS campaign_manager dari sini
from core.campaign_manager import campaign_manager, CampaignStatus, CampaignType  # ← TAMBAH campaign_manager di sini!
from core.scheduler import TaskType
from gui.styles import COLORS, FONTS

class CampaignTab:
    title = "📈 Campaigns"
    
    def __init__(self, parent, main_window=None):
        self.parent = parent
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        self.current_campaign_id = None
        self._create_widgets()
        self._load_campaigns()
    
    def _create_widgets(self):
        # Header
        tk.Label(self.frame, text="📈 Campaign Management", font=("Segoe UI", 24, "bold"),
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
        
        tk.Button(toolbar, text="➕ New Campaign", command=self._create_campaign,
                  bg=COLORS["success"], fg="white", font=FONTS["bold"]).pack(side="left", padx=5)
        tk.Button(toolbar, text="🔄 Refresh", command=self._load_campaigns,
                  bg=COLORS["bg_light"], fg=COLORS["text"], font=FONTS["bold"]).pack(side="left", padx=5)
        tk.Button(toolbar, text="🗑️ Delete Selected", command=self._delete_campaign,
                  bg=COLORS["error"], fg="white", font=FONTS["bold"]).pack(side="left", padx=5)
        
        # === 2. CAMPAIGN LIST ===
        list_frame = tk.LabelFrame(self.scrollable_frame, text="📋 All Campaigns",
                                   fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                   font=FONTS["heading"])
        list_frame.pack(fill="x", padx=10, pady=10)
        
        columns = ("ID", "Name", "Status", "Type", "Accounts", "Groups", "Sent", "Failed")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=8)
        
        for col in columns:
            self.tree.heading(col, text=col)
            width = 80 if col not in ["Name"] else 200
            self.tree.column(col, width=width)
        
        self.tree.pack(fill="x", padx=10, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self._on_campaign_select)
        
        # === 3. CAMPAIGN DETAILS ===
        details_frame = tk.LabelFrame(self.scrollable_frame, text="📝 Campaign Details",
                                      fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                      font=FONTS["heading"])
        details_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Name & Status
        info_frame = tk.Frame(details_frame, bg=COLORS["bg_medium"])
        info_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(info_frame, text="Name:", fg=COLORS["text"], bg=COLORS["bg_medium"]).grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.name_var = tk.StringVar()
        tk.Entry(info_frame, textvariable=self.name_var, width=40, bg=COLORS["bg_light"], fg=COLORS["text"]).grid(row=0, column=1, padx=10, pady=5)
        
        tk.Label(info_frame, text="Status:", fg=COLORS["text"], bg=COLORS["bg_medium"]).grid(row=0, column=2, padx=10, pady=5, sticky="w")
        self.status_var = tk.StringVar()
        tk.Label(info_frame, textvariable=self.status_var, fg=COLORS["accent"], bg=COLORS["bg_medium"], width=15, font=FONTS["bold"]).grid(row=0, column=3, padx=10, pady=5, sticky="w")
        
        # Type
        tk.Label(info_frame, text="Type:", fg=COLORS["text"], bg=COLORS["bg_medium"]).grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.type_var = tk.StringVar(value="immediate")
        type_combo = ttk.Combobox(info_frame, textvariable=self.type_var,
                                  values=["immediate", "scheduled", "recurring"], width=37)
        type_combo.grid(row=1, column=1, padx=10, pady=5)
        
        # === 4. MESSAGE TEMPLATES (PHASE 4) ===
        template_frame = tk.LabelFrame(details_frame, text="📝 Message Templates",
                                       fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                       font=FONTS["heading"])
        template_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(template_frame, text="Use Template:", fg=COLORS["text"], bg=COLORS["bg_medium"]).pack(anchor="w", padx=10, pady=5)
        
        self.template_var = tk.StringVar(value="")
        self.template_combo = ttk.Combobox(template_frame, textvariable=self.template_var, width=45)
        self.template_combo.pack(fill="x", padx=10, pady=5)
        
        # Load templates
        self._load_templates()
        
        def apply_template(event=None):
            selection = self.template_var.get()
            if selection:
                templates = template_manager.get_all_templates()
                for t in templates:
                    if f"{t['name']} ({t['category']})" == selection:
                        content = template_manager.render_template(t['id'])
                        self.message_text.delete("1.0", "end")
                        self.message_text.insert("1.0", content)
                        break
        
        self.template_combo.bind("<<ComboboxSelected>>", apply_template)
        
        tk.Button(template_frame, text="➕ Create Template", command=self._create_template_dialog,
                  bg=COLORS["info"], fg="white").pack(pady=5)
        
        # Message
        tk.Label(details_frame, text="Message:", fg=COLORS["text"], bg=COLORS["bg_medium"]).pack(anchor="w", padx=10, pady=(10, 5))
        self.message_text = scrolledtext.ScrolledText(details_frame, height=6, width=50, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.message_text.pack(fill="x", padx=10, pady=5)
        
        # Image
        self.image_var = tk.BooleanVar(value=False)
        tk.Checkbutton(details_frame, text="🖼️ Include Image", variable=self.image_var,
                      bg=COLORS["bg_medium"], fg=COLORS["text"]).pack(anchor="w", padx=20, pady=5)
        
        self.image_path_var = tk.StringVar()
        self.image_browse_btn = tk.Button(details_frame, text="📂 Browse", command=self._browse_image,
                                          bg=COLORS["info"], fg="white", state="disabled")
        self.image_browse_btn.pack(pady=5)
        self.image_var.trace_add("write", lambda *args: self._toggle_image_browse())
        
        # === 5. ACCOUNT SELECTION ===
        account_frame = tk.LabelFrame(details_frame, text="📱 Accounts (Unlimited)",
                                      fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                      font=FONTS["heading"])
        account_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(account_frame, text="Available:", fg=COLORS["text"], bg=COLORS["bg_medium"]).grid(row=0, column=0, padx=10, pady=5)
        tk.Label(account_frame, text="Selected:", fg=COLORS["text"], bg=COLORS["bg_medium"]).grid(row=0, column=2, padx=10, pady=5)
        
        self.available_accounts = tk.Listbox(account_frame, height=5, width=25, bg=COLORS["bg_light"], fg=COLORS["text"], selectmode="extended")
        self.available_accounts.grid(row=1, column=0, padx=10, pady=5)
        
        self.selected_accounts = tk.Listbox(account_frame, height=5, width=25, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.selected_accounts.grid(row=1, column=2, padx=10, pady=5)
        
        assign_frame = tk.Frame(account_frame, bg=COLORS["bg_medium"])
        assign_frame.grid(row=1, column=1, padx=10, pady=5)
        tk.Button(assign_frame, text="➡️", command=self._add_accounts, bg=COLORS["success"], fg="white").pack(pady=2)
        tk.Button(assign_frame, text="⬅️", command=self._remove_accounts, bg=COLORS["error"], fg="white").pack(pady=2)
        
        # === 6. GROUP SELECTION ===
        group_frame = tk.LabelFrame(details_frame, text="🎯 Target Groups",
                                    fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                    font=FONTS["heading"])
        group_frame.pack(fill="x", padx=10, pady=10)
        
        self.group_source_var = tk.StringVar(value="joined")
        tk.Radiobutton(group_frame, text="Joined Groups Only", variable=self.group_source_var,
                      value="joined", bg=COLORS["bg_medium"], fg=COLORS["text"]).pack(anchor="w", padx=20, pady=3)
        tk.Radiobutton(group_frame, text="Custom Group List", variable=self.group_source_var,
                      value="custom", bg=COLORS["bg_medium"], fg=COLORS["text"]).pack(anchor="w", padx=20, pady=3)
        tk.Radiobutton(group_frame, text="From groups/valid.txt", variable=self.group_source_var,
                      value="valid_txt", bg=COLORS["bg_medium"], fg=COLORS["text"]).pack(anchor="w", padx=20, pady=3)
        
        # === 7. SETTINGS ===
        settings_frame = tk.LabelFrame(details_frame, text="⚙️ Broadcast Settings",
                                       fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                       font=FONTS["heading"])
        settings_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(settings_frame, text="Delay (seconds):", fg=COLORS["text"], bg=COLORS["bg_medium"]).grid(row=0, column=0, padx=10, pady=5)
        self.delay_min = tk.Entry(settings_frame, width=8, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.delay_min.insert(0, "10")
        self.delay_min.grid(row=0, column=1, padx=5, pady=5)
        tk.Label(settings_frame, text="-", fg=COLORS["text"], bg=COLORS["bg_medium"]).grid(row=0, column=2)
        self.delay_max = tk.Entry(settings_frame, width=8, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.delay_max.insert(0, "30")
        self.delay_max.grid(row=0, column=3, padx=5, pady=5)
        
        self.round_robin_var = tk.BooleanVar(value=True)
        tk.Checkbutton(settings_frame, text="🔄 Round-Robin (Rotate Accounts)", variable=self.round_robin_var,
                      bg=COLORS["bg_medium"], fg=COLORS["success"]).grid(row=1, column=0, columnspan=4, padx=10, pady=5, sticky="w")
        
        self.auto_scrape_var = tk.BooleanVar(value=False)
        tk.Checkbutton(settings_frame, text="📥 Auto-Scrape Members", variable=self.auto_scrape_var,
                      bg=COLORS["bg_medium"], fg=COLORS["text"]).grid(row=2, column=0, columnspan=4, padx=10, pady=5, sticky="w")
        
        # === 8. SCHEDULE SECTION (PHASE 4) ===
        schedule_frame = tk.LabelFrame(details_frame, text="⏰ Schedule Broadcast",
                                       fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                       font=FONTS["heading"])
        schedule_frame.pack(fill="x", padx=10, pady=10)
        
        self.schedule_type_var = tk.StringVar(value="immediate")
        
        tk.Radiobutton(schedule_frame, text="▶ Run Immediately", variable=self.schedule_type_var,
                      value="immediate", bg=COLORS["bg_medium"], fg=COLORS["text"]).pack(anchor="w", padx=20, pady=3)
        tk.Radiobutton(schedule_frame, text="📅 Schedule for Later", variable=self.schedule_type_var,
                      value="scheduled", bg=COLORS["bg_medium"], fg=COLORS["text"]).pack(anchor="w", padx=20, pady=3)
        tk.Radiobutton(schedule_frame, text="🔄 Recurring", variable=self.schedule_type_var,
                      value="recurring", bg=COLORS["bg_medium"], fg=COLORS["text"]).pack(anchor="w", padx=20, pady=3)
        
        # Schedule options
        self.schedule_options = tk.Frame(schedule_frame, bg=COLORS["bg_medium"])
        
        tk.Label(self.schedule_options, text="Date & Time:", fg=COLORS["text"], bg=COLORS["bg_medium"]).grid(row=0, column=0, padx=10, pady=5)
        self.schedule_date = tk.Entry(self.schedule_options, width=20, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.schedule_date.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M"))
        self.schedule_date.grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(self.schedule_options, text="Repeat:", fg=COLORS["text"], bg=COLORS["bg_medium"]).grid(row=1, column=0, padx=10, pady=5)
        self.repeat_var = tk.BooleanVar(value=False)
        tk.Checkbutton(self.schedule_options, text="Yes", variable=self.repeat_var,
                      bg=COLORS["bg_medium"], fg=COLORS["text"]).grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        tk.Label(self.schedule_options, text="Every:", fg=COLORS["text"], bg=COLORS["bg_medium"]).grid(row=2, column=0, padx=10, pady=5)
        self.interval_combo = ttk.Combobox(self.schedule_options, values=["1 hour", "6 hours", "1 day", "1 week"], width=15)
        self.interval_combo.set("1 day")
        self.interval_combo.grid(row=2, column=1, padx=5, pady=5)
        
        def toggle_schedule_options():
            if self.schedule_type_var.get() == "immediate":
                self.schedule_options.pack_forget()
            else:
                self.schedule_options.pack(fill="x", padx=10, pady=10)
        
        self.schedule_type_var.trace_add("write", lambda *args: toggle_schedule_options())
        
        # === 9. CONTROL BUTTONS ===
        control_frame = tk.Frame(details_frame, bg=COLORS["bg_medium"])
        control_frame.pack(fill="x", padx=10, pady=10)
        
        self.start_btn = tk.Button(control_frame, text="▶ Start Campaign", command=self._start_campaign,
                  bg=COLORS["success"], fg="white", font=FONTS["bold"], width=18)
        self.start_btn.pack(side="left", padx=5)
        self.pause_btn = tk.Button(control_frame, text="⏸️ Pause", command=self._pause_campaign,
                  bg=COLORS["warning"], fg="white", font=FONTS["bold"], width=12)
        self.pause_btn.pack(side="left", padx=5)
        self.stop_btn = tk.Button(control_frame, text="⏹️ Stop", command=self._stop_campaign,
                  bg=COLORS["error"], fg="white", font=FONTS["bold"], width=12)
        self.stop_btn.pack(side="left", padx=5)
        self.save_btn = tk.Button(control_frame, text="💾 Save Campaign", command=self._save_campaign,
                  bg=COLORS["info"], fg="white", font=FONTS["bold"], width=18)
        self.save_btn.pack(side="left", padx=5)
        
        # Stats
        self.stats_label = tk.Label(details_frame, text="", fg=COLORS["text_muted"],
                                     bg=COLORS["bg_medium"], font=FONTS["bold"])
        self.stats_label.pack(pady=5)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _load_templates(self):
        """Load templates into dropdown"""
        templates = template_manager.get_all_templates()
        template_list = [f"{t['name']} ({t['category']})" for t in templates]
        self.template_combo['values'] = [""] + template_list
    
    def _load_campaigns(self):
        """Load all campaigns"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        campaigns = campaign_manager.get_all_campaigns()
        for camp in campaigns:
            self.tree.insert("", "end", values=(
                camp.id,
                camp.name,
                camp.status.value,
                camp.campaign_type.value,
                len(camp.account_ids),
                len(camp.group_ids),
                camp.stats.messages_sent,
                camp.stats.messages_failed
            ))
        
        self._load_account_lists()
        self._load_templates()
    
    def _on_campaign_select(self, event):
        """Load selected campaign details"""
        selection = self.tree.selection()
        if not selection:
            return
        
        camp_id = self.tree.item(selection[0])["values"][0]
        self.current_campaign_id = camp_id
        
        camp = campaign_manager.get_campaign(camp_id)
        if camp:
            self.name_var.set(camp.name)
            self.status_var.set(camp.status.value)
            self.type_var.set(camp.campaign_type.value)
            self.message_text.delete("1.0", "end")
            self.message_text.insert("1.0", camp.message.text)
            self.image_var.set(camp.message.has_image)
            if camp.message.image_path:
                self.image_path_var.set(camp.message.image_path)
                self._toggle_image_browse()
            
            # Load accounts
            self._load_account_lists(camp.account_ids)
            
            # Load settings
            self.delay_min.delete(0, "end")
            self.delay_min.insert(0, str(camp.settings.delay_min))
            self.delay_max.delete(0, "end")
            self.delay_max.insert(0, str(camp.settings.delay_max))
            self.round_robin_var.set(camp.settings.round_robin)
            self.auto_scrape_var.set(camp.settings.auto_scrape)
            
            # Update stats
            self.stats_label.config(
                text=f"Sent: {camp.stats.messages_sent} | Failed: {camp.stats.messages_failed} | "
                     f"Started: {camp.stats.started_at[:16] if camp.stats.started_at else 'N/A'}"
            )
    
    def _load_account_lists(self, selected_ids=None):
        """Load account lists"""
        self.available_accounts.delete(0, "end")
        self.selected_accounts.delete(0, "end")
        
        selected_ids = selected_ids or []
        
        for acc in account_manager.get_all():
            display = f"{acc['name']} (L{acc.get('level', 1)})"
            if acc['name'] in selected_ids:
                self.selected_accounts.insert("end", acc['name'])
            else:
                self.available_accounts.insert("end", display)
    
    def _add_accounts(self):
        """Add accounts to campaign"""
        selection = self.available_accounts.curselection()
        for i in selection:
            display = self.available_accounts.get(i)
            name = display.split(" (")[0]
            self.selected_accounts.insert("end", name)
            self.available_accounts.delete(i)
    
    def _remove_accounts(self):
        """Remove accounts from campaign"""
        selection = self.selected_accounts.curselection()
        for i in reversed(selection):
            name = self.selected_accounts.get(i)
            self.available_accounts.insert("end", f"{name} (L1)")
            self.selected_accounts.delete(i)
    
    def _browse_image(self):
        """Browse for image"""
        filepath = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg")])
        if filepath:
            self.image_path_var.set(filepath)
    
    def _toggle_image_browse(self):
        """Enable/disable image browse button"""
        if self.image_var.get():
            self.image_browse_btn.config(state="normal")
        else:
            self.image_browse_btn.config(state="disabled")
            self.image_path_var.set("")
    
    def _create_template_dialog(self):
        """Dialog to create new template"""
        dialog = tk.Toplevel(self.frame)
        dialog.title("📝 Create Message Template")
        dialog.geometry("550x500")
        dialog.configure(bg=COLORS["bg_dark"])
        
        tk.Label(dialog, text="📝 Create Template", font=("Segoe UI", 18, "bold"),
                 fg=COLORS["primary"], bg=COLORS["bg_dark"]).pack(pady=15)
        
        tk.Label(dialog, text="Template Name:", fg=COLORS["text"], bg=COLORS["bg_dark"]).pack(pady=5)
        name_entry = tk.Entry(dialog, width=50, bg=COLORS["bg_light"], fg=COLORS["text"])
        name_entry.pack(pady=5)
        
        tk.Label(dialog, text="Category:", fg=COLORS["text"], bg=COLORS["bg_dark"]).pack(pady=5)
        category_var = tk.StringVar(value="general")
        category_combo = ttk.Combobox(dialog, textvariable=category_var,
                                       values=["general", "promo", "announcement", "welcome"], width=47)
        category_combo.pack(pady=5)
        
        tk.Label(dialog, text="Content (use {variable} for dynamic content):",
                fg=COLORS["text"], bg=COLORS["bg_dark"]).pack(pady=5)
        content_text = scrolledtext.ScrolledText(dialog, height=12, width=60,
                                                  bg=COLORS["bg_light"], fg=COLORS["text"])
        content_text.pack(pady=5)
        
        tk.Label(dialog, text="Variables: {name}, {product}, {price}, {link}, {date}",
                fg=COLORS["text_muted"], bg=COLORS["bg_dark"], font=FONTS["small"]).pack(pady=5)
        
        def save_template():
            name = name_entry.get().strip()
            category = category_var.get()
            content = content_text.get("1.0", "end-1c").strip()
            
            if not name or not content:
                messagebox.showerror("Error", "Name and content required!")
                return
            
            template_manager.create_template(name, content, category)
            self._load_templates()
            messagebox.showinfo("Success", f"Template '{name}' created!")
            dialog.destroy()
        
        tk.Button(dialog, text="💾 Save Template", command=save_template,
                  bg=COLORS["success"], fg="white", font=FONTS["bold"],
                  padx=30, pady=10).pack(pady=20)
    
    def _create_campaign(self):
        """Create new campaign"""
        name = simpledialog.askstring("New Campaign", "Enter campaign name:")
        if name:
            camp = campaign_manager.create_campaign(name)
            self.current_campaign_id = camp.id
            self._load_campaigns()
            messagebox.showinfo("Success", f"Campaign created: {name}")
    
    def _save_campaign(self):
        """Save campaign"""
        if not self.current_campaign_id:
            messagebox.showwarning("Warning", "Select or create a campaign first!")
            return
        
        # Get selected accounts
        selected = [self.selected_accounts.get(i) for i in range(self.selected_accounts.size())]
        
        # Save campaign
        campaign_manager.update_campaign(
            self.current_campaign_id,
            name=self.name_var.get(),
            campaign_type=CampaignType(self.type_var.get()),
            message=type('obj', (object,), {
                'text': self.message_text.get("1.0", "end-1c").strip(),
                'image_path': self.image_path_var.get() if self.image_var.get() else None,
                'has_image': self.image_var.get()
            })(),
            settings=type('obj', (object,), {
                'delay_min': int(self.delay_min.get() or 10),
                'delay_max': int(self.delay_max.get() or 30),
                'round_robin': self.round_robin_var.get(),
                'auto_retry': True,
                'max_retries': 3,
                'rate_limit_per_hour': 100,
                'stop_on_error': False,
                'auto_scrape': self.auto_scrape_var.get()
            })(),
            account_ids=selected,
            group_source=self.group_source_var.get()
        )
        
        messagebox.showinfo("Success", "Campaign saved!")
        self._load_campaigns()
    
    def _delete_campaign(self):
        """Delete campaign"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Select a campaign first!")
            return
        
        if messagebox.askyesno("Confirm", "Delete this campaign?"):
            camp_id = self.tree.item(selection[0])["values"][0]
            campaign_manager.delete_campaign(camp_id)
            self.current_campaign_id = None
            self._load_campaigns()
    
    def _start_campaign(self):
        """Start or schedule campaign"""
        if not self.current_campaign_id:
            messagebox.showwarning("Warning", "Select a campaign first!")
            return
        
        # Save first
        self._save_campaign()
        
        schedule_type = self.schedule_type_var.get()
        
        if schedule_type == "immediate":
            # Start immediately
            if campaign_manager.start_campaign(self.current_campaign_id):
                messagebox.showinfo("Started", "Campaign started! Check Broadcast tab for progress.")
                self._load_campaigns()
            else:
                messagebox.showerror("Error", "Failed to start campaign")
        else:
            # Schedule for later
            self._schedule_campaign()
    
    def _schedule_campaign(self):
        """Schedule campaign for later execution"""
        schedule_time_str = self.schedule_date.get()
        repeat = self.repeat_var.get()
        interval = self.interval_combo.get()
        
        # Parse schedule time
        try:
            schedule_dt = datetime.strptime(schedule_time_str, "%Y-%m-%d %H:%M")
        except:
            messagebox.showerror("Error", "Invalid date/time format! Use: YYYY-MM-DD HH:MM")
            return
        
        # Get campaign data
        camp = campaign_manager.get_campaign(self.current_campaign_id)
        if not camp:
            return
        
        # Calculate repeat interval in seconds
        interval_map = {"1 hour": 3600, "6 hours": 21600, "1 day": 86400, "1 week": 604800}
        repeat_interval = interval_map.get(interval, 86400)
        
        # Create scheduled task
        task = scheduler.create_broadcast_schedule(
            campaign_id=self.current_campaign_id,
            schedule_time=schedule_dt.isoformat(),
            accounts=camp.account_ids,
            message=camp.message.text,
            repeat=repeat,
            repeat_interval=repeat_interval,
            delay_min=camp.settings.delay_min,
            delay_max=camp.settings.delay_max,
            round_robin=camp.settings.round_robin,
            auto_scrape=camp.settings.auto_scrape
        )
        
        if repeat:
            msg = f"Campaign scheduled to run every {interval}!\n\nFirst run: {schedule_dt.strftime('%Y-%m-%d %H:%M')}"
        else:
            msg = f"Campaign scheduled for {schedule_dt.strftime('%Y-%m-%d %H:%M')}!"
        
        messagebox.showinfo("Scheduled", msg)
    
    def _pause_campaign(self):
        """Pause campaign"""
        if not self.current_campaign_id:
            return
        campaign_manager.pause_campaign(self.current_campaign_id)
        self._load_campaigns()
    
    def _stop_campaign(self):
        """Stop campaign"""
        if not self.current_campaign_id:
            return
        campaign_manager.stop_campaign(self.current_campaign_id)
        self._load_campaigns()
    
    def _refresh(self):
        self._load_campaigns()