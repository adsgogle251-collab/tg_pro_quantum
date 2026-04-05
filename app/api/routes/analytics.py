"""
TG PRO QUANTUM - Analytics & Reporting Routes
"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_client
from app.core.analytics_engine import analytics_engine
from app.database import get_db
from app.models.database import (
    AuditLog, Campaign, CampaignStatus, Client, TelegramAccount, Group,
)
from app.models.schemas import CampaignStats, ClientStats

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/campaigns", response_model=List[CampaignStats])
async def campaign_stats(
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Per-campaign delivery statistics for current client."""
    return await analytics_engine.campaign_stats(current_client.id, db)


@router.get("/overview", response_model=ClientStats)
async def client_overview(
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Aggregated statistics for the current client."""
    return await analytics_engine.client_overview(current_client.id, db)


@router.get("/history")
async def campaign_history(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Recent campaign history with basic stats."""
    result = await db.execute(
        select(Campaign)
        .where(Campaign.client_id == current_client.id)
        .order_by(Campaign.created_at.desc())
        .limit(limit)
    )
    campaigns = result.scalars().all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "status": c.status.value,
            "sent_count": c.sent_count,
            "failed_count": c.failed_count,
            "total_targets": c.total_targets,
            "delivery_rate": round(c.sent_count / max(c.total_targets, 1) * 100, 2),
            "created_at": c.created_at,
            "completed_at": c.completed_at,
        }
        for c in campaigns
    ]


@router.get("/dashboard")
async def analytics_dashboard(
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Aggregated dashboard statistics for the current client."""
    # Campaigns counts
    total_campaigns = (
        await db.execute(
            select(func.count(Campaign.id)).where(Campaign.client_id == current_client.id)
        )
    ).scalar() or 0

    active_campaigns = (
        await db.execute(
            select(func.count(Campaign.id)).where(
                Campaign.client_id == current_client.id,
                Campaign.status == CampaignStatus.running,
            )
        )
    ).scalar() or 0

    # Accounts counts
    total_accounts = (
        await db.execute(
            select(func.count(TelegramAccount.id)).where(
                TelegramAccount.client_id == current_client.id
            )
        )
    ).scalar() or 0

    # Total messages
    total_sent = (
        await db.execute(
            select(func.coalesce(func.sum(Campaign.sent_count), 0)).where(
                Campaign.client_id == current_client.id
            )
        )
    ).scalar() or 0

    total_failed = (
        await db.execute(
            select(func.coalesce(func.sum(Campaign.failed_count), 0)).where(
                Campaign.client_id == current_client.id
            )
        )
    ).scalar() or 0

    success_rate = round((total_sent / max(total_sent + total_failed, 1)) * 100, 2)

    return {
        "total_campaigns": total_campaigns,
        "active_campaigns": active_campaigns,
        "total_accounts": total_accounts,
        "total_sent": total_sent,
        "total_failed": total_failed,
        "success_rate": success_rate,
        "monthly_growth": 5.2,  # placeholder; real growth would need historical data
    }


@router.get("/charts")
async def analytics_charts(
    range: str = Query("30d", pattern=r"^(7d|30d|90d)$"),
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Chart data for the analytics page (line, bar, pie)."""
    now = datetime.now(timezone.utc)
    days = {"7d": 7, "30d": 30, "90d": 90}.get(range, 30)
    since = now - timedelta(days=days)

    # Recent campaigns for bar chart
    result = await db.execute(
        select(Campaign)
        .where(
            Campaign.client_id == current_client.id,
            Campaign.created_at >= since,
        )
        .order_by(Campaign.created_at.asc())
        .limit(10)
    )
    campaigns = result.scalars().all()

    bar_data = [
        {"name": c.name[:20], "sent": c.sent_count, "failed": c.failed_count}
        for c in campaigns
    ]

    # Pie: delivery status distribution from all campaigns
    sent_total = sum(c.sent_count for c in campaigns) or 0
    failed_total = sum(c.failed_count for c in campaigns) or 0
    total = sent_total + failed_total or 1
    pie_data = [
        {"name": "Delivered", "value": round(sent_total / total * 100, 1)},
        {"name": "Failed", "value": round(failed_total / total * 100, 1)},
    ]

    # Line chart: simple trend by week
    line_data = []
    for i in range(min(days, 7)):
        day = now - timedelta(days=i)
        label = day.strftime("%b %d")
        line_data.insert(0, {"name": label, "sent": 0, "delivered": 0})

    return {
        "bar": bar_data,
        "pie": pie_data,
        "line": line_data,
        "range": range,
    }


@router.get("/timeline")
async def analytics_timeline(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Timeline of recent audit-log actions for the current user."""
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.client_id == current_client.id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    logs = result.scalars().all()
    return [
        {
            "id": log.id,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": log.details,
            "created_at": log.created_at,
        }
        for log in logs
    ]
