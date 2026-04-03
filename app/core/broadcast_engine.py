"""
TG PRO QUANTUM - Advanced Broadcast Engine
Supports: once, round-robin, loop, and 24/7 schedule modes.
"""
import asyncio
import random
from datetime import datetime, timezone
from typing import Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import (
    BroadcastLog, BroadcastStatus, Campaign, CampaignMode,
    CampaignStatus, Group, TelegramAccount,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class BroadcastEngine:
    """Orchestrates multi-account broadcasting with configurable modes."""

    def __init__(self):
        # In-memory set of paused/stopped campaign IDs
        self._paused: set = set()
        self._stopped: set = set()

    # ── Public interface ──────────────────────────────────────────────────────

    async def start_campaign(self, campaign: Campaign, db: AsyncSession) -> str:
        """
        Dispatch a Celery task for the campaign and return the task ID.
        Falls back to in-process async execution when Celery is unavailable.
        """
        from tasks.broadcast_tasks import run_broadcast_task

        try:
            task = run_broadcast_task.delay(campaign.id)
            task_id = task.id
        except Exception as exc:
            logger.warning("Celery unavailable (%s); running in-process", exc)
            task_id = f"local-{campaign.id}"
            asyncio.create_task(self._run_campaign(campaign.id))

        logger.info("Campaign %s started – task_id=%s", campaign.id, task_id)
        return task_id

    async def pause_campaign(self, campaign_id: int) -> None:
        self._paused.add(campaign_id)
        logger.info("Campaign %s paused", campaign_id)

    async def resume_campaign(self, campaign: Campaign, db: AsyncSession) -> str:
        self._paused.discard(campaign.id)
        return await self.start_campaign(campaign, db)

    async def stop_campaign(self, campaign_id: int) -> None:
        self._stopped.add(campaign_id)
        self._paused.discard(campaign_id)
        logger.info("Campaign %s stopped", campaign_id)

    # ── Internal execution ────────────────────────────────────────────────────

    async def _run_campaign(self, campaign_id: int) -> None:
        """
        Core broadcast loop – fetches targets & accounts, dispatches messages.
        Designed to be called from a Celery worker or directly as an asyncio task.
        """
        from app.database import AsyncSessionLocal
        from app.services.telegram_service import TelegramService

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
            campaign = result.scalar_one_or_none()
            if not campaign:
                logger.error("Campaign %s not found", campaign_id)
                return

            # Resolve groups
            group_result = await db.execute(
                select(Group).where(
                    Group.id.in_(campaign.target_group_ids),
                    Group.is_active.is_(True),
                )
            )
            groups = group_result.scalars().all()

            # Resolve accounts
            account_result = await db.execute(
                select(TelegramAccount).where(
                    TelegramAccount.id.in_(campaign.account_ids),
                    TelegramAccount.status == "active",
                )
            )
            accounts = account_result.scalars().all()

            if not accounts:
                logger.error("No active accounts for campaign %s", campaign_id)
                campaign.status = CampaignStatus.failed
                await db.commit()
                return

            telegram_svc = TelegramService()
            account_index = 0

            for group in groups:
                if campaign_id in self._stopped:
                    logger.info("Campaign %s was stopped", campaign_id)
                    break

                # Wait while paused
                while campaign_id in self._paused:
                    await asyncio.sleep(2)

                # Round-robin account selection
                if campaign.mode == CampaignMode.round_robin:
                    account = accounts[account_index % len(accounts)]
                    account_index += 1
                else:
                    account = accounts[0]

                success, error = await telegram_svc.send_message(
                    account=account,
                    username=group.username,
                    text=campaign.message_text,
                    media_url=campaign.media_url,
                )

                # Persist log
                log_entry = BroadcastLog(
                    campaign_id=campaign_id,
                    account_id=account.id,
                    group_username=group.username,
                    status=BroadcastStatus.completed if success else BroadcastStatus.failed,
                    error_message=error,
                    sent_at=datetime.now(timezone.utc) if success else None,
                )
                db.add(log_entry)

                if success:
                    campaign.sent_count += 1
                else:
                    campaign.failed_count += 1

                await db.commit()

                # Anti-ban delay
                delay = random.uniform(campaign.delay_min, campaign.delay_max)
                await asyncio.sleep(delay)

            # Handle loop mode
            if campaign.mode == CampaignMode.loop and campaign_id not in self._stopped:
                logger.info("Campaign %s looping (repeat_interval=%sm)", campaign_id, campaign.repeat_interval_minutes)
                if campaign.repeat_interval_minutes > 0:
                    await asyncio.sleep(campaign.repeat_interval_minutes * 60)
                asyncio.create_task(self._run_campaign(campaign_id))
                return

            # Mark complete
            if campaign_id not in self._stopped:
                campaign.status = CampaignStatus.completed
                campaign.completed_at = datetime.now(timezone.utc)
            else:
                campaign.status = CampaignStatus.failed

            await db.commit()
            self._stopped.discard(campaign_id)
            logger.info("Campaign %s finished. sent=%s failed=%s", campaign_id, campaign.sent_count, campaign.failed_count)


broadcast_engine = BroadcastEngine()
