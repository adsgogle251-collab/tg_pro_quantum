"""
TG PRO QUANTUM - Authentication & OTP Routes
"""
import secrets
from datetime import timedelta
from typing import List, Optional

import pyotp
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    blacklist_token,
    create_access_token, create_refresh_token, decode_token,
    get_current_client, hash_password, verify_password,
)
from app.config import settings
from app.core.otp_manager import otp_manager
from app.database import get_db
from app.models.database import Client
from app.models.schemas import (
    LoginRequest, MessageResponse, OTPRequestSchema, OTPResponse,
    OTPVerifySchema, ProfileUpdateRequest, RegisterRequest, RefreshRequest, TokenResponse,
    TOTPSetupResponse,
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


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    current_client: Client = Depends(get_current_client),
):
    """Invalidate the current access token."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[len("Bearer "):]
        blacklist_token(token)
    return MessageResponse(message="Logged out successfully")


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
        "totp_enabled": current_client.totp_enabled,
    }


@router.put("/profile", response_model=MessageResponse)
async def update_profile(
    body: ProfileUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Update the current user's profile (name, email, or password)."""
    if body.email and body.email != current_client.email:
        existing = await db.execute(select(Client).where(Client.email == body.email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Email already in use")
        current_client.email = body.email

    if body.name:
        current_client.name = body.name

    if body.new_password:
        if not body.current_password:
            raise HTTPException(status_code=400, detail="current_password is required to set a new password")
        if not verify_password(body.current_password, current_client.hashed_password):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        current_client.hashed_password = hash_password(body.new_password)

    await db.flush()
    return MessageResponse(message="Profile updated successfully")


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


# ── API Key Management ────────────────────────────────────────────────────────

@router.post("/api-keys", response_model=dict, status_code=status.HTTP_201_CREATED)
async def generate_new_api_key(
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Generate a new API key, replacing the existing one."""
    current_client.api_key = generate_api_key()
    await db.flush()
    return {"api_key": current_client.api_key, "message": "New API key generated"}


@router.get("/api-keys", response_model=List[dict])
async def list_api_keys(current_client: Client = Depends(get_current_client)):
    """List active API keys for the current client."""
    if not current_client.api_key:
        return []
    return [{"id": 1, "key_preview": f"{current_client.api_key[:8]}...", "created_at": current_client.created_at}]


@router.delete("/api-keys/{key_id}", response_model=MessageResponse)
async def revoke_api_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Revoke the current API key."""
    if key_id != 1:
        raise HTTPException(status_code=404, detail="API key not found")
    current_client.api_key = None
    await db.flush()
    return MessageResponse(message="API key revoked")


# ── 2FA / TOTP ────────────────────────────────────────────────────────────────

@router.post("/2fa/setup", response_model=TOTPSetupResponse)
async def setup_2fa(
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Generate a new TOTP secret and return the provisioning URI."""
    secret = pyotp.random_base32()
    current_client.totp_secret = secret
    await db.flush()
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=current_client.email, issuer_name="TG PRO QUANTUM")
    return TOTPSetupResponse(secret=secret, uri=uri)


@router.post("/2fa/verify", response_model=MessageResponse)
async def verify_2fa(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Verify a TOTP code to enable 2FA."""
    code = body.get("code", "")
    if not current_client.totp_secret:
        raise HTTPException(status_code=400, detail="2FA setup not initiated. Call /auth/2fa/setup first.")
    totp = pyotp.TOTP(current_client.totp_secret)
    if not totp.verify(code):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
    current_client.totp_enabled = True
    await db.flush()
    return MessageResponse(message="2FA enabled successfully")


@router.post("/2fa/disable", response_model=MessageResponse)
async def disable_2fa(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Disable 2FA after verifying the current TOTP code."""
    code = body.get("code", "")
    if not current_client.totp_enabled or not current_client.totp_secret:
        raise HTTPException(status_code=400, detail="2FA is not enabled")
    totp = pyotp.TOTP(current_client.totp_secret)
    if not totp.verify(code):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
    current_client.totp_enabled = False
    current_client.totp_secret = None
    await db.flush()
    return MessageResponse(message="2FA disabled successfully")
