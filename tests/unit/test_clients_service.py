"""
Unit tests for Client management service / API.
Tests create, update, assign account groups, client isolation, and API key generation.
"""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Client, AccountGroup, ClientStatus, ClientPlan
from app.api.dependencies import hash_password, verify_password
from app.utils.helpers import generate_api_key
from tests.conftest import (
    create_test_admin,
    create_test_client,
    create_test_account_group,
    make_auth_headers,
)


class TestClientService:
    """Unit tests for client creation, updates, and isolation."""

    @pytest.mark.asyncio
    async def test_create_client(self, db_session: AsyncSession):
        """Create a client and check all fields are persisted."""
        c = Client(
            name="New Client",
            email="newclient@test.com",
            hashed_password=hash_password("securepass"),
            api_key=generate_api_key(),
            status=ClientStatus.trial,
            plan_type=ClientPlan.starter,
        )
        db_session.add(c)
        await db_session.flush()
        await db_session.refresh(c)

        assert c.id is not None
        assert c.name == "New Client"
        assert c.email == "newclient@test.com"
        assert c.api_key is not None
        assert len(c.api_key) >= 32
        assert c.status == ClientStatus.trial

    @pytest.mark.asyncio
    async def test_update_client_name_and_plan(self, db_session: AsyncSession):
        """Update client name and plan type."""
        c = await create_test_client(db_session, "upd")
        c.name = "Updated Name"
        c.plan_type = ClientPlan.enterprise
        await db_session.flush()
        await db_session.refresh(c)

        assert c.name == "Updated Name"
        assert c.plan_type == ClientPlan.enterprise

    @pytest.mark.asyncio
    async def test_update_client_status(self, db_session: AsyncSession):
        """Suspend a client."""
        c = await create_test_client(db_session, "suspend")
        c.status = ClientStatus.suspended
        await db_session.flush()
        await db_session.refresh(c)

        assert c.status == ClientStatus.suspended

    @pytest.mark.asyncio
    async def test_assign_account_group_to_client(self, db_session: AsyncSession):
        """Assign an account group to a client."""
        c = await create_test_client(db_session, "assign_ag")
        group = await create_test_account_group(db_session, c, name="ClientPool")

        result = await db_session.execute(
            select(AccountGroup).where(AccountGroup.client_id == c.id)
        )
        groups = result.scalars().all()
        assert any(g.id == group.id for g in groups)

    @pytest.mark.asyncio
    async def test_client_isolation_enforcement(self, db_session: AsyncSession):
        """Clients should not see other clients' data."""
        client_a = await create_test_client(db_session, "ci_a")
        client_b = await create_test_client(db_session, "ci_b")

        group_a = await create_test_account_group(db_session, client_a, name="PoolA")
        group_b = await create_test_account_group(db_session, client_b, name="PoolB")

        result_a = await db_session.execute(
            select(AccountGroup).where(AccountGroup.client_id == client_a.id)
        )
        ids_a = {g.id for g in result_a.scalars().all()}
        assert group_b.id not in ids_a

    @pytest.mark.asyncio
    async def test_api_key_generation_unique(self, db_session: AsyncSession):
        """Each client gets a unique API key."""
        keys = {generate_api_key() for _ in range(100)}
        assert len(keys) == 100

    @pytest.mark.asyncio
    async def test_api_key_length(self):
        """API key meets minimum length requirement."""
        key = generate_api_key()
        assert len(key) >= 32

    @pytest.mark.asyncio
    async def test_password_hashing(self):
        """Password hash is not plaintext and verifies correctly."""
        plain = "MySecureP@ss123"
        hashed = hash_password(plain)
        assert hashed != plain
        assert verify_password(plain, hashed)
        assert not verify_password("wrongpass", hashed)

    @pytest.mark.asyncio
    async def test_duplicate_email_unique_constraint(self, db_session: AsyncSession):
        """Creating two clients with the same email should raise an error."""
        import sqlalchemy.exc
        c1 = Client(
            name="Dup1",
            email="dup@test.com",
            hashed_password=hash_password("pass"),
            api_key=generate_api_key(),
        )
        db_session.add(c1)
        await db_session.flush()

        c2 = Client(
            name="Dup2",
            email="dup@test.com",
            hashed_password=hash_password("pass"),
            api_key=generate_api_key(),
        )
        db_session.add(c2)
        with pytest.raises(Exception):
            await db_session.flush()
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_client_usage_limits(self, db_session: AsyncSession):
        """Verify usage limit fields are stored correctly."""
        c = Client(
            name="LimitedClient",
            email="limited@test.com",
            hashed_password=hash_password("pass"),
            api_key=generate_api_key(),
            usage_limit_monthly=5000,
            current_usage_monthly=0,
        )
        db_session.add(c)
        await db_session.flush()
        await db_session.refresh(c)

        assert c.usage_limit_monthly == 5000
        assert c.current_usage_monthly == 0


class TestClientAPI:
    """API-level tests for client endpoints."""

    @pytest.mark.asyncio
    async def test_list_clients_requires_admin(self, client, db_session):
        """Non-admin cannot list all clients."""
        regular = await create_test_client(db_session, "list_nonadmin")
        resp = await client.get(
            "/api/v1/clients/",
            headers=make_auth_headers(regular),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_list_clients_as_admin(self, client, db_session):
        """Admin can list clients."""
        admin = await create_test_admin(db_session, "list_admin_c")
        resp = await client.get(
            "/api/v1/clients/",
            headers=make_auth_headers(admin),
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_create_client_as_admin(self, client, db_session):
        """Admin can create a new client."""
        admin = await create_test_admin(db_session, "create_cl_api")
        payload = {
            "name": "Brand New Client",
            "email": "brand_new@example.com",
            "password": "securepassword",
            "plan_type": "pro",
        }
        resp = await client.post(
            "/api/v1/clients/",
            json=payload,
            headers=make_auth_headers(admin),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Brand New Client"
        assert "api_key" in body

    @pytest.mark.asyncio
    async def test_get_my_profile(self, client, db_session):
        """Client can retrieve own profile."""
        c = await create_test_client(db_session, "myprofile")
        resp = await client.get(
            "/api/v1/clients/me",
            headers=make_auth_headers(c),
        )
        assert resp.status_code == 200
        assert resp.json()["email"] == c.email

    @pytest.mark.asyncio
    async def test_get_other_client_profile_forbidden(self, client, db_session):
        """Non-admin cannot view another client's profile."""
        c1 = await create_test_client(db_session, "forbidden_c1")
        c2 = await create_test_client(db_session, "forbidden_c2")

        resp = await client.get(
            f"/api/v1/clients/{c2.id}",
            headers=make_auth_headers(c1),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_update_own_profile(self, client, db_session):
        """Client can update their own profile."""
        c = await create_test_client(db_session, "self_upd")
        resp = await client.patch(
            f"/api/v1/clients/{c.id}",
            json={"name": "Self Updated"},
            headers=make_auth_headers(c),
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Self Updated"

    @pytest.mark.asyncio
    async def test_create_client_duplicate_email_conflict(self, client, db_session):
        """Creating a client with a duplicate email returns 409."""
        admin = await create_test_admin(db_session, "dup_email_adm")
        payload = {
            "name": "Client X",
            "email": admin.email,  # same email as admin
            "password": "password123",
        }
        resp = await client.post(
            "/api/v1/clients/",
            json=payload,
            headers=make_auth_headers(admin),
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_unauthenticated_request(self, client):
        """Requests without auth return 401."""
        resp = await client.get("/api/v1/clients/me")
        assert resp.status_code == 401
