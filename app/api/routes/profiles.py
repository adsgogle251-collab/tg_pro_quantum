"""
TG PRO QUANTUM - User Profile Routes (/users/me)

Provides a clean /users/me namespace used by the web frontend.
All write operations require the current password or an authenticated session.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_current_client,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.models.database import Client
from app.models.schemas import ClientResponse, MessageResponse
from app.utils.helpers import generate_api_key
from pydantic import BaseModel, EmailStr, Field

router = APIRouter(prefix="/users", tags=["Profile"])


# ── Request schemas ────────────────────────────────────────────────────────────

class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class ApiKeyCreate(BaseModel):
    label: Optional[str] = Field(None, max_length=100)


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/me", response_model=ClientResponse)
async def get_my_profile(
    current_client: Client = Depends(get_current_client),
):
    """Return current user's profile."""
    return current_client


@router.patch("/me", response_model=ClientResponse)
async def update_my_profile(
    body: ProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Update the current user's name or email."""
    if body.email and body.email != current_client.email:
        existing = await db.execute(select(Client).where(Client.email == body.email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Email already in use")
        current_client.email = body.email
    if body.name:
        current_client.name = body.name
    await db.flush()
    await db.refresh(current_client)
    return current_client


@router.post("/me/change-password", response_model=MessageResponse)
async def change_password(
    body: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Change the current user's password (requires current password)."""
    if not verify_password(body.current_password, current_client.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_client.hashed_password = hash_password(body.new_password)
    await db.flush()
    return MessageResponse(message="Password changed successfully")


# ── API Key management ─────────────────────────────────────────────────────────

@router.get("/me/api-keys", response_model=List[dict])
async def list_api_keys(
    current_client: Client = Depends(get_current_client),
):
    """List API keys for the current user."""
    if not current_client.api_key:
        return []
    return [
        {
            "id": 1,
            "label": "Default",
            "key_preview": f"{current_client.api_key[:8]}...",
            "created_at": current_client.created_at,
        }
    ]


@router.post("/me/api-keys", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    body: ApiKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Generate a new API key for the current user (replaces existing)."""
    new_key = generate_api_key()
    current_client.api_key = new_key
    await db.flush()
    return {
        "id": 1,
        "label": body.label or "Default",
        "api_key": new_key,
        "key_preview": f"{new_key[:8]}...",
        "created_at": current_client.created_at,
        "message": "New API key generated",
    }


@router.delete("/me/api-keys/{key_id}", response_model=MessageResponse)
async def revoke_api_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Revoke (delete) an API key."""
    if key_id != 1 or not current_client.api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    current_client.api_key = None
    await db.flush()
    return MessageResponse(message="API key revoked")
