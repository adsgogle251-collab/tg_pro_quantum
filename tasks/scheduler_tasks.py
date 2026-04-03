import logging
from datetime import datetime, timedelta, timezone

from celery_app import celery_app
from app.utils.helpers import run_async

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.scheduler_tasks.execute_scheduled_campaign_task")
def execute_scheduled_campaign_task():
    """
    Periodic task: find campaigns scheduled to run now and dispatch them.
    Runs every minute via Celery Beat.
    """

    async def _run():
        from app.database import AsyncSessionLocal
        from app.models.database import Campaign, CampaignStatus
        from sqlalchemy import select

        now = datetime.now(timezone.utc)
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Campaign).where(
                    Campaign.status == CampaignStatus.scheduled,
                    Campaign.scheduled_at <= now,
                )
            )
            due_campaigns = result.scalars().all()
            for campaign in due_campaigns:
                logger.info(
                    "Scheduler: starting campaign %s (%s)", campaign.id, campaign.name
                )
                campaign.status = CampaignStatus.running
                campaign.started_at = now
                from tasks.broadcast_tasks import send_broadcast_task

                send_broadcast_task.delay(campaign.id)
            await db.commit()

    run_async(_run())


@celery_app.task(name="tasks.scheduler_tasks.cleanup_old_data_task")
def cleanup_old_data_task(days: int = 30):
    """
    Periodic task: remove broadcast queue items and history older than `days` days.
    Keeps the database lean.
    """

    async def _run():
        from app.database import AsyncSessionLocal
        from app.models.database import BroadcastHistory, BroadcastQueue, QueueStatus
        from sqlalchemy import delete

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        async with AsyncSessionLocal() as db:
            # Remove completed/failed queue entries older than cutoff
            await db.execute(
                delete(BroadcastQueue).where(
                    BroadcastQueue.created_at < cutoff,
                    BroadcastQueue.status.in_(
                        [QueueStatus.sent, QueueStatus.skipped]
                    ),
                )
            )
            # Remove history entries older than cutoff
            await db.execute(
                delete(BroadcastHistory).where(BroadcastHistory.created_at < cutoff)
            )
            await db.commit()
            logger.info("Cleanup task: removed records older than %s days", days)

    run_async(_run())

