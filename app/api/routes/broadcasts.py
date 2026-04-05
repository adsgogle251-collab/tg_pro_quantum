"""
TG PRO QUANTUM - Broadcast Control Routes
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_client
from app.core.broadcast_engine import broadcast_engine
from app.database import get_db
from app.models.database import BroadcastLog, Campaign, CampaignStatus, Client
from app.models.schemas import (
    BroadcastDashboard, BroadcastLogResponse, BroadcastStartRequest, MessageResponse,
)

router = APIRouter(prefix="/broadcasts", tags=["Broadcasts"])


def _require_owns(campaign: Campaign, client: Client) -> None:
    if campaign.client_id != client.id and not client.is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/start", response_model=MessageResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_broadcast(
    body: BroadcastStartRequest,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Start a broadcast campaign (dispatches Celery task)."""
    result = await db.execute(select(Campaign).where(Campaign.id == body.campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    _require_owns(campaign, current_client)

    if campaign.status == CampaignStatus.running:
        raise HTTPException(status_code=409, detail="Campaign is already running")

    task_id = await broadcast_engine.start_campaign(campaign, db)
    campaign.status = CampaignStatus.running
    campaign.celery_task_id = task_id
    await db.flush()

    return MessageResponse(message="Broadcast started", detail={"task_id": task_id})


@router.post("/{campaign_id}/pause", response_model=MessageResponse)
async def pause_broadcast(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Pause a running broadcast campaign."""
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    _require_owns(campaign, current_client)

    if campaign.status != CampaignStatus.running:
        raise HTTPException(status_code=409, detail="Campaign is not running")

    await broadcast_engine.pause_campaign(campaign_id)
    campaign.status = CampaignStatus.paused
    await db.flush()
    return MessageResponse(message="Campaign paused")


@router.post("/{campaign_id}/resume", response_model=MessageResponse)
async def resume_broadcast(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Resume a paused broadcast campaign."""
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    _require_owns(campaign, current_client)

    if campaign.status != CampaignStatus.paused:
        raise HTTPException(status_code=409, detail="Campaign is not paused")

    task_id = await broadcast_engine.resume_campaign(campaign, db)
    campaign.status = CampaignStatus.running
    campaign.celery_task_id = task_id
    await db.flush()
    return MessageResponse(message="Campaign resumed", detail={"task_id": task_id})


@router.post("/{campaign_id}/stop", response_model=MessageResponse)
async def stop_broadcast(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Stop a running/paused campaign."""
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    _require_owns(campaign, current_client)

    if campaign.status not in (CampaignStatus.running, CampaignStatus.paused):
        raise HTTPException(status_code=409, detail="Campaign is not running or paused")

    await broadcast_engine.stop_campaign(campaign_id)
    campaign.status = CampaignStatus.failed
    await db.flush()
    return MessageResponse(message="Campaign stopped")


@router.get("/{campaign_id}/dashboard", response_model=BroadcastDashboard)
async def get_dashboard(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Real-time dashboard for a campaign."""
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    _require_owns(campaign, current_client)

    total = campaign.total_targets or 1
    delivery_rate = campaign.sent_count / total * 100 if total else 0.0
    progress_pct = (campaign.sent_count + campaign.failed_count) / total * 100 if total else 0.0

    return BroadcastDashboard(
        campaign_id=campaign.id,
        campaign_name=campaign.name,
        status=campaign.status,
        total_targets=campaign.total_targets,
        sent_count=campaign.sent_count,
        failed_count=campaign.failed_count,
        retry_count=campaign.retry_count,
        delivery_rate=round(delivery_rate, 2),
        progress_pct=round(progress_pct, 2),
        started_at=None,
        completed_at=campaign.completed_at,
    )


@router.get("/{campaign_id}/logs", response_model=List[BroadcastLogResponse])
async def get_broadcast_logs(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Get broadcast logs for a campaign."""
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    _require_owns(campaign, current_client)

    logs_result = await db.execute(
        select(BroadcastLog)
        .where(BroadcastLog.campaign_id == campaign_id)
        .order_by(BroadcastLog.created_at.desc())
        .limit(500)
    )
    return logs_result.scalars().all()
