"""
TG PRO QUANTUM - Client Management Routes (Admin)
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_client, require_admin
from app.database import get_db
from app.models.database import Client, Campaign, CampaignStatus, TelegramAccount, AccountGroup
from app.models.schemas import ClientCreate, ClientResponse, ClientUpdate, ClientDashboard, MessageResponse
from app.api.dependencies import hash_password
from app.utils.helpers import generate_api_key

router = APIRouter(prefix="/clients", tags=["Clients"])


@router.get("/", response_model=List[ClientResponse])
async def list_clients(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _admin: Client = Depends(require_admin),
):
    """List all clients (admin only)."""
    result = await db.execute(select(Client).offset(skip).limit(limit))
    return result.scalars().all()


@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    body: ClientCreate,
    db: AsyncSession = Depends(get_db),
    _admin: Client = Depends(require_admin),
):
    """Create a new client (admin only)."""
    existing = await db.execute(select(Client).where(Client.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    client = Client(
        name=body.name,
        email=body.email,
        hashed_password=hash_password(body.password),
        api_key=generate_api_key(),
        plan_type=body.plan_type,
        usage_limit_monthly=body.usage_limit_monthly or 10000,
        webhook_url=body.webhook_url,
    )
    db.add(client)
    await db.flush()
    await db.refresh(client)
    return client


@router.get("/me", response_model=ClientResponse)
async def get_my_profile(current_client: Client = Depends(get_current_client)):
    """Return current client's profile."""
    return current_client


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Get a client by ID (admin or self)."""
    if not current_client.is_admin and current_client.id != client_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.patch("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: int,
    body: ClientUpdate,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Update a client (admin or self)."""
    if not current_client.is_admin and current_client.id != client_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(client, key, value)

    await db.flush()
    await db.refresh(client)
    return client


@router.delete("/{client_id}", response_model=MessageResponse)
async def delete_client(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: Client = Depends(require_admin),
):
    """Delete a client (admin only)."""
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    await db.delete(client)
    return MessageResponse(message="Client deleted")


@router.post("/{client_id}/regenerate-api-key", response_model=dict)
async def regenerate_api_key(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Regenerate API key for a client."""
    if not current_client.is_admin and current_client.id != client_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    client.api_key = generate_api_key()
    await db.flush()
    return {"api_key": client.api_key}


@router.get("/{client_id}/dashboard", response_model=ClientDashboard)
async def get_client_dashboard(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Get dashboard statistics for a client (admin or self)."""
    if not current_client.is_admin and current_client.id != client_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Campaign stats
    campaigns_result = await db.execute(
        select(Campaign).where(Campaign.client_id == client_id)
    )
    campaigns = campaigns_result.scalars().all()
    total_campaigns = len(campaigns)
    active_campaigns = sum(
        1 for c in campaigns if c.status in (CampaignStatus.running, CampaignStatus.scheduled)
    )
    total_sent = sum(c.sent_count for c in campaigns)
    total_targets = sum(c.total_targets for c in campaigns)
    delivery_rate = round(total_sent / total_targets * 100, 2) if total_targets else 0.0

    # Accounts
    accounts_result = await db.execute(
        select(func.count(TelegramAccount.id)).where(TelegramAccount.client_id == client_id)
    )
    accounts_count = accounts_result.scalar() or 0

    # Account groups
    groups_result = await db.execute(
        select(func.count(AccountGroup.id)).where(AccountGroup.client_id == client_id)
    )
    groups_count = groups_result.scalar() or 0

    return ClientDashboard(
        client_id=client.id,
        client_name=client.name,
        plan_type=client.plan_type.value,
        status=client.status.value,
        total_campaigns=total_campaigns,
        active_campaigns=active_campaigns,
        total_messages_sent=total_sent,
        usage_limit_monthly=client.usage_limit_monthly,
        current_usage_monthly=client.current_usage_monthly,
        usage_pct=round(client.current_usage_monthly / client.usage_limit_monthly * 100, 2)
        if client.usage_limit_monthly else 0.0,
        accounts_count=accounts_count,
        account_groups_count=groups_count,
        overall_delivery_rate=delivery_rate,
    )
