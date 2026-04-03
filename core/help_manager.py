"""Help Manager - In-App Documentation & Help System"""
import json
from pathlib import Path
from .utils import DATA_DIR, log

HELP_FILE = DATA_DIR / "help.json"

class HelpManager:
    def __init__(self):
        self.help_file = HELP_FILE
        self.help_data = self._load()
    
    def _load(self):
        """Load help data from file or use defaults"""
        if self.help_file.exists():
            try:
                with open(self.help_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        # Default help content
        return {
            "tabs": {
                "dashboard": {
                    "title": "📊 Dashboard",
                    "description": "Overview of system status and statistics",
                    "steps": [
                        "View real-time system status",
                        "Check account distribution",
                        "Monitor broadcast statistics",
                        "Access setup guide for new users"
                    ]
                },
                "accounts": {
                    "title": "📱 Accounts",
                    "description": "Manage Telegram accounts and groups",
                    "steps": [
                        "Add accounts manually or import from files",
                        "Create account groups for different clients",
                        "Assign accounts to features (Broadcast, Finder, etc.)",
                        "Filter and search accounts"
                    ]
                },
                "broadcast": {
                    "title": "📢 Broadcast",
                    "description": "Send messages to multiple groups",
                    "steps": [
                        "Select campaign or create manual broadcast",
                        "Choose account group to use",
                        "Configure delay and round-robin settings",
                        "Start broadcast and monitor progress"
                    ]
                },
                "campaign": {
                    "title": "📈 Campaigns",
                    "description": "Create and manage broadcast campaigns",
                    "steps": [
                        "Create new campaign with name and message",
                        "Select accounts and target groups",
                        "Configure timing and scheduling",
                        "Save and run campaigns"
                    ]
                },
                "finder": {
                    "title": "🔍 Finder",
                    "description": "Find Telegram groups by keywords",
                    "steps": [
                        "Enter seed keywords",
                        "Generate keyword variations",
                        "Search for groups",
                        "Save results to valid.txt"
                    ]
                },
                "join": {
                    "title": "📤 Join",
                    "description": "Join Telegram groups automatically",
                    "steps": [
                        "Select group source (valid.txt or custom)",
                        "Assign accounts for joining",
                        "Configure smart join settings",
                        "Start joining groups"
                    ]
                },
                "scrape": {
                    "title": "📥 Scrape",
                    "description": "Scrape members from groups",
                    "steps": [
                        "Assign accounts to scrape feature",
                        "Select target groups",
                        "Configure filters (bots, deleted)",
                        "Export scraped members"
                    ]
                }
            },
            "faq": [
                {
                    "question": "How do I add accounts?",
                    "answer": "Go to Accounts tab → Click 'Add Accounts' → Choose Single or Bulk mode → Enter account details"
                },
                {
                    "question": "How do I create a broadcast campaign?",
                    "answer": "Go to Campaigns tab → Click 'New Campaign' → Enter name and message → Select accounts and groups → Save"
                },
                {
                    "question": "How do I find groups to broadcast?",
                    "answer": "Go to Finder tab → Enter keywords → Generate variations → Start search → Results saved to groups/valid.txt"
                },
                {
                    "question": "How do I join groups?",
                    "answer": "Go to Join tab → Select source (valid.txt) → Assign accounts → Start Join → Joined groups saved to groups/joined.txt"
                },
                {
                    "question": "How do I schedule broadcasts?",
                    "answer": "Go to Campaigns tab → Create campaign → Select 'Schedule for Later' → Set date/time → Save"
                }
            ],
            "shortcuts": [
                {"key": "F1", "action": "Open Help"},
                {"key": "Ctrl+S", "action": "Save current settings"},
                {"key": "Ctrl+R", "action": "Refresh current tab"},
                {"key": "Ctrl+Q", "action": "Quick broadcast"}
            ]
        }
    
    def get_tab_help(self, tab_name: str) -> dict:
        """Get help content for a specific tab"""
        return self.help_data.get("tabs", {}).get(tab_name, {})
    
    def get_faq(self) -> list:
        """Get FAQ list"""
        return self.help_data.get("faq", [])
    
    def get_shortcuts(self) -> list:
        """Get keyboard shortcuts"""
        return self.help_data.get("shortcuts", [])
    
    def search_help(self, query: str) -> list:
        """Search help content"""
        results = []
        query = query.lower()
        
        for tab_name, tab_help in self.help_data.get("tabs", {}).items():
            if query in tab_help.get("title", "").lower() or query in tab_help.get("description", "").lower():
                results.append({"type": "tab", "name": tab_name, "data": tab_help})
        
        for faq in self.help_data.get("faq", []):
            if query in faq.get("question", "").lower() or query in faq.get("answer", "").lower():
                results.append({"type": "faq", "data": faq})
        
        return results


# Global instance
help_manager = HelpManager()
__all__ = ["HelpManager", "help_manager"]