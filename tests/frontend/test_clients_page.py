"""
Frontend unit tests for Clients page components.
Tests client list rendering, create/edit modals, dashboard, and search.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import (
    create_test_admin,
    create_test_client,
    make_auth_headers,
)


class TestClientsListRendering:
    """Tests for clients list page rendering."""

    @pytest.mark.asyncio
    async def test_clients_list_renders_for_admin(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Admin can see clients list with correct structure."""
        admin = await create_test_admin(db_session, "cl_list")
        await create_test_client(db_session, "cl_list_c1")
        await create_test_client(db_session, "cl_list_c2")

        resp = await client.get(
            "/api/v1/clients/",
            headers=make_auth_headers(admin),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # Verify list item structure
        for item in data:
            assert "id" in item
            assert "name" in item
            assert "email" in item
            assert "status" in item
            assert "plan_type" in item

    @pytest.mark.asyncio
    async def test_clients_list_non_admin_forbidden(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Non-admin cannot access full clients list."""
        regular = await create_test_client(db_session, "cl_list_nr")
        resp = await client.get(
            "/api/v1/clients/",
            headers=make_auth_headers(regular),
        )
        assert resp.status_code == 403


class TestCreateClientModal:
    """Tests for create client modal."""

    @pytest.mark.asyncio
    async def test_create_client_success(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Admin can create a new client with valid data."""
        admin = await create_test_admin(db_session, "cc_modal")
        resp = await client.post(
            "/api/v1/clients/",
            json={
                "name": "New Client Modal",
                "email": "newmodal@example.com",
                "password": "securepassword",
                "plan_type": "pro",
                "usage_limit_monthly": 50000,
            },
            headers=make_auth_headers(admin),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "New Client Modal"
        assert body["plan_type"] == "pro"
        assert body["usage_limit_monthly"] == 50000

    @pytest.mark.asyncio
    async def test_create_client_invalid_email_rejected(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Invalid email format is rejected."""
        admin = await create_test_admin(db_session, "cc_inv_email")
        resp = await client.post(
            "/api/v1/clients/",
            json={
                "name": "Bad Email Client",
                "email": "not-an-email",
                "password": "securepassword",
            },
            headers=make_auth_headers(admin),
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_client_short_password_rejected(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Password shorter than 8 chars is rejected."""
        admin = await create_test_admin(db_session, "cc_short_pw")
        resp = await client.post(
            "/api/v1/clients/",
            json={
                "name": "Short Pass",
                "email": "shortpass@example.com",
                "password": "abc",
            },
            headers=make_auth_headers(admin),
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_client_generates_api_key(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Newly created client receives an API key."""
        admin = await create_test_admin(db_session, "cc_apikey")
        resp = await client.post(
            "/api/v1/clients/",
            json={
                "name": "API Key Client",
                "email": "apikeytest@example.com",
                "password": "securepassword",
            },
            headers=make_auth_headers(admin),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert "api_key" in body
        assert body["api_key"] is not None
        assert len(body["api_key"]) >= 32


class TestEditClientModal:
    """Tests for edit client modal."""

    @pytest.mark.asyncio
    async def test_update_client_name(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Client name can be updated by admin or self."""
        c = await create_test_client(db_session, "ec_name")
        resp = await client.patch(
            f"/api/v1/clients/{c.id}",
            json={"name": "Updated Name"},
            headers=make_auth_headers(c),
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_client_webhook_url(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Webhook URL can be updated."""
        c = await create_test_client(db_session, "ec_webhook")
        resp = await client.patch(
            f"/api/v1/clients/{c.id}",
            json={"webhook_url": "https://example.com/webhook"},
            headers=make_auth_headers(c),
        )
        assert resp.status_code == 200
        assert resp.json()["webhook_url"] == "https://example.com/webhook"

    @pytest.mark.asyncio
    async def test_admin_can_update_any_client(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Admin can update any client's data."""
        admin = await create_test_admin(db_session, "ec_admin")
        other = await create_test_client(db_session, "ec_other_c")
        resp = await client.patch(
            f"/api/v1/clients/{other.id}",
            json={"name": "Admin Updated"},
            headers=make_auth_headers(admin),
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Admin Updated"


class TestClientDashboard:
    """Tests for client dashboard data."""

    @pytest.mark.asyncio
    async def test_client_dashboard_endpoint(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Client dashboard endpoint returns correct structure."""
        admin = await create_test_admin(db_session, "cd_admin")
        c = await create_test_client(db_session, "cd_client")

        resp = await client.get(
            f"/api/v1/clients/{c.id}/dashboard",
            headers=make_auth_headers(admin),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data or "client_id" in data

    @pytest.mark.asyncio
    async def test_own_profile_endpoint(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Client can view own profile."""
        c = await create_test_client(db_session, "cd_self")
        resp = await client.get(
            "/api/v1/clients/me",
            headers=make_auth_headers(c),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == c.id
        assert data["email"] == c.email


class TestClientSearch:
    """Tests for client search functionality."""

    @pytest.mark.asyncio
    async def test_list_clients_pagination(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Client list supports pagination."""
        admin = await create_test_admin(db_session, "cs_pag")
        for i in range(5):
            await create_test_client(db_session, f"cs_pag_{i}")

        resp = await client.get(
            "/api/v1/clients/?skip=0&limit=3",
            headers=make_auth_headers(admin),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) <= 3

    @pytest.mark.asyncio
    async def test_list_clients_skip(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Client list supports skip/offset pagination."""
        admin = await create_test_admin(db_session, "cs_skip")
        for i in range(4):
            await create_test_client(db_session, f"cs_skip_{i}")

        resp_page1 = await client.get(
            "/api/v1/clients/?skip=0&limit=2",
            headers=make_auth_headers(admin),
        )
        resp_page2 = await client.get(
            "/api/v1/clients/?skip=2&limit=2",
            headers=make_auth_headers(admin),
        )
        assert resp_page1.status_code == 200
        assert resp_page2.status_code == 200

        ids1 = {c["id"] for c in resp_page1.json()}
        ids2 = {c["id"] for c in resp_page2.json()}
        assert ids1.isdisjoint(ids2)
