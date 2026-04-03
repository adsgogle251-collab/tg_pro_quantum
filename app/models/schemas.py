from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


# ── Auth ──────────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class OTPRequest(BaseModel):
    phone: str


class OTPVerify(BaseModel):
    phone: str
    code: str


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Client ────────────────────────────────────────────────────────────────────

class ClientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    company: Optional[str] = None
    plan: str = "basic"
    max_accounts: int = Field(default=5, ge=1, le=1000)


class ClientUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    company: Optional[str] = None
    status: Optional[str] = None
    plan: Optional[str] = None
    max_accounts: Optional[int] = Field(None, ge=1, le=1000)


class ClientResponse(BaseModel):
    id: int
    user_id: int
    name: str
    company: Optional[str]
    api_key: str
    status: str
    plan: str
    max_accounts: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ClientStats(BaseModel):
    total_accounts: int
    active_accounts: int
    total_groups: int
    total_campaigns: int
    running_campaigns: int
    messages_sent_today: int


# ── TelegramAccount ───────────────────────────────────────────────────────────

class AccountCreate(BaseModel):
    phone: str
    account_name: Optional[str] = None
    api_id: Optional[int] = None
    api_hash: Optional[str] = None


class AccountOTPRequest(BaseModel):
    otp_service: str = "sms_activate"


class AccountOTPVerify(BaseModel):
    otp_code: str


class AccountResponse(BaseModel):
    id: int
    client_id: int
    phone: str
    account_name: Optional[str]
    status: str
    api_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AccountStatusResponse(BaseModel):
    id: int
    phone: str
    status: str
    is_connected: bool
    last_checked: datetime


# ── TelegramGroup ─────────────────────────────────────────────────────────────

class GroupAutoJoinRequest(BaseModel):
    group_links: List[str] = Field(min_length=1)
    account_id: int


class GroupScrapeMembersRequest(BaseModel):
    group_id: int
    account_id: int
    limit: int = Field(default=200, ge=1, le=10000)


class GroupUpdate(BaseModel):
    group_name: Optional[str] = None
    is_active: Optional[bool] = None
    auto_join: Optional[bool] = None


class GroupResponse(BaseModel):
    id: int
    client_id: int
    group_id: int
    group_name: str
    username: Optional[str]
    member_count: int
    type: str
    is_active: bool
    auto_join: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Campaign ──────────────────────────────────────────────────────────────────

class CampaignMessageCreate(BaseModel):
    message_text: Optional[str] = None
    has_media: bool = False
    media_path: Optional[str] = None
    message_type: str = "text"
    order_index: int = 0


class CampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    broadcast_mode: str = "immediate"
    delay_min: int = Field(default=5, ge=1, le=3600)
    delay_max: int = Field(default=15, ge=1, le=3600)
    max_messages_per_hour: int = Field(default=100, ge=1, le=10000)
    loop_count: int = Field(default=0, ge=0)
    is_loop_infinite: bool = False
    scheduled_at: Optional[datetime] = None
    account_ids: List[int] = Field(default_factory=list)
    group_ids: List[int] = Field(default_factory=list)
    messages: List[CampaignMessageCreate] = Field(default_factory=list)


class CampaignUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    broadcast_mode: Optional[str] = None
    delay_min: Optional[int] = Field(None, ge=1, le=3600)
    delay_max: Optional[int] = Field(None, ge=1, le=3600)
    max_messages_per_hour: Optional[int] = Field(None, ge=1, le=10000)
    loop_count: Optional[int] = Field(None, ge=0)
    is_loop_infinite: Optional[bool] = None
    scheduled_at: Optional[datetime] = None


class CampaignScheduleRequest(BaseModel):
    scheduled_at: datetime


class CampaignResponse(BaseModel):
    id: int
    client_id: int
    name: str
    description: Optional[str]
    status: str
    broadcast_mode: str
    delay_min: int
    delay_max: int
    max_messages_per_hour: int
    loop_count: int
    is_loop_infinite: bool
    scheduled_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CampaignValidationResult(BaseModel):
    is_valid: bool
    errors: List[str]
    warnings: List[str]


# ── Broadcast ─────────────────────────────────────────────────────────────────

class BroadcastSendRequest(BaseModel):
    dry_run: bool = False


class BroadcastStatusResponse(BaseModel):
    campaign_id: int
    status: str
    total_queued: int
    total_sent: int
    total_failed: int
    total_pending: int
    started_at: Optional[datetime]
    estimated_completion: Optional[datetime]


class BroadcastProgressResponse(BaseModel):
    campaign_id: int
    progress_pct: float
    messages_per_minute: float
    current_account: Optional[str]
    current_group: Optional[str]
    elapsed_seconds: float
    eta_seconds: Optional[float]


# ── Analytics ─────────────────────────────────────────────────────────────────

class CampaignAnalyticsResponse(BaseModel):
    campaign_id: int
    total_sent: int
    total_failed: int
    total_pending: int
    delivery_rate: float
    avg_send_time: Optional[float]
    last_updated: datetime

    model_config = {"from_attributes": True}


class ClientAnalyticsOverview(BaseModel):
    client_id: int
    total_campaigns: int
    completed_campaigns: int
    total_messages_sent: int
    total_messages_failed: int
    overall_delivery_rate: float
    active_accounts: int
    total_groups: int


class AnalyticsHistoryEntry(BaseModel):
    campaign_id: int
    campaign_name: str
    status: str
    total_sent: int
    total_failed: int
    delivery_rate: float
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


# ── Pagination ────────────────────────────────────────────────────────────────

class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
    total_pages: int
