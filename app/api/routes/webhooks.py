"""
TG PRO QUANTUM - Webhook Management Routes
"""
import secrets
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_client
from app.database import get_db
from app.models.database import Client, Webhook
from app.models.schemas import MessageResponse, WebhookCreate, WebhookResponse

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.get("/", response_model=List[WebhookResponse])
async def list_webhooks(
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """List all webhooks for the current client."""
    result = await db.execute(
        select(Webhook).where(Webhook.client_id == current_client.id)
    )
    return result.scalars().all()


@router.post("/", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    body: WebhookCreate,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Create a new webhook subscription."""
    wh_secret = body.secret or secrets.token_hex(32)
    webhook = Webhook(
        client_id=current_client.id,
        url=body.url,
        events=body.events,
        secret=wh_secret,
    )
    db.add(webhook)
    await db.flush()
    await db.refresh(webhook)
    return webhook


@router.delete("/{webhook_id}", response_model=MessageResponse)
async def delete_webhook(
    webhook_id: int,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Delete a webhook subscription."""
    result = await db.execute(select(Webhook).where(Webhook.id == webhook_id))
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    if webhook.client_id != current_client.id and not current_client.is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")
    await db.delete(webhook)
    return MessageResponse(message="Webhook deleted")
