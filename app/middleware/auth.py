import logging
from typing import Optional

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.utils.helpers import decode_access_token

logger = logging.getLogger(__name__)

PUBLIC_PATHS = {
    "/",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/otp/request",
    "/api/v1/auth/otp/verify",
    "/api/v1/auth/refresh",
}


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware that validates JWT tokens for protected routes,
    enforces client isolation, and applies Redis-backed rate limiting.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Allow WebSocket upgrade without Bearer header
        if request.headers.get("upgrade", "").lower() == "websocket":
            return await call_next(request)

        # Allow public paths
        if path in PUBLIC_PATHS or path.startswith("/ws/"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing or invalid Authorization header"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = auth_header[len("Bearer "):]
        payload = decode_access_token(token)
        if payload is None:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or expired token"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        request.state.user_id = payload.get("sub")
        request.state.user_email = payload.get("email")

        # Optional Redis rate limiting
        redis = getattr(request.app.state, "redis", None)
        if redis:
            try:
                from datetime import datetime, timedelta, timezone

                key = f"rate_limit:{request.state.user_id}:{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"
                count = await redis.incr(key)
                if count == 1:
                    await redis.expire(key, 60)
                if count > 300:
                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={"detail": "Rate limit exceeded"},
                        headers={"Retry-After": "60"},
                    )
            except Exception as exc:
                logger.debug("Rate limiter redis error: %s", exc)

        return await call_next(request)
