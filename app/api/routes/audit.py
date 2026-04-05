"""
TG PRO QUANTUM - Audit Log Routes
"""
from math import ceil

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_client, require_admin
from app.database import get_db
from app.models.database import AuditLog, Client
from app.models.schemas import AuditLogResponse, PaginatedResponse

router = APIRouter(prefix="/audit", tags=["Audit Logs"])


@router.get("/logs", response_model=PaginatedResponse)
async def list_my_audit_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """List audit logs for the current authenticated user (paginated)."""
    base = select(AuditLog).where(AuditLog.client_id == current_client.id)
    count_q = select(func.count(AuditLog.id)).where(AuditLog.client_id == current_client.id)

    total = (await db.execute(count_q)).scalar() or 0
    offset = (page - 1) * per_page
    result = await db.execute(base.order_by(AuditLog.created_at.desc()).offset(offset).limit(per_page))
    items = result.scalars().all()
    return PaginatedResponse(
        items=[AuditLogResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=ceil(total / per_page) if per_page else 1,
    )


@router.get("/logs/admin", response_model=PaginatedResponse)
async def list_all_audit_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin: Client = Depends(require_admin),
):
    """List ALL audit logs across all clients (admin only, paginated)."""
    total = (await db.execute(select(func.count(AuditLog.id)))).scalar() or 0
    offset = (page - 1) * per_page
    result = await db.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).offset(offset).limit(per_page)
    )
    items = result.scalars().all()
    return PaginatedResponse(
        items=[AuditLogResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=ceil(total / per_page) if per_page else 1,
    )
