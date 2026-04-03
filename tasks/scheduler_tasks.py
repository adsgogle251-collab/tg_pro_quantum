"""
TG PRO QUANTUM - Celery Scheduled Tasks (Beat)
"""
from celery import Celery
from celery.schedules import crontab

from app.config import settings
from tasks.utils import run_async

celery_app = Celery(
    "tg_quantum_beat",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        # Check every minute for campaigns due to be started
        "check-due-campaigns": {
            "task": "tasks.scheduler_tasks.check_due_campaigns",
            "schedule": crontab(minute="*"),
        },
    },
)


@celery_app.task(name="tasks.scheduler_tasks.check_due_campaigns")
def check_due_campaigns():
    """Scan for scheduled campaigns whose start time has arrived."""
    from app.database import AsyncSessionLocal
    from app.core.campaign_scheduler import campaign_scheduler

    async def _inner():
        async with AsyncSessionLocal() as db:
            count = await campaign_scheduler.check_due_campaigns(db)
            return count

    return run_async(_inner())


@celery_app.task(name="tasks.scheduler_tasks.trigger_scheduled_campaign")
def trigger_scheduled_campaign(campaign_id: int):
    """Trigger a specific campaign (called from Beat for 24/7 cron schedules)."""
    from app.database import AsyncSessionLocal
    from app.core.broadcast_engine import broadcast_engine
    from sqlalchemy import select
    from app.models.database import Campaign

    async def _inner():
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
            campaign = result.scalar_one_or_none()
            if campaign:
                task_id = await broadcast_engine.start_campaign(campaign, db)
                return task_id

    return run_async(_inner())
