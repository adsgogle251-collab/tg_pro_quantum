"""
TG PRO QUANTUM - SQLAlchemy ORM Models (PostgreSQL)
"""
import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, Enum, Float,
    ForeignKey, Integer, JSON, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


# ── Enumerations ──────────────────────────────────────────────────────────────

class ClientStatus(str, enum.Enum):
    active = "active"
    suspended = "suspended"
    trial = "trial"


class ClientPlan(str, enum.Enum):
    starter = "starter"
    pro = "pro"
    enterprise = "enterprise"


class AccountStatus(str, enum.Enum):
    active = "active"
    banned = "banned"
    flood_wait = "flood_wait"
    unverified = "unverified"
    inactive = "inactive"


class CampaignStatus(str, enum.Enum):
    draft = "draft"
    scheduled = "scheduled"
    running = "running"
    paused = "paused"
    completed = "completed"
    failed = "failed"


class CampaignMode(str, enum.Enum):
    once = "once"
    round_robin = "round_robin"
    loop = "loop"
    schedule_24_7 = "schedule_24_7"


class BroadcastStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class OTPStatus(str, enum.Enum):
    pending = "pending"
    verified = "verified"
    expired = "expired"
    failed = "failed"


# ── Models ────────────────────────────────────────────────────────────────────

class Client(Base):
    """Tenant / paying customer."""
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    api_key = Column(String(64), unique=True, index=True)
    status = Column(Enum(ClientStatus), default=ClientStatus.trial, nullable=False)
    plan_type = Column(Enum(ClientPlan), default=ClientPlan.starter, nullable=False)
    is_admin = Column(Boolean, default=False)
    settings = Column(JSON, default=dict)
    billing_info = Column(JSON, default=dict)
    usage_limit_monthly = Column(Integer, default=10000)
    current_usage_monthly = Column(Integer, default=0)
    webhook_url = Column(String(512), nullable=True)
    totp_secret = Column(String(32), nullable=True)
    totp_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # relationships
    accounts = relationship("TelegramAccount", back_populates="client", cascade="all, delete-orphan")
    campaigns = relationship("Campaign", back_populates="client", cascade="all, delete-orphan")
    groups = relationship("Group", back_populates="client", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="client", cascade="all, delete-orphan")


class TelegramAccount(Base):
    """Telegram account belonging to a client."""
    __tablename__ = "telegram_accounts"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    session_string = Column(Text)          # encrypted Telethon session
    api_id = Column(Integer)
    api_hash = Column(String(64))
    status = Column(Enum(AccountStatus), default=AccountStatus.unverified, nullable=False)
    health_score = Column(Float, default=100.0)
    messages_sent_today = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True))
    flood_wait_until = Column(DateTime(timezone=True))
    meta = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (UniqueConstraint("client_id", "phone", name="uq_client_phone"),)

    client = relationship("Client", back_populates="accounts")
    broadcast_logs = relationship("BroadcastLog", back_populates="account")
    feature_assignments = relationship("AccountFeature", back_populates="account", cascade="all, delete-orphan")
    group_links = relationship("AccountGroupLink", back_populates="account", cascade="all, delete-orphan")


class Group(Base):
    """Telegram group / channel target."""
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    username = Column(String(255), nullable=False)
    title = Column(String(255))
    member_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    tags = Column(JSON, default=list)
    meta = Column(JSON, default=dict)
    joined_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    client = relationship("Client", back_populates="groups")
    account_links = relationship("AccountGroupLink", back_populates="group", cascade="all, delete-orphan")


class Campaign(Base):
    """Broadcast campaign owned by a client."""
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    message_text = Column(Text, nullable=False)
    media_url = Column(String(512))        # optional media attachment
    status = Column(Enum(CampaignStatus), default=CampaignStatus.draft, nullable=False)
    mode = Column(Enum(CampaignMode), default=CampaignMode.once, nullable=False)
    # scheduling
    scheduled_at = Column(DateTime(timezone=True))
    cron_expression = Column(String(100))  # used for schedule_24_7 mode
    repeat_interval_minutes = Column(Integer, default=0)
    # targeting
    target_group_ids = Column(JSON, default=list)  # list[int] of Group.id
    account_ids = Column(JSON, default=list)        # list[int] of TelegramAccount.id
    # rate limiting
    delay_min = Column(Float, default=3.0)
    delay_max = Column(Float, default=8.0)
    max_retries = Column(Integer, default=3)
    # stats (denormalised for fast dashboard reads)
    total_targets = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    retry_count = Column(Integer, default=0)
    celery_task_id = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True))

    client = relationship("Client", back_populates="campaigns")
    broadcasts = relationship("BroadcastLog", back_populates="campaign", cascade="all, delete-orphan")


class BroadcastLog(Base):
    """Individual message send attempt."""
    __tablename__ = "broadcast_logs"

    id = Column(BigInteger, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("telegram_accounts.id"), nullable=True)
    group_username = Column(String(255), nullable=False)
    status = Column(Enum(BroadcastStatus), default=BroadcastStatus.pending, nullable=False)
    error_message = Column(Text)
    attempt_number = Column(Integer, default=1)
    sent_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    campaign = relationship("Campaign", back_populates="broadcasts")
    account = relationship("TelegramAccount", back_populates="broadcast_logs")


class OTPVerification(Base):
    """OTP session for phone-number / account verification."""
    __tablename__ = "otp_verifications"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(20), nullable=False, index=True)
    otp_code = Column(String(10))
    sms_activate_id = Column(String(64))   # activation ID from SMS Activate
    status = Column(Enum(OTPStatus), default=OTPStatus.pending, nullable=False)
    attempts = Column(Integer, default=0)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    verified_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    """Immutable audit trail."""
    __tablename__ = "audit_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(String(50), nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    client = relationship("Client", back_populates="audit_logs")


class AccountFeature(Base):
    """Maps a Telegram account to a functional feature (broadcast, scrape, join, etc.)."""
    __tablename__ = "account_features"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("telegram_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    feature = Column(String(64), nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(32), default="active", nullable=False)

    __table_args__ = (UniqueConstraint("account_id", "feature", name="uq_account_feature"),)

    account = relationship("TelegramAccount", back_populates="feature_assignments")


class AccountGroupLink(Base):
    """Associates a Telegram account with a target Group for a specific feature."""
    __tablename__ = "account_group_links"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("telegram_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("account_id", "group_id", name="uq_account_group"),)

    account = relationship("TelegramAccount", back_populates="group_links")
    group = relationship("Group", back_populates="account_links")


# ── New Enterprise Tables ─────────────────────────────────────────────────────

class AccountGroupFeatureType(str, enum.Enum):
    broadcast = "broadcast"
    finder = "finder"
    scrape = "scrape"
    join = "join"
    cs = "cs"
    warmer = "warmer"
    general = "general"


class AccountGroupStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    archived = "archived"


class AccountGroup(Base):
    """Named account pool that can be assigned to one or more features / clients."""
    __tablename__ = "account_groups_v2"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    feature_type = Column(Enum(AccountGroupFeatureType), default=AccountGroupFeatureType.general, nullable=False)
    status = Column(Enum(AccountGroupStatus), default=AccountGroupStatus.active, nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True)
    config = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    client = relationship("Client")
    assignments = relationship("AccountAssignment", back_populates="account_group", cascade="all, delete-orphan")
    health_records = relationship("AccountHealth", back_populates="account_group", cascade="all, delete-orphan")
    analytics_records = relationship("GroupAnalytics", back_populates="account_group", cascade="all, delete-orphan")


class AccountAssignment(Base):
    """Associates a TelegramAccount with an AccountGroup for a specific feature."""
    __tablename__ = "account_assignments"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("telegram_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    account_group_id = Column(Integer, ForeignKey("account_groups_v2.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_type = Column(String(64), nullable=False, default="general")
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(32), default="active", nullable=False)

    __table_args__ = (UniqueConstraint("account_id", "account_group_id", name="uq_account_assignment"),)

    account = relationship("TelegramAccount")
    account_group = relationship("AccountGroup", back_populates="assignments")


class AccountHealth(Base):
    """Health snapshot for a Telegram account within a group."""
    __tablename__ = "account_health"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("telegram_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    account_group_id = Column(Integer, ForeignKey("account_groups_v2.id", ondelete="CASCADE"), nullable=False, index=True)
    health_score = Column(Float, default=100.0, nullable=False)
    warnings = Column(Integer, default=0, nullable=False)
    is_banned = Column(Boolean, default=False, nullable=False)
    last_check = Column(DateTime(timezone=True), server_default=func.now())
    details = Column(JSON, default=dict)

    account = relationship("TelegramAccount")
    account_group = relationship("AccountGroup", back_populates="health_records")


class GroupAnalytics(Base):
    """Aggregated analytics for an account group."""
    __tablename__ = "group_analytics"

    id = Column(Integer, primary_key=True, index=True)
    account_group_id = Column(Integer, ForeignKey("account_groups_v2.id", ondelete="CASCADE"), nullable=False, index=True)
    messages_sent = Column(Integer, default=0, nullable=False)
    success_rate = Column(Float, default=0.0, nullable=False)
    health_avg = Column(Float, default=100.0, nullable=False)
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    account_group = relationship("AccountGroup", back_populates="analytics_records")


# ── Phase 3 Tables ────────────────────────────────────────────────────────────

class GroupVerificationStatus(str, enum.Enum):
    pending = "pending"
    verified = "verified"
    failed = "failed"


class CampaignActivity(Base):
    """Detailed per-message activity log for a campaign."""
    __tablename__ = "campaign_activities"

    id = Column(BigInteger, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    account_name = Column(String(255), nullable=False)
    group_target = Column(String(255), nullable=False)
    success = Column(Boolean, default=False, nullable=False)
    error_type = Column(String(100))       # user_limit, banned, spam, etc.
    error_message = Column(Text)
    duration_ms = Column(Integer)          # round-trip time in milliseconds
    attempt_number = Column(Integer, default=1)
    action_taken = Column(String(50))      # retry, skip, pause
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    campaign = relationship("Campaign")
    client = relationship("Client")


class FailedMessage(Base):
    """Retry queue for failed broadcast messages."""
    __tablename__ = "failed_messages"

    id = Column(BigInteger, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    group_target = Column(String(255), nullable=False)
    account_name = Column(String(255))
    error_type = Column(String(100))
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    next_retry_at = Column(DateTime(timezone=True))
    is_dead_letter = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    campaign = relationship("Campaign")
    client = relationship("Client")


class SafetyAlert(Base):
    """Safety alerts and admin notifications."""
    __tablename__ = "safety_alerts"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    alert_type = Column(String(100), nullable=False)  # ban_detected, success_rate_drop, campaign_stuck, etc.
    severity = Column(String(20), default="warning")  # warning, critical
    message = Column(Text, nullable=False)
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    campaign = relationship("Campaign")
    client = relationship("Client")


class ClientBroadcastStats(Base):
    """Per-client aggregated broadcast statistics (daily snapshot)."""
    __tablename__ = "client_broadcast_stats"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(DateTime(timezone=True), nullable=False)
    messages_sent = Column(Integer, default=0)
    messages_failed = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    active_campaigns = Column(Integer, default=0)
    accounts_used = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    client = relationship("Client")


# ── Phase 3 Campaign extra columns (added via alembic or create_all) ──────────
# These columns are added to the existing Campaign model:

# Extend Campaign with Phase 3 fields
Campaign.group_verification_status = Column(
    Enum(GroupVerificationStatus),
    default=GroupVerificationStatus.pending,
    nullable=True,
)
Campaign.safety_flags = Column(JSON, default=dict)
Campaign.error_count = Column(Integer, default=0)
Campaign.last_error_message = Column(Text, nullable=True)
Campaign.failed_groups_log = Column(JSON, default=list)
Campaign.account_group_id = Column(
    Integer, ForeignKey("account_groups_v2.id", ondelete="SET NULL"), nullable=True
)
Campaign.jitter_pct = Column(Float, default=10.0)   # ± percent jitter on delay
Campaign.max_per_hour = Column(Integer, default=100)
Campaign.max_per_day = Column(Integer, default=500)
Campaign.rotate_every = Column(Integer, default=20)  # rotate account every N messages
Campaign.link_url = Column(String(512), nullable=True)
Campaign.timing_start = Column(String(8), nullable=True)   # "08:00"
Campaign.timing_end = Column(String(8), nullable=True)     # "22:00"


# ── License & Webhook Tables ──────────────────────────────────────────────────

class LicenseTier(str, enum.Enum):
    starter = "starter"
    pro = "pro"
    enterprise = "enterprise"


class LicenseStatus(str, enum.Enum):
    active = "active"
    expired = "expired"
    revoked = "revoked"


class License(Base):
    """License key that can be assigned to a client."""
    __tablename__ = "licenses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(64), unique=True, nullable=False, index=True)
    tier = Column(Enum(LicenseTier), default=LicenseTier.starter)
    status = Column(Enum(LicenseStatus), default=LicenseStatus.active)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    max_accounts = Column(Integer, default=5)
    max_campaigns = Column(Integer, default=10)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    client = relationship("Client", backref="licenses")


class Webhook(Base):
    """Outgoing webhook subscriptions for a client."""
    __tablename__ = "webhooks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    url = Column(String(500), nullable=False)
    events = Column(JSON, default=list)
    secret = Column(String(64), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    client = relationship("Client", backref="webhooks")
