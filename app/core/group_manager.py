"""
TG PRO QUANTUM - Group Manager
Handles auto-join and member scraping.
"""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Group, TelegramAccount
from app.utils.logger import get_logger

logger = get_logger(__name__)


class GroupManager:
    """Automates group joining and member scraping."""

    async def join_group(
        self,
        username: str,
        account_id: int,
        db: AsyncSession,
    ) -> bool:
        """Join a Telegram group using the specified account."""
        from app.services.telegram_service import TelegramService

        result = await db.execute(
            select(TelegramAccount).where(TelegramAccount.id == account_id)
        )
        account = result.scalar_one_or_none()
        if not account:
            logger.error("Account %s not found", account_id)
            return False

        svc = TelegramService()
        try:
            success = await svc.join_group(account, username)
            if success:
                logger.info("Account %s joined @%s", account_id, username)
            return success
        except Exception as exc:
            logger.error("Failed to join @%s with account %s: %s", username, account_id, exc)
            return False

    async def scrape_members(
        self,
        username: str,
        account_id: int,
        db: AsyncSession,
        limit: int = 200,
    ) -> list:
        """Scrape members from a Telegram group."""
        from app.services.telegram_service import TelegramService

        result = await db.execute(
            select(TelegramAccount).where(TelegramAccount.id == account_id)
        )
        account = result.scalar_one_or_none()
        if not account:
            return []

        svc = TelegramService()
        try:
            members = await svc.get_members(account, username, limit=limit)
            return members
        except Exception as exc:
            logger.error("Failed to scrape members from @%s: %s", username, exc)
            return []

    async def sync_group_info(
        self,
        group: Group,
        account_id: int,
        db: AsyncSession,
    ) -> bool:
        """Fetch and update group metadata (title, member count)."""
        from app.services.telegram_service import TelegramService

        result = await db.execute(
            select(TelegramAccount).where(TelegramAccount.id == account_id)
        )
        account = result.scalar_one_or_none()
        if not account:
            return False

        svc = TelegramService()
        try:
            info = await svc.get_group_info(account, group.username)
            if info:
                group.title = info.get("title", group.title)
                group.member_count = info.get("members_count", group.member_count)
                await db.flush()
            return True
        except Exception as exc:
            logger.error("Failed to sync group info for @%s: %s", group.username, exc)
            return False


group_manager = GroupManager()
