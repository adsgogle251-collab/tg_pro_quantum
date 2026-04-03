"""Login/Logout System - FIXED & PRODUCTION READY"""
import tkinter as tk
from tkinter import ttk, messagebox
from core import log
from core.user_manager import user_manager
from license.manager import check_license, activate_license, load_session, save_session, clear_session
from gui.styles import COLORS, FONTS

class LoginDialog:
    """Modern Login Dialog - FIXED"""
    
    def __init__(self, parent):
        self.parent = parent
        self.result = None
        
        # Check for existing session (auto-login)
        try:
            saved_email = load_session()
            if saved_email:
                license_status = check_license()
                if license_status.get("valid"):
                    user = user_manager.get_user(saved_email)
                    if user:
                        self.result = {"success": True, "user": user, "email": saved_email, "auto_login": True}
                        log(f"Auto-login success: {saved_email}", "success")
                        return
        except Exception as e:
            log(f"Session check error: {e}", "warning")
        
        # Check license first
        try:
            license_status = check_license()
            if not license_status.get("valid"):
                if not self._show_license_activation(license_status):
                    self.result = {"success": False, "error": "License not activated"}
                    return
        except Exception as e:
            log(f"License check error: {e}", "warning")
        
        # Show login dialog
        self._create_login_dialog()
    
    def _show_license_activation(self, license_status):
        """Show license activation when invalid/expired"""
        admin_contact = {
            "email": "admin@tgproquantum.com",
            "whatsapp": "+62 812-3456-7890",
            "telegram": "@tgproquantum"
        }
        
        from license.manager import show_activation as show_act
        return show_act(admin_contact)
    
    def _create_login_dialog(self):
        """Create modern login dialog"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("🔐 Login - TG PRO QUANTUM")
        self.dialog.geometry("500x550")
        self.dialog.configure(bg=COLORS["bg_dark"])
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (550 // 2)
        self.dialog.geometry(f"500x550+{x}+{y}")
        
        # Header
        header_frame = tk.Frame(self.dialog, bg=COLORS["primary"], height=100)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        tk.Label(header_frame, text="🔐", font=("Inter", 40),
                 fg="white", bg=COLORS["primary"]).pack(pady=10)
        tk.Label(header_frame, text="TG PRO QUANTUM", 
                 font=("Inter", 20, "bold"), fg="white", bg=COLORS["primary"]).pack()
        tk.Label(header_frame, text="Enterprise Edition",
                 font=FONTS["small"], fg="white", bg=COLORS["primary"]).pack(pady=(0, 10))
        
        # Login form
        form_frame = tk.Frame(self.dialog, bg=COLORS["bg_medium"])
        form_frame.pack(fill="both", expand=True, padx=30, pady=20)
        
        # Email
        tk.Label(form_frame, text="Email:", fg=COLORS["text"],
                bg=COLORS["bg_medium"], font=FONTS["normal"]).pack(anchor="w", pady=(10, 5))
        self.email_entry = tk.Entry(form_frame, width=40, bg=COLORS["bg_light"], 
                                     fg=COLORS["text"], font=FONTS["normal"])
        self.email_entry.pack(fill="x", pady=5)
        self.email_entry.insert(0, "admin@tgproquantum.com")
        
        # Password
        tk.Label(form_frame, text="Password:", fg=COLORS["text"],
                bg=COLORS["bg_medium"], font=FONTS["normal"]).pack(anchor="w", pady=(10, 5))
        self.password_entry = tk.Entry(form_frame, width=40, bg=COLORS["bg_light"],
                                        fg=COLORS["text"], font=FONTS["normal"], show="•")
        self.password_entry.pack(fill="x", pady=5)
        self.password_entry.insert(0, "admin123")
        
        # Remember me
        self.remember_var = tk.BooleanVar(value=True)
        tk.Checkbutton(form_frame, text="🔒 Remember me (auto-login)", 
                      variable=self.remember_var, bg=COLORS["bg_medium"],
                      fg=COLORS["text"], selectcolor=COLORS["bg_medium"]).pack(anchor="w", pady=10)
        
        # Login button
        tk.Button(form_frame, text="🔐 Login", command=self._login,
                  bg=COLORS["primary"], fg="white", font=("Inter", 14, "bold"),
                  padx=40, pady=12).pack(pady=20)
        
        # Footer
        tk.Label(self.dialog, text="Default: admin@tgproquantum.com / admin123",
                fg=COLORS["text_muted"], bg=COLORS["bg_dark"],
                font=FONTS["small"]).pack(pady=(0, 10))
        
        # Bind Enter key
        self.dialog.bind('<Return>', lambda e: self._login())
        self.email_entry.focus_set()
    
    def _login(self):
        """Handle login - FIXED"""
        try:
            email = self.email_entry.get().strip()
            password = self.password_entry.get().strip()
            
            if not email or not password:
                messagebox.showerror("Error", "Email and password required!", parent=self.dialog)
                return
            
            # Authenticate user
            auth = user_manager.authenticate(email, password)
            if not auth["success"]:
                messagebox.showerror("Error", auth["error"], parent=self.dialog)
                return
            
            user = auth["user"]
            
            # Check license is valid
            license_status = check_license()
            if not license_status.get("valid"):
                messagebox.showerror("Error", "License validation failed! Please activate license.", parent=self.dialog)
                return
            
            # Save session if remember me
            if self.remember_var.get():
                token = user_manager.create_session(email)
                save_session(email, token)
            
            # SUCCESS - return user data
            self.result = {
                "success": True, 
                "user": user, 
                "email": email,
                "auto_login": False
            }
            log(f"✅ User logged in: {email}", "success")
            self.dialog.destroy()
            
        except Exception as e:
            log(f"Login error: {e}", "error")
            messagebox.showerror("Error", f"Login failed: {str(e)}", parent=self.dialog)
    
    def show(self):
        """Show dialog and return result"""
        if hasattr(self, 'dialog'):
            try:
                self.parent.wait_window(self.dialog)
            except:
                pass
        return self.result if self.result else {"success": False}


class LogoutButton:
    """Logout Button"""
    def __init__(self, parent, on_logout):
        self.parent = parent
        self.on_logout = on_logout
        self.btn = tk.Button(parent, text="🚪 Logout", command=self.on_logout,
                            bg=COLORS["error"], fg="white")
        self.btn.pack(side="right", padx=10, pady=5)


# Global
current_user = None

def get_current_user():
    return current_user

def set_current_user(user):
    global current_user
    current_user = user

__all__ = ["LoginDialog", "LogoutButton", "get_current_user", "set_current_user"]