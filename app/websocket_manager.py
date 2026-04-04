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

    # ── Utility ───────────────────────────────────────────────────────────────

    def room_size(self, room: str) -> int:
        """Return number of active connections in a room."""
        return len(self._rooms.get(room, []))

    def active_rooms(self) -> List[str]:
        """Return all room IDs that have at least one connection."""
        return list(self._rooms.keys())


# Singleton shared across the app
ws_manager = WebSocketManager()
