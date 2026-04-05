"""
TG PRO QUANTUM - Admin Panel & License Management Routes
"""
import secrets
from math import ceil
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_client, require_admin, hash_password
from app.database import get_db
from app.models.database import Client, License, LicenseStatus
from app.models.schemas import (
    AdminClientPlanUpdate,
    ClientResponse,
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
        query = query.where(Client.name.ilike(like) | Client.email.ilike(like))
        count_query = count_query.where(Client.name.ilike(like) | Client.email.ilike(like))

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
