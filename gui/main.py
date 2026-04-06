"""
gui/main.py - Main window with 8 tabs: Import, Account, Finder, Join, Broadcast, Ban Management, Analytics, Settings
"""
import tkinter as tk
from tkinter import ttk
import sys

from gui.styles import COLORS, FONTS, setup_theme
from gui.import_tab        import ImportTab
from gui.account_tab       import AccountTab
from gui.finder_tab        import FinderTab
from gui.join_tab          import JoinTab
from gui.broadcast_tab     import BroadcastTab
from gui.ban_management_tab import BanManagementTab
from gui.analytics_tab     import AnalyticsTab
from gui.settings_tab      import SettingsTab

BG   = COLORS["bg_dark"]
CYAN = COLORS["primary"]


class SimpleMainWindow:
    """Main window with tab-based navigation."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("TG Pro Quantum")
        self.root.geometry("1280x800")
        self.root.minsize(960, 600)
        self.root.configure(bg=BG)

        setup_theme(root)
        self._build()

    # ─────────────────────────────────────────────────────────────────────────
    def _build(self):
        header = tk.Frame(self.root, bg=COLORS["bg_medium"], height=48)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="⚡ TG Pro Quantum",
            font=FONTS["heading"],
            fg=CYAN,
            bg=COLORS["bg_medium"],
            padx=16,
        ).pack(side="left", fill="y")

        self._notebook = ttk.Notebook(self.root)
        self._notebook.pack(fill="both", expand=True, padx=0, pady=0)

        tab_classes = [
            ImportTab,
            AccountTab,
            FinderTab,
            JoinTab,
            BroadcastTab,
            BanManagementTab,
            AnalyticsTab,
            SettingsTab,
        ]

        self._tabs = []
        for TabClass in tab_classes:
            instance = TabClass(self._notebook, main_window=self)
            self._notebook.add(instance.frame, text=f"  {instance.title}  ")
            self._tabs.append(instance)

        self._status_var = tk.StringVar(value="Ready.")
        status_bar = tk.Frame(self.root, bg=COLORS["bg_medium"], height=24)
        status_bar.pack(fill="x", side="bottom")
        tk.Label(
            status_bar,
            textvariable=self._status_var,
            font=FONTS["small"],
            fg=COLORS["text_muted"],
            bg=COLORS["bg_medium"],
            padx=8,
        ).pack(side="left", fill="y")

    def set_status(self, msg: str):
        self._status_var.set(msg)

    def refresh_account_tab(self):
        """Refresh the Account tab list – called after a successful import."""
        account_tab = self._tabs[1]
        if hasattr(account_tab, "refresh_list"):
            account_tab.refresh_list()


# ─────────────────────────────────────────────────────────────────────────────
def launch():
    """Entry point for the GUI."""
    root = tk.Tk()
    app = SimpleMainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    launch()

