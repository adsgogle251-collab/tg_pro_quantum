from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "tg_pro_quantum",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "tasks.broadcast_tasks",
        "tasks.scheduler_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=86400,  # 24 hours
    beat_schedule={
        "execute-scheduled-campaigns": {
            "task": "tasks.scheduler_tasks.execute_scheduled_campaign_task",
            "schedule": crontab(minute="*"),  # every minute
        },
        "cleanup-old-data-daily": {
            "task": "tasks.scheduler_tasks.cleanup_old_data_task",
            "schedule": crontab(hour=2, minute=0),  # 2 AM UTC daily
            "kwargs": {"days": 30},
        },
    },
)

if __name__ == "__main__":
    celery_app.start()
