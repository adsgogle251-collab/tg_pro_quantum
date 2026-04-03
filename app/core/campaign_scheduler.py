import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CampaignScheduler:
    """
    Campaign scheduler with Celery Beat integration, loop mode,
    and account rotation logic for 24/7 operation.
    """

    def __init__(self):
        self._scheduled: Dict[int, Dict[str, Any]] = {}

    def schedule_campaign(
        self,
        campaign_id: int,
        scheduled_at: datetime,
        loop_count: int = 0,
        is_loop_infinite: bool = False,
        cron_expression: Optional[str] = None,
    ) -> str:
        """Register a campaign for execution at the given time or cron schedule."""
        from celery_app import celery_app
        from tasks.broadcast_tasks import send_broadcast_task

        eta = scheduled_at if scheduled_at > datetime.now(timezone.utc) else None

        if cron_expression and is_loop_infinite:
            # Use Celery Beat periodic task
            from celery.schedules import crontab

            parts = cron_expression.split()
            if len(parts) == 5:
                minute, hour, day_of_month, month_of_year, day_of_week = parts
                celery_app.conf.beat_schedule[f"campaign_{campaign_id}_loop"] = {
                    "task": "tasks.broadcast_tasks.send_broadcast_task",
                    "schedule": crontab(
                        minute=minute,
                        hour=hour,
                        day_of_month=day_of_month,
                        month_of_year=month_of_year,
                        day_of_week=day_of_week,
                    ),
                    "args": (campaign_id,),
                }
                task_id = f"beat_campaign_{campaign_id}"
            else:
                task_id = str(send_broadcast_task.apply_async((campaign_id,), eta=eta).id)
        else:
            task_id = str(send_broadcast_task.apply_async((campaign_id,), eta=eta).id)

        self._scheduled[campaign_id] = {
            "task_id": task_id,
            "scheduled_at": scheduled_at.isoformat(),
            "loop_count": loop_count,
            "is_loop_infinite": is_loop_infinite,
        }
        logger.info("Campaign %s scheduled: task_id=%s", campaign_id, task_id)
        return task_id

    def cancel_campaign(self, campaign_id: int) -> bool:
        """Cancel a scheduled campaign."""
        entry = self._scheduled.get(campaign_id)
        if not entry:
            logger.warning("Campaign %s not found in scheduler", campaign_id)
            return False

        task_id = entry["task_id"]
        if not task_id.startswith("beat_"):
            from celery_app import celery_app

            celery_app.control.revoke(task_id, terminate=True)
            logger.info("Campaign %s cancelled (task_id=%s)", campaign_id, task_id)
        else:
            from celery_app import celery_app

            beat_key = f"campaign_{campaign_id}_loop"
            celery_app.conf.beat_schedule.pop(beat_key, None)
            logger.info("Campaign %s periodic schedule removed", campaign_id)

        del self._scheduled[campaign_id]
        return True

    def get_scheduled_campaigns(self) -> List[Dict[str, Any]]:
        return [
            {"campaign_id": cid, **info} for cid, info in self._scheduled.items()
        ]

    async def rotate_accounts(
        self, campaign_id: int, accounts: List[Any]
    ) -> List[Any]:
        """Return accounts sorted by last_used_at for fair rotation."""
        active = [a for a in accounts if getattr(a, "status", None) == "active"]
        active.sort(
            key=lambda a: getattr(a, "last_used_at", None) or datetime(1900, 1, 1, tzinfo=timezone.utc)
        )
        return active

    async def execute_loop_campaign(
        self,
        campaign_id: int,
        loop_count: int,
        delay_between_loops: int = 3600,
    ) -> None:
        """Execute a campaign N times with a delay between iterations."""
        from app.core.broadcast_engine import BroadcastEngine

        engine = BroadcastEngine()
        import asyncio

        for i in range(loop_count):
            logger.info("Campaign %s loop %s/%s starting", campaign_id, i + 1, loop_count)
            # Actual run is delegated to the broadcast engine via task
            from tasks.broadcast_tasks import send_broadcast_task

            send_broadcast_task.delay(campaign_id)
            if i < loop_count - 1:
                await asyncio.sleep(delay_between_loops)
