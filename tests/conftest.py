"""
TG PRO QUANTUM - Shared Test Fixtures

Uses an in-memory SQLite database (via aiosqlite) so tests run without
a live PostgreSQL instance.  All async fixtures use pytest-asyncio.
"""
from __future__ import annotations

import os
import sys

# Ensure the project root is on sys.path so `app.*` imports work.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ── Override DATABASE_URL before any app module is imported ──────────────────
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-at-least-32-chars!!")
os.environ.setdefault("DEBUG", "false")

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

# Import app *after* env vars are set
from app.database import Base, get_db
from app.main import app
from app.models.database import (
    Client, TelegramAccount, Campaign, Group,
    AccountGroup, AccountAssignment, AccountHealth, GroupAnalytics,
    AccountStatus, CampaignStatus, CampaignMode, ClientStatus, ClientPlan,
    AccountGroupFeatureType, AccountGroupStatus,
)
from app.api.dependencies import hash_password
from app.utils.helpers import generate_api_key

# ── Test database engine ──────────────────────────────────────────────────────

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Session-scoped table creation ─────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    """Create all tables once per test session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ── Per-test DB session ───────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db_session(create_tables) -> AsyncSession:
    """Provide a fresh transactional DB session; rolls back after each test."""
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


# ── FastAPI test client ───────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncClient:
    """HTTP test client wired to the FastAPI app with the in-memory DB."""

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ── Seed helpers ──────────────────────────────────────────────────────────────

async def create_test_admin(db: AsyncSession, suffix: str = "") -> Client:
    """Create and persist an admin Client."""
    admin = Client(
        name=f"Admin{suffix}",
        email=f"admin{suffix}@test.com",
        hashed_password=hash_password("adminpass"),
        api_key=generate_api_key(),
        is_admin=True,
        status=ClientStatus.active,
        plan_type=ClientPlan.enterprise,
    )
    db.add(admin)
    await db.flush()
    await db.refresh(admin)
    return admin


async def create_test_client(db: AsyncSession, suffix: str = "") -> Client:
    """Create and persist a regular (non-admin) Client."""
    c = Client(
        name=f"TestClient{suffix}",
        email=f"client{suffix}@test.com",
        hashed_password=hash_password("clientpass"),
        api_key=generate_api_key(),
        is_admin=False,
        status=ClientStatus.active,
        plan_type=ClientPlan.pro,
    )
    db.add(c)
    await db.flush()
    await db.refresh(c)
    return c


async def create_test_account(
    db: AsyncSession,
    client: Client,
    phone: str = "+10000000001",
) -> TelegramAccount:
    """Create and persist a TelegramAccount."""
    acc = TelegramAccount(
        client_id=client.id,
        name=f"Account {phone}",
        phone=phone,
        status=AccountStatus.active,
        health_score=100.0,
    )
    db.add(acc)
    await db.flush()
    await db.refresh(acc)
    return acc


async def create_test_campaign(
    db: AsyncSession,
    client: Client,
    name: str = "Test Campaign",
) -> Campaign:
    """Create and persist a Campaign."""
    c = Campaign(
        client_id=client.id,
        name=name,
        message_text="Hello, world!",
        status=CampaignStatus.draft,
        mode=CampaignMode.once,
        delay_min=27.0,
        delay_max=33.0,
    )
    db.add(c)
    await db.flush()
    await db.refresh(c)
    return c


async def create_test_group(
    db: AsyncSession,
    client: Client,
    username: str = "testgroup",
) -> Group:
    """Create and persist a Group."""
    g = Group(
        client_id=client.id,
        username=username,
        title=f"Test Group {username}",
        member_count=100,
        is_active=True,
    )
    db.add(g)
    await db.flush()
    await db.refresh(g)
    return g


async def create_test_account_group(
    db: AsyncSession,
    client: Client,
    name: str = "Test Account Group",
    feature_type: AccountGroupFeatureType = AccountGroupFeatureType.broadcast,
) -> AccountGroup:
    """Create and persist an AccountGroup."""
    ag = AccountGroup(
        name=name,
        feature_type=feature_type,
        status=AccountGroupStatus.active,
        client_id=client.id,
        config={"max_per_hour": 100},
    )
    db.add(ag)
    await db.flush()
    await db.refresh(ag)
    return ag


# ── JWT token helper ──────────────────────────────────────────────────────────

def make_auth_headers(client_obj: Client) -> dict:
    """Return Authorization headers for the given client."""
    from app.api.dependencies import create_access_token
    token = create_access_token(client_obj.id, is_admin=client_obj.is_admin)
    return {"Authorization": f"Bearer {token}"}
