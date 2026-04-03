"""Broadcast Engine - REAL Telegram Send (100% REAL, NOT SIMULATION)"""
import asyncio
import random
from datetime import datetime
from typing import List, Callable
from telethon import TelegramClient, errors
from pathlib import Path
from .utils import log, log_error, SESSIONS_DIR
from .config_manager import get
from . import broadcast_history
from .account_manager import account_manager

class BroadcastEngine:
    """REAL broadcast engine - BENAR-BENAR KIRIM PESAN KE TELEGRAM"""
    
    def __init__(self):
        self.running = False
        self.paused = False
        self.clients = {}
        self.stats = {
            "sent": 0,
            "failed": 0,
            "total": 0
        }
        self.progress_callback = None
    
    async def get_client(self, account_name: str, api_id: int, api_hash: str):
        """Get Telegram client - REAL CONNECTION"""
        if account_name in self.clients:
            client = self.clients[account_name]
            if await client.is_connected():
                return client
        
        session_path = SESSIONS_DIR / account_name
        
        client = TelegramClient(
            str(session_path),
            api_id,
            api_hash,
            device_model="TG PRO QUANTUM",
            app_version="6.0.0"
        )
        
        try:
            await client.connect()
            
            if await client.is_user_authorized():
                self.clients[account_name] = client
                log(f"✅ CONNECTED: {account_name}", "success")
                return client
            else:
                log(f"❌ NOT AUTHORIZED: {account_name}", "error")
                return None
        except Exception as e:
            log_error(f"Failed to connect {account_name}: {e}")
            return None
    
    async def send_message_real(self, client, group: str, message: str) -> bool:
        """SEND MESSAGE TO TELEGRAM - 100% REAL"""
        try:
            # Extract username from link
            if "t.me/" in group:
                username = group.split("t.me/")[1].split("?")[0].strip()
            elif group.startswith("@"):
                username = group[1:].strip()
            else:
                username = group.strip()
            
            log(f"📤 Sending to: {username}", "info")
            
            # Get entity
            entity = await client.get_entity(username)
            
            # ✅✅✅ REAL SEND - INI YANG KIRIM PESAN BENAR-BENAR! ✅✅✅
            await client.send_message(entity, message)
            
            log(f"✅✅✅ BERHASIL DIKIRIM ke {username} ✅✅✅", "success")
            return True
            
        except errors.FloodWaitError as e:
            log(f"⏳ FLOOD WAIT: tunggu {e.seconds} detik", "warning")
            await asyncio.sleep(e.seconds)
            return False
        except errors.ChatWriteForbiddenError:
            log(f"❌ WRITE FORBIDDEN: {group}", "error")
            return False
        except errors.UserBannedInChannelError:
            log(f"❌ BANNED: {group}", "error")
            return False
        except errors.UsernameNotOccupiedError:
            log(f"❌ NOT FOUND: {group}", "error")
            return False
        except Exception as e:
            log_error(f"❌ ERROR: {e}")
            return False
    
    async def run(self, 
                  accounts: List[str] = None,
                  groups: List[str] = None,
                  message: str = "",
                  delay_min: int = 10,
                  delay_max: int = 30,
                  round_robin: bool = True,
                  progress_callback: Callable = None,
                  **kwargs):
        """Run REAL broadcast"""
        
        self.progress_callback = progress_callback
        self.running = True
        self.paused = False
        self.stats = {"sent": 0, "failed": 0, "total": len(groups) * len(accounts) if groups and accounts else 0}
        
        # Get API from config
        api_id = get("telegram.api_id", 0)
        api_hash = get("telegram.api_hash", "")
        
        if not api_id or not api_hash:
            log_error("❌ API ID/HASH KOSONG! Set di Settings tab dulu!", "error")
            return False
        
        log("="*70, "info")
        log("🚀🚀🚀 BROADCAST REAL DIMULAI (100% REAL) 🚀🚀🚀", "success")
        log("="*70, "info")
        log(f"Accounts: {len(accounts)}", "info")
        log(f"Groups: {len(groups)}", "info")
        log(f"Message: {len(message)} chars", "info")
        log(f"API ID: {api_id}", "info")
        log("="*70, "info")
        
        try:
            for group_idx, group in enumerate(groups, 1):
                if not self.running:
                    break
                
                while self.paused:
                    await asyncio.sleep(1)
                
                log(f"\n📤 GROUP {group_idx}/{len(groups)}: {group}", "info")
                
                for account in accounts:
                    if not self.running:
                        break
                    
                    client = await self.get_client(account, api_id, api_hash)
                    
                    if not client:
                        self.stats["failed"] += 1
                        continue
                    
                    sukses = await self.send_message_real(client, group, message)
                    
                    if sukses:
                        self.stats["sent"] += 1
                        log(f"✅ [{self.stats['sent']}] {account} → {group}", "success")
                    else:
                        self.stats["failed"] += 1
                        log(f"❌ [{self.stats['failed']}] {account} → {group}", "error")
                    
                    if self.progress_callback:
                        progress = (self.stats["sent"] / self.stats["total"]) * 100 if self.stats["total"] > 0 else 0
                        self.progress_callback(
                            sent=self.stats["sent"],
                            failed=self.stats["failed"],
                            total=self.stats["total"],
                            progress_percent=progress,
                            current_account=account,
                            current_group=group,
                            completed=False
                        )
                    
                    delay = random.uniform(delay_min, delay_max)
                    await asyncio.sleep(delay)
            
            # Save to history
            broadcast_history.add_broadcast(
                campaign_name="Manual",
                accounts=accounts,
                groups=groups,
                sent=self.stats["sent"],
                failed=self.stats["failed"],
                duration_sec=0
            )
            
            log("\n" + "="*70, "success")
            log("✅ BROADCAST SELESAI", "success")
            log(f"Sent: {self.stats['sent']}", "success")
            log(f"Failed: {self.stats['failed']}", "error")
            log("="*70, "success")
            
            # Disconnect clients
            for client in self.clients.values():
                await client.disconnect()
            
            return True
            
        except Exception as e:
            log_error(f"Broadcast error: {e}")
            return False
        
        finally:
            self.running = False
    
    def pause(self):
        self.paused = True
    
    def resume(self):
        self.paused = False
    
    def stop(self):
        self.running = False


# Global instance
broadcast_engine = BroadcastEngine()
__all__ = ["broadcast_engine"]