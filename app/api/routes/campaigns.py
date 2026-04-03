"""
TG PRO QUANTUM - Campaign CRUD Routes
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_client
from app.database import get_db
from app.models.database import Campaign, CampaignStatus, Client
from app.models.schemas import (
    CampaignCreate, CampaignResponse, CampaignUpdate, MessageResponse,
)

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


def _require_owns(campaign: Campaign, client: Client) -> None:
    if campaign.client_id != client.id and not client.is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("/", response_model=List[CampaignResponse])
async def list_campaigns(
    status_filter: str = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """List campaigns for the current client."""
    query = select(Campaign).where(Campaign.client_id == current_client.id)
    if status_filter:
        try:
            query = query.where(Campaign.status == CampaignStatus(status_filter))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status_filter}")
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
