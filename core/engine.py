"""TG PRO QUANTUM - Complete Engine Module (Broadcast, Join, Scrape)"""
import asyncio
import random
from datetime import datetime
from .utils import log, log_error, DATA_DIR
from . import statistics

# ==================== BROADCAST ENGINE ====================

broadcast_engine = None

class BroadcastEngine:
    def __init__(self):
        self._running = False
        self._paused = False
        self._session = None
    
    def init(self, api_id: int, api_hash: str):
        """Initialize Telegram client"""
        log(f"Broadcast engine initialized with API ID: {api_id}", "info")
    
    def stop(self):
        """Stop broadcast"""
        self._running = False
        log("Broadcast stopped", "warning")
    
    async def run(self, campaign_id=None, accounts=None, message=None, 
                  groups=None, delay_min=10, delay_max=30, 
                  round_robin=True, auto_scrape=False, 
                  progress_callback=None, **kwargs):
        """
        Enhanced broadcast engine with campaign support
        """
        
        # LOAD CAMPAIGN SETTINGS if campaign_id provided
        if campaign_id:
            try:
                from core.campaign_manager import campaign_manager
                campaign = campaign_manager.get_campaign(campaign_id)
                
                if campaign:
                    if accounts is None:
                        accounts = campaign.account_ids
                    if message is None:
                        message = campaign.message.text
                    if groups is None and campaign.group_ids:
                        groups = campaign.group_ids
                    delay_min = campaign.settings.delay_min
                    delay_max = campaign.settings.delay_max
                    round_robin = campaign.settings.round_robin
            except Exception as e:
                log_error(f"Failed to load campaign: {e}")
        
        # VALIDATE required parameters
        if not accounts:
            log("❌ Broadcast failed: No accounts specified", "error")
            if progress_callback:
                progress_callback(error="No accounts specified")
            return False
        
        if not message:
            log("❌ Broadcast failed: No message specified", "error")
            if progress_callback:
                progress_callback(error="No message specified")
            return False
        
        # DETERMINE target groups
        if groups is None:
            from core.utils import load_groups
            groups = load_groups()
        
        if not groups:
            log("❌ Broadcast failed: No target groups", "error")
            if progress_callback:
                progress_callback(error="No target groups")
            return False
        
        # INITIALIZE tracking
        self._running = True
        self._paused = False
        sent = 0
        failed = 0
        total = len(groups)
        account_index = 0
        
        log(f"📢 Starting broadcast: {len(accounts)} accounts, {len(groups)} groups", "info")
        
        # EXECUTE broadcast loop
        for group in groups:
            if not self._running:
                log("⏹️ Broadcast stopped by user", "warning")
                break
            
            while self._paused:
                await asyncio.sleep(1)
                if not self._running:
                    break
            
            # SELECT account (round-robin)
            if round_robin and len(accounts) > 1:
                account_name = accounts[account_index % len(accounts)]
                account_index += 1
            else:
                account_name = accounts[0] if accounts else None
            
            if not account_name:
                continue
            
            try:
                # SEND message (SIMULATED)
                success = await self._send_message(account_name, group, message)
                
                if success:
                    sent += 1
                    log(f"✅ Sent to {group} via {account_name}", "success")
                    statistics.increment_sent()
                else:
                    failed += 1
                    log(f"❌ Failed to send to {group}", "error")
                    statistics.increment_failed()
                
                # AUTO-SCRAPE if enabled
                if auto_scrape:
                    try:
                        from core import scrape_engine
                        members = await scrape_engine.scrape_group(account_name, group)
                        if members:
                            from core.utils import save_scraped_members
                            save_scraped_members(group, members)
                            log(f"📥 Scraped {len(members)} members from {group}", "success")
                    except Exception as scrape_error:
                        log(f"Scrape error: {scrape_error}", "warning")
                
                # PROGRESS CALLBACK
                if progress_callback:
                    try:
                        progress_callback(
                            sent=sent,
                            failed=failed, 
                            total=total,
                            current_group=group,
                            current_account=account_name,
                            progress_percent=(sent + failed) / total * 100
                        )
                    except Exception as cb_error:
                        log(f"Progress callback error: {cb_error}", "warning")
                
                # DELAY
                delay = random.uniform(delay_min, delay_max)
                await asyncio.sleep(delay)
                
            except Exception as e:
                failed += 1
                log(f"❌ Error broadcasting to {group}: {e}", "error")
                statistics.increment_failed()
                if progress_callback:
                    progress_callback(error=str(e), current_group=group)
        
        # FINAL callback
        if progress_callback:
            progress_callback(
                completed=True,
                sent=sent,
                failed=failed,
                total=total,
                success_rate=(sent/total*100) if total > 0 else 0
            )
        
        log(f"📢 Broadcast complete: {sent} sent, {failed} failed", "success")
        return True
    
    async def _send_message(self, account_name: str, group: str, message: str) -> bool:
        """Send message (SIMULATED)"""
        try:
            await asyncio.sleep(0.5)
            return True
        except Exception as e:
            log_error(f"Send message error: {e}")
            return False


# ==================== JOIN ENGINE ====================

join_engine = None

class JoinEngine:
    def __init__(self):
        self._running = False
        self._session = None
    
    def init(self, api_id: int, api_hash: str):
        """Initialize Telegram client"""
        log(f"Join engine initialized with API ID: {api_id}", "info")
    
    def stop(self):
        """Stop join"""
        self._running = False
        log("Join stopped", "warning")
    
    async def run(self, accounts=None, groups=None, delay_min=30, delay_max=60, 
                  smart_join=True, progress_callback=None, **kwargs):
        """
        Join groups engine
        """
        if not accounts:
            log("❌ Join failed: No accounts specified", "error")
            return False
        
        if not groups:
            from core.utils import load_groups
            groups = load_groups()
        
        if not groups:
            log("❌ Join failed: No groups specified", "error")
            return False
        
        self._running = True
        joined = 0
        skipped = 0
        failed = 0
        
        log(f"📤 Starting join: {len(accounts)} accounts, {len(groups)} groups", "info")
        
        for i, group in enumerate(groups):
            if not self._running:
                break
            
            account_name = accounts[i % len(accounts)]
            
            try:
                # Smart join - check if already joined
                if smart_join:
                    from core.utils import load_joined_groups
                    joined_groups = load_joined_groups()
                    if group in joined_groups:
                        skipped += 1
                        log(f"⏭️ Skip {group} (already joined)", "info")
                        continue
                
                # JOIN group (SIMULATED)
                success = await self._join_group(account_name, group)
                
                if success:
                    joined += 1
                    log(f"✅ Joined {group} via {account_name}", "success")
                    # Save to joined.txt
                    from core.utils import save_joined_group
                    save_joined_group(group)
                else:
                    failed += 1
                    log(f"❌ Failed to join {group}", "error")
                
                if progress_callback:
                    progress_callback(joined=joined, skipped=skipped, failed=failed, total=len(groups))
                
                delay = random.uniform(delay_min, delay_max)
                await asyncio.sleep(delay)
                
            except Exception as e:
                failed += 1
                log(f"❌ Error joining {group}: {e}", "error")
        
        log(f"📤 Join complete: {joined} joined, {skipped} skipped, {failed} failed", "success")
        return True
    
    async def _join_group(self, account_name: str, group: str) -> bool:
        """Join group (SIMULATED)"""
        try:
            await asyncio.sleep(0.5)
            return True
        except Exception as e:
            log_error(f"Join group error: {e}")
            return False


# ==================== SCRAPE ENGINE ====================

scrape_engine = None

class ScrapeEngine:
    def __init__(self):
        self._session = None
    
    def init(self, api_id: int, api_hash: str):
        """Initialize Telegram client"""
        log(f"Scrape engine initialized with API ID: {api_id}", "info")
    
    async def scrape_group(self, account_name: str, group: str) -> list:
        """Scrape members from group (SIMULATED)"""
        try:
            # SIMULATED - replace with actual API
            await asyncio.sleep(0.5)
            
            # Return simulated members
            members = []
            for i in range(random.randint(10, 50)):
                members.append({
                    'id': 100000000 + i,
                    'username': f'user{i}',
                    'first_name': f'User {i}',
                    'phone': f'+628{i:09d}' if i % 3 == 0 else ''
                })
            
            log(f"📥 Scraped {len(members)} members from {group}", "success")
            return members
        except Exception as e:
            log_error(f"Scrape error: {e}")
            return []


# ==================== GLOBAL INSTANCES ====================

broadcast_engine = BroadcastEngine()
join_engine = JoinEngine()
scrape_engine = ScrapeEngine()


# ==================== INIT FUNCTIONS ====================

def init_engines(api_id: int, api_hash: str):
    """Initialize all engines"""
    broadcast_engine.init(api_id, api_hash)
    join_engine.init(api_id, api_hash)
    scrape_engine.init(api_id, api_hash)
    log("✅ All engines initialized", "success")


__all__ = [
    "BroadcastEngine", "broadcast_engine",
    "JoinEngine", "join_engine",
    "ScrapeEngine", "scrape_engine",
    "init_engines"
]