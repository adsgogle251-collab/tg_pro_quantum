import base64
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AccountManager:
    """
    Manages Telegram account lifecycle: session loading/saving,
    health checks, and auto-rotation.
    """

    def __init__(self):
        self._sessions: Dict[int, Any] = {}  # account_id -> TelegramClient

    async def load_session(self, account: Any) -> Optional[Any]:
        """Load a Telethon client from stored session_data."""
        if account.id in self._sessions:
            client = self._sessions[account.id]
            if await self._is_connected(client):
                return client

        if not account.session_data:
            logger.warning("Account %s has no session data", account.id)
            return None

        from app.services.telegram_service import TelegramService

        svc = TelegramService(account)
        client = await svc.connect()
        if client:
            self._sessions[account.id] = client
        return client

    async def save_session(self, account: Any, client: Any, db: Any) -> None:
        """Serialize and persist session data back to the database."""
        try:
            session_string = client.session.save()
            account.session_data = session_string
            account.updated_at = datetime.now(timezone.utc)
            await db.flush()
            logger.debug("Session saved for account %s", account.id)
        except Exception as exc:
            logger.error("Failed to save session for account %s: %s", account.id, exc)

    async def check_account_health(self, account: Any) -> Dict[str, Any]:
        """Verify an account is connected and not banned."""
        result = {
            "account_id": account.id,
            "phone": account.phone,
            "is_healthy": False,
            "status": account.status,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            client = await self.load_session(account)
            if client is None:
                result["error"] = "Cannot load session"
                return result

            me = await client.get_me()
            if me:
                result["is_healthy"] = True
                result["username"] = me.username
                result["full_name"] = f"{me.first_name or ''} {me.last_name or ''}".strip()
        except Exception as exc:
            result["error"] = str(exc)
            if "banned" in str(exc).lower():
                account.status = "banned"
            elif "flood" in str(exc).lower():
                account.status = "limited"
        return result

    async def check_all_accounts(self, accounts: List[Any]) -> List[Dict[str, Any]]:
        """Run health checks on a list of accounts concurrently."""
        import asyncio

        tasks = [self.check_account_health(a) for a in accounts]
        return await asyncio.gather(*tasks, return_exceptions=False)

    async def get_best_account(self, accounts: List[Any]) -> Optional[Any]:
        """Return the active account with the oldest last_used_at timestamp."""
        active = [a for a in accounts if getattr(a, "status", None) == "active"]
        if not active:
            return None
        active.sort(key=lambda a: getattr(a, "last_used_at", None) or datetime(1900, 1, 1, tzinfo=timezone.utc))
        return active[0]

    async def disconnect_all(self) -> None:
        for account_id, client in list(self._sessions.items()):
            try:
                await client.disconnect()
            except Exception:
                pass
        self._sessions.clear()

    async def _is_connected(self, client: Any) -> bool:
        try:
            return client.is_connected()
        except Exception:
            return False

    def encode_session(self, session_string: str) -> str:
        return base64.b64encode(session_string.encode()).decode()

    def decode_session(self, encoded: str) -> str:
        return base64.b64decode(encoded.encode()).decode()
