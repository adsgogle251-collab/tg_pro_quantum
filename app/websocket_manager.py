"""
TG PRO QUANTUM - WebSocket Connection Manager

Provides real-time push updates for:
  - Campaign progress (sent count, success rate, active account)
  - Account status changes (health score, banned/active)
  - Message delivery confirmations
  - Multi-client room isolation (each client_id is a separate room)
"""
import asyncio
import json
from collections import defaultdict
from typing import Dict, List, Optional

from fastapi import WebSocket, WebSocketDisconnect
from app.utils.logger import get_logger

logger = get_logger(__name__)


class WebSocketManager:
    """
    Manages active WebSocket connections grouped by room.

    Rooms:
      - "campaign:{campaign_id}" – real-time broadcast progress
      - "client:{client_id}"     – client-level notifications
      - "admin"                  – platform-wide events (admin only)
    """

    def __init__(self):
        # room_id → list of active WebSocket connections
        self._rooms: Dict[str, List[WebSocket]] = defaultdict(list)

    # ── Connection lifecycle ──────────────────────────────────────────────────

    async def connect(self, websocket: WebSocket, room: str) -> None:
        """Accept and register a new WebSocket connection in a room."""
        await websocket.accept()
        self._rooms[room].append(websocket)
        logger.info("WS connected room=%s total=%d", room, len(self._rooms[room]))

    def disconnect(self, websocket: WebSocket, room: str) -> None:
        """Remove a disconnected WebSocket from its room."""
        try:
            self._rooms[room].remove(websocket)
        except ValueError:
            pass
        if not self._rooms[room]:
            self._rooms.pop(room, None)
        logger.info("WS disconnected room=%s", room)

    # ── Broadcasting ──────────────────────────────────────────────────────────

    async def broadcast(self, room: str, payload: dict) -> None:
        """Send a JSON payload to all connections in a room."""
        message = json.dumps(payload)
        dead: List[WebSocket] = []
        for ws in list(self._rooms.get(room, [])):
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, room)

    async def broadcast_campaign_update(
        self,
        campaign_id: int,
        *,
        sent: int,
        failed: int,
        total: int,
        success_rate: float,
        active_account: Optional[str] = None,
        status: str = "running",
        message: Optional[str] = None,
    ) -> None:
        """Push a campaign progress update to all watchers of that campaign."""
        await self.broadcast(
            f"campaign:{campaign_id}",
            {
                "type": "campaign_update",
                "campaign_id": campaign_id,
                "sent": sent,
                "failed": failed,
                "total": total,
                "progress_pct": round(sent / total * 100, 2) if total else 0.0,
                "success_rate": success_rate,
                "active_account": active_account,
                "status": status,
                "message": message,
            },
        )

    async def broadcast_account_status(
        self,
        client_id: int,
        account_name: str,
        health_score: float,
        status: str,
    ) -> None:
        """Push an account health/status change to the client room."""
        await self.broadcast(
            f"client:{client_id}",
            {
                "type": "account_status",
                "account": account_name,
                "health_score": health_score,
                "status": status,
            },
        )

    async def broadcast_message_delivery(
        self,
        campaign_id: int,
        group: str,
        account: str,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """Push a single message delivery confirmation."""
        await self.broadcast(
            f"campaign:{campaign_id}",
            {
                "type": "delivery",
                "campaign_id": campaign_id,
                "group": group,
                "account": account,
                "success": success,
                "error": error,
            },
        )

    async def broadcast_account_rotated(
        self,
        campaign_id: int,
        old_account: str,
        new_account: str,
        reason: str = "rotation",
    ) -> None:
        """Push an account-rotation event to a campaign room."""
        await self.broadcast(
            f"campaign:{campaign_id}",
            {
                "type": "account_rotated",
                "campaign_id": campaign_id,
                "old_account": old_account,
                "new_account": new_account,
                "reason": reason,
            },
        )

    async def broadcast_account_health_changed(
        self,
        client_id: int,
        account_name: str,
        old_health: float,
        new_health: float,
        status: str,
    ) -> None:
        """Push an account health-change event to the client room."""
        await self.broadcast(
            f"client:{client_id}",
            {
                "type": "account_health_changed",
                "account": account_name,
                "old_health": old_health,
                "new_health": new_health,
                "status": status,
            },
        )

    async def broadcast_campaign_status_changed(
        self,
        campaign_id: int,
        client_id: int,
        old_status: str,
        new_status: str,
    ) -> None:
        """Push a campaign status-change event to both rooms."""
        payload = {
            "type": "campaign_status_changed",
            "campaign_id": campaign_id,
            "old_status": old_status,
            "new_status": new_status,
        }
        await self.broadcast(f"campaign:{campaign_id}", payload)
        await self.broadcast(f"client:{client_id}", payload)

    async def broadcast_error(
        self,
        campaign_id: int,
        client_id: int,
        error_type: str,
        message: str,
    ) -> None:
        """Push an error event."""
        payload = {
            "type": "error_occurred",
            "campaign_id": campaign_id,
            "error_type": error_type,
            "message": message,
        }
        await self.broadcast(f"campaign:{campaign_id}", payload)
        await self.broadcast(f"client:{client_id}", payload)

    async def broadcast_safety_alert(
        self,
        client_id: int,
        alert_type: str,
        severity: str,
        message: str,
        campaign_id: Optional[int] = None,
    ) -> None:
        """Push a safety alert to the client room (and admin room)."""
        payload = {
            "type": "safety_alert",
            "campaign_id": campaign_id,
            "alert_type": alert_type,
            "severity": severity,
            "message": message,
        }
        await self.broadcast(f"client:{client_id}", payload)
        await self.broadcast("admin", payload)

    # ── Utility ───────────────────────────────────────────────────────────────

    def room_size(self, room: str) -> int:
        """Return number of active connections in a room."""
        return len(self._rooms.get(room, []))

    def active_rooms(self) -> List[str]:
        """Return all room IDs that have at least one connection."""
        return list(self._rooms.keys())


# Singleton shared across the app
ws_manager = WebSocketManager()
