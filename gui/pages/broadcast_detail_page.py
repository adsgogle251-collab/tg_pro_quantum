"""
TG PRO QUANTUM – Broadcast Detail Page (Phase 3A)

Full-screen campaign monitoring dashboard with:
  • Real-time progress bar and key metrics
  • Message / media / link details
  • Target groups verification status
  • Account rotation live table
  • Activity log (newest first) with virtual scrolling
  • Pause / Resume / Stop / Export controls
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
from datetime import datetime
from typing import Optional, List, Dict, Any

from gui.styles import COLORS, FONTS
from core import log

# ── Color aliases ─────────────────────────────────────────────────────────────
BG       = COLORS["bg_dark"]
PANEL    = COLORS["bg_medium"]
CARD     = COLORS["bg_light"]
CYAN     = COLORS["primary"]
GREEN    = COLORS["success"]
ORANGE   = COLORS["warning"]
RED      = COLORS["error"]
TEXT     = COLORS["text"]
MUTED    = COLORS["text_muted"]
BORDER   = COLORS["border"]


class BroadcastDetailPage:
    """
    Full-screen overlay rendered inside a parent frame.

    Usage::

        detail = BroadcastDetailPage(
            parent_frame,
            campaign_data={...},
            on_close=lambda: ...,
        )
        detail.show()
    """

    # ── Constructor ───────────────────────────────────────────────────────────

    def __init__(
        self,
        parent: tk.Widget,
        campaign_data: Optional[Dict[str, Any]] = None,
        on_close=None,
        on_pause=None,
        on_resume=None,
        on_stop=None,
    ):
        self.parent = parent
        self.campaign_data: Dict[str, Any] = campaign_data or {}
        self.on_close = on_close
        self.on_pause = on_pause
        self.on_resume = on_resume
        self.on_stop = on_stop

        # Runtime state
        self._running = False
        self._activity_rows: List[Dict] = []
        self._account_rows: List[Dict] = []
        self._refresh_thread: Optional[threading.Thread] = None

        # Build the page
        self.frame = tk.Frame(parent, bg=BG)
        self._build()

    # ── Public API ────────────────────────────────────────────────────────────

    def show(self):
        self.frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._start_refresh()

    def hide(self):
        self._stop_refresh()
        self.frame.place_forget()

    def update_campaign_data(self, data: Dict[str, Any]):
        """Push new data into the page and refresh widgets."""
        self.campaign_data.update(data)
        self._refresh_metrics()
        self._refresh_accounts()

    def append_activity(self, entry: Dict[str, Any]):
        """Prepend an activity entry to the live log."""
        self._activity_rows.insert(0, entry)
        if len(self._activity_rows) > 500:
            self._activity_rows = self._activity_rows[:500]
        self._refresh_activity_log()

    # ── UI Build ──────────────────────────────────────────────────────────────

    def _build(self):
        f = self.frame

        # ── Header bar ───────────────────────────────────────────────────────
        self._build_header(f)

        # ── Scrollable body ───────────────────────────────────────────────────
        canvas = tk.Canvas(f, bg=BG, highlightthickness=0)
        vscroll = ttk.Scrollbar(f, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)
        vscroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        body = tk.Frame(canvas, bg=BG)
        body_win = canvas.create_window((0, 0), window=body, anchor="nw")

        def _on_configure(evt):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(body_win, width=canvas.winfo_width())

        body.bind("<Configure>", _on_configure)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(body_win, width=e.width))
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(-int(e.delta / 120), "units"))

        # ── Sections ──────────────────────────────────────────────────────────
        self._build_progress_section(body)
        self._build_message_section(body)
        self._build_groups_section(body)
        self._build_accounts_section(body)
        self._build_activity_section(body)

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self, parent: tk.Widget):
        hdr = tk.Frame(parent, bg="#0f1833", height=70)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        # Back button
        tk.Button(
            hdr, text="← Back", command=self._on_back,
            bg=PANEL, fg=CYAN, font=FONTS["body"],
            relief="flat", cursor="hand2", padx=12, pady=6,
        ).pack(side="left", padx=10, pady=15)

        # Title
        name  = self.campaign_data.get("name", "Campaign")
        client = self.campaign_data.get("client_name", "")
        title_txt = f"📢 {name}"
        if client:
            title_txt += f"  |  Client: {client}"
        tk.Label(hdr, text=title_txt, font=FONTS["heading"],
                 fg=CYAN, bg="#0f1833").pack(side="left", padx=10)

        # Action buttons (right-aligned)
        btn_frame = tk.Frame(hdr, bg="#0f1833")
        btn_frame.pack(side="right", padx=10)

        self._btn_pause = tk.Button(
            btn_frame, text="⏸ Pause", command=self._on_pause,
            bg=ORANGE, fg="#000", font=FONTS["small"], relief="flat",
            cursor="hand2", padx=10, pady=5,
        )
        self._btn_pause.pack(side="left", padx=4)

        self._btn_resume = tk.Button(
            btn_frame, text="▶ Resume", command=self._on_resume,
            bg=GREEN, fg="#000", font=FONTS["small"], relief="flat",
            cursor="hand2", padx=10, pady=5,
        )
        self._btn_resume.pack(side="left", padx=4)

        self._btn_stop = tk.Button(
            btn_frame, text="■ Stop", command=self._on_stop,
            bg=RED, fg="#fff", font=FONTS["small"], relief="flat",
            cursor="hand2", padx=10, pady=5,
        )
        self._btn_stop.pack(side="left", padx=4)

        tk.Button(
            btn_frame, text="📤 Export", command=self._on_export,
            bg=PANEL, fg=CYAN, font=FONTS["small"], relief="flat",
            cursor="hand2", padx=10, pady=5,
        ).pack(side="left", padx=4)

    # ── Section: Real-time progress ───────────────────────────────────────────

    def _build_progress_section(self, parent: tk.Widget):
        sec = self._section(parent, "📊 REAL-TIME PROGRESS")

        # Progress bar container
        pb_frame = tk.Frame(sec, bg=PANEL)
        pb_frame.pack(fill="x", padx=15, pady=8)

        tk.Label(pb_frame, text="Overall Progress:", fg=MUTED,
                 bg=PANEL, font=FONTS["small"]).pack(side="left", padx=5)

        self._progress_var = tk.DoubleVar(value=0.0)
        self._progress_bar = ttk.Progressbar(
            pb_frame, variable=self._progress_var,
            maximum=100, length=400, style="cyan.Horizontal.TProgressbar"
        )
        self._progress_bar.pack(side="left", padx=10)

        self._progress_lbl = tk.Label(pb_frame, text="0% (0/0)",
                                       fg=CYAN, bg=PANEL, font=FONTS["body_bold"])
        self._progress_lbl.pack(side="left", padx=5)

        # Metrics grid
        metrics_frame = tk.Frame(sec, bg=CARD, bd=1, relief="flat")
        metrics_frame.pack(fill="x", padx=15, pady=8)

        self._metric_labels: Dict[str, tk.Label] = {}
        metrics = [
            ("msgs_sent",    "Messages Sent",  "0 ✅"),
            ("success",      "Success",        "0 (0%) 🟢"),
            ("failed",       "Failed",         "0 (0%) 🔴"),
            ("elapsed",      "Time Elapsed",   "0m ⏱"),
            ("remaining",    "Time Remaining", "-- ⏱"),
            ("speed",        "Speed",          "0 msg/min 🚀"),
            ("eta",          "ETA Finish",     "-- 🎯"),
        ]
        for col, (key, label, default) in enumerate(metrics):
            cell = tk.Frame(metrics_frame, bg=CARD)
            cell.grid(row=0, column=col, padx=10, pady=10, sticky="ew")
            metrics_frame.columnconfigure(col, weight=1)
            tk.Label(cell, text=label, fg=MUTED, bg=CARD,
                     font=FONTS["small"]).pack()
            lbl = tk.Label(cell, text=default, fg=TEXT, bg=CARD,
                           font=FONTS["body_bold"])
            lbl.pack()
            self._metric_labels[key] = lbl

    # ── Section: Message details ──────────────────────────────────────────────

    def _build_message_section(self, parent: tk.Widget):
        sec = self._section(parent, "💬 MESSAGE DETAILS")
        inner = tk.Frame(sec, bg=PANEL)
        inner.pack(fill="x", padx=15, pady=5)

        def _row(label: str, key: str, default: str = "—"):
            row = tk.Frame(inner, bg=PANEL)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=f"{label}:", fg=MUTED, bg=PANEL,
                     font=FONTS["small"], width=10, anchor="w").pack(side="left")
            lbl = tk.Label(row, text=self.campaign_data.get(key, default),
                           fg=TEXT, bg=PANEL, font=FONTS["body"],
                           wraplength=700, justify="left", anchor="w")
            lbl.pack(side="left", fill="x", expand=True)
            return lbl

        self._msg_text_lbl  = _row("Text",  "message_text")
        self._msg_media_lbl = _row("Media", "media_url", "No media")
        self._msg_link_lbl  = _row("Link",  "link_url",  "No link")

    # ── Section: Target groups ────────────────────────────────────────────────

    def _build_groups_section(self, parent: tk.Widget):
        sec = self._section(parent, "🎯 TARGET GROUPS (VERIFICATION)")
        inner = tk.Frame(sec, bg=PANEL)
        inner.pack(fill="x", padx=15, pady=5)

        info_row = tk.Frame(inner, bg=PANEL)
        info_row.pack(fill="x", pady=3)

        total = self.campaign_data.get("total_targets", 0)
        tk.Label(info_row,
                 text=f"Total Groups: {total} (GROUPS ONLY – NO CHANNELS!)",
                 fg=ORANGE, bg=PANEL, font=FONTS["body_bold"]).pack(side="left", padx=5)

        stats_row = tk.Frame(inner, bg=PANEL)
        stats_row.pack(fill="x", pady=3)

        self._grp_sent_lbl    = tk.Label(stats_row, text="Sent: 0 ✅",    fg=GREEN,  bg=PANEL, font=FONTS["body"])
        self._grp_pending_lbl = tk.Label(stats_row, text="Pending: 0 ⏳", fg=ORANGE, bg=PANEL, font=FONTS["body"])
        self._grp_failed_lbl  = tk.Label(stats_row, text="Failed: 0 ❌",  fg=RED,    bg=PANEL, font=FONTS["body"])

        for lbl in (self._grp_sent_lbl, self._grp_pending_lbl, self._grp_failed_lbl):
            lbl.pack(side="left", padx=15)

        tk.Label(inner, text="Group Type: verified (members > 10, active)",
                 fg=MUTED, bg=PANEL, font=FONTS["small"]).pack(anchor="w", padx=5, pady=3)

    # ── Section: Account rotation ─────────────────────────────────────────────

    def _build_accounts_section(self, parent: tk.Widget):
        sec = self._section(parent, "🔄 ACCOUNT ROTATION (LIVE)")

        summary = tk.Frame(sec, bg=PANEL)
        summary.pack(fill="x", padx=15, pady=5)

        self._acc_active_lbl  = tk.Label(summary, text="Active Accounts: 0 / 0",
                                          fg=CYAN, bg=PANEL, font=FONTS["body_bold"])
        self._acc_active_lbl.pack(side="left", padx=5)

        self._acc_health_lbl  = tk.Label(summary, text="Healthy: 0 (0%) | Warning: 0 | Banned: 0",
                                          fg=TEXT, bg=PANEL, font=FONTS["small"])
        self._acc_health_lbl.pack(side="left", padx=15)

        # Account table
        tbl_frame = tk.Frame(sec, bg=PANEL)
        tbl_frame.pack(fill="x", padx=15, pady=5)

        cols = ("Account", "Status", "Health", "Msgs", "Last Used")
        self._acc_tree = ttk.Treeview(
            tbl_frame, columns=cols, show="headings", height=6
        )
        for col in cols:
            self._acc_tree.heading(col, text=col)
            self._acc_tree.column(col, width=130, anchor="center")
        self._acc_tree.pack(fill="x")

        self._next_acc_lbl = tk.Label(sec, text="Next: —",
                                       fg=MUTED, bg=PANEL, font=FONTS["small"])
        self._next_acc_lbl.pack(anchor="w", padx=15, pady=3)

    # ── Section: Activity log ─────────────────────────────────────────────────

    def _build_activity_section(self, parent: tk.Widget):
        sec = self._section(parent, "📋 ACTIVITY LOG (LIVE – Newest First)")

        # Log text widget with virtual scrolling
        log_frame = tk.Frame(sec, bg=PANEL)
        log_frame.pack(fill="both", expand=True, padx=15, pady=5)

        self._activity_text = tk.Text(
            log_frame, bg="#0a0e1a", fg=TEXT, font=("Consolas", 10),
            state="disabled", height=12, wrap="none",
        )
        act_scroll_y = ttk.Scrollbar(log_frame, orient="vertical",
                                      command=self._activity_text.yview)
        act_scroll_x = ttk.Scrollbar(log_frame, orient="horizontal",
                                      command=self._activity_text.xview)
        self._activity_text.configure(
            yscrollcommand=act_scroll_y.set,
            xscrollcommand=act_scroll_x.set,
        )
        act_scroll_y.pack(side="right", fill="y")
        act_scroll_x.pack(side="bottom", fill="x")
        self._activity_text.pack(fill="both", expand=True)

        # Tag colours
        self._activity_text.tag_configure("success", foreground=GREEN)
        self._activity_text.tag_configure("failure", foreground=RED)
        self._activity_text.tag_configure("info",    foreground=CYAN)
        self._activity_text.tag_configure("ts",      foreground=MUTED)

        # Bottom buttons
        btn_row = tk.Frame(sec, bg=PANEL)
        btn_row.pack(fill="x", padx=15, pady=5)
        tk.Button(btn_row, text="↓ Load More", command=self._load_more_activity,
                  bg=CARD, fg=CYAN, relief="flat", padx=10, pady=4,
                  cursor="hand2").pack(side="left", padx=5)
        tk.Button(btn_row, text="📤 Export Log", command=self._export_log,
                  bg=CARD, fg=CYAN, relief="flat", padx=10, pady=4,
                  cursor="hand2").pack(side="left", padx=5)

    # ── Section helper ────────────────────────────────────────────────────────

    def _section(self, parent: tk.Widget, title: str) -> tk.Frame:
        """Create a titled section card."""
        card = tk.Frame(parent, bg=PANEL, bd=1, relief="flat")
        card.pack(fill="x", padx=10, pady=6)

        tk.Label(card, text=f"  {title}  ", fg=CYAN, bg="#0f1833",
                 font=FONTS["subheading"]).pack(fill="x", ipady=5)

        separator = tk.Frame(card, bg=BORDER, height=1)
        separator.pack(fill="x")

        body = tk.Frame(card, bg=PANEL)
        body.pack(fill="x", padx=5, pady=5)
        return body

    # ── Refresh helpers ───────────────────────────────────────────────────────

    def _start_refresh(self):
        """Start the background polling thread."""
        self._running = True
        self._refresh_thread = threading.Thread(
            target=self._refresh_loop, daemon=True
        )
        self._refresh_thread.start()

    def _stop_refresh(self):
        self._running = False

    def _refresh_loop(self):
        while self._running:
            try:
                self.frame.after(0, self._refresh_metrics)
            except Exception:
                pass
            time.sleep(1)

    def _refresh_metrics(self):
        """Pull latest values from campaign_data and update labels."""
        d = self.campaign_data

        sent    = int(d.get("sent_count", 0))
        failed  = int(d.get("failed_count", 0))
        total   = int(d.get("total_targets", 0) or 1)
        processed = sent + failed
        pct     = min(100.0, processed / total * 100)

        success_rate = (sent / processed * 100) if processed else 0.0

        # Progress bar
        self._progress_var.set(pct)
        self._progress_lbl.config(text=f"{pct:.0f}% ({processed}/{total})")

        # Elapsed / speed / ETA
        start_ts = d.get("_start_ts")
        elapsed_min = 0.0
        speed = 0.0
        eta_str = "--"
        remaining_str = "--"

        if start_ts:
            elapsed_sec = time.time() - start_ts
            elapsed_min = elapsed_sec / 60
            speed = sent / elapsed_min if elapsed_min > 0 else 0.0
            remaining = total - processed
            if speed > 0:
                remaining_min = remaining / speed
                remaining_str = f"{remaining_min:.0f}m ⏱"
                eta_dt = datetime.now()
                from datetime import timedelta
                eta_dt = eta_dt + timedelta(minutes=remaining_min)
                eta_str = eta_dt.strftime("%H:%M") + " 🎯"

        # Key metrics
        updates = {
            "msgs_sent":  f"{sent} ✅",
            "success":    f"{sent} ({success_rate:.0f}%) 🟢",
            "failed":     f"{failed} ({100-success_rate:.0f}%) 🔴",
            "elapsed":    f"{elapsed_min:.0f}m ⏱",
            "remaining":  remaining_str,
            "speed":      f"{speed:.1f} msg/min 🚀",
            "eta":        eta_str,
        }
        for key, val in updates.items():
            lbl = self._metric_labels.get(key)
            if lbl:
                lbl.config(text=val)

        # Groups section
        pending = total - processed
        self._grp_sent_lbl.config(text=f"Sent: {sent} ✅")
        self._grp_pending_lbl.config(text=f"Pending: {pending} ⏳")
        self._grp_failed_lbl.config(text=f"Failed: {failed} ❌")

    def _refresh_accounts(self):
        accounts = self._account_rows
        total_acc = len(accounts)
        active = sum(1 for a in accounts if a.get("status") == "active")
        healthy = sum(1 for a in accounts if float(a.get("health", 0)) >= 80)
        warned  = sum(1 for a in accounts if 0 < float(a.get("warnings", 0)) < 3)
        banned  = sum(1 for a in accounts if a.get("banned", False))

        self._acc_active_lbl.config(
            text=f"Active Accounts: {active} / {total_acc} available"
        )
        h_pct = healthy / total_acc * 100 if total_acc else 0
        self._acc_health_lbl.config(
            text=f"Healthy: {healthy} ({h_pct:.0f}%) | Warning: {warned} | Banned: {banned}"
        )

        # Re-populate tree
        for row in self._acc_tree.get_children():
            self._acc_tree.delete(row)

        for acc in accounts:
            status_icon = "✅" if acc.get("status") == "active" else "🔴"
            tag = "active" if acc.get("status") == "active" else "banned"
            self._acc_tree.insert("", "end", values=(
                acc.get("name", "?"),
                status_icon,
                f"{acc.get('health', 0):.0f}%",
                acc.get("msgs", 0),
                acc.get("last_used", "--"),
            ), tags=(tag,))

        self._acc_tree.tag_configure("active", foreground=GREEN)
        self._acc_tree.tag_configure("banned", foreground=RED)

    def _refresh_activity_log(self):
        """Re-render the activity log (newest 200 entries)."""
        self._activity_text.configure(state="normal")
        self._activity_text.delete("1.0", "end")

        for entry in self._activity_rows[:200]:
            ts      = entry.get("ts", "")
            account = entry.get("account", "?")
            group   = entry.get("group", "?")
            success = entry.get("success", True)
            detail  = entry.get("detail", "")
            icon    = "✅" if success else "❌"
            tag     = "success" if success else "failure"
            line    = f"[{ts}] {account} → {group} {icon} {detail}\n"
            self._activity_text.insert("end", line, tag)

        self._activity_text.configure(state="disabled")

    # ── Button callbacks ──────────────────────────────────────────────────────

    def _on_back(self):
        self.hide()
        if self.on_close:
            self.on_close()

    def _on_pause(self):
        if messagebox.askyesno("Pause Campaign", "Pause this campaign?"):
            if self.on_pause:
                self.on_pause(self.campaign_data.get("id"))

    def _on_resume(self):
        if self.on_resume:
            self.on_resume(self.campaign_data.get("id"))

    def _on_stop(self):
        if messagebox.askyesno(
            "Stop Campaign",
            "Stop this campaign permanently?\nThis cannot be undone.",
        ):
            if self.on_stop:
                self.on_stop(self.campaign_data.get("id"))

    def _on_export(self):
        path = filedialog.asksaveasfilename(
            title="Export Campaign Report",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            lines = [
                f"Campaign Report: {self.campaign_data.get('name', '?')}",
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "=" * 60,
            ]
            for entry in self._activity_rows:
                ts      = entry.get("ts", "")
                account = entry.get("account", "?")
                group   = entry.get("group", "?")
                icon    = "OK" if entry.get("success") else "FAIL"
                detail  = entry.get("detail", "")
                lines.append(f"[{ts}] {icon} {account} -> {group} {detail}")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines))
            messagebox.showinfo("Export", f"Saved to {path}")
        except Exception as exc:
            messagebox.showerror("Export Error", str(exc))

    def _load_more_activity(self):
        log("Load more activity – not yet connected to live source", "info")

    def _export_log(self):
        self._on_export()
