"""
TG PRO QUANTUM - Campaign CRUD Routes
"""
from math import ceil
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_client
from app.database import get_db
from app.models.database import Campaign, CampaignStatus, Client
from app.models.schemas import (
    CampaignCreate, CampaignResponse, CampaignUpdate, MessageResponse, PaginatedResponse,
)

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


def _require_owns(campaign: Campaign, client: Client) -> None:
    if campaign.client_id != client.id and not client.is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("/")
async def list_campaigns(
    page: Optional[int] = Query(None, ge=1),
    per_page: int = Query(20, ge=1, le=200),
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """List campaigns for the current client.

    When *page* is provided returns a paginated envelope; otherwise returns a plain list.
    """
    query = select(Campaign).where(Campaign.client_id == current_client.id)
    count_query = select(func.count(Campaign.id)).where(Campaign.client_id == current_client.id)

    if search:
        like = f"%{search}%"
        query = query.where(Campaign.name.ilike(like))
        count_query = count_query.where(Campaign.name.ilike(like))

    if status_filter:
        try:
            sv = CampaignStatus(status_filter)
            query = query.where(Campaign.status == sv)
            count_query = count_query.where(Campaign.status == sv)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status_filter}")

    if page is not None:
        total = (await db.execute(count_query)).scalar() or 0
        offset = (page - 1) * per_page
        result = await db.execute(query.order_by(Campaign.created_at.desc()).offset(offset).limit(per_page))
        items = result.scalars().all()
        from math import ceil
        return PaginatedResponse(
            items=[CampaignResponse.model_validate(c) for c in items],
            total=total,
            page=page,
            per_page=per_page,
            pages=ceil(total / per_page) if per_page else 1,
        )

    result = await db.execute(query.order_by(Campaign.created_at.desc()))
    return result.scalars().all()


@router.post("/", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    body: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Create a new broadcast campaign."""
    campaign = Campaign(
        client_id=current_client.id,
        **body.model_dump(),
    )
    campaign.total_targets = len(body.target_group_ids)
    db.add(campaign)
    await db.flush()
    await db.refresh(campaign)
    return campaign


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    _require_owns(campaign, current_client)
    return campaign


@router.patch("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: int,
    body: CampaignUpdate,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    _require_owns(campaign, current_client)

    if campaign.status in (CampaignStatus.running,):
        raise HTTPException(status_code=409, detail="Cannot edit a running campaign")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(campaign, key, value)
    if "target_group_ids" in update_data:
        campaign.total_targets = len(update_data["target_group_ids"])

    await db.flush()
    await db.refresh(campaign)
    return campaign


@router.delete("/{campaign_id}", response_model=MessageResponse)
async def delete_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    _require_owns(campaign, current_client)

    if campaign.status == CampaignStatus.running:
        raise HTTPException(status_code=409, detail="Stop the campaign before deleting")

    await db.delete(campaign)
    return MessageResponse(message="Campaign deleted")
