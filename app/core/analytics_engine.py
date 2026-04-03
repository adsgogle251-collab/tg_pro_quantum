"""
TG PRO QUANTUM - Analytics Engine
Calculates per-campaign and per-client metrics.
"""
from typing import List

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Campaign, CampaignStatus, Group, TelegramAccount
from app.models.schemas import CampaignStats, ClientStats
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AnalyticsEngine:
    async def campaign_stats(self, client_id: int, db: AsyncSession) -> List[CampaignStats]:
        """Return per-campaign delivery statistics."""
        result = await db.execute(
            select(Campaign).where(Campaign.client_id == client_id)
        )
        campaigns = result.scalars().all()

        stats = []
        for c in campaigns:
            total = max(c.total_targets, 1)
            stats.append(
                CampaignStats(
                    campaign_id=c.id,
                    campaign_name=c.name,
                    total_targets=c.total_targets,
                    sent_count=c.sent_count,
                    failed_count=c.failed_count,
                    delivery_rate=round(c.sent_count / total * 100, 2),
                    created_at=c.created_at,
                    completed_at=c.completed_at,
                )
            )
        return stats

    async def client_overview(self, client_id: int, db: AsyncSession) -> ClientStats:
        """Return aggregated statistics for a client."""
        campaigns_result = await db.execute(
            select(Campaign).where(Campaign.client_id == client_id)
        )
        campaigns = campaigns_result.scalars().all()

        accounts_result = await db.execute(
            select(func.count()).where(TelegramAccount.client_id == client_id)
        )
        accounts_count = accounts_result.scalar() or 0

        groups_result = await db.execute(
            select(func.count()).where(Group.client_id == client_id)
        )
        groups_count = groups_result.scalar() or 0

        total_sent = sum(c.sent_count for c in campaigns)
        total_failed = sum(c.failed_count for c in campaigns)
        total_msgs = total_sent + total_failed
        delivery_rate = round(total_sent / max(total_msgs, 1) * 100, 2)

        active_statuses = {CampaignStatus.running, CampaignStatus.scheduled}
        active_count = sum(1 for c in campaigns if c.status in active_statuses)

        return ClientStats(
            client_id=client_id,
            total_campaigns=len(campaigns),
            active_campaigns=active_count,
            total_messages_sent=total_sent,
            total_messages_failed=total_failed,
            overall_delivery_rate=delivery_rate,
            accounts_count=accounts_count,
            groups_count=groups_count,
        )


analytics_engine = AnalyticsEngine()
