"""
TG PRO QUANTUM - Celery Broadcast Tasks
"""
import asyncio

from celery import Celery

from app.config import settings

celery_app = Celery(
    "tg_quantum",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,  # fair scheduling for long-running tasks
)


def _run_async(coro):
    """Run an async coroutine inside a Celery (sync) worker."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, name="tasks.broadcast_tasks.run_broadcast_task", max_retries=1)
def run_broadcast_task(self, campaign_id: int):
    """
    Celery task: execute the broadcast engine for a given campaign.
    Called by BroadcastEngine.start_campaign().
    """
    from app.core.broadcast_engine import broadcast_engine

    try:
        _run_async(broadcast_engine._run_campaign(campaign_id))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)
