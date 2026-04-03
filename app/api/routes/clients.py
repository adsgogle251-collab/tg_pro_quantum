from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_admin, get_current_user
from app.database import get_db
from app.models.database import (
    Campaign,
    CampaignStatus,
    Client,
    TelegramAccount,
    TelegramGroup,
    User,
)
from app.models.schemas import (
    ClientCreate,
    ClientResponse,
    ClientStats,
    ClientUpdate,
)
from app.utils.helpers import generate_api_key

router = APIRouter(prefix="/clients", tags=["Clients"])


@router.get("/", response_model=List[ClientResponse])
async def list_clients(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
):
    query = select(Client)
    if current_user.role != "super_admin":
        query = query.where(Client.user_id == current_user.id)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    payload: ClientCreate,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    client = Client(
        user_id=current_user.id,
        name=payload.name,
        company=payload.company,
        api_key=generate_api_key(),
        status="active",
        plan=payload.plan,
        max_accounts=payload.max_accounts,
    )
    db.add(client)
    await db.flush()
    await db.refresh(client)
    return client


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    if current_user.role != "super_admin" and client.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return client


@router.put("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: int,
    payload: ClientUpdate,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    if current_user.role != "super_admin" and client.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(client, field, value)
    await db.flush()
    await db.refresh(client)
    return client


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: int,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    if current_user.role != "super_admin" and client.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    await db.delete(client)


@router.get("/{client_id}/stats", response_model=ClientStats)
async def get_client_stats(
    client_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    if current_user.role != "super_admin" and client.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    total_accounts_res = await db.execute(
        select(func.count(TelegramAccount.id)).where(TelegramAccount.client_id == client_id)
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
    total_campaigns_res = await db.execute(
        select(func.count(Campaign.id)).where(Campaign.client_id == client_id)
    )
    running_campaigns_res = await db.execute(
        select(func.count(Campaign.id)).where(
            Campaign.client_id == client_id,
            Campaign.status == CampaignStatus.running,
        )
    )

    return ClientStats(
        total_accounts=total_accounts_res.scalar() or 0,
        active_accounts=active_accounts_res.scalar() or 0,
        total_groups=total_groups_res.scalar() or 0,
        total_campaigns=total_campaigns_res.scalar() or 0,
        running_campaigns=running_campaigns_res.scalar() or 0,
        messages_sent_today=0,  # Populated from analytics in production
    )
