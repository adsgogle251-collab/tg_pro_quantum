"""TG PRO QUANTUM - Account Creator with OTP
Bulk account creation with SMS verification
"""
import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from telethon import TelegramClient, errors
from .utils import log, log_error, log_success, SESSIONS_DIR
from .sms_activate import get_sms_activate

class AccountCreator:
    """Bulk account creator with OTP verification"""
    
    def __init__(self, api_id: int, api_hash: str, sms_api_key: str):
        self.api_id = api_id
        self.api_hash = api_hash
        self.sms = get_sms_activate(sms_api_key)
        self.created_accounts: List[Dict] = []
    
    def check_balance(self) -> Tuple[bool, float]:
        """Check SMS Activate balance"""
        return self.sms.get_balance()
    
    async def create_account(self, account_name: str, country: str = '62') -> Tuple[bool, str]:
        """Create single account with OTP"""
        session_file = SESSIONS_DIR / f"{account_name}.session"
        
        # Get phone number
        success, activation_id, phone = self.sms.get_number('tg')
        if not success:
            log_error(f"Failed to get phone: {activation_id}")
            return False, activation_id
        
        log(f"Got phone: {phone} for {account_name}", "info")
        
        # Create Telegram client
        client = TelegramClient(session_file, self.api_id, self.api_hash)
        await client.connect()
        
        try:
            # Send code
            sent = await client.send_code_request(phone)
            log(f"Code sent to {phone}", "info")
            
            # Wait for SMS
            success, code = self.sms.get_sms(activation_id, timeout=120)
            if not success:
                await client.disconnect()
                self.sms.cancel_activation(activation_id)
                return False, "SMS not received"
            
            log(f"Received code: {code}", "success")
            
            # Sign in
            await client.sign_in(phone, code, sent.phone_code_hash)
            
            # Get me info
            me = await client.get_me()
            log(f"Account created: {me.first_name} (@{me.username or 'no username'})", "success")
            
            # Approve activation
            self.sms.approve_activation(activation_id)
            
            # Save account info
            self.created_accounts.append({
                "name": account_name,
                "phone": phone,
                "username": me.username,
                "created_at": datetime.now().isoformat()
            })
            
            await client.disconnect()
            return True, phone
            
        except errors.PhoneCodeInvalidError:
            log_error(f"Invalid code for {phone}")
            await client.disconnect()
            self.sms.cancel_activation(activation_id)
            return False, "Invalid code"
        except Exception as e:
            log_error(f"Account creation failed: {e}")
            await client.disconnect()
            self.sms.cancel_activation(activation_id)
            return False, str(e)
    
    async def create_multiple(self, count: int, prefix: str = "acc") -> Dict:
        """Create multiple accounts"""
        results = {"success": 0, "failed": 0, "accounts": []}
        
        # Check balance first
        balance_ok, balance = self.check_balance()
        if not balance_ok or balance < count * 0.25:  # Approx cost per account
            return {"error": f"Insufficient balance: ${balance:.2f} (need ${count * 0.25:.2f})"}
        
        log(f"Creating {count} accounts...", "info")
        
        for i in range(count):
            account_name = f"{prefix}_{i+1:03d}"
            success, result = await self.create_account(account_name)
            if success:
                results["success"] += 1
                results["accounts"].append({"name": account_name, "phone": result})
                log(f"[{i+1}/{count}] ✅ {account_name} created", "success")
            else:
                results["failed"] += 1
                log(f"[{i+1}/{count}] ❌ {account_name} failed: {result}", "error")
            
            # Delay between creations
            if i < count - 1:
                await asyncio.sleep(5)
        
        log(f"Created {results['success']}/{count} accounts", "success")
        return results
    
    def get_created_accounts(self) -> List[Dict]:
        """Get list of created accounts"""
        return self.created_accounts
    
    def export_created_accounts(self, filepath: str) -> bool:
        """Export created accounts to file"""
        import json
        try:
            filepath = Path(filepath)
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.created_accounts, f, indent=2, ensure_ascii=False)
            log_success(f"Exported {len(self.created_accounts)} accounts to {filepath}")
            return True
        except Exception as e:
            log_error(f"Export failed: {e}")
            return False

# Global instance (lazy init)
_creator_instance = None

def get_account_creator(api_id: int, api_hash: str, sms_api_key: str) -> AccountCreator:
    """Get AccountCreator instance"""
    global _creator_instance
    if _creator_instance is None:
        _creator_instance = AccountCreator(api_id, api_hash, sms_api_key)
    return _creator_instance

__all__ = ["AccountCreator", "get_account_creator"]