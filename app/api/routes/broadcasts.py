import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.database import AsyncSessionLocal, get_db
from app.models.database import (
    BroadcastHistory,
    BroadcastQueue,
    Campaign,
    CampaignStatus,
    QueueStatus,
    User,
)
from app.models.schemas import (
    BroadcastProgressResponse,
    BroadcastSendRequest,
    BroadcastStatusResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Broadcasts"])


async def _get_campaign_or_404(campaign_id: int, db: AsyncSession) -> Campaign:
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return campaign


@router.post("/campaigns/{campaign_id}/broadcast/send", status_code=status.HTTP_202_ACCEPTED)
async def send_broadcast(
    campaign_id: int,
    payload: BroadcastSendRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaign = await _get_campaign_or_404(campaign_id, db)
    if campaign.status == CampaignStatus.running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Campaign is already running",
        )
    if campaign.status not in (
        CampaignStatus.draft,
        CampaignStatus.scheduled,
        CampaignStatus.paused,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot start campaign in '{campaign.status}' state",
        )

    if payload.dry_run:
        return {"message": "Dry run completed - no messages sent", "campaign_id": campaign_id}

    from tasks.broadcast_tasks import send_broadcast_task

    send_broadcast_task.delay(campaign_id)
    campaign.status = CampaignStatus.running
    campaign.started_at = datetime.now(timezone.utc)
    await db.flush()
    return {"message": "Broadcast started", "campaign_id": campaign_id}


@router.get("/campaigns/{campaign_id}/broadcast/status", response_model=BroadcastStatusResponse)
async def get_broadcast_status(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaign = await _get_campaign_or_404(campaign_id, db)

    total_res = await db.execute(
        select(func.count(BroadcastQueue.id)).where(BroadcastQueue.campaign_id == campaign_id)
    )
    sent_res = await db.execute(
        select(func.count(BroadcastQueue.id)).where(
            BroadcastQueue.campaign_id == campaign_id,
            BroadcastQueue.status == QueueStatus.sent,
        )
    )
    failed_res = await db.execute(
        select(func.count(BroadcastQueue.id)).where(
            BroadcastQueue.campaign_id == campaign_id,
            BroadcastQueue.status == QueueStatus.failed,
        )
    )
    pending_res = await db.execute(
        select(func.count(BroadcastQueue.id)).where(
            BroadcastQueue.campaign_id == campaign_id,
            BroadcastQueue.status == QueueStatus.pending,
        )
    )

    total = total_res.scalar() or 0
    sent = sent_res.scalar() or 0
    failed = failed_res.scalar() or 0
    pending = pending_res.scalar() or 0

    return BroadcastStatusResponse(
        campaign_id=campaign_id,
        status=campaign.status.value
        if hasattr(campaign.status, "value")
        else campaign.status,
        total_queued=total,
        total_sent=sent,
        total_failed=failed,
        total_pending=pending,
        started_at=campaign.started_at,
        estimated_completion=None,
    )


@router.get(
    "/campaigns/{campaign_id}/broadcast/progress", response_model=BroadcastProgressResponse
)
async def get_broadcast_progress(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaign = await _get_campaign_or_404(campaign_id, db)

    total_res = await db.execute(
        select(func.count(BroadcastQueue.id)).where(BroadcastQueue.campaign_id == campaign_id)
    )
    sent_res = await db.execute(
        select(func.count(BroadcastQueue.id)).where(
            BroadcastQueue.campaign_id == campaign_id,
            BroadcastQueue.status == QueueStatus.sent,
        )
    )
    total = total_res.scalar() or 0
    sent = sent_res.scalar() or 0
    progress = (sent / total * 100) if total > 0 else 0.0

    elapsed = 0.0
    if campaign.started_at:
        elapsed = (datetime.now(timezone.utc) - campaign.started_at).total_seconds()

    rate = (sent / elapsed * 60) if elapsed > 0 else 0.0
    remaining = total - sent
    eta = (remaining / rate * 60) if rate > 0 else None

    return BroadcastProgressResponse(
        campaign_id=campaign_id,
        progress_pct=round(progress, 2),
        messages_per_minute=round(rate, 2),
        current_account=None,
        current_group=None,
        elapsed_seconds=elapsed,
        eta_seconds=eta,
    )


@router.post("/campaigns/{campaign_id}/broadcast/stop")
async def stop_broadcast(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaign = await _get_campaign_or_404(campaign_id, db)
    if campaign.status != CampaignStatus.running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Campaign is not running",
        )
    campaign.status = CampaignStatus.failed
    campaign.completed_at = datetime.now(timezone.utc)
    await db.flush()
    return {"message": "Campaign stopped", "campaign_id": campaign_id}


@router.post("/campaigns/{campaign_id}/broadcast/pause")
async def pause_broadcast(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaign = await _get_campaign_or_404(campaign_id, db)
    if campaign.status != CampaignStatus.running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Campaign is not running",
        )
    campaign.status = CampaignStatus.paused
    await db.flush()
    return {"message": "Campaign paused", "campaign_id": campaign_id}


@router.post("/campaigns/{campaign_id}/broadcast/resume")
async def resume_broadcast(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaign = await _get_campaign_or_404(campaign_id, db)
    if campaign.status != CampaignStatus.paused:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Campaign is not paused",
        )
    from tasks.broadcast_tasks import send_broadcast_task

    send_broadcast_task.delay(campaign_id)
    campaign.status = CampaignStatus.running
    await db.flush()
    return {"message": "Campaign resumed", "campaign_id": campaign_id}


@router.post("/campaigns/{campaign_id}/broadcast/retry-failed")
async def retry_failed_messages(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaign = await _get_campaign_or_404(campaign_id, db)

    result = await db.execute(
        select(BroadcastQueue).where(
            BroadcastQueue.campaign_id == campaign_id,
            BroadcastQueue.status == QueueStatus.failed,
            BroadcastQueue.retry_count < BroadcastQueue.max_retries,
        )
    )
    failed_items = result.scalars().all()
    if not failed_items:
        return {"message": "No retryable failed messages", "count": 0}

    for item in failed_items:
        item.status = QueueStatus.pending
        item.retry_count += 1
        item.error_message = None

    from tasks.broadcast_tasks import retry_failed_messages_task

    retry_failed_messages_task.delay(campaign_id)
    await db.flush()
    return {"message": "Retry initiated", "count": len(failed_items)}


@router.websocket("/ws/campaigns/{campaign_id}/live")
async def websocket_live(campaign_id: int, websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connected for campaign %s", campaign_id)
    try:
        while True:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Campaign).where(Campaign.id == campaign_id)
                )
                campaign = result.scalar_one_or_none()
                if campaign is None:
                    await websocket.send_text(
                        json.dumps({"error": "Campaign not found"})
                    )
                    break

                total_res = await db.execute(
                    select(func.count(BroadcastQueue.id)).where(
                        BroadcastQueue.campaign_id == campaign_id
                    )
                )
                sent_res = await db.execute(
                    select(func.count(BroadcastQueue.id)).where(
                        BroadcastQueue.campaign_id == campaign_id,
                        BroadcastQueue.status == QueueStatus.sent,
                    )
                )
                failed_res = await db.execute(
                    select(func.count(BroadcastQueue.id)).where(
                        BroadcastQueue.campaign_id == campaign_id,
                        BroadcastQueue.status == QueueStatus.failed,
                    )
                )
                total = total_res.scalar() or 0
                sent = sent_res.scalar() or 0
                failed = failed_res.scalar() or 0

            progress = (sent / total * 100) if total > 0 else 0.0
            await websocket.send_text(
                json.dumps(
                    {
                        "campaign_id": campaign_id,
                        "status": campaign.status.value
                        if hasattr(campaign.status, "value")
                        else campaign.status,
                        "total": total,
                        "sent": sent,
                        "failed": failed,
                        "progress_pct": round(progress, 2),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )
            )
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for campaign %s", campaign_id)
    except Exception as exc:
        logger.error("WebSocket error for campaign %s: %s", campaign_id, exc)
        await websocket.close()
