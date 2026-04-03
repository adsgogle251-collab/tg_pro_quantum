"""
TG PRO BROADCASTER v100 ULTIMATE - Ultimate Broadcast Tab
Complete broadcast control with AI content generation, scheduling, and analytics
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog, simpledialog
import threading
import asyncio
import json
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from core import log, load_message, save_message, load_groups, load_accounts
from core.parallel_broadcast import parallel_broadcast
from core.ai_content import ai_content
from core.spam_detector import spam_detector
from core.smart_scheduler import smart_scheduler
from core.statistics import statistics
from core.graph_manager import graph_manager
from core.notification_manager import notification_manager
from .styles import COLORS, FONTS

# ==================== DATA CLASSES ====================
@dataclass
class BroadcastStats:
    """Broadcast statistics"""
    total_sent: int = 0
    total_failed: int = 0
    total_groups: int = 0
    total_accounts: int = 0
    success_rate: float = 0.0
    messages_per_minute: float = 0.0
    messages_per_hour: float = 0.0
    current_speed: float = 0.0
    estimated_completion: Optional[str] = None
    start_time: Optional[datetime] = None
    last_message_time: Optional[datetime] = None

@dataclass
class BroadcastPreset:
    """Broadcast preset configuration"""
    name: str
    message: str
    delay_min: int = 10
    delay_max: int = 25
    parallel: bool = True
    anti_spam: bool = True
    proxy: bool = False
    schedule: str = "now"

# ==================== MAIN CLASS ====================
class BroadcastUltimate:
    """Ultimate Broadcast Tab with full features"""
    title = "📢 Broadcast"

    def __init__(self, parent, main_window=None):
        self.parent = parent
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        self.root = parent.winfo_toplevel()
        
        # State
        self.running = False
        self.paused = False
        self.stats = BroadcastStats()
        self.current_preset = None
        self.presets: Dict[str, BroadcastPreset] = {}
        self.history = []
        
        # Settings
        self.auto_save = True
        self.notify_on_complete = True
        self.show_preview = True
        
        # Create UI
        self._create_widgets()
        self._load_data()
        self._load_presets()
        self._start_stats_updater()
        
        # Bind keyboard shortcuts
        self._bind_shortcuts()

    def _bind_shortcuts(self):
        """Bind keyboard shortcuts"""
        self.frame.bind("<Control-s>", lambda e: self._save_message())
        self.frame.bind("<Control-l>", lambda e: self._load_template())
        self.frame.bind("<Control-r>", lambda e: self._rewrite_message())
        self.frame.bind("<Control-g>", lambda e: self._ai_generate())
        self.frame.bind("<F5>", lambda e: self._refresh_data())

    def _create_widgets(self):
        """Create all UI components"""
        # Header
        header = tk.Frame(self.frame, bg=COLORS["bg_dark"], height=100)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        title_frame = tk.Frame(header, bg=COLORS["bg_dark"])
        title_frame.pack(side="left", padx=20, pady=15)
        
        tk.Label(title_frame, text="Ultimate Broadcast Engine", 
                 font=("Inter", 24, "bold"),
                 fg=COLORS["accent"], bg=COLORS["bg_dark"]).pack(anchor="w")
        tk.Label(title_frame, text="24/7 Auto Broadcast with Smart AI", 
                 font=("Inter", 10), fg=COLORS["text_muted"], 
                 bg=COLORS["bg_dark"]).pack(anchor="w")
        
        # Status indicator
        status_frame = tk.Frame(header, bg=COLORS["bg_dark"])
        status_frame.pack(side="right", padx=20, pady=15)
        
        self.status_indicator = tk.Label(status_frame, text="⚪", font=("Arial", 14),
                                          fg="gray", bg=COLORS["bg_dark"])
        self.status_indicator.pack(side="left")
        
        self.status_text = tk.Label(status_frame, text="Ready", 
                                     fg=COLORS["text_muted"], bg=COLORS["bg_dark"],
                                     font=("Inter", 10, "bold"))
        self.status_text.pack(side="left", padx=5)
        
        # Main container
        main = tk.Frame(self.frame, bg=COLORS["bg_dark"])
        main.pack(fill="both", expand=True, padx=20, pady=10)
        
        # ==================== LEFT PANEL - MESSAGE EDITOR ====================
        left_panel = tk.Frame(main, bg=COLORS["bg_medium"], relief="flat", bd=1)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # Message toolbar
        msg_toolbar = tk.Frame(left_panel, bg=COLORS["bg_medium"])
        msg_toolbar.pack(fill="x", pady=5, padx=10)
        
        tk.Label(msg_toolbar, text="Broadcast Message", font=FONTS["heading"],
                 fg=COLORS["accent"], bg=COLORS["bg_medium"]).pack(side="left")
        
        # AI Buttons
        ai_btn_frame = tk.Frame(msg_toolbar, bg=COLORS["bg_medium"])
        ai_btn_frame.pack(side="right")
        
        tk.Button(ai_btn_frame, text="✨ AI Generate", command=self._ai_generate,
                  bg=COLORS["accent"], fg="white", font=FONTS["small"],
                  padx=8, pady=2).pack(side="left", padx=2)
        tk.Button(ai_btn_frame, text="🔄 Anti-Spam", command=self._rewrite_message,
                  bg=COLORS["warning"], fg="white", font=FONTS["small"],
                  padx=8, pady=2).pack(side="left", padx=2)
        tk.Button(ai_btn_frame, text="📝 Templates", command=self._show_templates,
                  bg=COLORS["info"], fg="white", font=FONTS["small"],
                  padx=8, pady=2).pack(side="left", padx=2)
        
        # Message text area
        self.message_text = scrolledtext.ScrolledText(left_panel, height=14, width=60,
                                                        bg=COLORS["bg_light"], fg=COLORS["text"],
                                                        font=FONTS["normal"], wrap=tk.WORD,
                                                        undo=True)
        self.message_text.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Message toolbar bottom
        msg_bottom = tk.Frame(left_panel, bg=COLORS["bg_medium"])
        msg_bottom.pack(fill="x", pady=5, padx=10)
        
        # Character counter
        self.char_counter = tk.Label(msg_bottom, text="0 characters", 
                                      fg=COLORS["text_muted"], bg=COLORS["bg_medium"],
                                      font=FONTS["small"])
        self.char_counter.pack(side="left")
        self.message_text.bind("<KeyRelease>", self._update_char_counter)
        
        # Variables info
        var_frame = tk.Frame(msg_bottom, bg=COLORS["bg_medium"])
        var_frame.pack(side="right")
        
        tk.Label(var_frame, text="Variables:", fg=COLORS["text_muted"],
                 bg=COLORS["bg_medium"], font=FONTS["small"]).pack(side="left")
        
        variables = ["{{name}}", "{{group}}", "{{member_count}}", "{{date}}", "{{time}}"]
        for var in variables:
            lbl = tk.Label(var_frame, text=var, fg=COLORS["accent"], bg=COLORS["bg_medium"],
                           font=FONTS["small"], cursor="hand2")
            lbl.pack(side="left", padx=3)
            lbl.bind("<Button-1>", lambda e, v=var: self._insert_variable(v))
        
        # Save/Load buttons
        btn_frame = tk.Frame(left_panel, bg=COLORS["bg_medium"])
        btn_frame.pack(fill="x", pady=5, padx=10)
        
        tk.Button(btn_frame, text="💾 Save Message", command=self._save_message,
                  bg=COLORS["info"], fg="white", padx=12).pack(side="left", padx=2)
        tk.Button(btn_frame, text="📂 Load Template", command=self._load_template,
                  bg=COLORS["accent"], fg="white", padx=12).pack(side="left", padx=2)
        tk.Button(btn_frame, text="📋 Copy to Clipboard", command=self._copy_message,
                  bg=COLORS["bg_light"], fg=COLORS["text"], padx=12).pack(side="left", padx=2)
        
        # ==================== RIGHT PANEL - CONTROLS ====================
        right_panel = tk.Frame(main, bg=COLORS["bg_medium"], relief="flat", bd=1)
        right_panel.pack(side="right", fill="both", expand=True)
        
        # Stats section
        stats_frame = tk.LabelFrame(right_panel, text="📊 Statistics", fg=COLORS["accent"],
                                     bg=COLORS["bg_medium"], font=FONTS["heading"])
        stats_frame.pack(fill="x", padx=10, pady=5)
        
        stats_grid = tk.Frame(stats_frame, bg=COLORS["bg_medium"])
        stats_grid.pack(fill="x", padx=5, pady=5)
        
        # Left stats
        left_stats = tk.Frame(stats_grid, bg=COLORS["bg_medium"])
        left_stats.pack(side="left", fill="both", expand=True)
        
        self.groups_label = tk.Label(left_stats, text="Groups: 0", fg=COLORS["text_muted"],
                                      bg=COLORS["bg_medium"], font=FONTS["normal"])
        self.groups_label.pack(anchor="w", pady=2)
        
        self.accounts_label = tk.Label(left_stats, text="Accounts: 0", fg=COLORS["text_muted"],
                                        bg=COLORS["bg_medium"], font=FONTS["normal"])
        self.accounts_label.pack(anchor="w", pady=2)
        
        self.sent_label = tk.Label(left_stats, text="Sent: 0", fg=COLORS["success"],
                                    bg=COLORS["bg_medium"], font=FONTS["bold"])
        self.sent_label.pack(anchor="w", pady=2)
        
        # Right stats
        right_stats = tk.Frame(stats_grid, bg=COLORS["bg_medium"])
        right_stats.pack(side="right", fill="both", expand=True)
        
        self.failed_label = tk.Label(right_stats, text="Failed: 0", fg=COLORS["error"],
                                      bg=COLORS["bg_medium"], font=FONTS["normal"])
        self.failed_label.pack(anchor="w", pady=2)
        
        self.rate_label = tk.Label(right_stats, text="Rate: 0%", fg=COLORS["accent"],
                                    bg=COLORS["bg_medium"], font=FONTS["normal"])
        self.rate_label.pack(anchor="w", pady=2)
        
        self.speed_label = tk.Label(right_stats, text="Speed: 0 msg/min", fg=COLORS["warning"],
                                     bg=COLORS["bg_medium"], font=FONTS["small"])
        self.speed_label.pack(anchor="w", pady=2)
        
        # Progress bar
        self.progress = ttk.Progressbar(stats_frame, mode='determinate')
        self.progress.pack(fill="x", padx=10, pady=5)
        
        # Control buttons
        control_frame = tk.LabelFrame(right_panel, text="🎮 Controls", fg=COLORS["accent"],
                                       bg=COLORS["bg_medium"], font=FONTS["heading"])
        control_frame.pack(fill="x", padx=10, pady=5)
        
        # Main control buttons
        self.start_btn = tk.Button(control_frame, text="▶ START BROADCAST", command=self._start_broadcast,
                                   bg=COLORS["success"], fg="white", font=FONTS["bold"],
                                   padx=20, pady=10, bd=0, cursor="hand2")
        self.start_btn.pack(pady=10, padx=10, fill="x")
        
        self.pause_btn = tk.Button(control_frame, text="⏸️ PAUSE", command=self._pause_broadcast,
                                   bg=COLORS["warning"], fg="white", font=FONTS["bold"],
                                   padx=20, pady=10, bd=0, cursor="hand2", state="disabled")
        self.pause_btn.pack(pady=5, padx=10, fill="x")
        
        self.stop_btn = tk.Button(control_frame, text="⏹️ STOP BROADCAST", command=self._stop_broadcast,
                                  bg=COLORS["error"], fg="white", font=FONTS["bold"],
                                  padx=20, pady=10, bd=0, cursor="hand2", state="disabled")
        self.stop_btn.pack(pady=5, padx=10, fill="x")
        
        # Mode selection
        mode_frame = tk.LabelFrame(control_frame, text="⚡ Broadcast Mode", fg=COLORS["accent"],
                                    bg=COLORS["bg_medium"], font=FONTS["small"])
        mode_frame.pack(fill="x", pady=5, padx=10)
        
        self.mode_var = tk.StringVar(value="pintar")
        modes = [
            ("🚀 Agresif (Fast - Higher risk)", "agresif", COLORS["error"]),
            ("🛡️ Aman (Safe - Lower risk)", "aman", COLORS["success"]),
            ("🧠 Pintar (Adaptive - Recommended)", "pintar", COLORS["accent"])
        ]
        for text, val, color in modes:
            rb = tk.Radiobutton(mode_frame, text=text, variable=self.mode_var, value=val,
                                bg=COLORS["bg_medium"], fg=color, selectcolor=COLORS["bg_medium"])
            rb.pack(anchor="w", padx=10, pady=2)
        
        # Schedule
        schedule_frame = tk.LabelFrame(control_frame, text="📅 Schedule", fg=COLORS["accent"],
                                        bg=COLORS["bg_medium"], font=FONTS["small"])
        schedule_frame.pack(fill="x", pady=5, padx=10)
        
        schedule_row = tk.Frame(schedule_frame, bg=COLORS["bg_medium"])
        schedule_row.pack(pady=5)
        
        self.schedule_var = tk.StringVar(value="now")
        tk.Radiobutton(schedule_row, text="Now", variable=self.schedule_var, value="now",
                       bg=COLORS["bg_medium"], fg=COLORS["text"]).pack(side="left", padx=5)
        tk.Radiobutton(schedule_row, text="Best Time (AI)", variable=self.schedule_var, value="best",
                       bg=COLORS["bg_medium"], fg=COLORS["text"]).pack(side="left", padx=5)
        tk.Radiobutton(schedule_row, text="Custom", variable=self.schedule_var, value="custom",
                       bg=COLORS["bg_medium"], fg=COLORS["text"]).pack(side="left", padx=5)
        
        self.custom_time_entry = tk.Entry(schedule_frame, width=15, bg=COLORS["bg_light"],
                                           fg=COLORS["text"], state="disabled")
        self.custom_time_entry.pack(pady=2)
        self.custom_time_entry.insert(0, "09:00")
        
        # Advanced options
        adv_frame = tk.LabelFrame(control_frame, text="⚙️ Advanced", fg=COLORS["accent"],
                                   bg=COLORS["bg_medium"], font=FONTS["small"])
        adv_frame.pack(fill="x", pady=5, padx=10)
        
        self.parallel_var = tk.BooleanVar(value=True)
        tk.Checkbutton(adv_frame, text="Parallel Broadcast (Multi-Account)", 
                       variable=self.parallel_var,
                       bg=COLORS["bg_medium"], fg=COLORS["text"]).pack(anchor="w", padx=10, pady=2)
        
        self.proxy_var = tk.BooleanVar(value=False)
        tk.Checkbutton(adv_frame, text="Use Proxy Rotation", variable=self.proxy_var,
                       bg=COLORS["bg_medium"], fg=COLORS["text"]).pack(anchor="w", padx=10, pady=2)
        
        self.antispam_var = tk.BooleanVar(value=True)
        tk.Checkbutton(adv_frame, text="Anti-Spam Protection", variable=self.antispam_var,
                       bg=COLORS["bg_medium"], fg=COLORS["text"]).pack(anchor="w", padx=10, pady=2)
        
        self.auto_retry_var = tk.BooleanVar(value=True)
        tk.Checkbutton(adv_frame, text="Auto Retry on Failure", variable=self.auto_retry_var,
                       bg=COLORS["bg_medium"], fg=COLORS["text"]).pack(anchor="w", padx=10, pady=2)
        
        # Delay settings
        delay_frame = tk.Frame(adv_frame, bg=COLORS["bg_medium"])
        delay_frame.pack(fill="x", pady=5, padx=10)
        
        tk.Label(delay_frame, text="Delay (min):", fg=COLORS["text_muted"],
                 bg=COLORS["bg_medium"], font=FONTS["small"]).pack(side="left")
        self.delay_min_var = tk.StringVar(value="10")
        tk.Entry(delay_frame, textvariable=self.delay_min_var, width=5,
                 bg=COLORS["bg_light"], fg=COLORS["text"]).pack(side="left", padx=5)
        
        tk.Label(delay_frame, text="-", fg=COLORS["text_muted"],
                 bg=COLORS["bg_medium"]).pack(side="left")
        self.delay_max_var = tk.StringVar(value="25")
        tk.Entry(delay_frame, textvariable=self.delay_max_var, width=5,
                 bg=COLORS["bg_light"], fg=COLORS["text"]).pack(side="left", padx=5)
        
        tk.Label(delay_frame, text="seconds", fg=COLORS["text_muted"],
                 bg=COLORS["bg_medium"]).pack(side="left", padx=5)
        
        # Presets
        preset_frame = tk.LabelFrame(control_frame, text="💾 Presets", fg=COLORS["accent"],
                                      bg=COLORS["bg_medium"], font=FONTS["small"])
        preset_frame.pack(fill="x", pady=5, padx=10)
        
        self.preset_combo = ttk.Combobox(preset_frame, width=25)
        self.preset_combo.pack(pady=5, padx=5)
        self.preset_combo.bind("<<ComboboxSelected>>", self._load_preset)
        
        preset_btn_frame = tk.Frame(preset_frame, bg=COLORS["bg_medium"])
        preset_btn_frame.pack(pady=5)
        
        tk.Button(preset_btn_frame, text="Save as Preset", command=self._save_preset,
                  bg=COLORS["info"], fg="white", padx=10).pack(side="left", padx=2)
        tk.Button(preset_btn_frame, text="Delete Preset", command=self._delete_preset,
                  bg=COLORS["error"], fg="white", padx=10).pack(side="left", padx=2)
        
        # Status bar
        self.status_bar = tk.Label(right_panel, text="Ready", relief=tk.SUNKEN, anchor=tk.W,
                                    bg=COLORS["bg_medium"], fg=COLORS["text_muted"])
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _load_data(self):
        """Load initial data"""
        self._load_message()
        self._update_stats_display()

    def _load_message(self):
        """Load saved message"""
        try:
            msg = load_message()
            self.message_text.delete(1.0, "end")
            self.message_text.insert(1.0, msg)
            self._update_char_counter()
        except Exception as e:
            log(f"Failed to load message: {e}", "error")

    def _save_message(self):
        """Save message to file"""
        try:
            msg = self.message_text.get(1.0, "end").strip()
            if not msg:
                messagebox.showwarning("Warning", "Message cannot be empty!")
                return
            
            save_message(msg)
            self.status_bar.config(text="Message saved")
            self.frame.after(2000, lambda: self.status_bar.config(text="Ready"))
            log("Message saved", "success")
        except Exception as e:
            log(f"Failed to save message: {e}", "error")
            messagebox.showerror("Error", f"Failed to save: {e}")

    def _update_char_counter(self, event=None):
        """Update character counter"""
        text = self.message_text.get(1.0, "end-1c")
        length = len(text)
        self.char_counter.config(text=f"{length} characters")
        
        # Warn if too long
        if length > 4000:
            self.char_counter.config(fg=COLORS["error"])
        elif length > 3500:
            self.char_counter.config(fg=COLORS["warning"])
        else:
            self.char_counter.config(fg=COLORS["text_muted"])

    def _insert_variable(self, var):
        """Insert variable at cursor position"""
        self.message_text.insert(tk.INSERT, var)

    def _copy_message(self):
        """Copy message to clipboard"""
        msg = self.message_text.get(1.0, "end-1c")
        if msg:
            self.frame.clipboard_clear()
            self.frame.clipboard_append(msg)
            self.status_bar.config(text="Copied to clipboard")
            self.frame.after(2000, lambda: self.status_bar.config(text="Ready"))

    def _show_templates(self):
        """Show message templates dialog"""
        templates = {
            "Promo": "🔥 PROMO TERBATAS! 🔥\n\nDapatkan diskon 50% hanya hari ini!\n\nKlik link: https://t.me/channel",
            "Info": "📢 INFO PENTING!\n\nUpdate terbaru sudah tersedia.\n\nCek sekarang: https://t.me/channel",
            "Welcome": "👋 SELAMAT DATANG!\n\nTerima kasih telah bergabung dengan komunitas kami.\n\nSilakan perkenalkan diri Anda!",
            "Announcement": "📢 ANNOUNCEMENT 📢\n\n{message}\n\nTerima kasih atas perhatiannya!",
            "Follow Up": "Hi! Just following up on our previous message.\n\nDid you have any questions?\n\nBest regards, {sender}"
        }
        
        dialog = tk.Toplevel(self.frame)
        dialog.title("Message Templates")
        dialog.geometry("500x400")
        dialog.configure(bg=COLORS["bg_dark"])
        dialog.transient(self.frame)
        dialog.grab_set()
        
        tk.Label(dialog, text="Select Template", font=FONTS["heading"],
                 fg=COLORS["accent"], bg=COLORS["bg_dark"]).pack(pady=10)
        
        listbox = tk.Listbox(dialog, bg=COLORS["bg_light"], fg=COLORS["text"],
                              font=FONTS["normal"], height=10)
        for name in templates.keys():
            listbox.insert(tk.END, name)
        listbox.pack(fill="both", expand=True, padx=20, pady=10)
        
        preview_text = scrolledtext.ScrolledText(dialog, height=8, bg=COLORS["bg_light"],
                                                   fg=COLORS["text"], font=FONTS["normal"])
        preview_text.pack(fill="both", expand=True, padx=20, pady=5)
        
        def on_select(event):
            selection = listbox.curselection()
            if selection:
                name = listbox.get(selection[0])
                template = templates[name]
                preview_text.delete(1.0, "end")
                preview_text.insert(1.0, template)
        
        listbox.bind("<<ListboxSelect>>", on_select)
        
        def load_template():
            selection = listbox.curselection()
            if selection:
                name = listbox.get(selection[0])
                template = templates[name]
                self.message_text.delete(1.0, "end")
                self.message_text.insert(1.0, template)
                dialog.destroy()
                self._update_char_counter()
        
        btn_frame = tk.Frame(dialog, bg=COLORS["bg_dark"])
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="Load", command=load_template,
                  bg=COLORS["success"], fg="white", padx=20).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancel", command=dialog.destroy,
                  bg=COLORS["error"], fg="white", padx=20).pack(side="left", padx=5)

    def _ai_generate(self):
        """Generate message with AI"""
        def generate():
            try:
                self.status_bar.config(text="AI generating message...")
                
                # Get topic from user
                topic = self._ask_topic()
                if not topic:
                    return
                
                # Get tone
                tone = self._ask_tone()
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(
                    ai_content.generate_broadcast(topic, "broadcast", tone, 100)
                )
                
                if result:
                    self.message_text.delete(1.0, "end")
                    self.message_text.insert(1.0, "\n\n".join(result[:3]))
                    self._update_char_counter()
                    self.status_bar.config(text="AI generated message")
                    log("AI generated message", "success")
                else:
                    self.status_bar.config(text="AI generation failed")
                    
            except Exception as e:
                log(f"AI generation error: {e}", "error")
                self.status_bar.config(text="AI generation error")
        
        threading.Thread(target=generate, daemon=True).start()

    def _ask_topic(self) -> str:
        """Ask for message topic"""
        return simpledialog.askstring("AI Topic", "What topic should the message be about?",
                                       parent=self.frame)

    def _ask_tone(self) -> str:
        """Ask for message tone"""
        tones = ["professional", "casual", "friendly", "urgent", "persuasif"]
        dialog = tk.Toplevel(self.frame)
        dialog.title("Select Tone")
        dialog.geometry("300x250")
        dialog.configure(bg=COLORS["bg_dark"])
        dialog.transient(self.frame)
        dialog.grab_set()
        
        result = ["professional"]
        
        tk.Label(dialog, text="Select Message Tone:", font=FONTS["heading"],
                 fg=COLORS["accent"], bg=COLORS["bg_dark"]).pack(pady=10)
        
        var = tk.StringVar(value="professional")
        for tone in tones:
            rb = tk.Radiobutton(dialog, text=tone.capitalize(), variable=var, value=tone,
                                bg=COLORS["bg_dark"], fg=COLORS["text"],
                                selectcolor=COLORS["bg_dark"])
            rb.pack(anchor="w", padx=30, pady=3)
        
        def confirm():
            result[0] = var.get()
            dialog.destroy()
        
        tk.Button(dialog, text="OK", command=confirm,
                  bg=COLORS["success"], fg="white", padx=20).pack(pady=15)
        
        dialog.wait_window()
        return result[0]

    def _rewrite_message(self):
        """Rewrite message to avoid spam"""
        def rewrite():
            msg = self.message_text.get(1.0, "end-1c").strip()
            if not msg:
                messagebox.showwarning("Warning", "Please enter a message first!")
                return
            
            self.status_bar.config(text="Rewriting message...")
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            rewritten = loop.run_until_complete(spam_detector.rewrite_message(msg))
            
            if rewritten and rewritten != msg:
                self.message_text.delete(1.0, "end")
                self.message_text.insert(1.0, rewritten)
                self._update_char_counter()
                self.status_bar.config(text="Message rewritten")
                log("Message rewritten to avoid spam", "success")
            else:
                self.status_bar.config(text="Message already looks good")
        
        threading.Thread(target=rewrite, daemon=True).start()

    def _load_presets(self):
        """Load saved presets"""
        preset_file = Path("data/broadcast_presets.json")
        if preset_file.exists():
            try:
                with open(preset_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for name, pdata in data.items():
                        self.presets[name] = BroadcastPreset(
                            name=name,
                            message=pdata.get("message", ""),
                            delay_min=pdata.get("delay_min", 10),
                            delay_max=pdata.get("delay_max", 25),
                            parallel=pdata.get("parallel", True),
                            anti_spam=pdata.get("anti_spam", True),
                            proxy=pdata.get("proxy", False),
                            schedule=pdata.get("schedule", "now")
                        )
                
                self.preset_combo['values'] = list(self.presets.keys())
                log(f"Loaded {len(self.presets)} presets", "debug")
            except Exception as e:
                log(f"Failed to load presets: {e}", "error")

    def _save_preset(self):
        """Save current settings as preset"""
        name = simpledialog.askstring("Save Preset", "Preset name:", parent=self.frame)
        if name:
            preset = BroadcastPreset(
                name=name,
                message=self.message_text.get(1.0, "end-1c").strip(),
                delay_min=int(self.delay_min_var.get() or 10),
                delay_max=int(self.delay_max_var.get() or 25),
                parallel=self.parallel_var.get(),
                anti_spam=self.antispam_var.get(),
                proxy=self.proxy_var.get(),
                schedule=self.schedule_var.get()
            )
            
            self.presets[name] = preset
            self.preset_combo['values'] = list(self.presets.keys())
            
            # Save to file
            preset_file = Path("data/broadcast_presets.json")
            preset_file.parent.mkdir(parents=True, exist_ok=True)
            data = {name: {
                "message": preset.message,
                "delay_min": preset.delay_min,
                "delay_max": preset.delay_max,
                "parallel": preset.parallel,
                "anti_spam": preset.anti_spam,
                "proxy": preset.proxy,
                "schedule": preset.schedule
            } for name, preset in self.presets.items()}
            
            with open(preset_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            self.status_bar.config(text=f"Preset '{name}' saved")
            log(f"Preset saved: {name}", "success")

    def _delete_preset(self):
        """Delete selected preset"""
        name = self.preset_combo.get()
        if name and name in self.presets:
            if messagebox.askyesno("Confirm", f"Delete preset '{name}'?"):
                del self.presets[name]
                self.preset_combo['values'] = list(self.presets.keys())
                self.preset_combo.set("")
                
                # Update file
                preset_file = Path("data/broadcast_presets.json")
                if preset_file.exists():
                    data = {n: {
                        "message": p.message,
                        "delay_min": p.delay_min,
                        "delay_max": p.delay_max,
                        "parallel": p.parallel,
                        "anti_spam": p.anti_spam,
                        "proxy": p.proxy,
                        "schedule": p.schedule
                    } for n, p in self.presets.items()}
                    with open(preset_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2)
                
                self.status_bar.config(text=f"Preset '{name}' deleted")
                log(f"Preset deleted: {name}", "warning")

    def _load_preset(self, event=None):
        """Load selected preset"""
        name = self.preset_combo.get()
        if name in self.presets:
            preset = self.presets[name]
            self.message_text.delete(1.0, "end")
            self.message_text.insert(1.0, preset.message)
            self.delay_min_var.set(str(preset.delay_min))
            self.delay_max_var.set(str(preset.delay_max))
            self.parallel_var.set(preset.parallel)
            self.antispam_var.set(preset.anti_spam)
            self.proxy_var.set(preset.proxy)
            self.schedule_var.set(preset.schedule)
            self._update_char_counter()
            self.status_bar.config(text=f"Loaded preset: {name}")
            log(f"Loaded preset: {name}", "info")

    def _start_stats_updater(self):
        """Start background stats updater"""
        def update():
            while True:
                try:
                    self._update_stats_display()
                    time.sleep(2)
                except:
                    pass
        
        threading.Thread(target=update, daemon=True).start()

    def _update_stats_display(self):
        """Update statistics display"""
        try:
            groups = load_groups()
            accounts = load_accounts()
            stats = parallel_broadcast.get_stats()
            
            sent = stats.get("total_sent", 0)
            failed = stats.get("total_failed", 0)
            total = sent + failed
            rate = (sent / total * 100) if total > 0 else 0
            
            self.groups_label.config(text=f"Groups: {len(groups)}")
            self.accounts_label.config(text=f"Accounts: {len(accounts)}")
            self.sent_label.config(text=f"Sent: {sent}")
            self.failed_label.config(text=f"Failed: {failed}")
            self.rate_label.config(text=f"Rate: {rate:.1f}%")
            
            # Calculate speed (messages per minute)
            if self.stats.last_message_time and sent > 0:
                elapsed = (datetime.now() - self.stats.start_time).total_seconds() if self.stats.start_time else 60
                speed = (sent / elapsed) * 60
                self.speed_label.config(text=f"Speed: {speed:.1f} msg/min")
            
            # Update progress
            if self.running and self.stats.total_groups > 0:
                progress = (sent / self.stats.total_groups) * 100
                self.progress['value'] = min(100, progress)
                
        except Exception as e:
            pass

    def _start_broadcast(self):
        """Start broadcast"""
        # Get message
        msg = self.message_text.get(1.0, "end-1c").strip()
        if not msg:
            messagebox.showwarning("Warning", "Please enter a message!")
            return
        
        # Check if engine is initialized
        from core.engine import broadcast_engine
        if not broadcast_engine.clients:
            messagebox.showwarning("Warning", "Accounts not initialized!\n\nClick 'INIT ACCOUNTS' first.")
            return
        
        # Save message
        save_message(msg)
        
        # Apply anti-spam if enabled
        if self.antispam_var.get():
            score = spam_detector.detect_spam_score(msg)
            if score > 0.3:
                if not messagebox.askyesno("Spam Warning", 
                    f"Spam Score: {score:.0%}\n\nYour message may be flagged as spam.\nContinue anyway?"):
                    return
        
        # Set mode
        from core.smart_loop import smart_loop
        mode = self.mode_var.get()
        smart_loop.set_mode(mode)
        
        # Set delays
        min_delay = int(self.delay_min_var.get() or 10)
        max_delay = int(self.delay_max_var.get() or 25)
        
        # Set parallel
        if self.parallel_var.get():
            parallel_broadcast.message = msg
        else:
            broadcast_engine.set_message(msg)
        
        # Update state
        self.running = True
        self.paused = False
        self.stats = BroadcastStats()
        self.stats.start_time = datetime.now()
        self.stats.total_groups = len(load_groups())
        self.stats.total_accounts = len(load_accounts())
        
        # Update UI
        self.start_btn.config(state="disabled")
        self.pause_btn.config(state="normal")
        self.stop_btn.config(state="normal")
        self.status_text.config(text="Broadcasting...", fg=COLORS["warning"])
        self.status_indicator.config(text="🟢", fg=COLORS["success"])
        self.progress['value'] = 0
        
        # Start broadcast thread
        def run():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                if self.parallel_var.get():
                    result = loop.run_until_complete(parallel_broadcast.run_parallel())
                    sent = result.get("sent", 0)
                else:
                    sent = loop.run_until_complete(broadcast_engine.run())
                
                self.frame.after(0, lambda: self._broadcast_complete(sent))
                
            except Exception as e:
                log(f"Broadcast error: {e}", "error")
                self.frame.after(0, lambda: self._broadcast_error(str(e)))
        
        threading.Thread(target=run, daemon=True).start()
        
        # Update stats
        self._update_stats_display()
        log("Broadcast started", "success")
        
        # Send notification
        notification_manager.send_notification(
            "Broadcast Started",
            f"Broadcast started with {self.stats.total_groups} groups",
            "info"
        )

    def _pause_broadcast(self):
        """Pause broadcast"""
        if self.running and not self.paused:
            if self.parallel_var.get():
                parallel_broadcast.pause()
            else:
                from core.engine import broadcast_engine
                broadcast_engine.pause()
            
            self.paused = True
            self.pause_btn.config(text="▶ Resume", command=self._resume_broadcast)
            self.status_text.config(text="Paused", fg=COLORS["warning"])
            self.status_indicator.config(text="🟡", fg=COLORS["warning"])
            log("Broadcast paused", "warning")

    def _resume_broadcast(self):
        """Resume broadcast"""
        if self.running and self.paused:
            if self.parallel_var.get():
                parallel_broadcast.resume()
            else:
                from core.engine import broadcast_engine
                broadcast_engine.resume()
            
            self.paused = False
            self.pause_btn.config(text="⏸️ PAUSE", command=self._pause_broadcast)
            self.status_text.config(text="Broadcasting...", fg=COLORS["warning"])
            self.status_indicator.config(text="🟢", fg=COLORS["success"])
            log("Broadcast resumed", "success")

    def _stop_broadcast(self):
        """Stop broadcast"""
        if self.running:
            if self.parallel_var.get():
                parallel_broadcast.stop()
            else:
                from core.engine import broadcast_engine
                broadcast_engine.stop()
            
            self.running = False
            self.paused = False
            
            self.start_btn.config(state="normal")
            self.pause_btn.config(state="disabled")
            self.stop_btn.config(state="disabled")
            self.status_text.config(text="Stopped", fg=COLORS["error"])
            self.status_indicator.config(text="⚪", fg="gray")
            self.progress['value'] = 0
            
            log("Broadcast stopped", "warning")
            
            notification_manager.send_notification(
                "Broadcast Stopped",
                "Broadcast has been stopped manually",
                "warning"
            )

    def _broadcast_complete(self, sent):
        """Handle broadcast completion"""
        self.running = False
        self.paused = False
        
        self.start_btn.config(state="normal")
        self.pause_btn.config(state="disabled")
        self.stop_btn.config(state="disabled")
        self.status_text.config(text="Completed", fg=COLORS["success"])
        self.status_indicator.config(text="✅", fg=COLORS["success"])
        self.progress['value'] = 100
        
        duration = (datetime.now() - self.stats.start_time).total_seconds() if self.stats.start_time else 0
        speed = sent / (duration / 60) if duration > 0 else 0
        
        log(f"Broadcast completed: {sent} messages sent in {duration/60:.1f} minutes ({speed:.1f} msg/min)", "success")
        
        # Send notification
        if self.notify_on_complete:
            notification_manager.send_notification(
                "Broadcast Completed",
                f"Sent {sent} messages to {self.stats.total_groups} groups\nSpeed: {speed:.1f} msg/min",
                "success"
            )
        
        # Record statistics
        statistics.record_broadcast(True, None)
        
        # Update graph
        for _ in range(sent):
            graph_manager.record_send()

    def _broadcast_error(self, error):
        """Handle broadcast error"""
        self.running = False
        self.paused = False
        
        self.start_btn.config(state="normal")
        self.pause_btn.config(state="disabled")
        self.stop_btn.config(state="disabled")
        self.status_text.config(text="Error", fg=COLORS["error"])
        self.status_indicator.config(text="🔴", fg=COLORS["error"])
        
        log(f"Broadcast error: {error}", "error")
        
        notification_manager.send_notification(
            "Broadcast Error",
            f"Broadcast failed: {error[:100]}",
            "error"
        )

    def _load_template(self):
        """Load message template"""
        self._show_templates()

    def _refresh_data(self):
        """Refresh all data"""
        self._update_stats_display()
        self.status_bar.config(text="Data refreshed")
        self.frame.after(2000, lambda: self.status_bar.config(text="Ready"))

# Register this tab
BroadcastTab = BroadcastUltimate