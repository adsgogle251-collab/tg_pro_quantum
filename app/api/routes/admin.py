"""
TG PRO QUANTUM - Admin Panel & License Management Routes
"""
import secrets
from math import ceil
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_client, require_admin, hash_password
from app.database import get_db
from app.models.database import (
    AuditLog, Campaign, Client, ClientStatus, License, LicenseStatus, TelegramAccount,
)
from app.models.schemas import (
    AdminClientPlanUpdate,
    AuditLogResponse,
    ClientCreate, ClientResponse,
    LicenseCreate, LicenseResponse, LicenseUpdate,
    MessageResponse,
    PaginatedResponse,
)
from app.utils.helpers import generate_api_key

router = APIRouter(prefix="/admin", tags=["Admin"])


# ── License endpoints ─────────────────────────────────────────────────────────

@router.get("/licenses", response_model=PaginatedResponse)
async def list_licenses(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin: Client = Depends(require_admin),
):
    """List all license keys (admin only)."""
    offset = (page - 1) * per_page
    total_result = await db.execute(select(func.count(License.id)))
    total = total_result.scalar() or 0
    result = await db.execute(select(License).offset(offset).limit(per_page))
    items = result.scalars().all()
    return PaginatedResponse(
        items=[LicenseResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=ceil(total / per_page) if per_page else 1,
    )


@router.post("/licenses", response_model=LicenseResponse, status_code=status.HTTP_201_CREATED)
async def create_license(
    body: LicenseCreate,
    db: AsyncSession = Depends(get_db),
    _admin: Client = Depends(require_admin),
):
    """Create a new license key (admin only)."""
    key = secrets.token_urlsafe(32)
    license_obj = License(
        key=key,
        tier=body.tier,
        client_id=body.client_id,
        max_accounts=body.max_accounts,
        max_campaigns=body.max_campaigns,
        expires_at=body.expires_at,
    )
    db.add(license_obj)
    await db.flush()
    await db.refresh(license_obj)
    return license_obj


@router.get("/licenses/{license_key}", response_model=LicenseResponse)
async def get_license(
    license_key: str,
    db: AsyncSession = Depends(get_db),
    _admin: Client = Depends(require_admin),
):
    """Get details for a specific license key (admin only)."""
    result = await db.execute(select(License).where(License.key == license_key))
    lic = result.scalar_one_or_none()
    if not lic:
        raise HTTPException(status_code=404, detail="License not found")
    return lic


@router.put("/licenses/{license_key}", response_model=LicenseResponse)
async def update_license(
    license_key: str,
    body: LicenseUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: Client = Depends(require_admin),
):
    """Update a license (activate/deactivate/extend) (admin only)."""
    result = await db.execute(select(License).where(License.key == license_key))
    lic = result.scalar_one_or_none()
    if not lic:
        raise HTTPException(status_code=404, detail="License not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(lic, field, value)
    await db.flush()
    await db.refresh(lic)
    return lic


@router.delete("/licenses/{license_key}", response_model=MessageResponse)
async def delete_license(
    license_key: str,
    db: AsyncSession = Depends(get_db),
    _admin: Client = Depends(require_admin),
):
    """Delete a license (admin only)."""
    result = await db.execute(select(License).where(License.key == license_key))
    lic = result.scalar_one_or_none()
    if not lic:
        raise HTTPException(status_code=404, detail="License not found")
    await db.delete(lic)
    return MessageResponse(message="License deleted")


# ── Client management endpoints ───────────────────────────────────────────────

@router.get("/clients", response_model=PaginatedResponse)
async def list_all_clients(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _admin: Client = Depends(require_admin),
):
    """List all clients with their license info (admin only)."""
    query = select(Client)
    count_query = select(func.count(Client.id))
    if search:
        like = f"%{search}%"
        query = query.where(or_(Client.name.ilike(like), Client.email.ilike(like)))
        count_query = count_query.where(or_(Client.name.ilike(like), Client.email.ilike(like)))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * per_page
    result = await db.execute(query.offset(offset).limit(per_page))
    items = result.scalars().all()
    return PaginatedResponse(
        items=[ClientResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=ceil(total / per_page) if per_page else 1,
    )


@router.put("/clients/{client_id}/plan", response_model=ClientResponse)
async def update_client_plan(
    client_id: int,
    body: AdminClientPlanUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: Client = Depends(require_admin),
):
    """Change a client's plan or status (admin only)."""
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(client, field, value)
    await db.flush()
    await db.refresh(client)
    return client


# ── Admin user management endpoints (/admin/users) ───────────────────────────

@router.get("/users", response_model=PaginatedResponse)
async def list_all_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None, pattern=r"^(admin|user)$"),
    account_status: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    _admin: Client = Depends(require_admin),
):
    """List all users (admin only) with filtering and pagination."""
    query = select(Client)
    count_query = select(func.count(Client.id))

    if search:
        like = f"%{search}%"
        query = query.where(or_(Client.name.ilike(like), Client.email.ilike(like)))
        count_query = count_query.where(or_(Client.name.ilike(like), Client.email.ilike(like)))

    if role == "admin":
        query = query.where(Client.is_admin.is_(True))
        count_query = count_query.where(Client.is_admin.is_(True))
    elif role == "user":
        query = query.where(Client.is_admin.is_(False))
        count_query = count_query.where(Client.is_admin.is_(False))

    if account_status:
        try:
            sv = ClientStatus(account_status)
            query = query.where(Client.status == sv)
            count_query = count_query.where(Client.status == sv)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {account_status}")

    total = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * per_page
    result = await db.execute(query.order_by(Client.created_at.desc()).offset(offset).limit(per_page))
    items = result.scalars().all()
    return PaginatedResponse(
        items=[ClientResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=ceil(total / per_page) if per_page else 1,
    )


@router.post("/users", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: ClientCreate,
    db: AsyncSession = Depends(get_db),
    _admin: Client = Depends(require_admin),
):
    """Create a new user (admin only)."""
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


@router.get("/users/{user_id}", response_model=ClientResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: Client = Depends(require_admin),
):
    """Get a user by ID (admin only)."""
    result = await db.execute(select(Client).where(Client.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/users/{user_id}", response_model=ClientResponse)
async def update_user(
    user_id: int,
    body: AdminClientPlanUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: Client = Depends(require_admin),
):
    """Update a user's plan or status (admin only)."""
    result = await db.execute(select(Client).where(Client.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    await db.flush()
    await db.refresh(user)
    return user


@router.delete("/users/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: int,
    admin: Client = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a user account (admin only). Cannot delete own account or other admin accounts."""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    result = await db.execute(select(Client).where(Client.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_admin:
        raise HTTPException(status_code=400, detail="Cannot delete another admin account")
    await db.delete(user)
    return MessageResponse(message="User deleted")


@router.put("/users/{user_id}/suspend", response_model=ClientResponse)
async def suspend_user(
    user_id: int,
    admin: Client = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Suspend a user account (admin only)."""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot suspend your own account")
    result = await db.execute(select(Client).where(Client.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.status = ClientStatus.suspended
    await db.flush()
    await db.refresh(user)
    return user


@router.put("/users/{user_id}/restore", response_model=ClientResponse)
async def restore_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: Client = Depends(require_admin),
):
    """Restore a suspended user account (admin only)."""
    result = await db.execute(select(Client).where(Client.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.status = ClientStatus.active
    await db.flush()
    await db.refresh(user)
    return user


# ── Admin statistics ──────────────────────────────────────────────────────────

@router.get("/stats")
async def admin_stats(
    db: AsyncSession = Depends(get_db),
    _admin: Client = Depends(require_admin),
):
    """System-wide statistics (admin only)."""
    total_users = (await db.execute(select(func.count(Client.id)))).scalar() or 0
    active_users = (
        await db.execute(
            select(func.count(Client.id)).where(Client.status == ClientStatus.active)
        )
    ).scalar() or 0
    total_campaigns = (await db.execute(select(func.count(Campaign.id)))).scalar() or 0
    total_accounts = (await db.execute(select(func.count(TelegramAccount.id)))).scalar() or 0
    total_licenses = (await db.execute(select(func.count(License.id)))).scalar() or 0
    total_audit_logs = (await db.execute(select(func.count(AuditLog.id)))).scalar() or 0

    return {
        "total_users": total_users,
        "active_users": active_users,
        "suspended_users": total_users - active_users,
        "total_campaigns": total_campaigns,
        "total_accounts": total_accounts,
        "total_licenses": total_licenses,
        "total_audit_logs": total_audit_logs,
        "system_health": "ok",
    }


# ── Admin audit logs ──────────────────────────────────────────────────────────

@router.get("/audit-logs", response_model=PaginatedResponse)
async def admin_audit_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _admin: Client = Depends(require_admin),
):
    """List all audit logs with filtering (admin only)."""
    query = select(AuditLog)
    count_query = select(func.count(AuditLog.id))

    if user_id is not None:
        query = query.where(AuditLog.client_id == user_id)
        count_query = count_query.where(AuditLog.client_id == user_id)
    if action:
        query = query.where(AuditLog.action.ilike(f"%{action}%"))
        count_query = count_query.where(AuditLog.action.ilike(f"%{action}%"))
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
        count_query = count_query.where(AuditLog.resource_type == resource_type)

    total = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * per_page
    result = await db.execute(
        query.order_by(AuditLog.created_at.desc()).offset(offset).limit(per_page)
    )
    items = result.scalars().all()
    return PaginatedResponse(
        items=[AuditLogResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=ceil(total / per_page) if per_page else 1,
    )
