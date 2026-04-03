"""
TG PRO QUANTUM - Campaign Scheduler
Handles cron-based and 24/7 scheduling via Celery Beat.
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Campaign, CampaignMode, CampaignStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CampaignScheduler:
    """Registers/removes Celery Beat periodic tasks for campaigns."""

    def schedule_campaign(self, campaign: Campaign) -> bool:
        """Register a Celery Beat entry for the campaign if it needs scheduling."""
        if campaign.mode not in (CampaignMode.schedule_24_7,):
            return False

        try:
            from celery.schedules import crontab
            from tasks.scheduler_tasks import celery_app

            schedule_name = f"campaign-{campaign.id}"
            if campaign.cron_expression:
                # Parse a 5-field cron expression
                parts = campaign.cron_expression.split()
                if len(parts) != 5:
                    raise ValueError(f"Invalid cron expression: {campaign.cron_expression}")
                minute, hour, day_of_month, month_of_year, day_of_week = parts
                celery_app.conf.beat_schedule[schedule_name] = {
                    "task": "tasks.scheduler_tasks.trigger_scheduled_campaign",
                    "schedule": crontab(
                        minute=minute,
                        hour=hour,
                        day_of_month=day_of_month,
                        month_of_year=month_of_year,
                        day_of_week=day_of_week,
                    ),
                    "args": (campaign.id,),
                }
                logger.info("Scheduled campaign %s with cron '%s'", campaign.id, campaign.cron_expression)
                return True
        except Exception as exc:
            logger.warning("Could not register Celery Beat schedule: %s", exc)

        return False

    def unschedule_campaign(self, campaign_id: int) -> None:
        """Remove a Celery Beat entry for the campaign."""
        try:
            from tasks.scheduler_tasks import celery_app
            schedule_name = f"campaign-{campaign_id}"
            celery_app.conf.beat_schedule.pop(schedule_name, None)
            logger.info("Unscheduled campaign %s", campaign_id)
        except Exception as exc:
            logger.warning("Could not unschedule campaign %s: %s", campaign_id, exc)

    async def check_due_campaigns(self, db: AsyncSession) -> int:
        """Start any campaigns whose scheduled_at time has arrived. Returns count."""
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(Campaign).where(
                Campaign.status == CampaignStatus.scheduled,
                Campaign.scheduled_at <= now,
            )
        )
        due = result.scalars().all()
        count = 0
        for campaign in due:
            try:
                from app.core.broadcast_engine import broadcast_engine
                task_id = await broadcast_engine.start_campaign(campaign, db)
                campaign.status = CampaignStatus.running
                campaign.celery_task_id = task_id
                count += 1
            except Exception as exc:
                logger.error("Failed to start scheduled campaign %s: %s", campaign.id, exc)
        if count:
            await db.commit()
        return count


campaign_scheduler = CampaignScheduler()
