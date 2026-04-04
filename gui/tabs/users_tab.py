"""Users Tab - Complete with Scrollable Content (Phase 8)"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from core import log
from core.user_manager import user_manager
from gui.styles import COLORS, FONTS
from core.localization import t

class UsersTab:
    title = "👥 Users"
    
    def __init__(self, parent, main_window=None):
        self.parent = parent
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        self._create_widgets()
        self._load_users()
    
    def _create_widgets(self):
        # Header
        tk.Label(self.frame, text=f"👥 {t('User Management')}", font=("Segoe UI", 24, "bold"),
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
        
        # === 1. TOOLBAR ===
        toolbar = tk.Frame(self.scrollable_frame, bg=COLORS["bg_dark"])
        toolbar.pack(fill="x", padx=10, pady=10)
        
        tk.Button(toolbar, text="➕ Add User", command=self._add_user,
                  bg=COLORS["success"], fg="white", font=FONTS["bold"]).pack(side="left", padx=5)
        tk.Button(toolbar, text="🔄 Refresh", command=self._load_users,
                  bg=COLORS["bg_light"], fg=COLORS["text"], font=FONTS["bold"]).pack(side="left", padx=5)
        
        # === 2. USER LIST ===
        list_frame = tk.LabelFrame(self.scrollable_frame, text="📋 All Users",
                                   fg=COLORS["accent"], bg=COLORS["bg_medium"],
                                   font=FONTS["heading"])
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        columns = ("Email", "Name", "Role", "Created", "Status")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=12)
        
        for col in columns:
            self.tree.heading(col, text=col)
            width = 200 if col not in ["Role", "Status"] else 120
            self.tree.column(col, width=width)
        
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)
        
        # === 3. ACTION BUTTONS ===
        btn_frame = tk.Frame(self.scrollable_frame, bg=COLORS["bg_dark"])
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Button(btn_frame, text="✏️ Edit User", command=self._edit_user,
                  bg=COLORS["info"], fg="white", font=FONTS["bold"]).pack(side="left", padx=5)
        tk.Button(btn_frame, text="🗑️ Delete User", command=self._delete_user,
                  bg=COLORS["error"], fg="white", font=FONTS["bold"]).pack(side="left", padx=5)
        tk.Button(btn_frame, text="🔑 Reset Password", command=self._reset_password,
                  bg=COLORS["warning"], fg="white", font=FONTS["bold"]).pack(side="left", padx=5)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _load_users(self):
        """Load all users"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        users = user_manager.get_all_users()
        for user in users:
            self.tree.insert("", "end", values=(
                user.get('email', 'N/A'),
                user.get('name', 'N/A'),
                user.get('role', 'member'),
                user.get('created', 'N/A')[:10],
                user.get('status', 'active')
            ))
    
    def _add_user(self):
        """Add new user"""
        dialog = tk.Toplevel(self.frame)
        dialog.title("➕ Add User")
        dialog.geometry("400x350")
        dialog.configure(bg=COLORS["bg_dark"])
        
        tk.Label(dialog, text="➕ Add User", font=("Segoe UI", 18, "bold"),
                 fg=COLORS["primary"], bg=COLORS["bg_dark"]).pack(pady=15)
        
        tk.Label(dialog, text="Email:", fg=COLORS["text"], bg=COLORS["bg_dark"]).pack(pady=5)
        email_entry = tk.Entry(dialog, width=40, bg=COLORS["bg_light"], fg=COLORS["text"])
        email_entry.pack(pady=5)
        
        tk.Label(dialog, text="Name:", fg=COLORS["text"], bg=COLORS["bg_dark"]).pack(pady=5)
        name_entry = tk.Entry(dialog, width=40, bg=COLORS["bg_light"], fg=COLORS["text"])
        name_entry.pack(pady=5)
        
        tk.Label(dialog, text="Password:", fg=COLORS["text"], bg=COLORS["bg_dark"]).pack(pady=5)
        password_entry = tk.Entry(dialog, width=40, bg=COLORS["bg_light"], fg=COLORS["text"], show="•")
        password_entry.pack(pady=5)
        
        def save():
            email = email_entry.get().strip()
            name = name_entry.get().strip()
            password = password_entry.get().strip()
            
            if not email or not password:
                messagebox.showerror("Error", "Email and password required!")
                return
            
            user_manager.add_user(email, password, name, "member")
            messagebox.showinfo("Success", "User added!")
            self._load_users()
            dialog.destroy()
        
        tk.Button(dialog, text="💾 Save", command=save,
                  bg=COLORS["success"], fg="white", font=FONTS["bold"],
                  padx=30, pady=10).pack(pady=20)
    
    def _edit_user(self):
        """Edit user"""
        messagebox.showinfo("Info", "Edit user feature - implement dialog")
    
    def _delete_user(self):
        """Delete user"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Select a user first!")
            return
        
        if messagebox.askyesno("Confirm", "Delete this user?"):
            email = self.tree.item(selection[0])["values"][0]
            user_manager.delete_user(email)
            self._load_users()
    
    def _reset_password(self):
        """Reset user password"""
        messagebox.showinfo("Info", "Reset password feature - implement dialog")
    
    def _refresh(self):
        self._load_users()