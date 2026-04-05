"""
TG PRO QUANTUM - Audit Logging Service
"""
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import AuditLog
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def log_action(
    db: AsyncSession,
    client_id: Optional[int],
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Any] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """Persist an audit log entry and return it."""
    entry = AuditLog(
        client_id=client_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
    )
    db.add(entry)
    try:
        await db.flush()
    except Exception as exc:
        logger.warning("Failed to write audit log: %s", exc)
    return entry
