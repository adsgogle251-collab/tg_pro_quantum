"""
TG PRO QUANTUM - Pydantic Schemas (request / response models)
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.database import (
    AccountStatus, BroadcastStatus, CampaignMode, CampaignStatus, ClientStatus, OTPStatus,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

class OrmBase(BaseModel):
    model_config = {"from_attributes": True}


# ── Auth ─────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


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


class ClientUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    status: Optional[ClientStatus] = None
    settings: Optional[Dict[str, Any]] = None


class ClientResponse(OrmBase):
    id: int
    name: str
    email: str
    api_key: Optional[str]
    status: ClientStatus
    is_admin: bool
    created_at: datetime


# ── Telegram Account ──────────────────────────────────────────────────────────

class AccountCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    phone: str = Field(..., pattern=r"^\+?[1-9]\d{6,14}$")
    api_id: int = Field(..., gt=0)
    api_hash: str = Field(..., min_length=32, max_length=64)


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[AccountStatus] = None


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


# ── Generic ───────────────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str
    detail: Optional[Any] = None


class PaginatedResponse(BaseModel):
    total: int
    page: int
    per_page: int
    items: List[Any]
