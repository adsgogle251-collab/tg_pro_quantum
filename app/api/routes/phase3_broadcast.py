"""
TG PRO QUANTUM - Phase 3 Broadcast API Routes

New endpoints:
  GET  /api/v1/campaigns/{id}/detail         – extended campaign details
  GET  /api/v1/campaigns/{id}/activity-log   – paginated activity log
  GET  /api/v1/campaigns/{id}/statistics     – campaign stats
  POST /api/v1/campaigns/{id}/pause          – pause (alias)
  POST /api/v1/campaigns/{id}/resume         – resume (alias)
  POST /api/v1/campaigns/{id}/stop           – stop (alias)
  POST /api/v1/groups/verify                 – group verification
  GET  /api/v1/dashboard/broadcast           – multi-client overview (admin)
  POST /api/v1/campaigns/broadcast           – create campaign with Phase 3 fields
"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_client
from app.core.broadcast_engine import broadcast_engine
from app.database import get_db
from app.models.database import (
    Campaign,
    CampaignActivity,
    CampaignStatus,
    Client,
    TelegramAccount,
)
from app.models.schemas import (
    BroadcastCampaignCreate,
    BroadcastOverviewResponse,
    CampaignActivityResponse,
    CampaignDetailResponse,
    CampaignStats,
    GroupVerifyRequest,
    GroupVerifyResponse,
    MessageResponse,
    MultiClientCampaignCard,
)
from app.services.group_verification import group_verifier

router = APIRouter(tags=["Phase3 Broadcast"])


def _require_owns(campaign: Campaign, client: Client) -> None:
    if campaign.client_id != client.id and not client.is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")


# ── Campaign detail ───────────────────────────────────────────────────────────

@router.get("/campaigns/{campaign_id}/detail", response_model=CampaignDetailResponse)
async def get_campaign_detail(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Extended campaign details including Phase 3 safety fields."""
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    _require_owns(campaign, current_client)
    return campaign


# ── Activity log ──────────────────────────────────────────────────────────────

@router.get(
    "/campaigns/{campaign_id}/activity-log",
    response_model=List[CampaignActivityResponse],
)
async def get_activity_log(
    campaign_id: int,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Paginated activity log (newest first) for a campaign."""
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    _require_owns(campaign, current_client)

    logs_result = await db.execute(
        select(CampaignActivity)
        .where(CampaignActivity.campaign_id == campaign_id)
        .order_by(CampaignActivity.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return logs_result.scalars().all()


# ── Campaign statistics ───────────────────────────────────────────────────────

@router.get("/campaigns/{campaign_id}/statistics", response_model=CampaignStats)
async def get_campaign_statistics(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Aggregated statistics for a campaign."""
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    _require_owns(campaign, current_client)

    total = campaign.total_targets or 1
    delivery_rate = campaign.sent_count / total * 100 if total else 0.0
    progress_pct = (campaign.sent_count + campaign.failed_count) / total * 100 if total else 0.0

    return CampaignStats(
        campaign_id=campaign.id,
        total_targets=campaign.total_targets,
        sent_count=campaign.sent_count,
        failed_count=campaign.failed_count,
        retry_count=campaign.retry_count,
        delivery_rate=round(delivery_rate, 2),
        progress_pct=round(progress_pct, 2),
    )


# ── Pause / Resume / Stop (aliases under /campaigns/{id}/) ────────────────────

@router.post("/campaigns/{campaign_id}/pause", response_model=MessageResponse)
async def pause_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Pause a running campaign."""
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


@router.post("/campaigns/{campaign_id}/resume", response_model=MessageResponse)
async def resume_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Resume a paused campaign."""
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


@router.post("/campaigns/{campaign_id}/stop", response_model=MessageResponse)
async def stop_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Stop a running or paused campaign."""
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    _require_owns(campaign, current_client)
    await broadcast_engine.stop_campaign(campaign_id)
    campaign.status = CampaignStatus.failed
    await db.flush()
    return MessageResponse(message="Campaign stopped")


# ── Group verification ────────────────────────────────────────────────────────

@router.post("/groups/verify", response_model=GroupVerifyResponse)
async def verify_groups(
    body: GroupVerifyRequest,
    current_client: Client = Depends(get_current_client),
):
    """
    Verify that a list of group usernames are valid broadcast targets.

    Rules applied:
      - Must be a GROUP (not a channel)
      - Username format valid
      - No spam indicators
      - Member count >= min_members (if metadata available)
    """
    results = group_verifier.verify_batch(
        body.group_usernames, min_members=body.min_members
    )
    summary = group_verifier.summary(results)
    return GroupVerifyResponse(**summary)


# ── Multi-client broadcast dashboard (admin only) ─────────────────────────────

@router.get("/dashboard/broadcast", response_model=BroadcastOverviewResponse)
async def broadcast_overview(
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """
    Multi-client broadcast overview.
    Admin: sees all clients.
    Regular client: sees only their own campaigns.
    """
    # Fetch campaigns
    if current_client.is_admin:
        camp_q = select(Campaign).order_by(Campaign.created_at.desc()).limit(100)
    else:
        camp_q = (
            select(Campaign)
            .where(Campaign.client_id == current_client.id)
            .order_by(Campaign.created_at.desc())
        )
    camp_result = await db.execute(camp_q)
    campaigns: List[Campaign] = list(camp_result.scalars().all())

    # Build client name map
    client_ids = {c.client_id for c in campaigns}
    client_map: dict[int, str] = {}
    if client_ids:
        cl_result = await db.execute(
            select(Client).where(Client.id.in_(client_ids))
        )
        for cl in cl_result.scalars().all():
            client_map[cl.id] = cl.name

    # Aggregate stats
    active = [c for c in campaigns if c.status == CampaignStatus.running]
    total_sent_24h = 0
    total_targets_24h = 0
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)
    for c in campaigns:
        if c.created_at and c.created_at >= cutoff:
            total_sent_24h += c.sent_count
            total_targets_24h += c.total_targets

    overall_success = (
        round(total_sent_24h / total_targets_24h * 100, 2)
        if total_targets_24h
        else 0.0
    )

    # Account health
    acc_result = await db.execute(
        select(
            func.count(TelegramAccount.id),
            func.sum(
                (TelegramAccount.health_score >= 80.0).cast(type_=func.count().type)
            ),
        )
    )
    # Simple counts fallback
    total_acc_result = await db.execute(select(func.count(TelegramAccount.id)))
    total_accounts = total_acc_result.scalar() or 0

    cards: List[MultiClientCampaignCard] = []
    for camp in campaigns:
        total = camp.total_targets or 1
        success_rate = camp.sent_count / total * 100 if total else 0.0
        elapsed: Optional[float] = None
        if camp.created_at:
            elapsed = (now - camp.created_at).total_seconds() / 60

        cards.append(
            MultiClientCampaignCard(
                client_id=camp.client_id,
                client_name=client_map.get(camp.client_id, "Unknown"),
                campaign_id=camp.id,
                campaign_name=camp.name,
                status=camp.status.value,
                progress_pct=round(
                    (camp.sent_count + camp.failed_count) / total * 100, 2
                ),
                sent_count=camp.sent_count,
                total_targets=camp.total_targets,
                success_rate=round(success_rate, 2),
                active_accounts=0,  # populated by real-time engine
                elapsed_minutes=elapsed,
            )
        )

    return BroadcastOverviewResponse(
        total_active_campaigns=len(active),
        messages_sent_24h=total_sent_24h,
        overall_success_rate=overall_success,
        total_accounts=total_accounts,
        healthy_accounts=total_accounts,  # refined by health engine
        campaigns=cards,
    )


# ── Create broadcast campaign (Phase 3 schema) ────────────────────────────────

@router.post(
    "/campaigns/broadcast",
    response_model=CampaignDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_broadcast_campaign(
    body: BroadcastCampaignCreate,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """
    Create a new broadcast campaign with Phase 3 safety and scheduling fields.
    Admins may specify a client_id; regular users always own the campaign.
    """
    if body.client_id and not current_client.is_admin:
        raise HTTPException(
            status_code=403, detail="Only admins can set client_id"
        )

    owner_id = body.client_id if (body.client_id and current_client.is_admin) else current_client.id

    campaign = Campaign(
        client_id=owner_id,
        name=body.name,
        message_text=body.message_text,
        media_url=body.media_url,
        mode=body.mode,
        scheduled_at=body.scheduled_at,
        target_group_ids=body.target_group_ids,
        account_ids=body.account_ids,
        delay_min=body.delay_min,
        delay_max=body.delay_max,
        max_retries=body.max_retries,
        total_targets=len(body.target_group_ids),
        # Phase 3 fields
        safety_flags=body.safety_flags or {
            "jitter_enabled": True,
            "rotation_enabled": True,
            "auto_pause_on_warnings": 3,
            "smart_retry": True,
        },
        error_count=0,
        failed_groups_log=[],
    )

    # Set optional Phase 3 columns via setattr to handle dynamic columns
    _p3_fields = {
        "link_url": body.link_url,
        "jitter_pct": body.jitter_pct,
        "max_per_hour": body.max_per_hour,
        "max_per_day": body.max_per_day,
        "rotate_every": body.rotate_every,
        "account_group_id": body.account_group_id,
        "timing_start": body.timing_start,
        "timing_end": body.timing_end,
    }
    for attr, val in _p3_fields.items():
        if val is not None:
            setattr(campaign, attr, val)

    db.add(campaign)
    await db.flush()
    await db.refresh(campaign)
    return campaign
