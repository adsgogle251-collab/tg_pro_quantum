"""Clients Tab - Complete with Plan Types, API Keys, Account Groups, Dashboard"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, scrolledtext
from core import log, client_manager, account_manager
from core.account_group_manager import account_group_manager
from gui.styles import COLORS, FONTS
from core.localization import t

PLAN_LABELS = {
    "starter":    "🌱 Starter (Rp 2jt/bulan)",
    "pro":        "⚡ Pro (Rp 5jt/bulan)",
    "enterprise": "🏢 Enterprise (Custom)",
}

STATUS_ICONS = {
    "active":    "✅",
    "suspended": "🔴",
    "trial":     "🔄",
}


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
        tk.Button(toolbar, text="📤 Export", command=self._export_client_report,
                  bg=COLORS["bg_light"], fg=COLORS["text"], font=FONTS["bold"]).pack(side="left", padx=5)

        # === 2. SEARCH + FILTER ===
        search_frame = tk.Frame(self.scrollable_frame, bg=COLORS["bg_dark"])
        search_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(search_frame, text="🔍 Search:", fg=COLORS["text"], bg=COLORS["bg_dark"]).pack(side="left", padx=5)
        self.search_entry = tk.Entry(search_frame, width=30, bg=COLORS["bg_light"], fg=COLORS["text"])
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<KeyRelease>", lambda e: self._filter_clients())

        tk.Label(search_frame, text="Status:", fg=COLORS["text"], bg=COLORS["bg_dark"]).pack(side="left", padx=(15, 5))
        self.status_filter_var = tk.StringVar(value="All")
        ttk.Combobox(search_frame, textvariable=self.status_filter_var,
                     values=["All", "active", "suspended", "trial"],
                     width=12, state="readonly").pack(side="left", padx=5)
        self.status_filter_var.trace_add("write", lambda *_: self._filter_clients())

        # === 3. CLIENT LIST ===
        list_frame = tk.LabelFrame(self.scrollable_frame, text="📋 All Clients",
                                   fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                   font=FONTS["heading"])
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)

        columns = ("ID", "Name", "Email", "Plan", "Company", "Broadcasts", "Status")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=12)

        col_widths = {"ID": 50, "Name": 180, "Email": 200, "Plan": 140,
                      "Company": 160, "Broadcasts": 100, "Status": 80}
        for col in columns:
            self.tree.heading(col, text=col,
                              command=lambda c=col: self._sort_tree(c))
            self.tree.column(col, width=col_widths.get(col, 120))

        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        vsb.pack(side="right", fill="y", pady=10, padx=(0, 5))
        self.tree.bind("<Double-1>", lambda e: self._view_client_details())

        # === 4. STATS ===
        self.stats_label = tk.Label(self.scrollable_frame, text="", fg=COLORS["text_muted"],
                                    bg=COLORS["bg_dark"], font=FONTS["bold"])
        self.stats_label.pack(pady=5)

        # === 5. ACTION BUTTONS ===
        action_frame = tk.Frame(self.scrollable_frame, bg=COLORS["bg_dark"])
        action_frame.pack(fill="x", padx=10, pady=10)

        tk.Button(action_frame, text="👁️ View Dashboard", command=self._view_client_details,
                  bg=COLORS["info"], fg="white", font=FONTS["bold"]).pack(side="left", padx=5)
        tk.Button(action_frame, text="✏️ Edit", command=self._edit_client,
                  bg=COLORS["warning"], fg="white", font=FONTS["bold"]).pack(side="left", padx=5)
        tk.Button(action_frame, text="🔑 New API Key", command=self._regenerate_api_key,
                  bg=COLORS["secondary"], fg="white", font=FONTS["bold"]).pack(side="left", padx=5)
        tk.Button(action_frame, text="⏸️ Suspend", command=self._toggle_suspend,
                  bg=COLORS["warning"], fg="white", font=FONTS["bold"]).pack(side="left", padx=5)
        tk.Button(action_frame, text="🗑️ Delete", command=self._delete_client,
                  bg=COLORS["error"], fg="white", font=FONTS["bold"]).pack(side="left", padx=5)

        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Keep full client list for filtering
        self._all_clients: list = []
        self._sort_col = ""
        self._sort_asc = True

    # ─────────────────────────────────────────────────────────────────
    # DATA LOADING
    # ─────────────────────────────────────────────────────────────────

    def _load_clients(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        self._all_clients = client_manager.get_all_clients()
        self._refresh_tree(self._all_clients)

    def _refresh_tree(self, clients):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for client in clients:
            plan = client.get("plan_type", "starter")
            plan_label = PLAN_LABELS.get(plan, plan)
            status = client.get("status", "active")
            icon = STATUS_ICONS.get(status, "")
            self.tree.insert("", "end", values=(
                client["id"],
                client["name"],
                client["email"],
                plan_label,
                client.get("company", ""),
                client.get("total_broadcasts", 0),
                f"{icon} {status}",
            ))
        self.stats_label.config(text=f"Total Clients: {len(clients)}")

    def _filter_clients(self):
        query = self.search_entry.get().lower()
        status_filter = self.status_filter_var.get()

        filtered = self._all_clients
        if query:
            filtered = [c for c in filtered if query in str(c).lower()]
        if status_filter != "All":
            filtered = [c for c in filtered if c.get("status", "active") == status_filter]
        self._refresh_tree(filtered)

    def _sort_tree(self, col: str):
        if self._sort_col == col:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_col = col
            self._sort_asc = True

        col_map = {"ID": "id", "Name": "name", "Email": "email",
                   "Plan": "plan_type", "Company": "company",
                   "Broadcasts": "total_broadcasts", "Status": "status"}
        key = col_map.get(col, "name")
        clients = sorted(self._all_clients, key=lambda c: c.get(key, ""), reverse=not self._sort_asc)
        self._refresh_tree(clients)

    # ─────────────────────────────────────────────────────────────────
    # CREATE CLIENT
    # ─────────────────────────────────────────────────────────────────

    def _create_client(self):
        dialog = tk.Toplevel(self.frame)
        dialog.title("➕ New Client")
        dialog.geometry("560x600")
        dialog.configure(bg=COLORS["bg_dark"])

        tk.Label(dialog, text="➕ New Client", font=("Segoe UI", 18, "bold"),
                 fg=COLORS["primary"], bg=COLORS["bg_dark"]).pack(pady=15)

        form_canvas = tk.Canvas(dialog, bg=COLORS["bg_dark"], highlightthickness=0)
        form_scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=form_canvas.yview)
        form_frame = tk.Frame(form_canvas, bg=COLORS["bg_medium"])

        form_frame.bind("<Configure>", lambda e: form_canvas.configure(scrollregion=form_canvas.bbox("all")))
        form_canvas.create_window((0, 0), window=form_frame, anchor="nw")
        form_canvas.configure(yscrollcommand=form_scrollbar.set)

        # ── Basic fields ──────────────────────────────────────────────
        fields = [("Name *", "name"), ("Email *", "email"), ("Company", "company"), ("Phone", "phone")]
        entries = {}
        for row_idx, (label, key) in enumerate(fields):
            tk.Label(form_frame, text=label, fg=COLORS["text"], bg=COLORS["bg_medium"],
                     font=FONTS["normal"]).grid(row=row_idx, column=0, padx=10, pady=8, sticky="w")
            e = tk.Entry(form_frame, width=35, bg=COLORS["bg_light"], fg=COLORS["text"])
            e.grid(row=row_idx, column=1, padx=10, pady=8)
            entries[key] = e

        # ── Plan type ─────────────────────────────────────────────────
        r = len(fields)
        tk.Label(form_frame, text="Plan Type:", fg=COLORS["text"], bg=COLORS["bg_medium"],
                 font=FONTS["normal"]).grid(row=r, column=0, padx=10, pady=8, sticky="w")
        plan_var = tk.StringVar(value="🌱 Starter (Rp 2jt/bulan)")
        plan_combo = ttk.Combobox(form_frame, textvariable=plan_var,
                                  values=list(PLAN_LABELS.values()), width=33, state="readonly")
        plan_combo.grid(row=r, column=1, padx=10, pady=8)

        # ── Account Groups ────────────────────────────────────────────
        r += 1
        tk.Label(form_frame, text="Assign Groups:", fg=COLORS["text"], bg=COLORS["bg_medium"],
                 font=FONTS["normal"]).grid(row=r, column=0, padx=10, pady=8, sticky="nw")

        groups_frame = tk.Frame(form_frame, bg=COLORS["bg_light"], relief="sunken", bd=1)
        groups_frame.grid(row=r, column=1, padx=10, pady=8, sticky="ew")
        groups_listbox = tk.Listbox(groups_frame, selectmode="multiple",
                                    bg=COLORS["bg_light"], fg=COLORS["text"],
                                    height=5, font=FONTS["small"])
        groups_listbox.pack(fill="both", expand=True)
        all_groups = account_group_manager.get_all_groups()
        group_ids = []
        for g in all_groups:
            groups_listbox.insert("end", f"  {g['name']} ({len(g.get('accounts',[]))} accs)")
            group_ids.append(g["id"])

        # ── Notes ─────────────────────────────────────────────────────
        r += 1
        tk.Label(form_frame, text="Notes:", fg=COLORS["text"], bg=COLORS["bg_medium"],
                 font=FONTS["normal"]).grid(row=r, column=0, padx=10, pady=8, sticky="nw")
        notes_text = scrolledtext.ScrolledText(form_frame, height=4, width=35,
                                               bg=COLORS["bg_light"], fg=COLORS["text"])
        notes_text.grid(row=r, column=1, padx=10, pady=8)

        form_canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        form_scrollbar.pack(side="right", fill="y", pady=10)

        def save():
            name = entries["name"].get().strip()
            email = entries["email"].get().strip()
            company = entries["company"].get().strip()
            phone = entries["phone"].get().strip()
            notes = notes_text.get("1.0", "end-1c").strip()
            plan_raw = plan_var.get()
            plan_key = next((k for k, v in PLAN_LABELS.items() if v == plan_raw), "starter")
            selected_idxs = groups_listbox.curselection()
            selected_group_ids = [group_ids[i] for i in selected_idxs]

            if not name or not email:
                messagebox.showerror("Error", "Name and email required!", parent=dialog)
                return

            client_id = client_manager.create_client(name, email, company, phone, notes,
                                                     plan_type=plan_key,
                                                     account_groups=selected_group_ids)
            messagebox.showinfo("Success", f"Client created: {client_id}", parent=dialog)
            self._load_clients()
            dialog.destroy()

        tk.Button(dialog, text="💾 Save Client", command=save,
                  bg=COLORS["success"], fg="white", font=FONTS["bold"],
                  padx=30, pady=10).pack(pady=10)

    # ─────────────────────────────────────────────────────────────────
    # VIEW CLIENT DASHBOARD
    # ─────────────────────────────────────────────────────────────────

    def _view_client_details(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Select a client first!")
            return

        client_id = self.tree.item(selection[0])["values"][0]
        client = client_manager.get_client(client_id)

        if not client:
            return

        dialog = tk.Toplevel(self.frame)
        dialog.title(f"📊 Client Dashboard: {client['name']}")
        dialog.geometry("700x620")
        dialog.configure(bg=COLORS["bg_dark"])

        # Canvas + scrollbar for the whole dialog
        c = tk.Canvas(dialog, bg=COLORS["bg_dark"], highlightthickness=0)
        sb = ttk.Scrollbar(dialog, orient="vertical", command=c.yview)
        inner = tk.Frame(c, bg=COLORS["bg_dark"])
        inner.bind("<Configure>", lambda e: c.configure(scrollregion=c.bbox("all")))
        c.create_window((0, 0), window=inner, anchor="nw")
        c.configure(yscrollcommand=sb.set)
        c.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        tk.Label(inner, text=f"📊 {client['name']} — Dashboard",
                 font=("Segoe UI", 18, "bold"),
                 fg=COLORS["primary"], bg=COLORS["bg_dark"]).pack(pady=15)

        # ── Info section ──────────────────────────────────────────────
        info_frame = tk.LabelFrame(inner, text="📋 Client Info",
                                   fg=COLORS["accent"], bg=COLORS["bg_medium"])
        info_frame.pack(fill="x", padx=20, pady=10)

        plan = client.get("plan_type", "starter")
        plan_label = PLAN_LABELS.get(plan, plan)
        status = client.get("status", "active")
        api_key = client.get("api_key", "")
        api_display = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else api_key or "—"

        info_text = (
            f"Name: {client['name']}    Email: {client['email']}\n"
            f"Company: {client.get('company','N/A')}    Phone: {client.get('phone','N/A')}\n"
            f"Plan: {plan_label}    Status: {STATUS_ICONS.get(status,'')} {status}\n"
            f"API Key: {api_display}    Created: {client['created_at'][:10]}"
        )
        tk.Label(info_frame, text=info_text, fg=COLORS["text"],
                 bg=COLORS["bg_medium"], justify="left").pack(padx=20, pady=15)

        # ── Broadcast statistics ──────────────────────────────────────
        stats = client_manager.get_client_stats(client_id)
        stats_frame = tk.LabelFrame(inner, text="📊 Broadcast Statistics (This Month)",
                                    fg=COLORS["accent"], bg=COLORS["bg_medium"])
        stats_frame.pack(fill="x", padx=20, pady=10)

        usage_limit = client.get("usage_limit_monthly", 10000)
        usage_current = client.get("current_usage_monthly", stats.get("total_sent", 0))
        usage_pct = round(usage_current / usage_limit * 100, 1) if usage_limit else 0

        stats_grid = tk.Frame(stats_frame, bg=COLORS["bg_medium"])
        stats_grid.pack(padx=20, pady=10)
        stat_items = [
            ("Total Broadcasts", stats["total_broadcasts"]),
            ("Total Sent", f"{usage_current:,} / {usage_limit:,}"),
            ("Usage", f"{usage_pct}%"),
            ("Success Rate", f"{stats['avg_success_rate']}%"),
            ("Total Failed", stats["total_failed"]),
        ]
        for idx, (label, value) in enumerate(stat_items):
            col = idx % 3
            row = idx // 3
            f = tk.Frame(stats_grid, bg=COLORS["bg_light"], padx=12, pady=8)
            f.grid(row=row, column=col, padx=8, pady=4)
            tk.Label(f, text=label, font=FONTS["small"], fg=COLORS["text_muted"],
                     bg=COLORS["bg_light"]).pack()
            tk.Label(f, text=str(value), font=FONTS["bold"], fg=COLORS["primary"],
                     bg=COLORS["bg_light"]).pack()

        # Usage progress bar
        pb_frame = tk.Frame(stats_frame, bg=COLORS["bg_medium"])
        pb_frame.pack(fill="x", padx=20, pady=(0, 10))
        tk.Label(pb_frame, text="Monthly Usage:", fg=COLORS["text"],
                 bg=COLORS["bg_medium"], font=FONTS["small"]).pack(side="left")
        pb = ttk.Progressbar(pb_frame, value=min(usage_pct, 100), length=300)
        pb.pack(side="left", padx=10)

        # ── Account Groups ────────────────────────────────────────────
        groups_frame = tk.LabelFrame(inner, text="📂 Account Groups",
                                     fg=COLORS["accent"], bg=COLORS["bg_medium"])
        groups_frame.pack(fill="x", padx=20, pady=10)

        assigned_groups = client.get("account_groups", [])
        all_groups = account_group_manager.get_all_groups()
        client_groups = [g for g in all_groups if g.get("client_id") == client_id
                         or g["name"] in assigned_groups]

        if client_groups:
            for g in client_groups:
                count = len(g.get("accounts", []))
                feature = g.get("feature_type", "general")
                tk.Label(groups_frame,
                         text=f"  📂 {g['name']} — {feature} — {count} accounts",
                         fg=COLORS["text"], bg=COLORS["bg_medium"],
                         font=FONTS["normal"]).pack(anchor="w", padx=20, pady=2)
        else:
            tk.Label(groups_frame, text="  No account groups assigned",
                     fg=COLORS["text_muted"], bg=COLORS["bg_medium"]).pack(padx=20, pady=10)

        # ── Action buttons ────────────────────────────────────────────
        btn_frame = tk.Frame(inner, bg=COLORS["bg_dark"])
        btn_frame.pack(pady=15)
        tk.Button(btn_frame, text="✏️ Edit Client", command=lambda: [dialog.destroy(), self._edit_client()],
                  bg=COLORS["warning"], fg="white", font=FONTS["bold"]).pack(side="left", padx=8)
        tk.Button(btn_frame, text="🔑 Regenerate API Key",
                  command=lambda: self._do_regenerate_api_key(client_id, dialog),
                  bg=COLORS["secondary"], fg="white", font=FONTS["bold"]).pack(side="left", padx=8)
        tk.Button(btn_frame, text="📤 Export Report",
                  command=lambda: [dialog.destroy(), self._export_client_report()],
                  bg=COLORS["success"], fg="white", font=FONTS["bold"]).pack(side="left", padx=8)

    # ─────────────────────────────────────────────────────────────────
    # EDIT CLIENT
    # ─────────────────────────────────────────────────────────────────

    def _edit_client(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Select a client first!")
            return

        client_id = self.tree.item(selection[0])["values"][0]
        client = client_manager.get_client(client_id)
        if not client:
            return

        dialog = tk.Toplevel(self.frame)
        dialog.title(f"✏️ Edit: {client['name']}")
        dialog.geometry("500x420")
        dialog.configure(bg=COLORS["bg_dark"])

        tk.Label(dialog, text=f"✏️ Edit {client['name']}", font=("Segoe UI", 16, "bold"),
                 fg=COLORS["primary"], bg=COLORS["bg_dark"]).pack(pady=15)

        form = tk.Frame(dialog, bg=COLORS["bg_medium"])
        form.pack(fill="both", expand=True, padx=15, pady=5)

        fields = [("Name", "name"), ("Company", "company"), ("Phone", "phone")]
        entries = {}
        for row_idx, (label, key) in enumerate(fields):
            tk.Label(form, text=f"{label}:", fg=COLORS["text"], bg=COLORS["bg_medium"]).grid(
                row=row_idx, column=0, padx=10, pady=8, sticky="w")
            e = tk.Entry(form, width=35, bg=COLORS["bg_light"], fg=COLORS["text"])
            e.insert(0, client.get(key, ""))
            e.grid(row=row_idx, column=1, padx=10, pady=8)
            entries[key] = e

        r = len(fields)
        tk.Label(form, text="Plan:", fg=COLORS["text"], bg=COLORS["bg_medium"]).grid(
            row=r, column=0, padx=10, pady=8, sticky="w")
        current_plan = client.get("plan_type", "starter")
        plan_var = tk.StringVar(value=PLAN_LABELS.get(current_plan, current_plan))
        ttk.Combobox(form, textvariable=plan_var,
                     values=list(PLAN_LABELS.values()), width=33, state="readonly").grid(
            row=r, column=1, padx=10, pady=8)

        r += 1
        tk.Label(form, text="Status:", fg=COLORS["text"], bg=COLORS["bg_medium"]).grid(
            row=r, column=0, padx=10, pady=8, sticky="w")
        status_var = tk.StringVar(value=client.get("status", "active"))
        ttk.Combobox(form, textvariable=status_var,
                     values=["active", "suspended", "trial"], width=33, state="readonly").grid(
            row=r, column=1, padx=10, pady=8)

        def save():
            plan_raw = plan_var.get()
            plan_key = next((k for k, v in PLAN_LABELS.items() if v == plan_raw), "starter")
            updates = {
                "name": entries["name"].get().strip() or client["name"],
                "company": entries["company"].get().strip(),
                "phone": entries["phone"].get().strip(),
                "plan_type": plan_key,
                "status": status_var.get(),
            }
            client_manager.update_client(client_id, **updates)
            messagebox.showinfo("Saved", "Client updated successfully!", parent=dialog)
            self._load_clients()
            dialog.destroy()

        tk.Button(dialog, text="💾 Save Changes", command=save,
                  bg=COLORS["success"], fg="white", font=FONTS["bold"],
                  padx=25, pady=8).pack(pady=15)

    # ─────────────────────────────────────────────────────────────────
    # ACTIONS
    # ─────────────────────────────────────────────────────────────────

    def _toggle_suspend(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Select a client first!")
            return
        client_id = self.tree.item(selection[0])["values"][0]
        client = client_manager.get_client(client_id)
        if not client:
            return
        current = client.get("status", "active")
        new_status = "active" if current == "suspended" else "suspended"
        action = "activate" if new_status == "active" else "suspend"
        if messagebox.askyesno("Confirm", f"{action.capitalize()} client '{client['name']}'?"):
            client_manager.update_client(client_id, status=new_status)
            self._load_clients()
            log(f"Client {client['name']} {action}d", "info")

    def _regenerate_api_key(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Select a client first!")
            return
        client_id = self.tree.item(selection[0])["values"][0]
        client = client_manager.get_client(client_id)
        if not client:
            return
        self._do_regenerate_api_key(client_id)

    def _do_regenerate_api_key(self, client_id, parent_dialog=None):
        parent = parent_dialog or self.frame
        if not messagebox.askyesno("Confirm", "Regenerate API key? Old key will stop working.",
                                   parent=parent):
            return
        new_key = client_manager.regenerate_api_key(client_id)
        messagebox.showinfo("New API Key", f"New API key:\n{new_key}\n\nCopy it now!", parent=parent)
        self._load_clients()

    def _delete_client(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Select a client first!")
            return
        if messagebox.askyesno("Confirm", "Delete this client? This cannot be undone."):
            client_id = self.tree.item(selection[0])["values"][0]
            client_manager.delete_client(client_id)
            self._load_clients()

    def _export_client_report(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Select a client first!")
            return

        client_id = self.tree.item(selection[0])["values"][0]
        client = client_manager.get_client(client_id)
        if not client:
            return

        from tkinter import filedialog
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile=f"report_{client['name']}.txt"
        )
        if not filepath:
            return

        stats = client_manager.get_client_stats(client_id)
        plan = PLAN_LABELS.get(client.get("plan_type", "starter"), "Starter")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write(f"       CLIENT REPORT - {client['name']}\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Email: {client['email']}\n")
            f.write(f"Company: {client.get('company', 'N/A')}\n")
            f.write(f"Phone: {client.get('phone', 'N/A')}\n")
            f.write(f"Plan: {plan}\n")
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