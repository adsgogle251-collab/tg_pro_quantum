"""
TG PRO QUANTUM - FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.api.routes import auth, clients, accounts, groups, campaigns, broadcasts, analytics
from app.api.routes import account_groups
from app.api.routes import phase3_broadcast
from app.api.routes import admin, audit, exports, webhooks
from app.api.routes import profiles, settings as user_settings, notifications
from app.utils.logger import get_logger
from app.websocket_manager import ws_manager

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup & shutdown lifecycle."""
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    await init_db()
    logger.info("Database tables verified / created")
    yield
    logger.info("Shutting down %s", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Professional multi-client Telegram broadcast-as-a-service API. "
        "Supports JWT + OTP authentication, multi-account broadcasting, "
        "advanced scheduling (24/7, round-robin, loop), and real-time analytics."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(ErrorHandlerMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────

API_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(clients.router, prefix=API_PREFIX)
app.include_router(accounts.router, prefix=API_PREFIX)
app.include_router(groups.router, prefix=API_PREFIX)
app.include_router(campaigns.router, prefix=API_PREFIX)
app.include_router(broadcasts.router, prefix=API_PREFIX)
app.include_router(analytics.router, prefix=API_PREFIX)
app.include_router(account_groups.router, prefix=API_PREFIX)
app.include_router(phase3_broadcast.router, prefix=API_PREFIX)
app.include_router(admin.router, prefix=API_PREFIX)
app.include_router(audit.router, prefix=API_PREFIX)
app.include_router(exports.router, prefix=API_PREFIX)
app.include_router(webhooks.router, prefix=API_PREFIX)
app.include_router(profiles.router, prefix=API_PREFIX)
app.include_router(user_settings.router, prefix=API_PREFIX)
app.include_router(notifications.router, prefix=API_PREFIX)


# ── Health endpoint ───────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "version": settings.APP_VERSION}


@app.get("/health/detailed", tags=["Health"])
async def health_detailed():
    """
    Detailed health check including database connectivity.
    Returns HTTP 200 when healthy or HTTP 503 when any component is down.
    """
    import time
    from fastapi.responses import JSONResponse
    from app.database import engine

    checks: dict = {}
    overall_healthy = True

    # Database check
    db_start = time.monotonic()
    try:
        async with engine.connect() as conn:
            from sqlalchemy import text
            await conn.execute(text("SELECT 1"))
        checks["database"] = {
            "status": "ok",
            "latency_ms": round((time.monotonic() - db_start) * 1000, 2),
        }
    except Exception as exc:
        checks["database"] = {"status": "error", "detail": str(exc)}
        overall_healthy = False

    # Redis check (optional – don't fail if Redis is not configured)
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=1)
        redis_start = time.monotonic()
        await r.ping()
        await r.aclose()
        checks["redis"] = {
            "status": "ok",
            "latency_ms": round((time.monotonic() - redis_start) * 1000, 2),
        }
    except Exception as exc:
        checks["redis"] = {"status": "unavailable", "detail": str(exc)}
        # Redis is optional; don't mark as unhealthy

    response_body = {
        "status": "ok" if overall_healthy else "degraded",
        "version": settings.APP_VERSION,
        "checks": checks,
    }
    status_code = 200 if overall_healthy else 503
    return JSONResponse(content=response_body, status_code=status_code)


@app.get("/", tags=["Root"])
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


# ── WebSocket endpoints ───────────────────────────────────────────────────────

@app.websocket("/ws/campaigns/{campaign_id}")
async def ws_campaign(websocket: WebSocket, campaign_id: int):
    """
    Real-time campaign progress stream.

    Clients connect here to receive live updates:
      - campaign_update: sent/failed/total/success_rate/active_account/status
      - delivery: per-message delivery confirmation
    """
    room = f"campaign:{campaign_id}"
    await ws_manager.connect(websocket, room)
    try:
        while True:
            # Keep connection alive; clients may send ping frames
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, room)


@app.websocket("/ws/clients/{client_id}")
async def ws_client(websocket: WebSocket, client_id: int):
    """
    Real-time client-level notifications (account health changes, etc.).
    """
    room = f"client:{client_id}"
    await ws_manager.connect(websocket, room)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, room)
