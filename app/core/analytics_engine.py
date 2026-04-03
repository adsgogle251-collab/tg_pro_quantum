import csv
import io
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import BroadcastHistory, BroadcastQueue, Campaign, CampaignAnalytics, QueueStatus

logger = logging.getLogger(__name__)


class AnalyticsEngine:
    """
    Computes real-time campaign metrics, generates reports,
    tracks historical data, and exports to CSV/JSON.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def compute_campaign_analytics(
        self, campaign_id: int
    ) -> CampaignAnalytics:
        """Compute or update analytics for a single campaign."""
        total_res = await self.db.execute(
            select(func.count(BroadcastQueue.id)).where(
                BroadcastQueue.campaign_id == campaign_id
            )
        )
        sent_res = await self.db.execute(
            select(func.count(BroadcastQueue.id)).where(
                BroadcastQueue.campaign_id == campaign_id,
                BroadcastQueue.status == QueueStatus.sent,
            )
        )
        failed_res = await self.db.execute(
            select(func.count(BroadcastQueue.id)).where(
                BroadcastQueue.campaign_id == campaign_id,
                BroadcastQueue.status == QueueStatus.failed,
            )
        )
        pending_res = await self.db.execute(
            select(func.count(BroadcastQueue.id)).where(
                BroadcastQueue.campaign_id == campaign_id,
                BroadcastQueue.status == QueueStatus.pending,
            )
        )

        total = total_res.scalar() or 0
        sent = sent_res.scalar() or 0
        failed = failed_res.scalar() or 0
        pending = pending_res.scalar() or 0
        attempts = sent + failed
        delivery_rate = (sent / attempts * 100) if attempts > 0 else 0.0

        existing_res = await self.db.execute(
            select(CampaignAnalytics).where(CampaignAnalytics.campaign_id == campaign_id)
        )
        analytics = existing_res.scalar_one_or_none()
        if analytics is None:
            analytics = CampaignAnalytics(campaign_id=campaign_id)
            self.db.add(analytics)

        analytics.total_sent = sent
        analytics.total_failed = failed
        analytics.total_pending = pending
        analytics.delivery_rate = round(delivery_rate, 4)
        analytics.last_updated = datetime.utcnow()
        await self.db.flush()
        return analytics

    async def get_campaign_metrics(self, campaign_id: int) -> Dict[str, Any]:
        """Return a metrics dict for dashboard display."""
        analytics = await self.compute_campaign_analytics(campaign_id)
        return {
            "campaign_id": campaign_id,
            "total_sent": analytics.total_sent,
            "total_failed": analytics.total_failed,
            "total_pending": analytics.total_pending,
            "delivery_rate": analytics.delivery_rate,
            "avg_send_time": analytics.avg_send_time,
            "last_updated": analytics.last_updated.isoformat(),
        }

    async def get_client_summary(self, client_id: int) -> Dict[str, Any]:
        campaigns_res = await self.db.execute(
            select(Campaign).where(Campaign.client_id == client_id)
        )
        campaigns = campaigns_res.scalars().all()
        total_sent = 0
        total_failed = 0
        for campaign in campaigns:
            m = await self.get_campaign_metrics(campaign.id)
            total_sent += m["total_sent"]
            total_failed += m["total_failed"]
        total = total_sent + total_failed
        return {
            "client_id": client_id,
            "total_campaigns": len(campaigns),
            "total_sent": total_sent,
            "total_failed": total_failed,
            "overall_delivery_rate": round(total_sent / total * 100, 2) if total else 0.0,
        }

    def export_to_csv(self, data: List[Dict[str, Any]]) -> str:
        if not data:
            return ""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()

    def export_to_json(self, data: List[Dict[str, Any]]) -> str:
        return json.dumps(data, indent=2, default=str)
