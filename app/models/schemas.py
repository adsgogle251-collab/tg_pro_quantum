"""
TG PRO QUANTUM - Pydantic Schemas (request / response models)
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.database import (
    AccountStatus, BroadcastStatus, CampaignMode, CampaignStatus, ClientStatus, ClientPlan, OTPStatus,
    AccountFeature, AccountGroupLink,
    AccountGroupFeatureType, AccountGroupStatus,
    LicenseTier, LicenseStatus,
    ImportSourceType, ImportStatus,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

class OrmBase(BaseModel):
    model_config = {"from_attributes": True}


# ── Auth ─────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        errors = []
        if not any(c.isupper() for c in v):
            errors.append("at least one uppercase letter")
        if not any(c.islower() for c in v):
            errors.append("at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            errors.append("at least one digit")
        if not any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in v):
            errors.append("at least one special character")
        if errors:
            raise ValueError("Password must contain " + ", ".join(errors))
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = Field(None, min_length=8, max_length=128)


class TOTPSetupResponse(BaseModel):
    secret: str
    uri: str


# ── OTP ──────────────────────────────────────────────────────────────────────

class OTPRequestSchema(BaseModel):
    phone: str = Field(..., pattern=r"^\+?[1-9]\d{6,14}$")


class OTPVerifySchema(BaseModel):
    phone: str = Field(..., pattern=r"^\+?[1-9]\d{6,14}$")
    code: str = Field(..., min_length=4, max_length=8)


class OTPResponse(OrmBase):
    id: int
    phone: str
    status: OTPStatus
    expires_at: datetime
    created_at: datetime


# ── Client ────────────────────────────────────────────────────────────────────

class ClientCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    plan_type: Optional[ClientPlan] = ClientPlan.starter
    usage_limit_monthly: Optional[int] = Field(10000, ge=0)
    webhook_url: Optional[str] = None


class ClientUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    status: Optional[ClientStatus] = None
    plan_type: Optional[ClientPlan] = None
    settings: Optional[Dict[str, Any]] = None
    billing_info: Optional[Dict[str, Any]] = None
    usage_limit_monthly: Optional[int] = Field(None, ge=0)
    current_usage_monthly: Optional[int] = Field(None, ge=0)
    webhook_url: Optional[str] = None


class ClientResponse(OrmBase):
    id: int
    name: str
    email: str
    api_key: Optional[str]
    status: ClientStatus
    plan_type: ClientPlan
    is_admin: bool
    usage_limit_monthly: int
    current_usage_monthly: int
    webhook_url: Optional[str]
    created_at: datetime


class ClientDashboard(BaseModel):
    client_id: int
    client_name: str
    plan_type: str
    status: str
    total_campaigns: int
    active_campaigns: int
    total_messages_sent: int
    usage_limit_monthly: int
    current_usage_monthly: int
    usage_pct: float
    accounts_count: int
    account_groups_count: int
    overall_delivery_rate: float


# ── Telegram Account ──────────────────────────────────────────────────────────

class AccountCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    phone: str = Field(..., pattern=r"^\+?[1-9]\d{6,14}$")
    api_id: Optional[int] = Field(None, gt=0)
    api_hash: Optional[str] = Field(None, min_length=32, max_length=64)


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[AccountStatus] = None
    tags: Optional[List[str]] = None
    account_settings: Optional[Dict[str, Any]] = None


class AccountResponse(OrmBase):
    id: int
    client_id: int
    name: str
    phone: str
    status: AccountStatus
    health_score: float
    messages_sent_today: int
    last_used_at: Optional[datetime]
    created_at: datetime
    # Sprint 3 fields
    tags: Optional[List[str]] = None
    import_source: Optional[str] = None
    last_activity: Optional[datetime] = None
    otp_enabled: bool = False


# ── Telegram OTP Login (account onboarding) ───────────────────────────────────

class TelegramLoginRequest(BaseModel):
    """Step 1: send OTP code to the phone number via Telegram."""
    phone: str = Field(..., pattern=r"^\+?[1-9]\d{6,14}$")
    api_id: int = Field(..., gt=0)
    api_hash: str = Field(..., min_length=32, max_length=64)


class TelegramLoginResponse(BaseModel):
    phone_code_hash: str
    type: str
    timeout: int


class TelegramVerifyRequest(BaseModel):
    """Step 2: verify OTP and finalise login for an existing account record."""
    account_id: int
    code: str = Field(..., min_length=1, max_length=10)
    phone_code_hash: str
    password: str = Field("", description="2FA password if enabled")


# ── Group ─────────────────────────────────────────────────────────────────────

class GroupCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=255)
    title: Optional[str] = None
    tags: List[str] = []


class GroupUpdate(BaseModel):
    title: Optional[str] = None
    is_active: Optional[bool] = None
    tags: Optional[List[str]] = None


class GroupResponse(OrmBase):
    id: int
    client_id: int
    username: str
    title: Optional[str]
    member_count: int
    is_active: bool
    tags: List[str]
    created_at: datetime


# ── Campaign ──────────────────────────────────────────────────────────────────

class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    message_text: str = Field(..., min_length=1)
    media_url: Optional[str] = None
    mode: CampaignMode = CampaignMode.once
    scheduled_at: Optional[datetime] = None
    cron_expression: Optional[str] = None
    repeat_interval_minutes: int = Field(0, ge=0)
    target_group_ids: List[int] = []
    account_ids: List[int] = []
    delay_min: float = Field(3.0, ge=0.5)
    delay_max: float = Field(8.0, ge=0.5)
    max_retries: int = Field(3, ge=0, le=10)

    @field_validator("delay_max")
    @classmethod
    def delay_max_gte_min(cls, v: float, info: Any) -> float:
        if "delay_min" in info.data and v < info.data["delay_min"]:
            raise ValueError("delay_max must be >= delay_min")
        return v


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    message_text: Optional[str] = None
    media_url: Optional[str] = None
    mode: Optional[CampaignMode] = None
    scheduled_at: Optional[datetime] = None
    cron_expression: Optional[str] = None
    repeat_interval_minutes: Optional[int] = None
    target_group_ids: Optional[List[int]] = None
    account_ids: Optional[List[int]] = None
    delay_min: Optional[float] = None
    delay_max: Optional[float] = None
    max_retries: Optional[int] = None


class CampaignResponse(OrmBase):
    id: int
    client_id: int
    name: str
    message_text: str
    media_url: Optional[str]
    status: CampaignStatus
    mode: CampaignMode
    scheduled_at: Optional[datetime]
    cron_expression: Optional[str]
    repeat_interval_minutes: int
    target_group_ids: List[int]
    account_ids: List[int]
    delay_min: float
    delay_max: float
    max_retries: int
    total_targets: int
    sent_count: int
    failed_count: int
    retry_count: int
    celery_task_id: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    completed_at: Optional[datetime]


# ── Broadcast ─────────────────────────────────────────────────────────────────

class BroadcastStartRequest(BaseModel):
    campaign_id: int


class BroadcastLogResponse(OrmBase):
    id: int
    campaign_id: int
    account_id: Optional[int]
    group_username: str
    status: BroadcastStatus
    error_message: Optional[str]
    attempt_number: int
    sent_at: Optional[datetime]
    created_at: datetime


class BroadcastDashboard(BaseModel):
    campaign_id: int
    campaign_name: str
    status: CampaignStatus
    total_targets: int
    sent_count: int
    failed_count: int
    retry_count: int
    delivery_rate: float
    progress_pct: float
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


# ── Analytics ─────────────────────────────────────────────────────────────────

class CampaignStats(BaseModel):
    campaign_id: int
    campaign_name: str
    total_targets: int
    sent_count: int
    failed_count: int
    delivery_rate: float
    created_at: datetime
    completed_at: Optional[datetime]


class ClientStats(BaseModel):
    client_id: int
    total_campaigns: int
    active_campaigns: int
    total_messages_sent: int
    total_messages_failed: int
    overall_delivery_rate: float
    accounts_count: int
    groups_count: int


# ── Account Feature / Group Assignment ───────────────────────────────────────

class AccountFeatureResponse(OrmBase):
    id: int
    account_id: int
    feature: str
    assigned_at: datetime
    status: str


class AccountGroupLinkResponse(OrmBase):
    id: int
    account_id: int
    group_id: int
    assigned_at: datetime


# ── Generic ───────────────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str
    detail: Optional[Any] = None


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    per_page: int
    pages: int


# ── Account Groups (Enterprise) ───────────────────────────────────────────────

class AccountGroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    feature_type: AccountGroupFeatureType = AccountGroupFeatureType.general
    client_id: Optional[int] = None
    config: Optional[Dict[str, Any]] = None


class AccountGroupUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    feature_type: Optional[AccountGroupFeatureType] = None
    status: Optional[AccountGroupStatus] = None
    client_id: Optional[int] = None
    config: Optional[Dict[str, Any]] = None


class AccountGroupResponse(OrmBase):
    id: int
    name: str
    feature_type: AccountGroupFeatureType
    status: AccountGroupStatus
    client_id: Optional[int]
    config: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: Optional[datetime]


class AccountAssignmentCreate(BaseModel):
    account_id: int
    feature_type: str = "general"


class AccountAssignmentResponse(OrmBase):
    id: int
    account_id: int
    account_group_id: int
    feature_type: str
    assigned_at: datetime
    status: str


class AccountHealthResponse(OrmBase):
    id: int
    account_id: int
    account_group_id: int
    health_score: float
    warnings: int
    is_banned: bool
    last_check: datetime
    details: Optional[Dict[str, Any]]


class GroupAnalyticsResponse(OrmBase):
    id: int
    account_group_id: int
    messages_sent: int
    success_rate: float
    health_avg: float
    period_start: datetime
    period_end: Optional[datetime]
    created_at: datetime


class AccountGroupBulkImport(BaseModel):
    account_ids: List[int] = Field(..., min_length=1)
    feature_type: str = "general"


# ── Phase 3 Schemas ───────────────────────────────────────────────────────────

class CampaignActivityResponse(OrmBase):
    id: int
    campaign_id: int
    client_id: int
    account_name: str
    group_target: str
    success: bool
    error_type: Optional[str]
    error_message: Optional[str]
    duration_ms: Optional[int]
    attempt_number: int
    action_taken: Optional[str]
    created_at: datetime


class FailedMessageResponse(OrmBase):
    id: int
    campaign_id: int
    client_id: int
    group_target: str
    account_name: Optional[str]
    error_type: Optional[str]
    error_message: Optional[str]
    retry_count: int
    next_retry_at: Optional[datetime]
    is_dead_letter: bool
    created_at: datetime


class SafetyAlertResponse(OrmBase):
    id: int
    campaign_id: Optional[int]
    client_id: int
    alert_type: str
    severity: str
    message: str
    is_resolved: bool
    resolved_at: Optional[datetime]
    created_at: datetime


class ClientBroadcastStatsResponse(OrmBase):
    id: int
    client_id: int
    date: datetime
    messages_sent: int
    messages_failed: int
    success_rate: float
    active_campaigns: int
    accounts_used: int


class GroupVerifyRequest(BaseModel):
    group_usernames: List[str] = Field(..., min_length=1)
    min_members: int = Field(10, ge=0)


class GroupVerifyResult(BaseModel):
    username: str
    verified: bool
    member_count: Optional[int]
    is_group: Optional[bool]
    reason: Optional[str]


class GroupVerifyResponse(BaseModel):
    verified: List[GroupVerifyResult]
    total: int
    passed: int
    failed: int


class MultiClientCampaignCard(BaseModel):
    client_id: int
    client_name: str
    campaign_id: int
    campaign_name: str
    status: str
    progress_pct: float
    sent_count: int
    total_targets: int
    success_rate: float
    active_accounts: int
    elapsed_minutes: Optional[float]


class BroadcastOverviewResponse(BaseModel):
    total_active_campaigns: int
    messages_sent_24h: int
    overall_success_rate: float
    total_accounts: int
    healthy_accounts: int
    campaigns: List[MultiClientCampaignCard]


class CampaignDetailResponse(OrmBase):
    """Extended campaign response with Phase 3 fields."""
    id: int
    client_id: int
    name: str
    message_text: str
    media_url: Optional[str]
    link_url: Optional[str]
    status: CampaignStatus
    mode: CampaignMode
    scheduled_at: Optional[datetime]
    total_targets: int
    sent_count: int
    failed_count: int
    retry_count: int
    jitter_pct: Optional[float]
    max_per_hour: Optional[int]
    max_per_day: Optional[int]
    rotate_every: Optional[int]
    timing_start: Optional[str]
    timing_end: Optional[str]
    safety_flags: Optional[Dict[str, Any]]
    error_count: Optional[int]
    last_error_message: Optional[str]
    account_group_id: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]
    completed_at: Optional[datetime]


class BroadcastCampaignCreate(BaseModel):
    """Schema for creating a campaign with Phase 3 fields."""
    name: str = Field(..., min_length=1, max_length=255)
    client_id: Optional[int] = None     # admin only; regular users use their own id
    message_text: str = Field(..., min_length=1)
    media_url: Optional[str] = None
    link_url: Optional[str] = None
    mode: CampaignMode = CampaignMode.once
    scheduled_at: Optional[datetime] = None
    timing_start: Optional[str] = None
    timing_end: Optional[str] = None
    target_group_ids: List[int] = Field(default_factory=list)
    account_ids: List[int] = Field(default_factory=list)
    account_group_id: Optional[int] = None
    delay_min: float = Field(30.0, ge=1.0)
    delay_max: float = Field(33.0, ge=1.0)
    jitter_pct: float = Field(10.0, ge=0.0, le=50.0)
    max_retries: int = Field(3, ge=0)
    max_per_hour: int = Field(100, ge=1)
    max_per_day: int = Field(500, ge=1)
    rotate_every: int = Field(20, ge=1)
    safety_flags: Optional[Dict[str, Any]] = None


# ── License ───────────────────────────────────────────────────────────────────

class LicenseCreate(BaseModel):
    tier: LicenseTier = LicenseTier.starter
    client_id: Optional[int] = None
    max_accounts: int = Field(5, ge=1)
    max_campaigns: int = Field(10, ge=1)
    expires_at: Optional[datetime] = None


class LicenseUpdate(BaseModel):
    tier: Optional[LicenseTier] = None
    status: Optional[LicenseStatus] = None
    client_id: Optional[int] = None
    max_accounts: Optional[int] = Field(None, ge=1)
    max_campaigns: Optional[int] = Field(None, ge=1)
    expires_at: Optional[datetime] = None


class LicenseResponse(OrmBase):
    id: int
    key: str
    tier: LicenseTier
    status: LicenseStatus
    client_id: Optional[int]
    max_accounts: int
    max_campaigns: int
    expires_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]


# ── Admin Client ──────────────────────────────────────────────────────────────

class AdminClientPlanUpdate(BaseModel):
    plan_type: Optional[ClientPlan] = None
    status: Optional[ClientStatus] = None
    usage_limit_monthly: Optional[int] = Field(None, ge=0)


# ── Audit Log ─────────────────────────────────────────────────────────────────

class AuditLogResponse(OrmBase):
    id: int
    client_id: Optional[int]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    details: Optional[Dict[str, Any]]
    ip_address: Optional[str]
    created_at: datetime


# ── Webhook ───────────────────────────────────────────────────────────────────

class WebhookCreate(BaseModel):
    url: str = Field(..., max_length=500)
    events: List[str] = Field(default_factory=list)
    secret: Optional[str] = Field(None, max_length=64)


class WebhookResponse(OrmBase):
    id: int
    client_id: int
    url: str
    events: List[str]
    secret: Optional[str]
    is_active: bool
    created_at: datetime


# ── Sprint 3: Import & OTP Schemas ───────────────────────────────────────────

class SessionImportRequest(BaseModel):
    """Import a single account from a pasted session string."""
    session_text: str = Field(..., min_length=10, description="Pasted session block (Ctrl+A)")
    phone: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{6,14}$")
    name: Optional[str] = Field(None, max_length=255)


class BulkAccountCreate(BaseModel):
    """Create multiple accounts in a single request."""

    class AccountItem(BaseModel):
        phone: str = Field(..., pattern=r"^\+?[1-9]\d{6,14}$")
        name: Optional[str] = Field(None, max_length=255)
        api_id: Optional[int] = Field(None, gt=0)
        api_hash: Optional[str] = Field(None, max_length=64)
        session_string: Optional[str] = None
        tags: Optional[List[str]] = None

    accounts: List[AccountItem] = Field(..., min_length=1, max_length=500)


class ImportResultResponse(BaseModel):
    import_log_id: int
    total_rows: int
    imported: int
    skipped: int
    failed_rows: int
    errors: List[str]
    status: ImportStatus


class ImportLogResponse(OrmBase):
    id: int
    client_id: int
    source_type: ImportSourceType
    status: ImportStatus
    total_rows: int
    imported: int
    skipped: int
    failed_rows: int
    errors: List[str]
    filename: Optional[str]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    created_at: datetime


class TOTPEnableResponse(BaseModel):
    """Returned when TOTP is enabled for an account; contains the QR URI and backup codes."""
    secret: str
    provisioning_uri: str
    backup_codes: List[str]    # shown once; not stored in plaintext


class TOTPVerifyRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=8, description="6-digit TOTP code")


class TOTPVerifyResponse(BaseModel):
    verified: bool
    remaining_backup_codes: Optional[int] = None
