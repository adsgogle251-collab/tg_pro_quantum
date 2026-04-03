import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_client_or_403, get_current_user
from app.database import get_db
from app.models.database import Client, TelegramAccount, TelegramGroup, User
from app.models.schemas import GroupAutoJoinRequest, GroupResponse, GroupScrapeMembersRequest, GroupUpdate

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Groups"])


@router.get("/clients/{client_id}/groups/", response_model=List[GroupResponse])
async def list_groups(
    client_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _client: Client = Depends(get_client_or_403),
    skip: int = 0,
    limit: int = 100,
):
    result = await db.execute(
        select(TelegramGroup)
        .where(TelegramGroup.client_id == client_id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.post("/clients/{client_id}/groups/auto-join", status_code=status.HTTP_202_ACCEPTED)
async def auto_join_groups(
    client_id: int,
    payload: GroupAutoJoinRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _client: Client = Depends(get_client_or_403),
):
    acc_result = await db.execute(
        select(TelegramAccount).where(
            TelegramAccount.id == payload.account_id,
            TelegramAccount.client_id == client_id,
            TelegramAccount.status == "active",
        )
    )
    account = acc_result.scalar_one_or_none()
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active account not found",
        )

    from app.core.group_manager import GroupManager

    gm = GroupManager()
    results = await gm.auto_join(account, payload.group_links, client_id, db)
    return {"message": "Auto-join initiated", "results": results}


@router.post("/clients/{client_id}/groups/scrape-members", status_code=status.HTTP_202_ACCEPTED)
async def scrape_members(
    client_id: int,
    payload: GroupScrapeMembersRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _client: Client = Depends(get_client_or_403),
):
    acc_result = await db.execute(
        select(TelegramAccount).where(
            TelegramAccount.id == payload.account_id,
            TelegramAccount.client_id == client_id,
            TelegramAccount.status == "active",
        )
    )
    account = acc_result.scalar_one_or_none()
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active account not found",
        )

    grp_result = await db.execute(
        select(TelegramGroup).where(
            TelegramGroup.id == payload.group_id,
            TelegramGroup.client_id == client_id,
        )
    )
    group = grp_result.scalar_one_or_none()
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    from app.core.group_manager import GroupManager

    gm = GroupManager()
    count = await gm.scrape_members(account, group, payload.limit, db)
    return {"message": "Member scraping completed", "members_scraped": count}


@router.put("/clients/{client_id}/groups/{group_id}", response_model=GroupResponse)
async def update_group(
    client_id: int,
    group_id: int,
    payload: GroupUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _client: Client = Depends(get_client_or_403),
):
    result = await db.execute(
        select(TelegramGroup).where(
            TelegramGroup.id == group_id,
            TelegramGroup.client_id == client_id,
        )
    )
    group = result.scalar_one_or_none()
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(group, field, value)
    await db.flush()
    await db.refresh(group)
    return group


@router.delete(
    "/clients/{client_id}/groups/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_group(
    client_id: int,
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _client: Client = Depends(get_client_or_403),
):
    result = await db.execute(
        select(TelegramGroup).where(
            TelegramGroup.id == group_id,
            TelegramGroup.client_id == client_id,
        )
    )
    group = result.scalar_one_or_none()
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    await db.delete(group)
