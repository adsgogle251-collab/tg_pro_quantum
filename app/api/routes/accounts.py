import logging
from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_client_or_403, get_current_user
from app.database import get_db
from app.models.database import AccountVerification, Client, TelegramAccount
from app.models.schemas import (
    AccountCreate,
    AccountOTPRequest,
    AccountOTPVerify,
    AccountResponse,
    AccountStatusResponse,
)
from app.models.database import User

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Accounts"])


@router.get("/clients/{client_id}/accounts/", response_model=List[AccountResponse])
async def list_accounts(
    client_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _client: Client = Depends(get_client_or_403),
    skip: int = 0,
    limit: int = 100,
):
    result = await db.execute(
        select(TelegramAccount)
        .where(TelegramAccount.client_id == client_id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.post(
    "/clients/{client_id}/accounts/",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_account(
    client_id: int,
    payload: AccountCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    client: Client = Depends(get_client_or_403),
):
    # Check account limit
    result = await db.execute(
        select(TelegramAccount).where(TelegramAccount.client_id == client_id)
    )
    existing = result.scalars().all()
    if len(existing) >= client.max_accounts:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account limit reached ({client.max_accounts}). Upgrade your plan.",
        )

    account = TelegramAccount(
        client_id=client_id,
        phone=payload.phone,
        account_name=payload.account_name or payload.phone,
        api_id=payload.api_id,
        api_hash=payload.api_hash,
        status="pending",
    )
    db.add(account)
    await db.flush()
    await db.refresh(account)
    return account


@router.post("/clients/{client_id}/accounts/{account_id}/request-otp")
async def request_otp(
    client_id: int,
    account_id: int,
    payload: AccountOTPRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _client: Client = Depends(get_client_or_403),
):
    result = await db.execute(
        select(TelegramAccount).where(
            TelegramAccount.id == account_id,
            TelegramAccount.client_id == client_id,
        )
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    from app.core.otp_manager import OTPManager

    otp_manager = OTPManager()
    activation_id = await otp_manager.request_number(account.phone, payload.otp_service)

    verification = AccountVerification(
        account_id=account_id,
        otp_service=payload.otp_service,
        phone_number=account.phone,
        activation_id=str(activation_id),
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db.add(verification)
    await db.flush()
    return {"message": "OTP requested", "activation_id": activation_id}


@router.post("/clients/{client_id}/accounts/{account_id}/verify-otp")
async def verify_otp(
    client_id: int,
    account_id: int,
    payload: AccountOTPVerify,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _client: Client = Depends(get_client_or_403),
):
    result = await db.execute(
        select(TelegramAccount).where(
            TelegramAccount.id == account_id,
            TelegramAccount.client_id == client_id,
        )
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    ver_result = await db.execute(
        select(AccountVerification)
        .where(
            AccountVerification.account_id == account_id,
            AccountVerification.status == "pending",
        )
        .order_by(AccountVerification.created_at.desc())
    )
    verification = ver_result.scalars().first()
    if verification is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pending verification found",
        )

    if datetime.now(timezone.utc) > verification.expires_at:
        verification.status = "expired"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP verification expired",
        )

    verification.otp_code = payload.otp_code
    verification.status = "verified"
    verification.verified_at = datetime.now(timezone.utc)
    account.status = "active"
    await db.flush()

    return {"message": "Account verified and activated successfully"}


@router.get(
    "/clients/{client_id}/accounts/{account_id}/status",
    response_model=AccountStatusResponse,
)
async def get_account_status(
    client_id: int,
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _client: Client = Depends(get_client_or_403),
):
    result = await db.execute(
        select(TelegramAccount).where(
            TelegramAccount.id == account_id,
            TelegramAccount.client_id == client_id,
        )
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return AccountStatusResponse(
        id=account.id,
        phone=account.phone,
        status=account.status.value if hasattr(account.status, "value") else account.status,
        is_connected=account.status == "active",
        last_checked=datetime.now(timezone.utc),
    )


@router.delete(
    "/clients/{client_id}/accounts/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_account(
    client_id: int,
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _client: Client = Depends(get_client_or_403),
):
    result = await db.execute(
        select(TelegramAccount).where(
            TelegramAccount.id == account_id,
            TelegramAccount.client_id == client_id,
        )
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    await db.delete(account)
