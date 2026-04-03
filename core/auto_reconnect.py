"""Auto-Reconnect Manager - Handle Connection Errors & Recovery"""
import asyncio
import time
from datetime import datetime, timedelta
from typing import Callable, Optional, Dict
from .utils import log, log_error

class AutoReconnectManager:
    def __init__(self):
        self.max_retries = 5
        self.base_delay = 5  # seconds
        self.max_delay = 300  # 5 minutes
        self.connections: Dict[str, dict] = {}
    
    def register_connection(self, connection_id: str, connect_func: Callable, 
                           disconnect_func: Callable = None):
        """Register a connection for auto-reconnect"""
        self.connections[connection_id] = {
            "connect_func": connect_func,
            "disconnect_func": disconnect_func,
            "is_connected": False,
            "retry_count": 0,
            "last_attempt": None,
            "last_success": None,
            "last_error": None
        }
        log(f"Connection registered: {connection_id}", "info")
    
    async def connect_with_retry(self, connection_id: str) -> bool:
        """Attempt to connect with exponential backoff"""
        conn = self.connections.get(connection_id)
        if not conn:
            log_error(f"Connection not registered: {connection_id}")
            return False
        
        while conn["retry_count"] < self.max_retries:
            try:
                conn["last_attempt"] = datetime.now()
                
                # Attempt connection
                result = await conn["connect_func"]()
                
                if result:
                    conn["is_connected"] = True
                    conn["last_success"] = datetime.now()
                    conn["retry_count"] = 0
                    log(f"Connection established: {connection_id}", "success")
                    return True
                else:
                    raise Exception("Connection failed")
            
            except Exception as e:
                conn["last_error"] = str(e)
                conn["retry_count"] += 1
                
                # Calculate delay with exponential backoff
                delay = min(self.base_delay * (2 ** conn["retry_count"]), self.max_delay)
                
                log_error(f"Connection failed: {connection_id} (Attempt {conn['retry_count']}/{self.max_retries})")
                log(f"Retrying in {delay} seconds...", "warning")
                
                await asyncio.sleep(delay)
        
        # All retries exhausted
        conn["is_connected"] = False
        log_error(f"Connection failed after {self.max_retries} attempts: {connection_id}")
        
        # Call disconnect handler if available
        if conn["disconnect_func"]:
            try:
                await conn["disconnect_func"]()
            except Exception as e:
                log_error(f"Disconnect handler error: {e}")
        
        return False
    
    def is_connected(self, connection_id: str) -> bool:
        """Check if connection is active"""
        conn = self.connections.get(connection_id)
        return conn["is_connected"] if conn else False
    
    def get_connection_status(self, connection_id: str) -> dict:
        """Get connection status"""
        conn = self.connections.get(connection_id)
        if not conn:
            return {"status": "not_registered"}
        
        return {
            "status": "connected" if conn["is_connected"] else "disconnected",
            "retry_count": conn["retry_count"],
            "last_attempt": conn["last_attempt"].isoformat() if conn["last_attempt"] else None,
            "last_success": conn["last_success"].isoformat() if conn["last_success"] else None,
            "last_error": conn["last_error"]
        }
    
    def reset_connection(self, connection_id: str):
        """Reset connection state"""
        conn = self.connections.get(connection_id)
        if conn:
            conn["retry_count"] = 0
            conn["is_connected"] = False
            conn["last_error"] = None
            log(f"Connection reset: {connection_id}", "info")
    
    def disconnect(self, connection_id: str):
        """Manually disconnect"""
        conn = self.connections.get(connection_id)
        if conn:
            conn["is_connected"] = False
            if conn["disconnect_func"]:
                asyncio.create_task(conn["disconnect_func"]())
            log(f"Connection disconnected: {connection_id}", "info")


# Global instance
auto_reconnect = AutoReconnectManager()
__all__ = ["AutoReconnectManager", "auto_reconnect"]