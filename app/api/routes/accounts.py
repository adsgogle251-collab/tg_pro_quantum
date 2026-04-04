"""
TG PRO QUANTUM - Telegram Account Management Routes
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_client
from app.database import get_db
from app.models.database import AccountStatus, Client, TelegramAccount, AccountFeature, AccountGroupLink, Group
from app.models.schemas import (
    AccountCreate, AccountResponse, AccountUpdate, MessageResponse,
    TelegramLoginRequest, TelegramLoginResponse, TelegramVerifyRequest,
    AccountFeatureResponse, AccountGroupLinkResponse,
)
from app.core.account_manager import account_manager as acct_mgr

router = APIRouter(prefix="/accounts", tags=["Telegram Accounts"])

VALID_FEATURES = {"broadcast", "campaign", "finder", "scrape", "join", "ai_cs", "analytics", "crm", "cs"}


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


# ── Feature Assignment Endpoints ─────────────────────────────────────────────

@router.get("/assignments/all", response_model=dict)
async def get_all_assignments(
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Get all feature assignments for the client's accounts."""
    result = await db.execute(
        select(TelegramAccount, AccountFeature)
        .join(AccountFeature, AccountFeature.account_id == TelegramAccount.id, isouter=True)
        .where(TelegramAccount.client_id == current_client.id)
    )
    assignments: dict = {f: [] for f in VALID_FEATURES}
    for account, feature in result.all():
        if feature and feature.feature in assignments:
            assignments[feature.feature].append(account.name)
    return assignments


@router.get("/by-feature/{feature}", response_model=List[AccountResponse])
async def get_accounts_by_feature(
    feature: str,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Get all accounts assigned to a specific feature."""
    if feature not in VALID_FEATURES:
        raise HTTPException(status_code=400, detail=f"Invalid feature. Valid: {sorted(VALID_FEATURES)}")
    result = await db.execute(
        select(TelegramAccount)
        .join(AccountFeature, AccountFeature.account_id == TelegramAccount.id)
        .where(TelegramAccount.client_id == current_client.id, AccountFeature.feature == feature)
    )
    return result.scalars().all()


@router.post("/{account_id}/features/{feature}", response_model=MessageResponse)
async def assign_feature(
    account_id: int,
    feature: str,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Assign a feature to an account."""
    if feature not in VALID_FEATURES:
        raise HTTPException(status_code=400, detail=f"Invalid feature. Valid: {sorted(VALID_FEATURES)}")
    result = await db.execute(select(TelegramAccount).where(TelegramAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    _require_owns(account, current_client)

    existing = await db.execute(
        select(AccountFeature).where(
            AccountFeature.account_id == account_id,
            AccountFeature.feature == feature
        )
    )
    if not existing.scalar_one_or_none():
        db.add(AccountFeature(account_id=account_id, feature=feature))
    return MessageResponse(message=f"Feature '{feature}' assigned to account {account_id}")


@router.delete("/{account_id}/features/{feature}", response_model=MessageResponse)
async def remove_feature(
    account_id: int,
    feature: str,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Remove a feature assignment from an account."""
    if feature not in VALID_FEATURES:
        raise HTTPException(status_code=400, detail=f"Invalid feature. Valid: {sorted(VALID_FEATURES)}")
    result = await db.execute(select(TelegramAccount).where(TelegramAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    _require_owns(account, current_client)

    await db.execute(
        delete(AccountFeature).where(
            AccountFeature.account_id == account_id,
            AccountFeature.feature == feature
        )
    )
    return MessageResponse(message=f"Feature '{feature}' removed from account {account_id}")


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


# ── Feature Assignment Endpoints ───────────────────────────────────────────────

@router.post("/{account_id}/features/{feature}", response_model=AccountFeatureResponse, status_code=status.HTTP_201_CREATED)
async def assign_feature(
    account_id: int,
    feature: str,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Assign a feature to a Telegram account."""
    result = await db.execute(select(TelegramAccount).where(TelegramAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    _require_owns(account, current_client)

    existing = await db.execute(
        select(AccountFeature).where(
            AccountFeature.account_id == account_id,
            AccountFeature.feature == feature,
        )
    )
    af = existing.scalar_one_or_none()
    if af:
        af.status = "active"
    else:
        af = AccountFeature(account_id=account_id, feature=feature)
        db.add(af)
    await db.flush()
    await db.refresh(af)
    return af


@router.delete("/{account_id}/features/{feature}", response_model=MessageResponse)
async def remove_feature(
    account_id: int,
    feature: str,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Remove a feature assignment from a Telegram account."""
    result = await db.execute(select(TelegramAccount).where(TelegramAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    _require_owns(account, current_client)

    await db.execute(
        delete(AccountFeature).where(
            AccountFeature.account_id == account_id,
            AccountFeature.feature == feature,
        )
    )
    return MessageResponse(message=f"Feature '{feature}' removed from account {account_id}")


@router.get("/by-feature/{feature}", response_model=List[AccountResponse])
async def get_accounts_by_feature(
    feature: str,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Get all accounts assigned to a specific feature."""
    result = await db.execute(
        select(TelegramAccount)
        .join(AccountFeature, AccountFeature.account_id == TelegramAccount.id)
        .where(
            TelegramAccount.client_id == current_client.id,
            AccountFeature.feature == feature,
            AccountFeature.status == "active",
        )
    )
    return result.scalars().all()


@router.get("/assignments", response_model=dict)
async def get_all_assignments(
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Get all feature and group assignments for the current client."""
    result = await db.execute(
        select(AccountFeature)
        .join(TelegramAccount, TelegramAccount.id == AccountFeature.account_id)
        .where(TelegramAccount.client_id == current_client.id)
    )
    features = result.scalars().all()

    result2 = await db.execute(
        select(AccountGroupLink)
        .join(TelegramAccount, TelegramAccount.id == AccountGroupLink.account_id)
        .where(TelegramAccount.client_id == current_client.id)
    )
    group_links = result2.scalars().all()

    assignments: dict = {}
    for af in features:
        assignments.setdefault(af.account_id, {"features": [], "groups": []})
        assignments[af.account_id]["features"].append(af.feature)
    for gl in group_links:
        assignments.setdefault(gl.account_id, {"features": [], "groups": []})
        assignments[gl.account_id]["groups"].append(gl.group_id)

    return assignments


# ── Group Link Endpoints ───────────────────────────────────────────────────────

@router.post("/{account_id}/groups/{group_id}", response_model=AccountGroupLinkResponse, status_code=status.HTTP_201_CREATED)
async def assign_group_to_account(
    account_id: int,
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Assign a group to a Telegram account."""
    result = await db.execute(select(TelegramAccount).where(TelegramAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    _require_owns(account, current_client)

    grp_result = await db.execute(select(Group).where(Group.id == group_id))
    group = grp_result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    existing = await db.execute(
        select(AccountGroupLink).where(
            AccountGroupLink.account_id == account_id,
            AccountGroupLink.group_id == group_id,
        )
    )
    link = existing.scalar_one_or_none()
    if not link:
        link = AccountGroupLink(account_id=account_id, group_id=group_id)
        db.add(link)
        await db.flush()
        await db.refresh(link)
    return link


@router.delete("/{account_id}/groups/{group_id}", response_model=MessageResponse)
async def remove_group_from_account(
    account_id: int,
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Remove a group assignment from a Telegram account."""
    result = await db.execute(select(TelegramAccount).where(TelegramAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    _require_owns(account, current_client)

    await db.execute(
        delete(AccountGroupLink).where(
            AccountGroupLink.account_id == account_id,
            AccountGroupLink.group_id == group_id,
        )
    )
    return MessageResponse(message=f"Group {group_id} unlinked from account {account_id}")


@router.get("/{account_id}/groups", response_model=List[AccountGroupLinkResponse])
async def get_account_groups(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """Get all groups linked to a Telegram account."""
    result = await db.execute(select(TelegramAccount).where(TelegramAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    _require_owns(account, current_client)

    links_result = await db.execute(
        select(AccountGroupLink).where(AccountGroupLink.account_id == account_id)
    )
    return links_result.scalars().all()
