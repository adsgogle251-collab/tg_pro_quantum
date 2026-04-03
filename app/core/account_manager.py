"""
TG PRO QUANTUM - Account Manager
Handles multi-account health monitoring and session management.
"""
from datetime import datetime, timezone
from typing import Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import AccountStatus, TelegramAccount
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AccountManager:
    """Manages Telegram account lifecycle within the multi-tenant service."""

    async def check_health(self, account: TelegramAccount) -> Dict:
        """
        Lightweight health check: verifies session connectivity.
        Returns a dict with score, status, and details.
        """
        from app.services.telegram_service import TelegramService
        svc = TelegramService()

        try:
            connected = await svc.test_connection(account)
            if connected:
                score = 100.0
                status = "healthy"
            else:
                score = 0.0
                status = "unreachable"
        except Exception as exc:
            logger.warning("Health check failed for account %s: %s", account.id, exc)
            score = 0.0
            status = f"error: {exc}"

        return {
            "account_id": account.id,
            "phone": account.phone,
            "score": score,
            "status": status,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    async def rotate_account(
        self,
        accounts: list,
        current_index: int,
    ) -> Optional[TelegramAccount]:
        """Return the next available healthy account (round-robin)."""
        if not accounts:
            return None
        for i in range(len(accounts)):
            candidate = accounts[(current_index + i) % len(accounts)]
            if candidate.status == AccountStatus.active:
                return candidate
        return None

    async def mark_flood_wait(
        self,
        account: TelegramAccount,
        seconds: int,
        db: AsyncSession,
    ) -> None:
        """Mark an account as flood-waited."""
        from datetime import timedelta
        account.status = AccountStatus.flood_wait
        account.flood_wait_until = datetime.now(timezone.utc) + timedelta(seconds=seconds)
        await db.flush()
        logger.warning("Account %s flood-waited for %ss", account.id, seconds)

    async def increment_sent(self, account: TelegramAccount, db: AsyncSession) -> None:
        account.messages_sent_today = (account.messages_sent_today or 0) + 1
        account.last_used_at = datetime.now(timezone.utc)
        await db.flush()


account_manager = AccountManager()
