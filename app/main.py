import logging
from contextlib import asynccontextmanager
from typing import Any, Dict

import redis.asyncio as aioredis
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as exc:
        logger.warning("Database init skipped (not connected): %s", exc)

    try:
        app.state.redis = await aioredis.from_url(
            settings.REDIS_URL, encoding="utf-8", decode_responses=True
        )
        logger.info("Redis connected")
    except Exception as exc:
        logger.warning("Redis connection failed (optional): %s", exc)
        app.state.redis = None

    yield

    # Shutdown
    if getattr(app.state, "redis", None):
        await app.state.redis.aclose()
    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "Production-ready FastAPI multi-client Telegram broadcast service. "
            "Manage clients, Telegram accounts, groups, campaigns and real-time broadcasts."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Middleware ────────────────────────────────────────────────────────────
    from app.middleware.error_handler import add_error_handlers

    add_error_handlers(app)

    # ── Routers ───────────────────────────────────────────────────────────────
    from app.api.routes.auth import router as auth_router
    from app.api.routes.clients import router as clients_router
    from app.api.routes.accounts import router as accounts_router
    from app.api.routes.groups import router as groups_router
    from app.api.routes.campaigns import router as campaigns_router
    from app.api.routes.broadcasts import router as broadcasts_router
    from app.api.routes.analytics import router as analytics_router

    api_prefix = "/api/v1"
    app.include_router(auth_router, prefix=api_prefix)
    app.include_router(clients_router, prefix=api_prefix)
    app.include_router(accounts_router, prefix=api_prefix)
    app.include_router(groups_router, prefix=api_prefix)
    app.include_router(campaigns_router, prefix=api_prefix)
    app.include_router(broadcasts_router, prefix=api_prefix)
    app.include_router(analytics_router, prefix=api_prefix)

    # ── Health check ──────────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"])
    async def health_check(request: Request) -> Dict[str, Any]:
        redis_ok = False
        if getattr(request.app.state, "redis", None):
            try:
                await request.app.state.redis.ping()
                redis_ok = True
            except Exception:
                pass
        return {
            "status": "healthy",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "redis": "connected" if redis_ok else "disconnected",
        }

    @app.get("/", tags=["Root"])
    async def root() -> Dict[str, str]:
        return {
            "message": f"Welcome to {settings.APP_NAME} API",
            "docs": "/docs",
            "version": settings.APP_VERSION,
        }

    return app


app = create_app()
