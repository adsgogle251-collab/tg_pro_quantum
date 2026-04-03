import csv
import io
import json
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_client_or_403, get_current_user
from app.database import get_db
from app.models.database import (
    BroadcastHistory,
    Campaign,
    CampaignAnalytics,
    CampaignStatus,
    Client,
    TelegramAccount,
    TelegramGroup,
    User,
)
from app.models.schemas import (
    AnalyticsHistoryEntry,
    CampaignAnalyticsResponse,
    ClientAnalyticsOverview,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Analytics"])


@router.get("/campaigns/{campaign_id}/analytics/", response_model=CampaignAnalyticsResponse)
async def get_campaign_analytics(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CampaignAnalytics).where(CampaignAnalytics.campaign_id == campaign_id)
    )
    analytics = result.scalar_one_or_none()
    if analytics is None:
        # Compute on-the-fly if analytics record doesn't exist yet
        campaign_res = await db.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        if campaign_res.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found"
            )
        from app.core.analytics_engine import AnalyticsEngine

        engine = AnalyticsEngine(db)
        analytics = await engine.compute_campaign_analytics(campaign_id)

    return CampaignAnalyticsResponse(
        campaign_id=analytics.campaign_id,
        total_sent=analytics.total_sent,
        total_failed=analytics.total_failed,
        total_pending=analytics.total_pending,
        delivery_rate=analytics.delivery_rate,
        avg_send_time=analytics.avg_send_time,
        last_updated=analytics.last_updated,
    )


@router.get("/clients/{client_id}/analytics/overview", response_model=ClientAnalyticsOverview)
async def get_client_overview(
    client_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _client: Client = Depends(get_client_or_403),
):
    total_campaigns_res = await db.execute(
        select(func.count(Campaign.id)).where(Campaign.client_id == client_id)
    )
    completed_campaigns_res = await db.execute(
        select(func.count(Campaign.id)).where(
            Campaign.client_id == client_id,
            Campaign.status == CampaignStatus.completed,
        )
    )
    active_accounts_res = await db.execute(
        select(func.count(TelegramAccount.id)).where(
            TelegramAccount.client_id == client_id,
            TelegramAccount.status == "active",
        )
    )
    total_groups_res = await db.execute(
        select(func.count(TelegramGroup.id)).where(TelegramGroup.client_id == client_id)
    )

    # Aggregate analytics across all campaigns
    campaigns_res = await db.execute(
        select(Campaign.id).where(Campaign.client_id == client_id)
    )
    campaign_ids = [row[0] for row in campaigns_res.fetchall()]

    total_sent = 0
    total_failed = 0
    if campaign_ids:
        sent_res = await db.execute(
            select(func.sum(CampaignAnalytics.total_sent)).where(
                CampaignAnalytics.campaign_id.in_(campaign_ids)
            )
        )
        failed_res = await db.execute(
            select(func.sum(CampaignAnalytics.total_failed)).where(
                CampaignAnalytics.campaign_id.in_(campaign_ids)
            )
        )
        total_sent = sent_res.scalar() or 0
        total_failed = failed_res.scalar() or 0

    total_attempts = total_sent + total_failed
    delivery_rate = (total_sent / total_attempts * 100) if total_attempts > 0 else 0.0

    return ClientAnalyticsOverview(
        client_id=client_id,
        total_campaigns=total_campaigns_res.scalar() or 0,
        completed_campaigns=completed_campaigns_res.scalar() or 0,
        total_messages_sent=total_sent,
        total_messages_failed=total_failed,
        overall_delivery_rate=round(delivery_rate, 2),
        active_accounts=active_accounts_res.scalar() or 0,
        total_groups=total_groups_res.scalar() or 0,
    )


@router.get("/clients/{client_id}/analytics/history", response_model=List[AnalyticsHistoryEntry])
async def get_analytics_history(
    client_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _client: Client = Depends(get_client_or_403),
    skip: int = 0,
    limit: int = 50,
):
    result = await db.execute(
        select(Campaign, CampaignAnalytics)
        .outerjoin(CampaignAnalytics, Campaign.id == CampaignAnalytics.campaign_id)
        .where(Campaign.client_id == client_id)
        .order_by(Campaign.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    rows = result.all()
    entries = []
    for campaign, analytics in rows:
        entries.append(
            AnalyticsHistoryEntry(
                campaign_id=campaign.id,
                campaign_name=campaign.name,
                status=campaign.status.value
                if hasattr(campaign.status, "value")
                else campaign.status,
                total_sent=analytics.total_sent if analytics else 0,
                total_failed=analytics.total_failed if analytics else 0,
                delivery_rate=analytics.delivery_rate if analytics else 0.0,
                started_at=campaign.started_at,
                completed_at=campaign.completed_at,
            )
        )
    return entries


@router.get("/clients/{client_id}/analytics/export")
async def export_analytics(
    client_id: int,
    format: str = "csv",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _client: Client = Depends(get_client_or_403),
):
    result = await db.execute(
        select(Campaign, CampaignAnalytics)
        .outerjoin(CampaignAnalytics, Campaign.id == CampaignAnalytics.campaign_id)
        .where(Campaign.client_id == client_id)
        .order_by(Campaign.created_at.desc())
    )
    rows = result.all()
    data = [
        {
            "campaign_id": c.id,
            "campaign_name": c.name,
            "status": c.status.value if hasattr(c.status, "value") else c.status,
            "total_sent": a.total_sent if a else 0,
            "total_failed": a.total_failed if a else 0,
            "delivery_rate": a.delivery_rate if a else 0.0,
            "started_at": c.started_at.isoformat() if c.started_at else "",
            "completed_at": c.completed_at.isoformat() if c.completed_at else "",
        }
        for c, a in rows
    ]

    if format == "json":
        return Response(
            content=json.dumps(data, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=analytics_{client_id}.json"},
        )

    # Default: CSV
    output = io.StringIO()
    if data:
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=analytics_{client_id}.csv"
        },
    )
