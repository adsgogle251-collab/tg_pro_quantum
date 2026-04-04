"""Broadcast Tab - SIMPLE with VISIBLE Buttons"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import asyncio
import time
from datetime import datetime
from core import log, load_message, save_message, load_groups, statistics, campaign_manager, account_manager
from core.engine import broadcast_engine
from core import broadcast_history
from core.state_manager import state_manager
from core.localization import t
from gui.styles import COLORS, FONTS

class BroadcastTab:
    title = "📢 Siaran"
    
    def __init__(self, parent, main_window=None):
        self.parent = parent
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        self.running = False
        self.paused = False
        self.current_campaign_id = None
        self._broadcast_start_time = None
        
        self._create_widgets()
        self._load_message()
        self._load_broadcast_groups()
        self._load_campaigns()
        
        # Listen for account assignment changes to refresh groups
        state_manager.on_state_change("account_assigned", self._on_account_changed)
        state_manager.on_state_change("refresh_all", self._on_refresh_all)
    
    def _on_account_changed(self, data=None):
        """Called when account assignments change"""
        try:
            self._load_broadcast_groups()
        except Exception:
            pass
    
    def _on_refresh_all(self, data=None):
        """Called on global refresh"""
        try:
            self._load_broadcast_groups()
            self._load_campaigns()
        except Exception:
            pass
    
    def _create_widgets(self):
        # ═══════════════════════════════════════════════════
        # TOP SECTION - All controls visible
        # ═══════════════════════════════════════════════════
        top_frame = tk.Frame(self.frame, bg="#1a1a2e")
        top_frame.pack(fill="x", padx=10, pady=10)
        
        # ───────────────────────────────────────────────────
        # LEFT: Campaign & Message
        # ───────────────────────────────────────────────────
        left_frame = tk.LabelFrame(top_frame, text=f"📝 {t('Message')}", 
                                    bg="#0f3460", fg="#00d9ff",
                                    font=("Segoe UI", 12, "bold"))
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        # Campaign
        tk.Label(left_frame, text=f"{t('Campaign')}:", bg="#0f3460", fg="#ffffff").pack(anchor="w", padx=10, pady=5)
        self.campaign_var = tk.StringVar(value="")
        self.campaign_combo = ttk.Combobox(left_frame, textvariable=self.campaign_var, width=40)
        self.campaign_combo.pack(fill="x", padx=10, pady=5)
        self.campaign_combo.bind("<<ComboboxSelected>>", self._on_campaign_select)
        
        # Message text
        self.message_text = scrolledtext.ScrolledText(left_frame, height=8, bg="#1a1a2e", fg="#ffffff", font=("Consolas", 11))
        self.message_text.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Save/Load buttons
        btn_fr = tk.Frame(left_frame, bg="#0f3460")
        btn_fr.pack(pady=5)
        tk.Button(btn_fr, text=f"💾 {t('Save')}", command=self._save_message, bg="#00d9ff", fg="#000000", width=15).pack(side="left", padx=5)
        tk.Button(btn_fr, text=f"📂 {t('Load')}", command=self._load_message, bg="#ff6b6b", fg="#ffffff", width=15).pack(side="left", padx=5)
        
        # ───────────────────────────────────────────────────
        # RIGHT: Settings (Account Group, Target, Delay)
        # ───────────────────────────────────────────────────
        right_frame = tk.LabelFrame(top_frame, text=f"⚙️ {t('Settings')}", 
                                     bg="#0f3460", fg="#00d9ff",
                                     font=("Segoe UI", 12, "bold"))
        right_frame.pack(side="right", fill="y", padx=(5, 0))
        
        # Account Group
        tk.Label(right_frame, text=f"📱 {t('Account Group')}:", bg="#0f3460", fg="#ffffff", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=(10,5))
        self.group_var = tk.StringVar(value=t("All Accounts"))
        self.group_combo = ttk.Combobox(right_frame, textvariable=self.group_var, width=25)
        self.group_combo.pack(padx=10, pady=5)
        self.group_combo.bind("<<ComboboxSelected>>", lambda e: self._on_group_select())
        
        self.acc_count_lbl = tk.Label(right_frame, text="0 akun", bg="#0f3460", fg="#888888")
        self.acc_count_lbl.pack(pady=5)
        
        # Target Groups
        tk.Label(right_frame, text=f"🎯 {t('Target Groups')}:", bg="#0f3460", fg="#ffffff", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=(10,5))
        self.mode_var = tk.StringVar(value="joined")
        tk.Radiobutton(right_frame, text=t("Joined Groups"), variable=self.mode_var, value="joined", bg="#0f3460", fg="#ffffff", selectcolor="#00d9ff").pack(anchor="w", padx=20, pady=2)
        tk.Radiobutton(right_frame, text=t("Custom List"), variable=self.mode_var, value="custom", bg="#0f3460", fg="#ffffff", selectcolor="#00d9ff").pack(anchor="w", padx=20, pady=2)
        
        # Delay
        tk.Label(right_frame, text=f"⏱️ {t('Delay (seconds)')}:", bg="#0f3460", fg="#ffffff", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=(10,5))
        delay_fr = tk.Frame(right_frame, bg="#0f3460")
        delay_fr.pack(padx=10, pady=5)
        self.delay_min = tk.Entry(delay_fr, width=5, bg="#1a1a2e", fg="#ffffff")
        self.delay_min.insert(0, "10")
        self.delay_min.pack(side="left", padx=5)
        tk.Label(delay_fr, text="-", bg="#0f3460", fg="#ffffff").pack(side="left")
        self.delay_max = tk.Entry(delay_fr, width=5, bg="#1a1a2e", fg="#ffffff")
        self.delay_max.insert(0, "30")
        self.delay_max.pack(side="left", padx=5)
        
        # Round Robin
        self.round_robin_var = tk.BooleanVar(value=True)
        tk.Checkbutton(right_frame, text=f"🔄 {t('Round-Robin')}", variable=self.round_robin_var, bg="#0f3460", fg="#ffffff", selectcolor="#00d9ff").pack(anchor="w", padx=10, pady=5)
        
        # ═══════════════════════════════════════════════════
        # MIDDLE: Progress Detail
        # ═══════════════════════════════════════════════════
        mid_frame = tk.LabelFrame(self.frame, text="📊 Progress Langsung", 
                                   bg="#0f3460", fg="#00d9ff",
                                   font=("Segoe UI", 12, "bold"))
        mid_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.progress_tree = ttk.Treeview(mid_frame, columns=("Time", "Account", "Group", "Status"), show="headings", height=8)
        self.progress_tree.heading("Time", text="Time")
        self.progress_tree.heading("Account", text="Account")
        self.progress_tree.heading("Group", text="Group")
        self.progress_tree.heading("Status", text="Status")
        self.progress_tree.column("Time", width=70)
        self.progress_tree.column("Account", width=100)
        self.progress_tree.column("Group", width=300)
        self.progress_tree.column("Status", width=80)
        self.progress_tree.pack(fill="both", expand=True, padx=10, pady=5)
        
        # ═══════════════════════════════════════════════════
        # BOTTOM: Control Panel with BIG VISIBLE BUTTONS
        # ═══════════════════════════════════════════════════
        bottom_frame = tk.Frame(self.frame, bg="#0f3460", height=150)
        bottom_frame.pack(fill="x", padx=10, pady=10)
        bottom_frame.pack_propagate(False)
        
        # Stats
        stats_fr = tk.Frame(bottom_frame, bg="#0f3460")
        stats_fr.pack(fill="x", padx=20, pady=10)
        
        self.sent_lbl = tk.Label(stats_fr, text="✅ Sent: 0", bg="#0f3460", fg="#00ff00", font=("Segoe UI", 14, "bold"))
        self.sent_lbl.pack(side="left", padx=20)
        
        self.fail_lbl = tk.Label(stats_fr, text="❌ Failed: 0", bg="#0f3460", fg="#ff0000", font=("Segoe UI", 14, "bold"))
        self.fail_lbl.pack(side="left", padx=20)

        self.rate_lbl = tk.Label(stats_fr, text="📊 Rate: —", bg="#0f3460", fg="#00d9ff", font=("Segoe UI", 14, "bold"))
        self.rate_lbl.pack(side="left", padx=20)

        self.active_acc_lbl = tk.Label(stats_fr, text="📱 Active: —", bg="#0f3460", fg="#ffaa00", font=("Segoe UI", 11))
        self.active_acc_lbl.pack(side="left", padx=20)
        
        # Progress bar
        prog_fr = tk.Frame(bottom_frame, bg="#0f3460")
        prog_fr.pack(fill="x", padx=20, pady=5)
        
        tk.Label(prog_fr, text="Progress:", bg="#0f3460", fg="#ffffff").pack(side="left", padx=10)
        self.progress = ttk.Progressbar(prog_fr, mode='determinate', length=400)
        self.progress.pack(side="left", padx=10, fill="x", expand=True)
        self.prog_lbl = tk.Label(prog_fr, text="0%", bg="#0f3460", fg="#888888", width=6)
        self.prog_lbl.pack(side="left", padx=10)
        
        # ═══════════════════════════════════════════════════
        # BIG VISIBLE BUTTONS - PASTI TERLIHAT!
        # ═══════════════════════════════════════════════════
        btn_fr = tk.Frame(bottom_frame, bg="#0f3460")
        btn_fr.pack(fill="x", padx=20, pady=15)
        
        # START BUTTON - BIG GREEN
        self.start_btn = tk.Button(btn_fr, text="▶ START BROADCAST", 
                                    command=self._start_broadcast,
                                    bg="#00ff00", fg="#000000", 
                                    font=("Segoe UI", 16, "bold"),
                                    padx=50, pady=15,
                                    activebackground="#00cc00",
                                    activeforeground="#000000")
        self.start_btn.pack(side="left", padx=10)
        
        # PAUSE BUTTON - BIG ORANGE
        self.pause_btn = tk.Button(btn_fr, text="⏸️ PAUSE", 
                                    command=self._pause_broadcast,
                                    bg="#ffaa00", fg="#000000", 
                                    font=("Segoe UI", 16, "bold"),
                                    padx=40, pady=15,
                                    state="disabled",
                                    activebackground="#ff8800",
                                    activeforeground="#000000")
        self.pause_btn.pack(side="left", padx=10)
        
        # STOP BUTTON - BIG RED
        self.stop_btn = tk.Button(btn_fr, text="⏹️ STOP", 
                                   command=self._stop_broadcast,
                                   bg="#ff0000", fg="#ffffff", 
                                   font=("Segoe UI", 16, "bold"),
                                   padx=40, pady=15,
                                   state="disabled",
                                   activebackground="#cc0000",
                                   activeforeground="#ffffff")
        self.stop_btn.pack(side="left", padx=10)
    
    # ═══════════════════════════════════════════════════════
    # HELPER METHODS
    # ═══════════════════════════════════════════════════════
    def _load_campaigns(self):
        try:
            camps = campaign_manager.get_all_campaigns()
            self.campaign_combo['values'] = [""] + [f"{c.name} ({c.id})" for c in camps]
        except: pass
    
    def _on_campaign_select(self, e=None):
        sel = self.campaign_var.get()
        if not sel: return
        try:
            cid = sel.split(" (")[1].rstrip(")")
            camp = campaign_manager.get_campaign(cid)
            if camp:
                self.message_text.delete(1.0, "end")
                self.message_text.insert(1.0, camp.message.text)
        except: pass
    
    def _load_broadcast_groups(self):
        try:
            groups = account_manager.load_groups()
            # Include "Assigned (Broadcast)" as first option for auto-loaded accounts
            assigned = account_manager.get_accounts_by_feature("broadcast")
            group_list = []
            if assigned:
                group_list.append(f"Assigned ({len(assigned)})")
            group_list += ["All Accounts"] + list(groups.keys())
            self.group_combo['values'] = group_list
            if assigned and hasattr(self, 'group_var') and not self.group_var.get():
                self.group_var.set(f"Assigned ({len(assigned)})")
            self._on_group_select()
        except Exception as e:
            log(f"Error loading groups: {e}", "error")

    def refresh_assigned_accounts(self):
        """Refresh account dropdown from feature assignments - called on tab focus."""
        self._load_broadcast_groups()

    def _on_tab_selected(self):
        """Called by main_window when this tab is selected."""
        self.refresh_assigned_accounts()
        self._load_campaigns()

    def _on_group_select(self, e=None):
        grp = self.group_var.get()
        try:
            if grp.startswith("Assigned"):
                accounts = account_manager.get_accounts_by_feature("broadcast")
                cnt = len(accounts)
            elif grp == "All Accounts":
                cnt = len(account_manager.get_all())
            elif grp == "📢 Akun Siaran":
                cnt = len(account_manager.get_accounts_by_feature("broadcast"))
            else:
                cnt = len(account_manager.get_group_accounts(grp))
            self.acc_count_lbl.config(text=f"{cnt} akun" + (" ✅" if cnt > 0 else " ⚠️"))
        except:
            self.acc_count_lbl.config(text="0 akun ⚠️")
    
    def _load_message(self):
        try:
            msg = load_message()
            self.message_text.delete(1.0, "end")
            self.message_text.insert(1.0, msg)
        except: pass
    
    def _save_message(self):
        msg = self.message_text.get(1.0, "end-1c").strip()
        if not msg:
            messagebox.showwarning("Warning", "Message empty!")
            return
        save_message(msg)
        messagebox.showinfo("Success", "Message saved!")
    
    def _add_entry(self, account, group, status):
        ts = time.strftime("%H:%M:%S")
        icon = "✅" if status == "success" else "❌"
        # Insert newest first
        self.progress_tree.insert("", 0, values=(ts, account[:15], group[:40], icon))
        if status == "success":
            c = int(self.sent_lbl.cget("text").split(": ")[1])
            self.sent_lbl.config(text=f"✅ Sent: {c+1}")
        else:
            c = int(self.fail_lbl.cget("text").split(": ")[1])
            self.fail_lbl.config(text=f"❌ Failed: {c+1}")
    
    def _on_broadcast_progress(self, **kwargs):
        sent = kwargs.get('sent', 0)
        failed = kwargs.get('failed', 0)
        total = kwargs.get('total', 1)
        cur_grp = kwargs.get('current_group', '')
        cur_acc = kwargs.get('current_account', '')
        prog = kwargs.get('progress_percent', 0)
        done = kwargs.get('completed', False)
        err = kwargs.get('error')
        
        self.sent_lbl.config(text=f"✅ Sent: {sent}")
        self.fail_lbl.config(text=f"❌ Failed: {failed}")

        # Live success rate
        total_attempts = sent + failed
        rate = round(sent / total_attempts * 100, 1) if total_attempts > 0 else 0.0
        rate_color = "#00ff00" if rate >= 90 else "#ffaa00" if rate >= 70 else "#ff4444"
        self.rate_lbl.config(text=f"📊 Rate: {rate}%", fg=rate_color)

        # Active account display
        if cur_acc:
            self.active_acc_lbl.config(text=f"📱 Active: {cur_acc[:20]}")
        
        if total > 0:
            self.progress['value'] = min(100, prog)
            self.prog_lbl.config(text=f"{prog:.1f}%")
        
        if cur_acc and cur_grp:
            self._add_entry(cur_acc, cur_grp, "failed" if err else "success")
        
        if done:
            self.running = False
            self.start_btn.config(state="normal")
            self.pause_btn.config(state="disabled", text="⏸️ PAUSE")
            self.stop_btn.config(state="disabled")
            self.active_acc_lbl.config(text="📱 Active: —")
            messagebox.showinfo("Complete", f"Sent: {sent}\nFailed: {failed}\nSuccess Rate: {rate}%")
    
    def _start_broadcast(self):
        msg = self.message_text.get(1.0, "end-1c").strip()
        if not msg:
            messagebox.showwarning("Warning", "Enter message!")
            return
        
        grp = self.group_var.get()
        if grp.startswith("Assigned"):
            accs = [a['name'] for a in account_manager.get_accounts_by_feature("broadcast")]
        elif grp == "All Accounts":
            accs = [a['name'] for a in account_manager.get_all()]
        elif grp == "📢 Akun Siaran":
            accs = [a['name'] for a in account_manager.get_accounts_by_feature("broadcast")]
        else:
            accs = account_manager.get_group_accounts(grp)
        
        if not accs:
            messagebox.showwarning("Warning", "No accounts!")
            return
        
        grps = load_groups()
        if not grps:
            messagebox.showwarning("Warning", "No target groups!\n\nUse Finder tab first.")
            return
        
        save_message(msg)
        self.running = True
        self.paused = False
        self._broadcast_start_time = datetime.now()
        self.start_btn.config(state="disabled")
        self.pause_btn.config(state="normal")
        self.stop_btn.config(state="normal")
        
        # Reset stats display
        self.sent_lbl.config(text="✅ Sent: 0")
        self.fail_lbl.config(text="❌ Failed: 0")
        self.rate_lbl.config(text="📊 Rate: —", fg="#00d9ff")
        self.progress['value'] = 0
        self.prog_lbl.config(text="0%")
        for item in self.progress_tree.get_children():
            self.progress_tree.delete(item)
        
        log(f"📢 BROADCAST STARTED: {len(accs)} accounts, {len(grps)} groups", "success")
        
        def cb(**kw):
            self.frame.after(0, lambda: self._on_broadcast_progress(**kw))
        
        def run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    broadcast_engine.run(
                        campaign_id=self.current_campaign_id,
                        accounts=accs, message=msg, groups=grps,
                        delay_min=int(self.delay_min.get()),
                        delay_max=int(self.delay_max.get()),
                        round_robin=self.round_robin_var.get(),
                        progress_callback=cb
                    )
                )
            except Exception as e:
                log(f"Error: {e}", "error")
                self.frame.after(0, lambda: self._on_broadcast_progress(error=str(e)))
            finally:
                loop.close()
        
        threading.Thread(target=run, daemon=True).start()
        # Start auto-refresh monitor (updates live stats every second)
        self._auto_refresh_monitor()

    def _auto_refresh_monitor(self):
        """Auto-refresh live stats every second while broadcast is running."""
        if not self.running:
            return
        # Scroll progress tree to top (newest entry)
        children = self.progress_tree.get_children()
        if children:
            self.progress_tree.see(children[0])
        self.frame.after(1000, self._auto_refresh_monitor)
    
    def _pause_broadcast(self):
        if self.running and not self.paused:
            self.paused = True
            self.pause_btn.config(text="▶ RESUME", command=self._resume_broadcast)
    
    def _resume_broadcast(self):
        if self.running and self.paused:
            self.paused = False
            self.pause_btn.config(text="⏸️ PAUSE", command=self._pause_broadcast)
    
    def _stop_broadcast(self):
        self.running = False
        self.paused = False
        self.start_btn.config(state="normal")
        self.pause_btn.config(state="disabled", text="⏸️ PAUSE")
        self.stop_btn.config(state="disabled")
    
    def _refresh(self):
        self._load_message()
        self._load_broadcast_groups()
        self._load_campaigns()