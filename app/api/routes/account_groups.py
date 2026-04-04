"""
TG PRO QUANTUM - Account Groups API Routes

Provides CRUD and account management for named account pools that can be
assigned to features (broadcast, finder, scrape, join, cs, warmer).
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_client
from app.database import get_db
from app.models.database import (
    AccountAssignment, AccountGroup, AccountGroupStatus,
    AccountHealth, GroupAnalytics, TelegramAccount, Client,
)
from app.models.schemas import (
    AccountGroupBulkImport, AccountGroupCreate, AccountGroupResponse,
    AccountGroupUpdate, AccountAssignmentCreate, AccountAssignmentResponse,
    AccountHealthResponse, GroupAnalyticsResponse, MessageResponse,
)

router = APIRouter(prefix="/account-groups", tags=["Account Groups"])


def _require_owns_group(group: AccountGroup, client: Client) -> None:
    if group.client_id is not None and group.client_id != client.id and not client.is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")


# ── Group CRUD ────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[AccountGroupResponse])
async def list_account_groups(
    feature_type: Optional[str] = Query(None),
    status_filter: Optional[AccountGroupStatus] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """List account groups accessible to the current client."""
    query = select(AccountGroup)
    if not current_client.is_admin:
        # Non-admins see groups assigned to them or unassigned groups
        from sqlalchemy import or_
        query = query.where(
            or_(AccountGroup.client_id == current_client.id, AccountGroup.client_id.is_(None))
        )
    if feature_type:
        query = query.where(AccountGroup.feature_type == feature_type)
    if status_filter:
        query = query.where(AccountGroup.status == status_filter)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=AccountGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_account_group(
    body: AccountGroupCreate,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Create a new account group."""
    # Non-admins can only create groups for themselves
    client_id = body.client_id
    if not current_client.is_admin:
        client_id = current_client.id

    group = AccountGroup(
        name=body.name,
        feature_type=body.feature_type,
        client_id=client_id,
        config=body.config or {},
    )
    db.add(group)
    await db.flush()
    await db.refresh(group)
    return group


@router.get("/{group_id}", response_model=AccountGroupResponse)
async def get_account_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Get a specific account group."""
    result = await db.execute(select(AccountGroup).where(AccountGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Account group not found")
    _require_owns_group(group, current_client)
    return group


@router.put("/{group_id}", response_model=AccountGroupResponse)
async def update_account_group(
    group_id: int,
    body: AccountGroupUpdate,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Update an account group."""
    result = await db.execute(select(AccountGroup).where(AccountGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Account group not found")
    _require_owns_group(group, current_client)

    update_data = body.model_dump(exclude_unset=True)
    if not current_client.is_admin:
        update_data.pop("client_id", None)  # non-admins cannot reassign group ownership
    for field, value in update_data.items():
        setattr(group, field, value)
    await db.flush()
    await db.refresh(group)
    return group


@router.delete("/{group_id}", response_model=MessageResponse)
async def delete_account_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Delete an account group (cascades assignments and health records)."""
    result = await db.execute(select(AccountGroup).where(AccountGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Account group not found")
    _require_owns_group(group, current_client)
    await db.delete(group)
    await db.flush()
    return MessageResponse(message=f"Account group '{group.name}' deleted")


# ── Account Assignments ───────────────────────────────────────────────────────

@router.get("/{group_id}/accounts", response_model=List[AccountAssignmentResponse])
async def list_group_accounts(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """List accounts assigned to a group."""
    result = await db.execute(select(AccountGroup).where(AccountGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Account group not found")
    _require_owns_group(group, current_client)

    assignments = await db.execute(
        select(AccountAssignment).where(AccountAssignment.account_group_id == group_id)
    )
    return assignments.scalars().all()


@router.post("/{group_id}/accounts", response_model=AccountAssignmentResponse,
             status_code=status.HTTP_201_CREATED)
async def add_account_to_group(
    group_id: int,
    body: AccountAssignmentCreate,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Add a single account to a group."""
    result = await db.execute(select(AccountGroup).where(AccountGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Account group not found")
    _require_owns_group(group, current_client)

    # Verify account belongs to client
    acc_result = await db.execute(
        select(TelegramAccount).where(TelegramAccount.id == body.account_id)
    )
    account = acc_result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if not current_client.is_admin and account.client_id != current_client.id:
        raise HTTPException(status_code=403, detail="Account does not belong to client")

    # Check duplicate
    existing = await db.execute(
        select(AccountAssignment).where(
            AccountAssignment.account_id == body.account_id,
            AccountAssignment.account_group_id == group_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Account already assigned to this group")

    assignment = AccountAssignment(
        account_id=body.account_id,
        account_group_id=group_id,
        feature_type=body.feature_type,
    )
    db.add(assignment)
    await db.flush()
    await db.refresh(assignment)
    return assignment


@router.post("/{group_id}/import", response_model=MessageResponse,
             status_code=status.HTTP_201_CREATED)
async def bulk_import_accounts(
    group_id: int,
    body: AccountGroupBulkImport,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Bulk-import accounts into a group (up to 10 000 at once)."""
    result = await db.execute(select(AccountGroup).where(AccountGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Account group not found")
    _require_owns_group(group, current_client)

    added = 0
    skipped = 0
    for account_id in body.account_ids:
        # Check account ownership
        acc_result = await db.execute(
            select(TelegramAccount).where(TelegramAccount.id == account_id)
        )
        account = acc_result.scalar_one_or_none()
        if not account:
            skipped += 1
            continue
        if not current_client.is_admin and account.client_id != current_client.id:
            skipped += 1
            continue

        existing = await db.execute(
            select(AccountAssignment).where(
                AccountAssignment.account_id == account_id,
                AccountAssignment.account_group_id == group_id,
            )
        )
        if existing.scalar_one_or_none():
            skipped += 1
            continue

        assignment = AccountAssignment(
            account_id=account_id,
            account_group_id=group_id,
            feature_type=body.feature_type,
        )
        db.add(assignment)
        added += 1

    await db.flush()
    return MessageResponse(
        message=f"Bulk import complete: {added} added, {skipped} skipped",
        detail={"added": added, "skipped": skipped},
    )


@router.delete("/{group_id}/accounts/{account_id}", response_model=MessageResponse)
async def remove_account_from_group(
    group_id: int,
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Remove an account from a group."""
    result = await db.execute(select(AccountGroup).where(AccountGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Account group not found")
    _require_owns_group(group, current_client)

    assignment_result = await db.execute(
        select(AccountAssignment).where(
            AccountAssignment.account_id == account_id,
            AccountAssignment.account_group_id == group_id,
        )
    )
    assignment = assignment_result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Account not in group")
    await db.delete(assignment)
    await db.flush()
    return MessageResponse(message="Account removed from group")


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/{group_id}/health", response_model=List[AccountHealthResponse])
async def get_group_health(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Get health records for all accounts in a group."""
    result = await db.execute(select(AccountGroup).where(AccountGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Account group not found")
    _require_owns_group(group, current_client)

    health_result = await db.execute(
        select(AccountHealth).where(AccountHealth.account_group_id == group_id)
    )
    return health_result.scalars().all()


# ── Analytics ─────────────────────────────────────────────────────────────────

@router.get("/{group_id}/analytics", response_model=List[GroupAnalyticsResponse])
async def get_group_analytics(
    group_id: int,
    limit: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Get analytics records for an account group."""
    result = await db.execute(select(AccountGroup).where(AccountGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Account group not found")
    _require_owns_group(group, current_client)

    analytics_result = await db.execute(
        select(GroupAnalytics)
        .where(GroupAnalytics.account_group_id == group_id)
        .order_by(GroupAnalytics.created_at.desc())
        .limit(limit)
    )
    return analytics_result.scalars().all()
