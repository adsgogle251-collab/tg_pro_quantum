"""Account Groups Tab - Enterprise Account Pool Management"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog, scrolledtext as _scrolledtext
from core import log, account_manager
from core.account_group_manager import account_group_manager, FEATURE_TYPES
from gui.styles import COLORS, FONTS

FEATURE_LABELS = {
    "broadcast": "📢 Broadcast",
    "finder":    "🔍 Finder",
    "scrape":    "📥 Scrape",
    "join":      "📤 Join",
    "cs":        "💬 CS/AI",
    "warmer":    "🔥 Warmer",
    "general":   "📁 General",
}

STATUS_COLORS = {
    "active":   "#00FF41",
    "paused":   "#FFB800",
    "archived": "#718096",
}


class AccountGroupsTab:
    title = "📂 Account Groups"

    def __init__(self, parent, main_window=None):
        self.parent = parent
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        self.selected_group_id = None

        self._create_widgets()
        self._load_groups()

    # ─────────────────────────────────────────────────────────────────
    # UI BUILD
    # ─────────────────────────────────────────────────────────────────

    def _create_widgets(self):
        BG = COLORS["bg_dark"]
        PANEL = COLORS["bg_medium"]
        CYAN = COLORS["primary"]
        TEXT = COLORS["text"]

        # ── Header ───────────────────────────────────────────────────
        header = tk.Frame(self.frame, bg="#1a1a2e", height=55)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header, text="📂 Account Groups", font=FONTS["title"],
                 fg=CYAN, bg="#1a1a2e").pack(side="left", padx=20, pady=15)

        # Quick stats
        self.stats_lbl = tk.Label(header, text="Groups: 0 | Accounts: 0",
                                   font=FONTS["small"], fg=COLORS["text_muted"],
                                   bg="#1a1a2e")
        self.stats_lbl.pack(side="right", padx=20)

        # ── Main split layout ─────────────────────────────────────────
        body = tk.Frame(self.frame, bg=BG)
        body.pack(fill="both", expand=True, padx=10, pady=5)

        # LEFT: group list panel
        left_panel = tk.Frame(body, bg=PANEL, width=320)
        left_panel.pack(side="left", fill="y", padx=(0, 5))
        left_panel.pack_propagate(False)

        self._build_group_list_panel(left_panel, PANEL, CYAN, TEXT)

        # RIGHT: group detail panel
        self.detail_panel = tk.Frame(body, bg=PANEL)
        self.detail_panel.pack(side="left", fill="both", expand=True)

        self._build_detail_panel(self.detail_panel, PANEL, CYAN, TEXT)

    # ── Left: Group List ──────────────────────────────────────────────

    def _build_group_list_panel(self, parent, bg, cyan, text):
        # Toolbar
        tb = tk.Frame(parent, bg=bg)
        tb.pack(fill="x", padx=8, pady=8)

        tk.Button(tb, text="➕ New Group", bg=COLORS["success"], fg="#000",
                  font=FONTS["bold"], bd=0, padx=8, pady=5,
                  command=self._create_group).pack(side="left", padx=2)

        tk.Button(tb, text="🗑️", bg=COLORS["error"], fg="#fff",
                  font=FONTS["bold"], bd=0, padx=8, pady=5,
                  command=self._delete_group).pack(side="left", padx=2)

        tk.Button(tb, text="🔄", bg=COLORS["bg_light"], fg=cyan,
                  font=FONTS["bold"], bd=0, padx=8, pady=5,
                  command=self._load_groups).pack(side="right", padx=2)

        # Feature filter
        filter_frame = tk.Frame(parent, bg=bg)
        filter_frame.pack(fill="x", padx=8, pady=(0, 4))

        tk.Label(filter_frame, text="Feature:", bg=bg, fg=text,
                 font=FONTS["small"]).pack(side="left")

        self.feature_filter_var = tk.StringVar(value="All")
        feature_options = ["All"] + [FEATURE_LABELS.get(f, f) for f in FEATURE_TYPES]
        self.feature_filter_combo = ttk.Combobox(filter_frame, textvariable=self.feature_filter_var,
                                                  values=feature_options, width=18, state="readonly")
        self.feature_filter_combo.pack(side="left", padx=4)
        self.feature_filter_combo.bind("<<ComboboxSelected>>", lambda _e: self._load_groups())

        # Group listbox with scrollbar
        list_frame = tk.Frame(parent, bg=bg)
        list_frame.pack(fill="both", expand=True, padx=8, pady=4)

        self.group_listbox = tk.Listbox(list_frame, bg="#16213e", fg=text,
                                         selectbackground=COLORS["primary_light"],
                                         selectforeground=cyan,
                                         font=FONTS["normal"], bd=0,
                                         activestyle="none")
        sb = ttk.Scrollbar(list_frame, orient="vertical", command=self.group_listbox.yview)
        self.group_listbox.configure(yscrollcommand=sb.set)
        self.group_listbox.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.group_listbox.bind("<<ListboxSelect>>", self._on_group_select)

    # ── Right: Group Detail ───────────────────────────────────────────

    def _build_detail_panel(self, parent, bg, cyan, text):
        # Placeholder shown when no group is selected
        self.no_selection_lbl = tk.Label(parent,
                                          text="← Select a group to manage accounts",
                                          font=FONTS["normal"], fg=COLORS["text_muted"],
                                          bg=bg)
        self.no_selection_lbl.place(relx=0.5, rely=0.5, anchor="center")

        # Detail content (hidden until group is selected)
        self.detail_content = tk.Frame(parent, bg=bg)

        # Group info header
        info_bar = tk.Frame(self.detail_content, bg="#1a1a2e", height=55)
        info_bar.pack(fill="x")
        info_bar.pack_propagate(False)

        self.detail_name_lbl = tk.Label(info_bar, text="", font=FONTS["heading"],
                                         fg=cyan, bg="#1a1a2e")
        self.detail_name_lbl.pack(side="left", padx=15, pady=10)

        self.detail_meta_lbl = tk.Label(info_bar, text="", font=FONTS["small"],
                                         fg=COLORS["text_muted"], bg="#1a1a2e")
        self.detail_meta_lbl.pack(side="left", padx=10)

        # Toolbar for accounts
        acc_tb = tk.Frame(self.detail_content, bg=bg)
        acc_tb.pack(fill="x", padx=10, pady=6)

        tk.Button(acc_tb, text="➕ Add Account", bg=COLORS["success"], fg="#000",
                  font=FONTS["bold"], bd=0, padx=8, pady=5,
                  command=self._add_account).pack(side="left", padx=2)

        tk.Button(acc_tb, text="📥 Bulk Import", bg=COLORS["secondary"], fg="#fff",
                  font=FONTS["bold"], bd=0, padx=8, pady=5,
                  command=self._bulk_import).pack(side="left", padx=2)

        tk.Button(acc_tb, text="📤 Export", bg=COLORS["bg_light"], fg=cyan,
                  font=FONTS["bold"], bd=0, padx=8, pady=5,
                  command=self._export_accounts).pack(side="left", padx=2)

        tk.Button(acc_tb, text="🗑️ Remove", bg=COLORS["error"], fg="#fff",
                  font=FONTS["bold"], bd=0, padx=8, pady=5,
                  command=self._remove_account).pack(side="left", padx=2)

        tk.Button(acc_tb, text="🔄 Refresh", bg=COLORS["bg_light"], fg=cyan,
                  font=FONTS["bold"], bd=0, padx=8, pady=5,
                  command=self._load_group_accounts).pack(side="right", padx=2)

        # Stats row
        stats_row = tk.Frame(self.detail_content, bg=COLORS["bg_light"])
        stats_row.pack(fill="x", padx=10, pady=(0, 4))

        self.stat_total = self._make_stat_label(stats_row, "Total", "0")
        self.stat_healthy = self._make_stat_label(stats_row, "Healthy", "0", COLORS["success"])
        self.stat_warning = self._make_stat_label(stats_row, "Warning", "0", COLORS["warning"])
        self.stat_banned = self._make_stat_label(stats_row, "Banned", "0", COLORS["error"])

        # Account treeview
        tree_frame = tk.Frame(self.detail_content, bg=bg)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=4)

        cols = ("name", "phone", "status", "health", "features")
        self.account_tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                          selectmode="extended")

        headers = {
            "name":     ("Account Name", 180),
            "phone":    ("Phone", 130),
            "status":   ("Status", 90),
            "health":   ("Health %", 80),
            "features": ("Features", 200),
        }
        for col, (label, width) in headers.items():
            self.account_tree.heading(col, text=label)
            self.account_tree.column(col, width=width, anchor="w")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.account_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.account_tree.xview)
        self.account_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.account_tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")

        # Edit group settings section
        edit_frame = tk.LabelFrame(self.detail_content, text="⚙️ Group Settings",
                                    bg=bg, fg=cyan, font=FONTS["subheading"])
        edit_frame.pack(fill="x", padx=10, pady=6)

        row1 = tk.Frame(edit_frame, bg=bg)
        row1.pack(fill="x", padx=10, pady=6)

        tk.Label(row1, text="Name:", bg=bg, fg=text, font=FONTS["small"]).pack(side="left")
        self.edit_name_var = tk.StringVar()
        tk.Entry(row1, textvariable=self.edit_name_var, width=25,
                 bg=COLORS["bg_light"], fg=text, font=FONTS["normal"],
                 insertbackground=cyan).pack(side="left", padx=6)

        tk.Label(row1, text="Feature:", bg=bg, fg=text, font=FONTS["small"]).pack(side="left", padx=(15, 0))
        self.edit_feature_var = tk.StringVar()
        feature_vals = [FEATURE_LABELS.get(f, f) for f in FEATURE_TYPES]
        self.edit_feature_combo = ttk.Combobox(row1, textvariable=self.edit_feature_var,
                                                values=feature_vals, width=18, state="readonly")
        self.edit_feature_combo.pack(side="left", padx=4)

        tk.Button(row1, text="💾 Save", bg=COLORS["primary"], fg="#000",
                  font=FONTS["bold"], bd=0, padx=10, pady=4,
                  command=self._save_group_settings).pack(side="left", padx=10)

    def _make_stat_label(self, parent, label, value, color=None):
        frame = tk.Frame(parent, bg=COLORS["bg_light"])
        frame.pack(side="left", padx=10, pady=6)
        tk.Label(frame, text=label, font=FONTS["small"], fg=COLORS["text_muted"],
                 bg=COLORS["bg_light"]).pack()
        val_lbl = tk.Label(frame, text=value, font=FONTS["bold"],
                            fg=color or COLORS["text"], bg=COLORS["bg_light"])
        val_lbl.pack()
        return val_lbl

    # ─────────────────────────────────────────────────────────────────
    # DATA LOADING
    # ─────────────────────────────────────────────────────────────────

    def _load_groups(self):
        self.group_listbox.delete(0, "end")
        self._group_ids = []

        selected_feature = self.feature_filter_var.get() if hasattr(self, "feature_filter_var") else "All"

        groups = account_group_manager.get_all_groups()

        # Apply feature filter
        if selected_feature != "All":
            # Map back label to key
            reverse_map = {v: k for k, v in FEATURE_LABELS.items()}
            feature_key = reverse_map.get(selected_feature, selected_feature)
            groups = [g for g in groups if g.get("feature_type") == feature_key]

        total_accounts = sum(len(g.get("accounts", [])) for g in groups)
        self.stats_lbl.config(text=f"Groups: {len(groups)} | Accounts: {total_accounts}")

        for g in groups:
            feature_label = FEATURE_LABELS.get(g.get("feature_type", "general"), "📁 General")
            count = len(g.get("accounts", []))
            status = g.get("status", "active")
            display = f"  {g['name']}  [{feature_label}] ({count} accs)"
            self.group_listbox.insert("end", display)
            self._group_ids.append(g["id"])

    def _on_group_select(self, event=None):
        sel = self.group_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self._group_ids):
            return
        self.selected_group_id = self._group_ids[idx]
        self._show_group_detail(self.selected_group_id)

    def _show_group_detail(self, group_id: str):
        group = account_group_manager.get_group(group_id)
        if not group:
            return

        # Show detail panel
        self.no_selection_lbl.place_forget()
        self.detail_content.pack(fill="both", expand=True)

        feature_label = FEATURE_LABELS.get(group.get("feature_type", "general"), "General")
        self.detail_name_lbl.config(text=f"📂 {group['name']}")
        self.detail_meta_lbl.config(
            text=f"{feature_label} | Status: {group.get('status','active')} | ID: {group['id']}"
        )

        # Populate edit fields
        self.edit_name_var.set(group["name"])
        feature_key = group.get("feature_type", "general")
        self.edit_feature_var.set(FEATURE_LABELS.get(feature_key, "📁 General"))

        # Health stats
        health = group.get("health", {})
        self.stat_total.config(text=str(health.get("total", 0)))
        self.stat_healthy.config(text=str(health.get("healthy", 0)))
        self.stat_warning.config(text=str(health.get("warning", 0)))
        self.stat_banned.config(text=str(health.get("banned", 0)))

        self._load_group_accounts()

    def _load_group_accounts(self):
        if not self.selected_group_id:
            return
        for item in self.account_tree.get_children():
            self.account_tree.delete(item)

        accounts_list = account_group_manager.get_group_accounts(self.selected_group_id)
        all_accounts = {a.get("name", ""): a for a in account_manager.get_all()}

        for name in accounts_list:
            acc = all_accounts.get(name, {})
            phone = acc.get("phone", "-")
            status = acc.get("status", "active")
            health = acc.get("health_score", 100)
            features = ", ".join(acc.get("features", []))
            self.account_tree.insert("", "end", values=(name, phone, status, f"{health}%", features))

    # ─────────────────────────────────────────────────────────────────
    # GROUP ACTIONS
    # ─────────────────────────────────────────────────────────────────

    def _create_group(self):
        name = simpledialog.askstring("New Group", "Enter group name:", parent=self.frame)
        if not name or not name.strip():
            return

        # Ask for feature type
        win = tk.Toplevel(self.frame)
        win.title("Select Feature Type")
        win.configure(bg=COLORS["bg_dark"])
        win.geometry("320x200")
        win.resizable(False, False)

        tk.Label(win, text="Feature Type:", font=FONTS["normal"],
                 fg=COLORS["text"], bg=COLORS["bg_dark"]).pack(pady=10)

        feature_var = tk.StringVar(value="📁 General")
        feature_vals = [FEATURE_LABELS.get(f, f) for f in FEATURE_TYPES]
        ttk.Combobox(win, textvariable=feature_var, values=feature_vals,
                     width=28, state="readonly").pack(pady=5)

        def confirm():
            reverse_map = {v: k for k, v in FEATURE_LABELS.items()}
            ftype = reverse_map.get(feature_var.get(), "general")
            gid = account_group_manager.create_group(name.strip(), feature_type=ftype)
            log(f"Created group '{name}' ({gid})", "success")
            win.destroy()
            self._load_groups()

        tk.Button(win, text="✅ Create", bg=COLORS["success"], fg="#000",
                  font=FONTS["bold"], bd=0, padx=15, pady=8,
                  command=confirm).pack(pady=15)

    def _delete_group(self):
        if not self.selected_group_id:
            messagebox.showwarning("No Selection", "Please select a group first.")
            return
        group = account_group_manager.get_group(self.selected_group_id)
        if not group:
            return
        if not messagebox.askyesno("Delete Group",
                                    f"Delete group '{group['name']}'?\nThis will remove all account assignments."):
            return
        account_group_manager.delete_group(self.selected_group_id)
        self.selected_group_id = None
        self.detail_content.pack_forget()
        self.no_selection_lbl.place(relx=0.5, rely=0.5, anchor="center")
        self._load_groups()
        log(f"Group deleted", "info")

    def _save_group_settings(self):
        if not self.selected_group_id:
            return
        name = self.edit_name_var.get().strip()
        if not name:
            messagebox.showerror("Error", "Group name cannot be empty.")
            return
        reverse_map = {v: k for k, v in FEATURE_LABELS.items()}
        ftype = reverse_map.get(self.edit_feature_var.get(), "general")
        account_group_manager.update_group(self.selected_group_id, name=name, feature_type=ftype)
        messagebox.showinfo("Saved", "Group settings saved.")
        self._load_groups()
        self._show_group_detail(self.selected_group_id)

    # ─────────────────────────────────────────────────────────────────
    # ACCOUNT ACTIONS
    # ─────────────────────────────────────────────────────────────────

    def _add_account(self):
        if not self.selected_group_id:
            messagebox.showwarning("No Group", "Select a group first.")
            return

        all_accounts = account_manager.get_all()
        if not all_accounts:
            messagebox.showinfo("No Accounts", "No accounts available. Add accounts in the Accounts tab first.")
            return

        # Show selection dialog
        win = tk.Toplevel(self.frame)
        win.title("Add Account to Group")
        win.configure(bg=COLORS["bg_dark"])
        win.geometry("400x450")

        tk.Label(win, text="Select accounts to add:", font=FONTS["normal"],
                 fg=COLORS["text"], bg=COLORS["bg_dark"]).pack(pady=10)

        listbox = tk.Listbox(win, selectmode="extended", bg="#16213e",
                              fg=COLORS["text"], font=FONTS["normal"], bd=0)
        listbox.pack(fill="both", expand=True, padx=15, pady=5)

        current = set(account_group_manager.get_group_accounts(self.selected_group_id))
        acc_names = []
        for acc in all_accounts:
            name = acc.get("name", "")
            if name not in current:
                listbox.insert("end", f"  {name}  ({acc.get('phone','-')})")
                acc_names.append(name)

        def confirm():
            sel = listbox.curselection()
            if not sel:
                return
            added = 0
            for i in sel:
                account_group_manager.add_account(self.selected_group_id, acc_names[i])
                added += 1
            win.destroy()
            self._load_group_accounts()
            self._load_groups()
            log(f"Added {added} accounts to group", "success")

        tk.Button(win, text=f"➕ Add Selected", bg=COLORS["success"], fg="#000",
                  font=FONTS["bold"], bd=0, padx=15, pady=8,
                  command=confirm).pack(pady=10)

    def _bulk_import(self):
        if not self.selected_group_id:
            messagebox.showwarning("No Group", "Select a group first.")
            return

        win = tk.Toplevel(self.frame)
        win.title("Bulk Import Accounts")
        win.configure(bg=COLORS["bg_dark"])
        win.geometry("500x400")

        tk.Label(win, text="Paste account names (one per line / comma separated):",
                 font=FONTS["normal"], fg=COLORS["text"], bg=COLORS["bg_dark"]).pack(pady=10)

        text_widget = _scrolledtext.ScrolledText(win, height=12, bg="#16213e", fg=COLORS["text"],
                                                  font=FONTS["mono"])
        text_widget.pack(fill="both", expand=True, padx=15, pady=5)

        def from_file():
            path = filedialog.askopenfilename(
                title="Select account list file",
                filetypes=[("Text files", "*.txt"), ("CSV files", "*.csv"), ("All", "*.*")]
            )
            if path:
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    text_widget.delete("1.0", "end")
                    text_widget.insert("1.0", content)
                except Exception as e:
                    messagebox.showerror("Error", f"Could not read file: {e}")

        btn_row = tk.Frame(win, bg=COLORS["bg_dark"])
        btn_row.pack(pady=8)

        tk.Button(btn_row, text="📁 From File", bg=COLORS["bg_light"], fg=COLORS["text"],
                  font=FONTS["bold"], bd=0, padx=10, pady=6,
                  command=from_file).pack(side="left", padx=5)

        def confirm_import():
            text = text_widget.get("1.0", "end").strip()
            if not text:
                return
            added = account_group_manager.import_accounts_from_text(self.selected_group_id, text)
            win.destroy()
            self._load_group_accounts()
            self._load_groups()
            messagebox.showinfo("Import Complete", f"Imported {added} new accounts.")

        tk.Button(btn_row, text="📥 Import", bg=COLORS["success"], fg="#000",
                  font=FONTS["bold"], bd=0, padx=15, pady=6,
                  command=confirm_import).pack(side="left", padx=5)

    def _remove_account(self):
        if not self.selected_group_id:
            return
        sel = self.account_tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Select accounts to remove.")
            return
        names = [self.account_tree.item(s, "values")[0] for s in sel]
        if not messagebox.askyesno("Remove", f"Remove {len(names)} account(s) from this group?"):
            return
        for name in names:
            account_group_manager.remove_account(self.selected_group_id, name)
        self._load_group_accounts()
        self._load_groups()

    def _export_accounts(self):
        if not self.selected_group_id:
            messagebox.showwarning("No Group", "Select a group first.")
            return
        text = account_group_manager.export_group_accounts(self.selected_group_id)
        if not text:
            messagebox.showinfo("Empty Group", "This group has no accounts to export.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("CSV files", "*.csv")],
            title="Export accounts"
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
                messagebox.showinfo("Exported", f"Accounts exported to {path}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save file: {e}")

    # Called when tab is activated
    def _on_tab_selected(self):
        self._load_groups()
