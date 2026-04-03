import logging
from datetime import datetime

from celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="tasks.broadcast_tasks.send_broadcast_task", max_retries=3)
def send_broadcast_task(self, campaign_id: int):
    """
    Main Celery task: load campaign from DB, build queue, and run broadcast engine.
    """
    import asyncio

    async def _run():
        from app.database import AsyncSessionLocal
        from app.models.database import (
            BroadcastQueue,
            Campaign,
            CampaignAccount,
            CampaignGroup,
            CampaignMessage,
            CampaignStatus,
            QueueStatus,
            TelegramAccount,
            TelegramGroup,
        )
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            # Load campaign
            result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
            campaign = result.scalar_one_or_none()
            if campaign is None:
                logger.error("Campaign %s not found", campaign_id)
                return

            # Load accounts
            accs_res = await db.execute(
                select(TelegramAccount)
                .join(CampaignAccount, CampaignAccount.account_id == TelegramAccount.id)
                .where(
                    CampaignAccount.campaign_id == campaign_id,
                    TelegramAccount.status == "active",
                )
            )
            accounts = accs_res.scalars().all()

            # Load groups
            grps_res = await db.execute(
                select(TelegramGroup)
                .join(CampaignGroup, CampaignGroup.group_id == TelegramGroup.id)
                .where(CampaignGroup.campaign_id == campaign_id)
            )
            groups = grps_res.scalars().all()

            # Load messages
            msgs_res = await db.execute(
                select(CampaignMessage)
                .where(CampaignMessage.campaign_id == campaign_id)
                .order_by(CampaignMessage.order_index)
            )
            messages = msgs_res.scalars().all()

            if not accounts or not groups or not messages:
                logger.warning(
                    "Campaign %s missing accounts/groups/messages; aborting", campaign_id
                )
                campaign.status = CampaignStatus.failed
                await db.commit()
                return

            from app.core.broadcast_engine import BroadcastEngine

            engine = BroadcastEngine()
            result = await engine.run_campaign(
                campaign_id=campaign_id,
                accounts=list(accounts),
                groups=list(groups),
                messages=list(messages),
                delay_min=campaign.delay_min,
                delay_max=campaign.delay_max,
                max_messages_per_hour=campaign.max_messages_per_hour,
                loop_count=campaign.loop_count,
                is_loop_infinite=campaign.is_loop_infinite,
            )

            campaign.status = CampaignStatus.completed
            campaign.completed_at = datetime.utcnow()
            await db.commit()
            logger.info("Campaign %s broadcast task done: %s", campaign_id, result)

    try:
        asyncio.run(_run())
    except Exception as exc:
        logger.error("Campaign %s broadcast task error: %s", campaign_id, exc)
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(name="tasks.broadcast_tasks.retry_failed_messages_task")
def retry_failed_messages_task(campaign_id: int):
    """Reset failed queue items to pending so the engine picks them up again."""
    import asyncio

    async def _run():
        from app.database import AsyncSessionLocal
        from app.models.database import BroadcastQueue, QueueStatus
        from sqlalchemy import select, update

        async with AsyncSessionLocal() as db:
            await db.execute(
                update(BroadcastQueue)
                .where(
                    BroadcastQueue.campaign_id == campaign_id,
                    BroadcastQueue.status == QueueStatus.failed,
                    BroadcastQueue.retry_count < BroadcastQueue.max_retries,
                )
                .values(status=QueueStatus.pending, error_message=None)
            )
            await db.commit()
            logger.info("Failed messages reset for campaign %s", campaign_id)

    asyncio.run(_run())


@celery_app.task(name="tasks.broadcast_tasks.update_campaign_status_task")
def update_campaign_status_task(campaign_id: int, new_status: str):
    """Update a campaign's status field from a background task."""
    import asyncio

    async def _run():
        from app.database import AsyncSessionLocal
        from app.models.database import Campaign, CampaignStatus
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
            campaign = result.scalar_one_or_none()
            if campaign:
                campaign.status = CampaignStatus(new_status)
                if new_status == "completed":
                    campaign.completed_at = datetime.utcnow()
                await db.commit()

    asyncio.run(_run())
