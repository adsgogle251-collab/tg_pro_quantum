"""
TG PRO QUANTUM – Smoke Tests: Core Features
Validates the primary business workflows: account groups, clients,
campaigns, and broadcast operations.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import (
    CampaignStatus,
    AccountGroupFeatureType,
)
from tests.conftest import (
    create_test_admin,
    create_test_client,
    create_test_account,
    create_test_campaign,
    create_test_group,
    create_test_account_group,
    make_auth_headers,
)


class TestSmokeAccountGroupManagement:
    """Smoke test: account group CRUD via API."""

    @pytest.mark.asyncio
    async def test_create_account_group(self, client: AsyncClient, db_session: AsyncSession):
        """Admin can create an account group via the API."""
        admin = await create_test_admin(db_session, "ag_smoke1")
        headers = make_auth_headers(admin)

        payload = {
            "name": "Smoke_Broadcast_Group",
            "feature_type": "broadcast",
            "config": {"max_per_hour": 60},
        }
        response = await client.post("/api/v1/account-groups/", json=payload, headers=headers)
        assert response.status_code in (200, 201)
        data = response.json()
        assert data["name"] == "Smoke_Broadcast_Group"

    @pytest.mark.asyncio
    async def test_list_account_groups(self, client: AsyncClient, db_session: AsyncSession):
        """Admin can list account groups."""
        admin = await create_test_admin(db_session, "ag_smoke2")
        headers = make_auth_headers(admin)

        # Create one via ORM helper to guarantee existence
        await create_test_account_group(db_session, admin, name="ListGroup_Smoke")

        response = await client.get("/api/v1/account-groups/", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_account_group_by_id(self, client: AsyncClient, db_session: AsyncSession):
        """Admin can retrieve a single account group by ID."""
        admin = await create_test_admin(db_session, "ag_smoke3")
        headers = make_auth_headers(admin)
        ag = await create_test_account_group(db_session, admin, name="GetGroup_Smoke")

        response = await client.get(f"/api/v1/account-groups/{ag.id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == ag.id


class TestSmokeClientManagement:
    """Smoke test: client CRUD via API."""

    @pytest.mark.asyncio
    async def test_create_client(self, client: AsyncClient, db_session: AsyncSession):
        """Admin can create a new client via API."""
        admin = await create_test_admin(db_session, "cl_smoke1")
        headers = make_auth_headers(admin)

        payload = {
            "name": "SmokeClient",
            "email": "smoke_client_new@test.com",
            "password": "SecurePass123!",
            "plan_type": "pro",
        }
        response = await client.post("/api/v1/clients/", json=payload, headers=headers)
        assert response.status_code in (200, 201)
        data = response.json()
        assert data["email"] == "smoke_client_new@test.com"

    @pytest.mark.asyncio
    async def test_list_clients_as_admin(self, client: AsyncClient, db_session: AsyncSession):
        """Admin can list all clients."""
        admin = await create_test_admin(db_session, "cl_smoke2")
        headers = make_auth_headers(admin)
        response = await client.get("/api/v1/clients/", headers=headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_client_has_api_key(self, client: AsyncClient, db_session: AsyncSession):
        """Created client must have an API key."""
        admin = await create_test_admin(db_session, "cl_smoke3")
        headers = make_auth_headers(admin)

        payload = {
            "name": "APIKeyClient",
            "email": "apikey_smoke@test.com",
            "password": "SecurePass123!",
            "plan_type": "starter",
        }
        response = await client.post("/api/v1/clients/", json=payload, headers=headers)
        assert response.status_code in (200, 201)
        data = response.json()
        assert data.get("api_key")


class TestSmokeCampaignManagement:
    """Smoke test: campaign lifecycle."""

    @pytest.mark.asyncio
    async def test_create_campaign(self, client: AsyncClient, db_session: AsyncSession):
        """Client can create a broadcast campaign via API."""
        c = await create_test_client(db_session, "camp_smoke1")
        headers = make_auth_headers(c)

        payload = {
            "name": "Smoke Campaign",
            "message_text": "Hello from smoke test!",
            "mode": "once",
            "delay_min": 27.0,
            "delay_max": 33.0,
        }
        response = await client.post("/api/v1/campaigns/", json=payload, headers=headers)
        assert response.status_code in (200, 201)
        data = response.json()
        assert data["name"] == "Smoke Campaign"
        assert data["status"] == "draft"

    @pytest.mark.asyncio
    async def test_list_campaigns(self, client: AsyncClient, db_session: AsyncSession):
        """Client can list their campaigns."""
        c = await create_test_client(db_session, "camp_smoke2")
        headers = make_auth_headers(c)
        await create_test_campaign(db_session, c, name="Smoke List Camp")

        response = await client.get("/api/v1/campaigns/", headers=headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_get_campaign_status(self, client: AsyncClient, db_session: AsyncSession):
        """Client can retrieve a campaign and check its status field."""
        c = await create_test_client(db_session, "camp_smoke3")
        headers = make_auth_headers(c)
        campaign = await create_test_campaign(db_session, c, name="Status Check")

        response = await client.get(f"/api/v1/campaigns/{campaign.id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == CampaignStatus.draft.value

    @pytest.mark.asyncio
    async def test_campaign_response_schema(self, client: AsyncClient, db_session: AsyncSession):
        """Campaign response must include required schema fields."""
        c = await create_test_client(db_session, "camp_smoke4")
        headers = make_auth_headers(c)
        campaign = await create_test_campaign(db_session, c, name="Schema Check")

        response = await client.get(f"/api/v1/campaigns/{campaign.id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        required_fields = {"id", "name", "status", "message_text", "sent_count", "failed_count"}
        assert required_fields.issubset(data.keys())


class TestSmokeBroadcastWorkflow:
    """Smoke test: broadcast start/stop operations."""

    @pytest.mark.asyncio
    async def test_start_broadcast_requires_groups(self, client: AsyncClient, db_session: AsyncSession):
        """Starting a broadcast without groups returns 400/422."""
        c = await create_test_client(db_session, "bc_smoke1")
        headers = make_auth_headers(c)
        campaign = await create_test_campaign(db_session, c, name="No Groups")

        response = await client.post(
            f"/api/v1/broadcasts/{campaign.id}/start",
            headers=headers,
        )
        # No groups → should fail gracefully (not 500)
        assert response.status_code in (400, 404, 422)

    @pytest.mark.asyncio
    async def test_stop_nonexistent_broadcast_graceful(self, client: AsyncClient, db_session: AsyncSession):
        """Stopping a non-running campaign returns a safe error code."""
        c = await create_test_client(db_session, "bc_smoke2")
        headers = make_auth_headers(c)
        campaign = await create_test_campaign(db_session, c, name="Not Running")

        response = await client.post(
            f"/api/v1/broadcasts/{campaign.id}/stop",
            headers=headers,
        )
        assert response.status_code in (400, 404, 409, 422)

    @pytest.mark.asyncio
    async def test_campaign_isolation_between_clients(self, client: AsyncClient, db_session: AsyncSession):
        """Client A cannot access Client B's campaign."""
        client_a = await create_test_client(db_session, "iso_smoke1")
        client_b = await create_test_client(db_session, "iso_smoke2")
        campaign_b = await create_test_campaign(db_session, client_b, name="Private Campaign B")

        headers_a = make_auth_headers(client_a)
        response = await client.get(f"/api/v1/campaigns/{campaign_b.id}", headers=headers_a)
        assert response.status_code in (403, 404)
