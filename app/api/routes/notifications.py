"""
TG PRO QUANTUM - Notifications Routes (/notifications)

Provides a simple in-session notifications list backed by the AuditLog
table.  Notifications are scoped to the current user.
"""
from math import ceil
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_client
from app.database import get_db
from app.models.database import AuditLog, Client
from app.models.schemas import MessageResponse, PaginatedResponse, AuditLogResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/")
async def list_notifications(
    page: Optional[int] = Query(None, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Return recent audit-log entries as notifications for the current user."""
    base = (
        select(AuditLog)
        .where(AuditLog.client_id == current_client.id)
        .order_by(AuditLog.created_at.desc())
    )
    count_q = select(func.count(AuditLog.id)).where(AuditLog.client_id == current_client.id)

    if page is not None:
        total = (await db.execute(count_q)).scalar() or 0
        offset = (page - 1) * per_page
        result = await db.execute(base.offset(offset).limit(per_page))
        items = result.scalars().all()
        return PaginatedResponse(
            items=[AuditLogResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            per_page=per_page,
            pages=ceil(total / per_page) if per_page else 1,
        )

    result = await db.execute(base.limit(per_page))
    items = result.scalars().all()
    return [AuditLogResponse.model_validate(i) for i in items]


@router.patch("/{notification_id}/read", response_model=MessageResponse)
async def mark_notification_read(
    notification_id: int,
    current_client: Client = Depends(get_current_client),
):
    """Mark a notification as read (no-op in current implementation; returns success)."""
    return MessageResponse(message="Notification marked as read")
