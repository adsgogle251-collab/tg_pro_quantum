import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── Password ──────────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_access_token(
    data: Dict[str, Any],
    expires_minutes: Optional[int] = None,
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {**data, "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    data: Dict[str, Any],
    expires_days: Optional[int] = None,
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=expires_days or settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {**data, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


def decode_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("type") != "refresh":
            return None
        return payload
    except JWTError:
        return None


# ── API Key ───────────────────────────────────────────────────────────────────

def generate_api_key(length: int = 48) -> str:
    alphabet = string.ascii_letters + string.digits
    return "tgpq_" + "".join(secrets.choice(alphabet) for _ in range(length))


# ── Pagination ────────────────────────────────────────────────────────────────

def paginate(items: list, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    total = len(items)
    total_pages = max(1, (total + page_size - 1) // page_size)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "items": items[start:end],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


def get_pagination_params(skip: int = 0, limit: int = 20) -> Dict[str, int]:
    page = (skip // limit) + 1 if limit > 0 else 1
    return {"page": page, "page_size": limit, "skip": skip, "limit": limit}


# ── Celery async helper ───────────────────────────────────────────────────────

import asyncio
from typing import Callable, Coroutine


def run_async(coro: Coroutine) -> Any:
    """
    Run an async coroutine from a synchronous Celery task context.

    Creates a fresh event loop so Celery workers (which have no running loop)
    can safely execute async code.  Using asyncio.run() directly is equivalent
    on CPython, but this wrapper makes the intent explicit and allows us to
    add per-task loop cleanup in the future.
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        finally:
            loop.close()
