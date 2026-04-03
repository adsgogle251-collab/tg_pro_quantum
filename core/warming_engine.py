"""Warming Engine - Automated Account Warming (Phase 10)"""
import asyncio
import random
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable
from .utils import log, log_error, DATA_DIR
from .account_manager import account_manager

# Import Telegram engines
try:
    from .engine import join_engine as tg_join_engine
    ENGINE_AVAILABLE = True
except:
    ENGINE_AVAILABLE = False
    log("Telegram engine not available - warming simulation mode", "warning")

class WarmingConfig:
    """Warming configuration"""
    def __init__(self):
        self.target_messages = 50  # Messages to send during warming
        self.delay_min = 30  # Longer delays for new accounts
        self.delay_max = 120
        self.groups_per_day = 10
        self.messages_per_group = 5
        self.warming_duration_days = 7
        self.auto_join_groups = True
        self.simulate_human_behavior = True

class WarmingEngine:
    """Automated account warming system"""
    
    def __init__(self):
        self.config = WarmingConfig()
        self.running = False
        self.warming_accounts = []
        self.progress_callback: Optional[Callable] = None
    
    def configure(self, **kwargs):
        """Configure warming settings"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        log(f"Warming configured: {kwargs}", "info")
    
    async def warm_account(self, 
                           account_name: str,
                           groups: List[str] = None,
                           progress_callback: Callable = None,
                           **kwargs):
        """Warm up a single account"""
        
        self.progress_callback = progress_callback
        self.configure(**kwargs)
        
        log(f"🔥 Starting warming for {account_name}", "success")
        
        # Start warming in account manager
        account_manager.start_warming(account_name, self.config.target_messages)
        
        if not groups:
            # Load joined groups for warming
            groups_file = DATA_DIR / "groups" / "joined.txt"
            if groups_file.exists():
                with open(groups_file, 'r', encoding='utf-8') as f:
                    groups = [line.strip() for line in f if line.strip()]
            else:
                log_error("No groups available for warming")
                return False
        
        # Limit groups for warming
        groups = groups[:self.config.groups_per_day]
        
        messages_sent = 0
        
        try:
            for group in groups:
                if not self.running:
                    break
                
                for i in range(self.config.messages_per_group):
                    if messages_sent >= self.config.target_messages:
                        break
                    
                    # Simulate human behavior
                    if self.config.simulate_human_behavior:
                        # Read messages first (simulate)
                        await asyncio.sleep(random.uniform(5, 15))
                        
                        # Type message (simulate)
                        await asyncio.sleep(random.uniform(3, 10))
                    
                    # Send warming message
                    message = self._generate_warming_message(i)
                    
                    if ENGINE_AVAILABLE:
                        success = await tg_join_engine.send_message(
                            account=account_name,
                            group=group,
                            message=message
                        )
                    else:
                        # Simulation
                        success = True
                        await asyncio.sleep(1)
                    
                    if success:
                        messages_sent += 1
                        account_manager.update_warming_progress(account_name, 1)
                        
                        warming_status = account_manager.get_warming_status(account_name)
                        
                        log(f"✅ Warming message {messages_sent}/{self.config.target_messages} sent", "success")
                        
                        # Progress callback
                        if progress_callback:
                            progress_callback(
                                account=account_name,
                                messages_sent=messages_sent,
                                target_messages=self.config.target_messages,
                                progress=warming_status.get("progress", 0),
                                status="warming"
                            )
                    
                    # Delay between messages (longer for new accounts)
                    delay = random.uniform(self.config.delay_min, self.config.delay_max)
                    await asyncio.sleep(delay)
                
                if messages_sent >= self.config.target_messages:
                    break
            
            # Complete warming
            if messages_sent >= self.config.target_messages:
                account_manager.complete_warming(account_name)
                log(f"✅ Warming completed for {account_name}!", "success")
                
                if progress_callback:
                    progress_callback(
                        account=account_name,
                        messages_sent=messages_sent,
                        target_messages=self.config.target_messages,
                        progress=100,
                        status="completed"
                    )
                
                return True
            else:
                log(f"⚠️ Warming incomplete for {account_name}: {messages_sent}/{self.config.target_messages}", "warning")
                return False
                
        except Exception as e:
            log_error(f"Warming error for {account_name}: {e}")
            return False
    
    def _generate_warming_message(self, index: int) -> str:
        """Generate natural warming messages"""
        messages = [
            "Hello everyone! 👋",
            "Nice to be here!",
            "Thanks for adding me!",
            "Looking forward to connecting with you all!",
            "Great group! 🎉",
            "Happy to join this community!",
            "Greetings from Indonesia! 🇮🇩",
            "Excited to be part of this group!",
            "Hello friends! 😊",
            "Nice meeting you all!"
        ]
        return messages[index % len(messages)]
    
    async def warm_multiple_accounts(self,
                                      accounts: List[str],
                                      groups: List[str] = None,
                                      parallel: int = 3,
                                      progress_callback: Callable = None):
        """Warm multiple accounts in parallel"""
        
        self.running = True
        self.warming_accounts = accounts
        
        log(f"🔥 Starting warming for {len(accounts)} accounts", "success")
        
        # Create tasks for parallel warming
        tasks = []
        for account in accounts:
            task = asyncio.create_task(
                self.warm_account(
                    account_name=account,
                    groups=groups,
                    progress_callback=progress_callback
                )
            )
            tasks.append(task)
            
            # Limit parallel warming
            if len(tasks) >= parallel:
                await asyncio.gather(*tasks)
                tasks = []
        
        # Wait for remaining tasks
        if tasks:
            await asyncio.gather(*tasks)
        
        self.running = False
        
        # Summary
        completed = sum(1 for acc in accounts 
                       if account_manager.get_warming_status(acc).get("completed", False))
        
        log(f"✅ Warming completed: {completed}/{len(accounts)} accounts", "success")
        
        return completed
    
    def start_auto_warming(self, new_accounts: List[str] = None):
        """Start automatic warming for new accounts"""
        
        if not new_accounts:
            # Find all level 1 accounts that aren't warming
            all_accounts = account_manager.get_all()
            new_accounts = [
                acc["name"] for acc in all_accounts
                if acc.get("level", 1) == 1
                and acc.get("status") != "warming"
            ]
        
        if new_accounts:
            log(f"Auto-warming started for {len(new_accounts)} new accounts", "success")
            
            # Start warming in background
            asyncio.create_task(self.warm_multiple_accounts(new_accounts))
        else:
            log("No new accounts need warming", "info")
    
    def get_warming_summary(self) -> dict:
        """Get warming summary for all accounts"""
        
        all_accounts = account_manager.get_all()
        warming_accounts = []
        completed_accounts = []
        not_started_accounts = []
        
        for acc in all_accounts:
            status = account_manager.get_warming_status(acc["name"])
            
            if status.get("completed", True):
                completed_accounts.append(acc["name"])
            elif status.get("enabled", False):
                warming_accounts.append({
                    "name": acc["name"],
                    "progress": status.get("progress", 0),
                    "messages_sent": status.get("messages_sent", 0),
                    "target_messages": status.get("target_messages", 0)
                })
            else:
                not_started_accounts.append(acc["name"])
        
        return {
            "total_accounts": len(all_accounts),
            "warming": warming_accounts,
            "completed": completed_accounts,
            "not_started": not_started_accounts,
            "warming_count": len(warming_accounts),
            "completed_count": len(completed_accounts),
            "not_started_count": len(not_started_accounts)
        }
    
    def stop(self):
        """Stop warming process"""
        self.running = False
        log("Warming stopped", "warning")


# Global instance
warming_engine = WarmingEngine()
__all__ = ["WarmingEngine", "warming_engine", "WarmingConfig"]