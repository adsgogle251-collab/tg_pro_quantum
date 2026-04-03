import enum
from datetime import datetime
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    super_admin = "super_admin"


class AccountStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    banned = "banned"
    limited = "limited"


class GroupType(str, enum.Enum):
    group = "group"
    channel = "channel"


class CampaignStatus(str, enum.Enum):
    draft = "draft"
    scheduled = "scheduled"
    running = "running"
    paused = "paused"
    completed = "completed"
    failed = "failed"


class BroadcastMode(str, enum.Enum):
    immediate = "immediate"
    scheduled = "scheduled"
    loop = "loop"
    round_robin = "round_robin"


class MessageType(str, enum.Enum):
    text = "text"
    photo = "photo"
    video = "video"
    document = "document"


class QueueStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    sent = "sent"
    failed = "failed"
    skipped = "skipped"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), default=UserRole.admin, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    clients: Mapped[list["Client"]] = relationship("Client", back_populates="user")


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=True)
    api_key: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    plan: Mapped[str] = mapped_column(String(50), default="basic", nullable=False)
    max_accounts: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="clients")
    accounts: Mapped[list["TelegramAccount"]] = relationship(
        "TelegramAccount", back_populates="client"
    )
    groups: Mapped[list["TelegramGroup"]] = relationship(
        "TelegramGroup", back_populates="client"
    )
    campaigns: Mapped[list["Campaign"]] = relationship(
        "Campaign", back_populates="client"
    )


class TelegramAccount(Base):
    __tablename__ = "telegram_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    client_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    account_name: Mapped[str] = mapped_column(String(255), nullable=True)
    session_data: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[AccountStatus] = mapped_column(
        Enum(AccountStatus), default=AccountStatus.pending, nullable=False
    )
    api_id: Mapped[int] = mapped_column(Integer, nullable=True)
    api_hash: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    client: Mapped["Client"] = relationship("Client", back_populates="accounts")
    verifications: Mapped[list["AccountVerification"]] = relationship(
        "AccountVerification", back_populates="account"
    )
    campaign_accounts: Mapped[list["CampaignAccount"]] = relationship(
        "CampaignAccount", back_populates="account"
    )


class AccountVerification(Base):
    __tablename__ = "account_verifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("telegram_accounts.id", ondelete="CASCADE"), nullable=False
    )
    otp_service: Mapped[str] = mapped_column(String(100), default="sms_activate", nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    activation_id: Mapped[str] = mapped_column(String(100), nullable=True)
    otp_code: Mapped[str] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    account: Mapped["TelegramAccount"] = relationship(
        "TelegramAccount", back_populates="verifications"
    )


class TelegramGroup(Base):
    __tablename__ = "telegram_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    client_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    group_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    group_name: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=True)
    member_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    type: Mapped[GroupType] = mapped_column(
        Enum(GroupType), default=GroupType.group, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_join: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (UniqueConstraint("client_id", "group_id", name="uq_client_group"),)

    client: Mapped["Client"] = relationship("Client", back_populates="groups")
    members: Mapped[list["GroupMember"]] = relationship("GroupMember", back_populates="group")
    campaign_groups: Mapped[list["CampaignGroup"]] = relationship(
        "CampaignGroup", back_populates="group"
    )


class GroupMember(Base):
    __tablename__ = "group_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("telegram_groups.id", ondelete="CASCADE"), nullable=False
    )
    telegram_group_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str] = mapped_column(String(255), nullable=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=True)
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    group: Mapped["TelegramGroup"] = relationship("TelegramGroup", back_populates="members")


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    client_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus), default=CampaignStatus.draft, nullable=False
    )
    broadcast_mode: Mapped[BroadcastMode] = mapped_column(
        Enum(BroadcastMode), default=BroadcastMode.immediate, nullable=False
    )
    delay_min: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    delay_max: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    max_messages_per_hour: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    loop_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_loop_infinite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    client: Mapped["Client"] = relationship("Client", back_populates="campaigns")
    campaign_accounts: Mapped[list["CampaignAccount"]] = relationship(
        "CampaignAccount", back_populates="campaign"
    )
    campaign_groups: Mapped[list["CampaignGroup"]] = relationship(
        "CampaignGroup", back_populates="campaign"
    )
    messages: Mapped[list["CampaignMessage"]] = relationship(
        "CampaignMessage", back_populates="campaign", order_by="CampaignMessage.order_index"
    )
    queue_items: Mapped[list["BroadcastQueue"]] = relationship(
        "BroadcastQueue", back_populates="campaign"
    )
    history: Mapped[list["BroadcastHistory"]] = relationship(
        "BroadcastHistory", back_populates="campaign"
    )
    analytics: Mapped["CampaignAnalytics"] = relationship(
        "CampaignAnalytics", back_populates="campaign", uselist=False
    )


class CampaignAccount(Base):
    __tablename__ = "campaign_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    campaign_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("telegram_accounts.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    messages_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    messages_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="campaign_accounts")
    account: Mapped["TelegramAccount"] = relationship(
        "TelegramAccount", back_populates="campaign_accounts"
    )


class CampaignGroup(Base):
    __tablename__ = "campaign_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    campaign_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False
    )
    group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("telegram_groups.id", ondelete="CASCADE"), nullable=False
    )
    target_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    messages_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="campaign_groups")
    group: Mapped["TelegramGroup"] = relationship(
        "TelegramGroup", back_populates="campaign_groups"
    )


class CampaignMessage(Base):
    __tablename__ = "campaign_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    campaign_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False
    )
    message_text: Mapped[str] = mapped_column(Text, nullable=True)
    has_media: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    media_path: Mapped[str] = mapped_column(String(500), nullable=True)
    message_type: Mapped[MessageType] = mapped_column(
        Enum(MessageType), default=MessageType.text, nullable=False
    )
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="messages")
    queue_items: Mapped[list["BroadcastQueue"]] = relationship(
        "BroadcastQueue", back_populates="message"
    )
    history_items: Mapped[list["BroadcastHistory"]] = relationship(
        "BroadcastHistory", back_populates="message"
    )


class BroadcastQueue(Base):
    __tablename__ = "broadcast_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    campaign_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("telegram_accounts.id", ondelete="SET NULL"), nullable=True
    )
    group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("telegram_groups.id", ondelete="SET NULL"), nullable=True
    )
    message_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("campaign_messages.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[QueueStatus] = mapped_column(
        Enum(QueueStatus), default=QueueStatus.pending, nullable=False
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="queue_items")
    message: Mapped["CampaignMessage"] = relationship(
        "CampaignMessage", back_populates="queue_items"
    )


class BroadcastHistory(Base):
    __tablename__ = "broadcast_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    campaign_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("telegram_accounts.id", ondelete="SET NULL"), nullable=True
    )
    group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("telegram_groups.id", ondelete="SET NULL"), nullable=True
    )
    message_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("campaign_messages.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="history")
    message: Mapped["CampaignMessage"] = relationship(
        "CampaignMessage", back_populates="history_items"
    )


class CampaignAnalytics(Base):
    __tablename__ = "campaign_analytics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    campaign_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    total_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_pending: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    delivery_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    avg_send_time: Mapped[float] = mapped_column(Float, nullable=True)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="analytics")
