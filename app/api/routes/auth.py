"""
TG PRO QUANTUM - Authentication & OTP Routes
"""
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    create_access_token, create_refresh_token, decode_token,
    get_current_client, hash_password, verify_password,
)
from app.config import settings
from app.core.otp_manager import otp_manager
from app.database import get_db
from app.models.database import Client
from app.models.schemas import (
    LoginRequest, MessageResponse, OTPRequestSchema, OTPResponse,
    OTPVerifySchema, RegisterRequest, RefreshRequest, TokenResponse,
)
from app.utils.helpers import generate_api_key
from app.utils.logger import get_logger

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = get_logger(__name__)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new client account."""
    result = await db.execute(select(Client).where(Client.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    client = Client(
        name=body.name,
        email=body.email,
        hashed_password=hash_password(body.password),
        api_key=generate_api_key(),
    )
    db.add(client)
    await db.flush()
    await db.refresh(client)

    return TokenResponse(
        access_token=create_access_token(client.id, client.is_admin),
        refresh_token=create_refresh_token(client.id),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login with email & password."""
    result = await db.execute(select(Client).where(Client.email == body.email))
    client = result.scalar_one_or_none()

    if not client or not verify_password(body.password, client.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if client.status.value == "suspended":
        raise HTTPException(status_code=403, detail="Account suspended")

    return TokenResponse(
        access_token=create_access_token(client.id, client.is_admin),
        refresh_token=create_refresh_token(client.id),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Issue new access token using a refresh token."""
    payload = decode_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    client_id = int(payload["sub"])
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=401, detail="Client not found")

    return TokenResponse(
        access_token=create_access_token(client.id, client.is_admin),
        refresh_token=create_refresh_token(client.id),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=dict)
async def get_me(current_client: Client = Depends(get_current_client)):
    """Return current authenticated client info."""
    return {
        "id": current_client.id,
        "name": current_client.name,
        "email": current_client.email,
        "status": current_client.status.value,
        "is_admin": current_client.is_admin,
        "api_key": current_client.api_key,
    }


# ── OTP endpoints ─────────────────────────────────────────────────────────────

@router.post("/otp/request", response_model=MessageResponse)
async def request_otp(
    body: OTPRequestSchema,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Request an OTP SMS for phone verification."""
    otp_id = await otp_manager.request_otp(body.phone, db)
    logger.info("OTP requested for phone=%s client=%s", body.phone, current_client.id)
    return MessageResponse(message="OTP sent", detail={"otp_request_id": otp_id})


@router.post("/otp/verify", response_model=MessageResponse)
async def verify_otp(
    body: OTPVerifySchema,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Verify OTP code received via SMS."""
    success = await otp_manager.verify_otp(body.phone, body.code, db)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP code")
    return MessageResponse(message="Phone verified successfully")
