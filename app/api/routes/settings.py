"""
TG PRO QUANTUM - User Settings Routes (/settings)

Stores per-user preferences and configuration as a JSON blob inside the
Client.settings column.  No separate database table is needed.
"""
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_client
from app.database import get_db
from app.models.database import Client
from app.models.schemas import MessageResponse

router = APIRouter(prefix="/settings", tags=["Settings"])

# ── Default settings ───────────────────────────────────────────────────────────

_DEFAULTS: Dict[str, Any] = {
    "theme": "dark",
    "language": "en",
    "timezone": "UTC",
    "notifications": {
        "email": True,
        "in_app": True,
        "campaign_completed": True,
        "error_alerts": True,
        "account_banned": False,
    },
    "privacy": {
        "account_visibility": "private",
        "data_sharing": False,
        "privacy_level": "high",
    },
    "advanced": {
        "api_rate_limit": 100,
        "webhook_enabled": False,
    },
}


def _merge_defaults(stored: Optional[Dict]) -> Dict[str, Any]:
    """Return stored settings merged over the defaults."""
    result = dict(_DEFAULTS)
    if stored:
        result.update(stored)
    return result


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/")
async def get_settings(
    current_client: Client = Depends(get_current_client),
):
    """Return full settings for the current user."""
    return _merge_defaults(current_client.settings)


@router.put("/", response_model=MessageResponse)
async def update_settings(
    body: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Update (merge) settings for the current user."""
    current = current_client.settings or {}
    current.update(body)
    current_client.settings = current
    await db.flush()
    return MessageResponse(message="Settings updated")


@router.get("/preferences")
async def get_preferences(
    current_client: Client = Depends(get_current_client),
):
    """Return notification / privacy preferences."""
    merged = _merge_defaults(current_client.settings)
    return {
        "notifications": merged.get("notifications", _DEFAULTS["notifications"]),
        "privacy": merged.get("privacy", _DEFAULTS["privacy"]),
    }


@router.put("/preferences", response_model=MessageResponse)
async def update_preferences(
    body: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Update notification / privacy preferences."""
    current = current_client.settings or {}
    for key in ("notifications", "privacy"):
        if key in body:
            current.setdefault(key, {}).update(body[key])
    current_client.settings = current
    await db.flush()
    return MessageResponse(message="Preferences updated")
