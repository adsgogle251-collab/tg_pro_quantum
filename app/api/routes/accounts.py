"""
TG PRO QUANTUM - Telegram Account Management Routes
"""
from math import ceil
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, or_, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_client
from app.database import get_db
from app.models.database import (
    AccountStatus, Client, TelegramAccount, AccountFeature, AccountGroupLink, Group,
    ImportSourceType,
)
from app.models.schemas import (
    AccountCreate, AccountResponse, AccountUpdate, MessageResponse,
    TelegramLoginRequest, TelegramLoginResponse, TelegramVerifyRequest,
    AccountFeatureResponse, AccountGroupLinkResponse,
    PaginatedResponse,
    # Sprint 3
    SessionImportRequest, BulkAccountCreate, ImportResultResponse, ImportLogResponse,
    TOTPEnableResponse, TOTPVerifyRequest, TOTPVerifyResponse,
)
from app.core.account_manager import account_manager as acct_mgr
from app.services.import_service import import_service, parse_session_text, parse_csv_content, parse_excel_content
from app.services.totp_service import totp_service
from app.websocket_manager import ws_manager

router = APIRouter(prefix="/accounts", tags=["Telegram Accounts"])

VALID_FEATURES = {"broadcast", "campaign", "finder", "scrape", "join", "ai_cs", "analytics", "crm", "cs"}


def _require_owns(account: TelegramAccount, client: Client) -> None:
    if account.client_id != client.id and not client.is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("/")
async def list_accounts(
    page: Optional[int] = Query(None, ge=1),
    per_page: int = Query(20, ge=1, le=200),
    search: Optional[str] = Query(None),
    account_status: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """List accounts belonging to the current client.

    When *page* is provided returns a paginated envelope; otherwise returns a plain list.
    """
    query = select(TelegramAccount).where(TelegramAccount.client_id == current_client.id)
    count_query = select(func.count(TelegramAccount.id)).where(TelegramAccount.client_id == current_client.id)

    if search:
        like = f"%{search}%"
        query = query.where(or_(TelegramAccount.name.ilike(like), TelegramAccount.phone.ilike(like)))
        count_query = count_query.where(or_(TelegramAccount.name.ilike(like), TelegramAccount.phone.ilike(like)))

    if account_status:
        try:
            status_val = AccountStatus(account_status)
            query = query.where(TelegramAccount.status == status_val)
            count_query = count_query.where(TelegramAccount.status == status_val)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {account_status}")

    if page is not None:
        total = (await db.execute(count_query)).scalar() or 0
        offset = (page - 1) * per_page
        result = await db.execute(query.offset(offset).limit(per_page))
        items = result.scalars().all()
        return PaginatedResponse(
            items=[AccountResponse.model_validate(a) for a in items],
            total=total,
            page=page,
            per_page=per_page,
            pages=ceil(total / per_page) if per_page else 1,
        )

    result = await db.execute(query)
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


# ═══════════════════════════════════════════════════════════════════════════════
# Sprint 3: Session Import, Bulk Create, File Import, OTP/2FA
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/import-session", response_model=ImportResultResponse, status_code=status.HTTP_201_CREATED)
async def import_session(
    body: SessionImportRequest,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """
    Import a single Telegram account from a pasted session string (Ctrl+A).

    Parses the text to extract phone / api_id / api_hash / session_string,
    then persists the account and fires a WebSocket ``account.imported`` event.
    """
    parsed = parse_session_text(body.session_text)

    # Allow the caller to override phone and name
    if body.phone:
        parsed["phone"] = body.phone
    if body.name:
        parsed["name"] = body.name

    if not parsed.get("phone"):
        raise HTTPException(
            status_code=422,
            detail="Could not extract a phone number from the session text. "
                   "Provide it explicitly via the 'phone' field.",
        )

    log = await import_service.create_import_log(
        client_id=current_client.id,
        source_type=ImportSourceType.session,
        filename=None,
        db=db,
    )

    imported, skipped, failed, errors = await import_service.bulk_upsert_accounts(
        client_id=current_client.id,
        rows=[parsed],
        import_source="session",
        db=db,
    )
    await import_service.finish_import_log(log, imported, skipped, failed, errors, db)

    # Real-time notification
    await ws_manager.broadcast(
        f"client:{current_client.id}",
        {"event": "account.imported", "source": "session", "imported": imported},
    )

    return ImportResultResponse(
        import_log_id=log.id,
        total_rows=log.total_rows,
        imported=imported,
        skipped=skipped,
        failed_rows=failed,
        errors=errors,
        status=log.status,
    )


@router.post("/bulk-create", response_model=ImportResultResponse, status_code=status.HTTP_201_CREATED)
async def bulk_create_accounts(
    body: BulkAccountCreate,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """
    Create multiple accounts in one request.

    Duplicate phones (same client) are silently skipped.
    Fires a WebSocket ``account.bulk_created`` event on completion.
    """
    rows = [a.model_dump(exclude_none=True) for a in body.accounts]

    log = await import_service.create_import_log(
        client_id=current_client.id,
        source_type=ImportSourceType.bulk,
        filename=None,
        db=db,
    )

    imported, skipped, failed, errors = await import_service.bulk_upsert_accounts(
        client_id=current_client.id,
        rows=rows,
        import_source="bulk",
        db=db,
    )
    await import_service.finish_import_log(log, imported, skipped, failed, errors, db)

    await ws_manager.broadcast(
        f"client:{current_client.id}",
        {"event": "account.bulk_created", "imported": imported, "skipped": skipped},
    )

    return ImportResultResponse(
        import_log_id=log.id,
        total_rows=log.total_rows,
        imported=imported,
        skipped=skipped,
        failed_rows=failed,
        errors=errors,
        status=log.status,
    )


@router.post("/import-file", response_model=ImportResultResponse, status_code=status.HTTP_201_CREATED)
async def import_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """
    Mass import accounts from a CSV or Excel (.xlsx) file.

    The file must contain at least a ``phone`` column.
    Optional columns: ``name``, ``api_id``, ``api_hash``, ``session_string``, ``tags``.
    Fires a WebSocket ``account.file_imported`` event on completion.
    """
    filename = file.filename or "upload"
    content = await file.read()

    # Detect format
    if filename.lower().endswith((".xlsx", ".xls")):
        rows, parse_errors = parse_excel_content(content)
        source_type = ImportSourceType.excel
    else:
        rows, parse_errors = parse_csv_content(content)
        source_type = ImportSourceType.csv

    if parse_errors and not rows:
        raise HTTPException(status_code=422, detail="; ".join(parse_errors))

    log = await import_service.create_import_log(
        client_id=current_client.id,
        source_type=source_type,
        filename=filename,
        db=db,
    )

    imported, skipped, failed, errors = await import_service.bulk_upsert_accounts(
        client_id=current_client.id,
        rows=rows,
        import_source=source_type.value,
        db=db,
    )
    errors = parse_errors + errors
    await import_service.finish_import_log(log, imported, skipped, failed, errors, db)

    await ws_manager.broadcast(
        f"client:{current_client.id}",
        {"event": "account.file_imported", "filename": filename, "imported": imported},
    )

    return ImportResultResponse(
        import_log_id=log.id,
        total_rows=log.total_rows,
        imported=imported,
        skipped=skipped,
        failed_rows=failed,
        errors=errors,
        status=log.status,
    )


@router.post("/{account_id}/enable-otp", response_model=TOTPEnableResponse)
async def enable_otp(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """
    Enable TOTP 2FA for an account.

    Generates a new TOTP secret and 10 one-time backup codes.
    The ``provisioning_uri`` can be rendered as a QR code by the frontend.
    **Backup codes are shown only once** — the client must save them.
    """
    result = await db.execute(select(TelegramAccount).where(TelegramAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    _require_owns(account, current_client)

    secret = totp_service.generate_secret()
    plaintext_codes, hashed_codes = totp_service.generate_backup_codes()
    uri = totp_service.get_provisioning_uri(
        secret=secret,
        account_label=account.phone,
    )

    account.otp_secret = secret
    account.backup_codes = hashed_codes
    # OTP is *not* marked enabled until the client verifies the first code
    await db.flush()

    await ws_manager.broadcast(
        f"client:{current_client.id}",
        {"event": "account.otp_setup", "account_id": account_id},
    )

    return TOTPEnableResponse(
        secret=secret,
        provisioning_uri=uri,
        backup_codes=plaintext_codes,
    )


@router.post("/{account_id}/verify-otp", response_model=TOTPVerifyResponse)
async def verify_otp(
    account_id: int,
    body: TOTPVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """
    Verify the first TOTP code after setup, activating 2FA for the account.

    Also accepts backup codes (8-character alphanumeric) in place of a TOTP code.
    """
    result = await db.execute(select(TelegramAccount).where(TelegramAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    _require_owns(account, current_client)

    if not account.otp_secret:
        raise HTTPException(status_code=400, detail="OTP not set up for this account. Call /enable-otp first.")

    code = body.code.strip()
    remaining: Optional[int] = None

    # 8-char code → try backup codes
    if len(code) == 8:
        valid, remaining_hashes = totp_service.verify_backup_code(
            code=code,
            stored_hashes=account.backup_codes or [],
        )
        if valid:
            account.backup_codes = remaining_hashes
            account.otp_enabled = True
            await db.flush()
            remaining = len(remaining_hashes)
            return TOTPVerifyResponse(verified=True, remaining_backup_codes=remaining)
        return TOTPVerifyResponse(verified=False)

    # 6-char code → TOTP
    verified = totp_service.verify_code(account.otp_secret, code)
    if verified and not account.otp_enabled:
        account.otp_enabled = True
        await db.flush()

        await ws_manager.broadcast(
            f"client:{current_client.id}",
            {"event": "account.otp_verified", "account_id": account_id},
        )

    return TOTPVerifyResponse(verified=verified)


@router.get("/import-logs", response_model=List[ImportLogResponse])
async def list_import_logs(
    db: AsyncSession = Depends(get_db),
    current_client: Client = Depends(get_current_client),
):
    """List all import logs for the current client (most recent first)."""
    from app.models.database import ImportLog
    result = await db.execute(
        select(ImportLog)
        .where(ImportLog.client_id == current_client.id)
        .order_by(ImportLog.created_at.desc())
        .limit(100)
    )
    return result.scalars().all()
