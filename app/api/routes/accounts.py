"""
TG PRO QUANTUM - Telegram Account Management Routes
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_client
from app.database import get_db
from app.models.database import AccountStatus, Client, TelegramAccount
from app.models.schemas import (
    AccountCreate, AccountResponse, AccountUpdate, MessageResponse,
    TelegramLoginRequest, TelegramLoginResponse, TelegramVerifyRequest,
)
from app.core.account_manager import account_manager as acct_mgr

router = APIRouter(prefix="/accounts", tags=["Telegram Accounts"])


def _require_owns(account: TelegramAccount, client: Client) -> None:
    if account.client_id != client.id and not client.is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("/", response_model=List[AccountResponse])
async def list_accounts(
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """List accounts belonging to the current client."""
    result = await db.execute(
        select(TelegramAccount).where(TelegramAccount.client_id == current_client.id)
    )
    return result.scalars().all()


@router.post("/", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    body: AccountCreate,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Add a new Telegram account (OTP verification required separately)."""
    existing = await db.execute(
        select(TelegramAccount).where(
            TelegramAccount.client_id == current_client.id,
            TelegramAccount.phone == body.phone,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Account with this phone already exists")

    account = TelegramAccount(
        client_id=current_client.id,
        name=body.name,
        phone=body.phone,
        api_id=body.api_id,
        api_hash=body.api_hash,
    )
    db.add(account)
    await db.flush()
    await db.refresh(account)
    return account


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    result = await db.execute(select(TelegramAccount).where(TelegramAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    _require_owns(account, current_client)
    return account


@router.patch("/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: int,
    body: AccountUpdate,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    result = await db.execute(select(TelegramAccount).where(TelegramAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    _require_owns(account, current_client)

    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(account, key, value)
    await db.flush()
    await db.refresh(account)
    return account


@router.delete("/{account_id}", response_model=MessageResponse)
async def delete_account(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    result = await db.execute(select(TelegramAccount).where(TelegramAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    _require_owns(account, current_client)
    await db.delete(account)
    return MessageResponse(message="Account deleted")


@router.post("/{account_id}/health-check", response_model=dict)
async def health_check(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Run a health check on the Telegram account."""
    result = await db.execute(select(TelegramAccount).where(TelegramAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    _require_owns(account, current_client)

    health = await acct_mgr.check_health(account)
    account.health_score = health.get("score", account.health_score)
    await db.flush()
    # Return sanitized result (no raw exception details to the caller)
    return {
        "account_id": health.get("account_id"),
        "phone": health.get("phone"),
        "score": health.get("score"),
        "status": health.get("status"),
        "checked_at": health.get("checked_at"),
    }


# ── Telegram OTP Login (account onboarding) ───────────────────────────────────

@router.post("/telegram/request-code", response_model=TelegramLoginResponse)
async def request_telegram_code(
    body: TelegramLoginRequest,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """
    Step 1 of Telegram account login.

    Sends an OTP to *phone* via the Telegram API.
    Returns a ``phone_code_hash`` that must be passed to ``/telegram/verify``.
    """
    from app.services.telegram_service import TelegramService

    svc = TelegramService()
    try:
        result = await svc.request_login_code(body.phone, body.api_id, body.api_hash)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return TelegramLoginResponse(**result)


@router.post("/telegram/verify", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def verify_telegram_code(
    body: TelegramVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """
    Step 2 of Telegram account login.

    Verifies the OTP for the account record identified by *account_id*,
    persists the session string, and marks the account as ``active``.
    """
    from app.services.telegram_service import TelegramService

    result = await db.execute(select(TelegramAccount).where(TelegramAccount.id == body.account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    _require_owns(account, current_client)

    if not account.api_id:
        raise HTTPException(
            status_code=422,
            detail="Account is missing api_id – update the account with a valid Telegram API ID first",
        )
    if not account.api_hash:
        raise HTTPException(
            status_code=422,
            detail="Account is missing api_hash – update the account with a valid Telegram API hash first",
        )

    svc = TelegramService()
    try:
        session_string = await svc.complete_login(
            phone=account.phone,
            code=body.code,
            phone_code_hash=body.phone_code_hash,
            password=body.password,
            api_id=account.api_id,
            api_hash=account.api_hash,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    account.session_string = session_string
    account.status = AccountStatus.active
    await db.flush()
    await db.refresh(account)
    return account
