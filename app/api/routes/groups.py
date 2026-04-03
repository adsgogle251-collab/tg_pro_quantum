"""
TG PRO QUANTUM - Group Management Routes
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_client
from app.core.group_manager import group_manager
from app.database import get_db
from app.models.database import Client, Group
from app.models.schemas import GroupCreate, GroupResponse, GroupUpdate, MessageResponse

router = APIRouter(prefix="/groups", tags=["Groups"])


def _require_owns(group: Group, client: Client) -> None:
    if group.client_id != client.id and not client.is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("/", response_model=List[GroupResponse])
async def list_groups(
    active_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """List groups for the current client."""
    query = select(Group).where(Group.client_id == current_client.id)
    if active_only:
        query = query.where(Group.is_active == True)  # noqa: E712
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    body: GroupCreate,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Add a group/channel target."""
    from app.utils.helpers import safe_username
    username = safe_username(body.username)

    existing = await db.execute(
        select(Group).where(Group.client_id == current_client.id, Group.username == username)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Group already exists")

    group = Group(
        client_id=current_client.id,
        username=username,
        title=body.title,
        tags=body.tags,
    )
    db.add(group)
    await db.flush()
    await db.refresh(group)
    return group


@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    _require_owns(group, current_client)
    return group


@router.patch("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: int,
    body: GroupUpdate,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    _require_owns(group, current_client)

    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(group, key, value)
    await db.flush()
    await db.refresh(group)
    return group


@router.delete("/{group_id}", response_model=MessageResponse)
async def delete_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    _require_owns(group, current_client)
    await db.delete(group)
    return MessageResponse(message="Group deleted")


@router.post("/{group_id}/auto-join", response_model=MessageResponse)
async def auto_join_group(
    group_id: int,
    account_id: int = Query(..., description="Telegram account ID to use for joining"),
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Auto-join a Telegram group using the specified account."""
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    _require_owns(group, current_client)

    success = await group_manager.join_group(group.username, account_id, db)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to join group")
    return MessageResponse(message=f"Joined group @{group.username}")


@router.post("/bulk-import", response_model=MessageResponse)
async def bulk_import_groups(
    usernames: List[str],
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Bulk-import a list of group usernames."""
    from app.utils.helpers import safe_username
    added = 0
    for raw in usernames:
        username = safe_username(raw)
        existing = await db.execute(
            select(Group).where(Group.client_id == current_client.id, Group.username == username)
        )
        if existing.scalar_one_or_none():
            continue
        db.add(Group(client_id=current_client.id, username=username))
        added += 1

    await db.flush()
    return MessageResponse(message=f"Imported {added} groups")
