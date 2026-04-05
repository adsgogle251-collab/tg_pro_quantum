"""
TG PRO QUANTUM - Data Export Routes (CSV)
"""
import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_client
from app.database import get_db
from app.models.database import Campaign, Client, TelegramAccount

router = APIRouter(prefix="/exports", tags=["Exports"])


@router.get("/campaigns")
async def export_campaigns(
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Export campaigns for the current client as CSV."""
    result = await db.execute(
        select(Campaign)
        .where(Campaign.client_id == current_client.id)
        .order_by(Campaign.created_at.desc())
    )
    campaigns = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "name", "status", "mode",
        "total_targets", "sent_count", "failed_count",
        "created_at", "completed_at",
    ])
    for c in campaigns:
        writer.writerow([
            c.id, c.name, c.status.value, c.mode.value,
            c.total_targets, c.sent_count, c.failed_count,
            c.created_at, c.completed_at,
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=campaigns.csv"},
    )


@router.get("/accounts")
async def export_accounts(
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Export Telegram accounts for the current client as CSV."""
    result = await db.execute(
        select(TelegramAccount)
        .where(TelegramAccount.client_id == current_client.id)
        .order_by(TelegramAccount.created_at.desc())
    )
    accounts = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "name", "phone", "status",
        "health_score", "messages_sent_today", "created_at",
    ])
    for a in accounts:
        writer.writerow([
            a.id, a.name, a.phone, a.status.value,
            a.health_score, a.messages_sent_today, a.created_at,
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=accounts.csv"},
    )
