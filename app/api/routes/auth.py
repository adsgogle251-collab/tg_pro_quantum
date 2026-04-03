import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.database import User
from app.models.schemas import (
    OTPRequest,
    OTPVerify,
    RefreshTokenRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.utils.helpers import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])

# In-memory OTP store (replace with Redis in production)
_otp_store: dict = {}


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role="admin",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )
    return TokenResponse(
        access_token=create_access_token({"sub": str(user.id), "email": user.email}),
        refresh_token=create_refresh_token({"sub": str(user.id)}),
    )


@router.post("/otp/request", status_code=status.HTTP_200_OK)
async def request_otp(payload: OTPRequest):
    import random

    code = str(random.randint(100000, 999999))
    _otp_store[payload.phone] = {
        "code": code,
        "expires_at": datetime.utcnow() + timedelta(minutes=10),
    }
    # In production: send via SMS / email
    logger.info("OTP for %s: %s", payload.phone, code)
    return {"message": "OTP sent", "expires_in": 600}


@router.post("/otp/verify", status_code=status.HTTP_200_OK)
async def verify_otp(payload: OTPVerify):
    entry = _otp_store.get(payload.phone)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP not requested")
    if datetime.utcnow() > entry["expires_at"]:
        del _otp_store[payload.phone]
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP expired")
    if entry["code"] != payload.code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP code")
    del _otp_store[payload.phone]
    return {"message": "OTP verified successfully"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(payload: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    token_data = decode_refresh_token(payload.refresh_token)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    user_id = token_data.get("sub")
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return TokenResponse(
        access_token=create_access_token({"sub": str(user.id), "email": user.email}),
        refresh_token=create_refresh_token({"sub": str(user.id)}),
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout():
    # With stateless JWT, logout is handled client-side by discarding the token.
    # In production, add the token to a Redis blacklist.
    return {"message": "Logged out successfully"}
