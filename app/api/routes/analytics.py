"""
TG PRO QUANTUM - Analytics & Reporting Routes
"""
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_client
from app.core.analytics_engine import analytics_engine
from app.database import get_db
from app.models.database import Campaign, Client, TelegramAccount, Group
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
