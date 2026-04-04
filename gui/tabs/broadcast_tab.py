"""Broadcast Tab - Phase 3 Redesign with Campaign List & Detail View"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
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
from gui.pages.broadcast_detail_page import BroadcastDetailPage

# ── colour aliases ─────────────────────────────────────────────────────────
BG    = COLORS["bg_dark"]
PANEL = COLORS["bg_medium"]
CARD  = COLORS["bg_light"]
CYAN  = COLORS["primary"]
GREEN = COLORS["success"]
ORANGE = COLORS["warning"]
RED   = COLORS["error"]
TEXT  = COLORS["text"]
MUTED = COLORS["text_muted"]

# Campaign status display map
STATUS_DISPLAY = {
    "running":   ("▶️ Run",   GREEN),
    "paused":    ("⏸️ Pause", ORANGE),
    "completed": ("✅ Done",  GREEN),
    "failed":    ("❌ Failed", RED),
    "draft":     ("📝 Draft",  MUTED),
    "scheduled": ("🕐 Sched", CYAN),
}


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
        self._campaigns: list = []      # cached campaign list
        self._detail_page = None        # BroadcastDetailPage instance
        
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

    # ─────────────────────────────────────────────────────────────────────────
    # PHASE 3A: CAMPAIGN LIST SECTION
    # ─────────────────────────────────────────────────────────────────────────

    def _build_campaign_list_section(self):
        """Build the Phase 3 campaign list with client filter."""
        outer = tk.Frame(self.frame, bg=PANEL)
        outer.pack(fill="x", padx=10, pady=6)

        # ── Header row ────────────────────────────────────────────────────────
        hdr = tk.Frame(outer, bg=PANEL)
        hdr.pack(fill="x", padx=10, pady=6)

        tk.Label(hdr, text="📢 BROADCAST CAMPAIGNS",
                 font=FONTS["heading"], fg=CYAN, bg=PANEL).pack(side="left")

        btn_fr = tk.Frame(hdr, bg=PANEL)
        btn_fr.pack(side="right")

        tk.Button(btn_fr, text="+ New Campaign",
                  command=self._open_create_modal,
                  bg=GREEN, fg="#000", font=FONTS["small"],
                  relief="flat", cursor="hand2", padx=8, pady=4).pack(side="left", padx=4)

        tk.Button(btn_fr, text="🔄 Refresh",
                  command=self._load_campaigns,
                  bg=CARD, fg=CYAN, font=FONTS["small"],
                  relief="flat", cursor="hand2", padx=8, pady=4).pack(side="left", padx=4)

        # ── Filter row ────────────────────────────────────────────────────────
        flt = tk.Frame(outer, bg=PANEL)
        flt.pack(fill="x", padx=10, pady=4)

        tk.Label(flt, text="Filter Client:", fg=MUTED, bg=PANEL,
                 font=FONTS["small"]).pack(side="left", padx=5)
        self._filter_client_var = tk.StringVar(value="All Clients")
        self._filter_client_cb = ttk.Combobox(
            flt, textvariable=self._filter_client_var,
            values=["All Clients"], width=22, state="readonly"
        )
        self._filter_client_cb.pack(side="left", padx=5)
        self._filter_client_cb.bind("<<ComboboxSelected>>", lambda e: self._apply_campaign_filter())

        tk.Label(flt, text="Status:", fg=MUTED, bg=PANEL,
                 font=FONTS["small"]).pack(side="left", padx=10)
        self._filter_status_var = tk.StringVar(value="All")
        status_cb = ttk.Combobox(
            flt, textvariable=self._filter_status_var,
            values=["All", "running", "paused", "completed", "failed", "draft", "scheduled"],
            width=12, state="readonly"
        )
        status_cb.pack(side="left", padx=5)
        status_cb.bind("<<ComboboxSelected>>", lambda e: self._apply_campaign_filter())

        tk.Label(flt, text="Search:", fg=MUTED, bg=PANEL,
                 font=FONTS["small"]).pack(side="left", padx=10)
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._apply_campaign_filter())
        tk.Entry(flt, textvariable=self._search_var,
                 bg=CARD, fg=TEXT, insertbackground=CYAN,
                 width=20).pack(side="left", padx=5)

        # ── Campaign tree ─────────────────────────────────────────────────────
        tbl_frame = tk.Frame(outer, bg=PANEL)
        tbl_frame.pack(fill="x", padx=10, pady=4)

        cols = ("Campaign", "Client", "Status", "Progress", "Msgs")
        self._camp_tree = ttk.Treeview(
            tbl_frame, columns=cols, show="headings", height=5
        )
        col_widths = {"Campaign": 180, "Client": 140, "Status": 90, "Progress": 120, "Msgs": 100}
        for col in cols:
            self._camp_tree.heading(col, text=col)
            self._camp_tree.column(col, width=col_widths.get(col, 120), anchor="w")

        tree_scroll = ttk.Scrollbar(tbl_frame, orient="vertical",
                                     command=self._camp_tree.yview)
        self._camp_tree.configure(yscrollcommand=tree_scroll.set)
        tree_scroll.pack(side="right", fill="y")
        self._camp_tree.pack(fill="x")
        self._camp_tree.bind("<Double-1>", self._on_campaign_double_click)

        # Tag colours
        self._camp_tree.tag_configure("running",   foreground=GREEN)
        self._camp_tree.tag_configure("paused",    foreground=ORANGE)
        self._camp_tree.tag_configure("completed", foreground=CYAN)
        self._camp_tree.tag_configure("failed",    foreground=RED)

        # ── Action row ────────────────────────────────────────────────────────
        act = tk.Frame(outer, bg=PANEL)
        act.pack(fill="x", padx=10, pady=4)

        for lbl, cmd, color in [
            ("👁 View",   self._view_campaign,  CYAN),
            ("⏸ Pause",  self._pause_selected,  ORANGE),
            ("▶ Resume", self._resume_selected, GREEN),
            ("■ Stop",   self._stop_selected,   RED),
        ]:
            tk.Button(act, text=lbl, command=cmd,
                      bg=CARD, fg=color, font=FONTS["small"],
                      relief="flat", cursor="hand2",
                      padx=8, pady=4).pack(side="left", padx=4)

    # ── Campaign list helpers ─────────────────────────────────────────────────

    def _populate_campaign_tree(self, campaigns: list):
        """Populate the campaign treeview from a list of campaign objects/dicts."""
        for row in self._camp_tree.get_children():
            self._camp_tree.delete(row)

        client_set = {"All Clients"}
        for c in campaigns:
            if hasattr(c, "__dict__"):
                d = c.__dict__
            elif isinstance(c, dict):
                d = c
            else:
                continue

            name   = d.get("name", "?")
            client = d.get("client_name", d.get("client_id", "—"))
            status = d.get("status", "draft")
            if hasattr(status, "value"):
                status = status.value
            sent   = d.get("sent_count", 0)
            total  = d.get("total_targets", 0)
            pct    = round(sent / total * 100, 0) if total else 0
            prog   = f"{pct:.0f}% ({sent}/{total})"
            msgs   = f"{sent}/{total}"

            status_txt, _ = STATUS_DISPLAY.get(status, (status, TEXT))
            tag = status if status in STATUS_DISPLAY else "draft"

            client_set.add(str(client))
            self._camp_tree.insert(
                "", "end",
                iid=str(d.get("id", "")),
                values=(name, str(client), status_txt, prog, msgs),
                tags=(tag,),
            )

        # Update client filter dropdown
        existing = list(client_set)
        self._filter_client_cb.configure(values=sorted(existing))

    def _apply_campaign_filter(self):
        """Re-filter the displayed campaigns based on filter controls."""
        if not self._campaigns:
            return
        client_filter = self._filter_client_var.get()
        status_filter = self._filter_status_var.get()
        search = self._search_var.get().lower().strip()

        filtered = []
        for c in self._campaigns:
            d = c.__dict__ if hasattr(c, "__dict__") else (c if isinstance(c, dict) else {})
            name   = str(d.get("name", "")).lower()
            client = str(d.get("client_name", d.get("client_id", "")))
            status = d.get("status", "draft")
            if hasattr(status, "value"):
                status = status.value

            if client_filter != "All Clients" and client != client_filter:
                continue
            if status_filter != "All" and status != status_filter:
                continue
            if search and search not in name and search not in client.lower():
                continue
            filtered.append(c)

        self._populate_campaign_tree(filtered)

    def _view_campaign(self):
        """Open the BroadcastDetailPage for the selected campaign."""
        sel = self._camp_tree.selection()
        if not sel:
            messagebox.showinfo("Select", "Select a campaign first.")
            return
        cid = sel[0]
        campaign_data = self._get_campaign_dict(cid)
        self._open_detail_page(campaign_data)

    def _on_campaign_double_click(self, _event):
        self._view_campaign()

    def _pause_selected(self):
        sel = self._camp_tree.selection()
        if not sel:
            return
        log(f"Pause campaign {sel[0]}", "info")
        messagebox.showinfo("Pause", f"Campaign {sel[0]} pause requested.")

    def _resume_selected(self):
        sel = self._camp_tree.selection()
        if not sel:
            return
        log(f"Resume campaign {sel[0]}", "info")
        messagebox.showinfo("Resume", f"Campaign {sel[0]} resume requested.")

    def _stop_selected(self):
        sel = self._camp_tree.selection()
        if not sel:
            return
        if messagebox.askyesno("Stop", f"Stop campaign {sel[0]}?"):
            log(f"Stop campaign {sel[0]}", "warning")

    def _get_campaign_dict(self, campaign_id: str) -> dict:
        """Return a dict for the given campaign id from cache."""
        for c in self._campaigns:
            d = c.__dict__ if hasattr(c, "__dict__") else (c if isinstance(c, dict) else {})
            if str(d.get("id", "")) == str(campaign_id):
                return d
        return {"id": campaign_id}

    # ── Detail page ───────────────────────────────────────────────────────────

    def _open_detail_page(self, campaign_data: dict):
        """Show the full-screen BroadcastDetailPage overlay."""
        if (
            self._detail_page is None
            or self._detail_page.campaign_data.get("id") != campaign_data.get("id")
        ):
            self._detail_page = BroadcastDetailPage(
                self.frame,
                campaign_data=campaign_data,
                on_close=self._on_detail_close,
                on_pause=self._on_detail_pause,
                on_resume=self._on_detail_resume,
                on_stop=self._on_detail_stop,
            )
        else:
            self._detail_page.campaign_data.update(campaign_data)

        if "_start_ts" not in self._detail_page.campaign_data:
            self._detail_page.campaign_data["_start_ts"] = time.time()

        self._detail_page.show()

    def _on_detail_close(self):
        self._load_campaigns()

    def _on_detail_pause(self, campaign_id):
        log(f"Pause campaign {campaign_id} from detail view", "info")
        self._load_campaigns()

    def _on_detail_resume(self, campaign_id):
        log(f"Resume campaign {campaign_id} from detail view", "info")
        self._load_campaigns()

    def _on_detail_stop(self, campaign_id):
        log(f"Stop campaign {campaign_id} from detail view", "warning")
        self._load_campaigns()

    # ── Create Campaign Modal (Phase 3A) ──────────────────────────────────────

    def _open_create_modal(self):
        """Open the Create Broadcast Campaign modal dialog."""
        modal = tk.Toplevel(self.frame)
        modal.title("Create Broadcast Campaign")
        modal.geometry("620x780")
        modal.configure(bg=BG)
        modal.grab_set()
        modal.resizable(True, True)

        # Scrollable canvas
        canvas = tk.Canvas(modal, bg=BG, highlightthickness=0)
        vscroll = ttk.Scrollbar(modal, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)
        vscroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        body = tk.Frame(canvas, bg=BG)
        body_win = canvas.create_window((0, 0), window=body, anchor="nw")
        body.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(body_win, width=e.width),
        )

        PAD = {"padx": 15, "pady": 5}

        def section_header(title):
            tk.Label(body, text=title, font=FONTS["subheading"],
                     fg=CYAN, bg=BG).pack(anchor="w", **PAD)
            tk.Frame(body, bg=COLORS["border"], height=1).pack(fill="x", padx=15)

        def labeled_entry(parent, label, default="", wide=False):
            row = tk.Frame(parent, bg=BG)
            row.pack(fill="x", **PAD)
            tk.Label(row, text=label, fg=MUTED, bg=BG,
                     font=FONTS["small"], width=20, anchor="w").pack(side="left")
            var = tk.StringVar(value=default)
            tk.Entry(row, textvariable=var, bg=CARD, fg=TEXT,
                     insertbackground=CYAN,
                     width=35 if wide else 28).pack(side="left", fill="x", expand=wide)
            return var

        # ── Campaign Info ──────────────────────────────────────────────────────
        section_header("📝 CAMPAIGN INFO")
        v_name   = labeled_entry(body, "Campaign Name:")
        v_client = labeled_entry(body, "Client:")

        row_ag = tk.Frame(body, bg=BG)
        row_ag.pack(fill="x", **PAD)
        tk.Label(row_ag, text="Account Group:", fg=MUTED, bg=BG,
                 font=FONTS["small"], width=20, anchor="w").pack(side="left")
        v_ag = tk.StringVar(value="")
        try:
            from core.account_group_manager import account_group_manager
            groups_list = [
                g["name"] for g in account_group_manager.list_groups().values()
            ]
        except Exception:
            groups_list = []
        ttk.Combobox(row_ag, textvariable=v_ag, values=groups_list,
                     width=28).pack(side="left")

        # ── Message ────────────────────────────────────────────────────────────
        section_header("💬 MESSAGE")
        tk.Label(body, text="Text:", fg=MUTED, bg=BG,
                 font=FONTS["small"]).pack(anchor="w", padx=15)
        msg_text = scrolledtext.ScrolledText(
            body, height=5, bg=CARD, fg=TEXT,
            insertbackground=CYAN, font=("Consolas", 10)
        )
        msg_text.pack(fill="x", padx=15, pady=5)
        try:
            msg_text.insert("1.0", load_message())
        except Exception:
            pass

        v_media = labeled_entry(body, "Media URL:")
        v_link  = labeled_entry(body, "Link URL:")

        # ── Target Groups ──────────────────────────────────────────────────────
        section_header("🎯 TARGET GROUPS")
        v_source = tk.StringVar(value="joined")
        for val, lbl in [
            ("joined",  "Use Joined Groups"),
            ("csv",     "Upload CSV"),
            ("scrape",  "Use Scrape Results"),
            ("finder",  "Use Finder Results"),
        ]:
            tk.Radiobutton(body, text=lbl, variable=v_source, value=val,
                           bg=BG, fg=TEXT, selectcolor=CARD,
                           activebackground=BG).pack(anchor="w", padx=25, pady=2)

        v_dedup = tk.BooleanVar(value=True)
        tk.Checkbutton(body, text="✅ Deduplicate (auto)",
                       variable=v_dedup, bg=BG, fg=TEXT,
                       selectcolor=CARD, activebackground=BG).pack(anchor="w", padx=25, pady=2)

        # ── Schedule ───────────────────────────────────────────────────────────
        section_header("⏱️ SCHEDULE")
        v_schedule = tk.StringVar(value="now")
        for val, lbl in [("now", "Start Now"), ("schedule", "Schedule:")]:
            tk.Radiobutton(body, text=lbl, variable=v_schedule, value=val,
                           bg=BG, fg=TEXT, selectcolor=CARD,
                           activebackground=BG).pack(anchor="w", padx=25, pady=2)
        v_sched_dt = labeled_entry(body, "Date/Time (optional):", "YYYY-MM-DD HH:MM")

        row_timing = tk.Frame(body, bg=BG)
        row_timing.pack(fill="x", padx=15, pady=3)
        v_24h = tk.BooleanVar(value=True)
        tk.Checkbutton(row_timing, text="24/7  OR  Custom hours:",
                       variable=v_24h, bg=BG, fg=TEXT,
                       selectcolor=CARD, activebackground=BG).pack(side="left")
        v_timing = labeled_entry(row_timing, "", "08:00-22:00")

        # ── Advanced ───────────────────────────────────────────────────────────
        section_header("⚙️ ADVANCED")
        v_delay_min = labeled_entry(body, "Delay msg (sec):", "30")
        v_delay_max = labeled_entry(body, "Delay acc (sec):", "60")
        v_max_hour  = labeled_entry(body, "Max/hour:", "50")
        v_max_day   = labeled_entry(body, "Max/day:", "500")
        v_rotate    = labeled_entry(body, "Rotate every N msg:", "20")
        v_jitter    = labeled_entry(body, "Jitter (%):", "10")

        v_retry = tk.BooleanVar(value=True)
        v_auto  = tk.BooleanVar(value=True)
        tk.Checkbutton(body, text="Smart retry ✅", variable=v_retry,
                       bg=BG, fg=TEXT, selectcolor=CARD,
                       activebackground=BG).pack(anchor="w", padx=25)
        tk.Checkbutton(body, text="Auto-pause on 3 warnings ✅", variable=v_auto,
                       bg=BG, fg=TEXT, selectcolor=CARD,
                       activebackground=BG).pack(anchor="w", padx=25)

        # ── Buttons ────────────────────────────────────────────────────────────
        tk.Frame(body, bg=COLORS["border"], height=1).pack(fill="x", padx=15, pady=10)
        btn_row = tk.Frame(body, bg=BG)
        btn_row.pack(pady=10)

        def _on_start_now():
            name = v_name.get().strip()
            if not name:
                messagebox.showwarning("Validation", "Campaign Name required.", parent=modal)
                return
            msg = msg_text.get("1.0", "end-1c").strip()
            if not msg:
                messagebox.showwarning("Validation", "Message text required.", parent=modal)
                return
            try:
                camp = campaign_manager.create_campaign(name=name)
                # Set message and optional Phase 3 fields on the created campaign
                timing_str = v_timing.get().strip()
                timing_parts = timing_str.split("-") if "-" in timing_str else []
                extra: dict = {
                    "message_text": msg,
                    "media_url": v_media.get().strip() or None,
                    "link_url": v_link.get().strip() or None,
                    "timing_start": timing_parts[0] if len(timing_parts) >= 1 else None,
                    "timing_end": timing_parts[1] if len(timing_parts) >= 2 else None,
                }
                # Remove None values to avoid overwriting existing fields
                extra = {k: v for k, v in extra.items() if v is not None}
                try:
                    campaign_manager.update_campaign(camp.id, **extra)
                except Exception:
                    pass
                log(f"Campaign '{name}' created", "success")
                messagebox.showinfo("Created", f"Campaign '{name}' created!", parent=modal)
                modal.destroy()
                self._load_campaigns()
            except Exception as exc:
                messagebox.showerror("Error", str(exc), parent=modal)

        def _on_schedule():
            dt_str = v_sched_dt.get().strip()
            if not dt_str or dt_str == "YYYY-MM-DD HH:MM":
                messagebox.showwarning(
                    "Schedule",
                    "Enter a date/time in 'YYYY-MM-DD HH:MM' format.",
                    parent=modal,
                )
                return
            messagebox.showinfo(
                "Schedule",
                f"Scheduled for: {dt_str}\n(Backend integration pending.)",
                parent=modal,
            )

        tk.Button(btn_row, text="PREVIEW", bg=CARD, fg=CYAN,
                  font=FONTS["body"], relief="flat", padx=15, pady=8,
                  command=lambda: messagebox.showinfo(
                      "Preview",
                      f"Message:\n{msg_text.get('1.0', 'end-1c')[:200]}",
                      parent=modal,
                  )).pack(side="left", padx=8)
        tk.Button(btn_row, text="SCHEDULE", bg=ORANGE, fg="#000",
                  font=FONTS["body"], relief="flat", padx=15, pady=8,
                  command=_on_schedule).pack(side="left", padx=8)
        tk.Button(btn_row, text="START NOW", bg=GREEN, fg="#000",
                  font=FONTS["body_bold"], relief="flat", padx=15, pady=8,
                  command=_on_start_now).pack(side="left", padx=8)

    # ─────────────────────────────────────────────────────────────────────────

    def _create_widgets(self):
        # ── Campaign List Section (Phase 3A redesign) ─────────────────────────
        self._build_campaign_list_section()

        # ── Separator ────────────────────────────────────────────────────────
        tk.Frame(self.frame, bg=COLORS["border"], height=2).pack(fill="x", padx=10, pady=4)

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
            self._campaigns = camps
            self.campaign_combo['values'] = [""] + [f"{c.name} ({c.id})" for c in camps]
            # Update Phase 3 campaign list tree
            self._populate_campaign_tree(camps)
        except Exception:
            pass
    
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