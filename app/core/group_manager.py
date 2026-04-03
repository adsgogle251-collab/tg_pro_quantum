import asyncio
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import GroupMember, TelegramGroup

logger = logging.getLogger(__name__)


class GroupManager:
    """
    Manages Telegram group operations: auto-join, member scraping, and filtering.
    """

    async def auto_join(
        self,
        account: Any,
        group_links: List[str],
        client_id: int,
        db: AsyncSession,
    ) -> List[Dict[str, Any]]:
        """Join groups via their invite links or usernames and persist them."""
        from app.services.telegram_service import TelegramService

        svc = TelegramService(account)
        results = []
        for link in group_links:
            result = {"link": link, "success": False}
            try:
                group_entity = await svc.join_group(link)
                if group_entity:
                    group = TelegramGroup(
                        client_id=client_id,
                        group_id=group_entity.id,
                        group_name=getattr(group_entity, "title", link),
                        username=getattr(group_entity, "username", None),
                        member_count=getattr(group_entity, "participants_count", 0) or 0,
                        type="channel"
                        if getattr(group_entity, "broadcast", False)
                        else "group",
                        is_active=True,
                        auto_join=True,
                    )
                    db.add(group)
                    await db.flush()
                    result["success"] = True
                    result["group_name"] = group.group_name
                    result["group_id"] = group.group_id
                    logger.info("Joined group %s for client %s", link, client_id)
            except Exception as exc:
                result["error"] = str(exc)
                logger.warning("Failed to join group %s: %s", link, exc)
            results.append(result)
        return results

    async def scrape_members(
        self,
        account: Any,
        group: TelegramGroup,
        limit: int,
        db: AsyncSession,
    ) -> int:
        """Scrape members from a group and store them in the database."""
        from app.services.telegram_service import TelegramService

        svc = TelegramService(account)
        members_data = await svc.get_participants(group.group_id, limit=limit)

        count = 0
        for participant in members_data:
            member = GroupMember(
                group_id=group.id,
                telegram_group_id=group.group_id,
                user_id=participant.get("user_id", 0),
                username=participant.get("username"),
                first_name=participant.get("first_name"),
                last_name=participant.get("last_name"),
                phone=participant.get("phone"),
                is_bot=participant.get("is_bot", False),
            )
            db.add(member)
            count += 1

        await db.flush()
        group.member_count = count
        logger.info("Scraped %s members from group %s", count, group.group_id)
        return count

    async def filter_groups(
        self,
        groups: List[TelegramGroup],
        min_members: int = 0,
        active_only: bool = True,
        group_type: Optional[str] = None,
    ) -> List[TelegramGroup]:
        """Filter groups by criteria."""
        filtered = groups
        if active_only:
            filtered = [g for g in filtered if g.is_active]
        if min_members > 0:
            filtered = [g for g in filtered if g.member_count >= min_members]
        if group_type:
            filtered = [g for g in filtered if g.type == group_type]
        return filtered

    async def get_active_groups(
        self, client_id: int, db: AsyncSession
    ) -> List[TelegramGroup]:
        result = await db.execute(
            select(TelegramGroup).where(
                TelegramGroup.client_id == client_id,
                TelegramGroup.is_active == True,
            )
        )
        return result.scalars().all()
