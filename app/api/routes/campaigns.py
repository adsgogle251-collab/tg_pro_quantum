import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_client_or_403, get_current_user
from app.database import get_db
from app.models.database import (
    Campaign,
    CampaignAccount,
    CampaignGroup,
    CampaignMessage,
    CampaignStatus,
    Client,
    TelegramAccount,
    TelegramGroup,
    User,
)
from app.models.schemas import (
    CampaignCreate,
    CampaignResponse,
    CampaignScheduleRequest,
    CampaignUpdate,
    CampaignValidationResult,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Campaigns"])


@router.get("/clients/{client_id}/campaigns/", response_model=List[CampaignResponse])
async def list_campaigns(
    client_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _client: Client = Depends(get_client_or_403),
    skip: int = 0,
    limit: int = 50,
):
    result = await db.execute(
        select(Campaign)
        .where(Campaign.client_id == client_id)
        .offset(skip)
        .limit(limit)
        .order_by(Campaign.created_at.desc())
    )
    return result.scalars().all()


@router.post(
    "/clients/{client_id}/campaigns/",
    response_model=CampaignResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_campaign(
    client_id: int,
    payload: CampaignCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _client: Client = Depends(get_client_or_403),
):
    campaign = Campaign(
        client_id=client_id,
        name=payload.name,
        description=payload.description,
        broadcast_mode=payload.broadcast_mode,
        delay_min=payload.delay_min,
        delay_max=payload.delay_max,
        max_messages_per_hour=payload.max_messages_per_hour,
        loop_count=payload.loop_count,
        is_loop_infinite=payload.is_loop_infinite,
        scheduled_at=payload.scheduled_at,
        status=CampaignStatus.draft,
    )
    db.add(campaign)
    await db.flush()

    for account_id in payload.account_ids:
        db.add(CampaignAccount(campaign_id=campaign.id, account_id=account_id))

    for group_id in payload.group_ids:
        db.add(CampaignGroup(campaign_id=campaign.id, group_id=group_id))

    for idx, msg in enumerate(payload.messages):
        db.add(
            CampaignMessage(
                campaign_id=campaign.id,
                message_text=msg.message_text,
                has_media=msg.has_media,
                media_path=msg.media_path,
                message_type=msg.message_type,
                order_index=msg.order_index if msg.order_index else idx,
            )
        )

    await db.flush()
    await db.refresh(campaign)
    return campaign


@router.get("/clients/{client_id}/campaigns/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    client_id: int,
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _client: Client = Depends(get_client_or_403),
):
    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.client_id == client_id,
        )
    )
    campaign = result.scalar_one_or_none()
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return campaign


@router.put("/clients/{client_id}/campaigns/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    client_id: int,
    campaign_id: int,
    payload: CampaignUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _client: Client = Depends(get_client_or_403),
):
    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.client_id == client_id,
        )
    )
    campaign = result.scalar_one_or_none()
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    if campaign.status == CampaignStatus.running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot update a running campaign. Pause it first.",
        )
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(campaign, field, value)
    await db.flush()
    await db.refresh(campaign)
    return campaign


@router.delete(
    "/clients/{client_id}/campaigns/{campaign_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_campaign(
    client_id: int,
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _client: Client = Depends(get_client_or_403),
):
    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.client_id == client_id,
        )
    )
    campaign = result.scalar_one_or_none()
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    if campaign.status == CampaignStatus.running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Stop the campaign before deleting it.",
        )
    await db.delete(campaign)


@router.post("/clients/{client_id}/campaigns/{campaign_id}/schedule")
async def schedule_campaign(
    client_id: int,
    campaign_id: int,
    payload: CampaignScheduleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _client: Client = Depends(get_client_or_403),
):
    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.client_id == client_id,
        )
    )
    campaign = result.scalar_one_or_none()
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    if campaign.status not in (CampaignStatus.draft, CampaignStatus.paused):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot schedule campaign in '{campaign.status}' state",
        )
    campaign.scheduled_at = payload.scheduled_at
    campaign.status = CampaignStatus.scheduled
    await db.flush()
    return {"message": "Campaign scheduled", "scheduled_at": payload.scheduled_at}


@router.post("/clients/{client_id}/campaigns/{campaign_id}/validate")
async def validate_campaign(
    client_id: int,
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _client: Client = Depends(get_client_or_403),
):
    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.client_id == client_id,
        )
    )
    campaign = result.scalar_one_or_none()
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    errors: List[str] = []
    warnings: List[str] = []

    msgs_res = await db.execute(
        select(CampaignMessage).where(CampaignMessage.campaign_id == campaign_id)
    )
    messages = msgs_res.scalars().all()
    if not messages:
        errors.append("Campaign has no messages")

    accs_res = await db.execute(
        select(CampaignAccount).where(CampaignAccount.campaign_id == campaign_id)
    )
    accounts = accs_res.scalars().all()
    if not accounts:
        errors.append("Campaign has no assigned accounts")

    grps_res = await db.execute(
        select(CampaignGroup).where(CampaignGroup.campaign_id == campaign_id)
    )
    groups = grps_res.scalars().all()
    if not groups:
        errors.append("Campaign has no target groups")

    if campaign.delay_min > campaign.delay_max:
        errors.append("delay_min must be <= delay_max")

    if campaign.max_messages_per_hour > 500:
        warnings.append("High message rate may trigger Telegram rate limits")

    return CampaignValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )
