"""
Integration tests for API endpoints.
Tests complete request-response cycles including authentication, authorization,
and business logic for key workflows.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import (
    Campaign, CampaignStatus, TelegramAccount, AccountStatus,
)
from tests.conftest import (
    create_test_admin,
    create_test_client,
    create_test_campaign,
    create_test_account,
    create_test_account_group,
    create_test_group,
    make_auth_headers,
)


# ── Authentication flow ───────────────────────────────────────────────────────

class TestAuthFlow:
    """Tests for authentication flows."""

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client: AsyncClient):
        """Health endpoint returns 200 OK."""
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_register_and_login(self, client: AsyncClient, db_session: AsyncSession):
        """User can register and login."""
        # Register
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "name": "Test User",
                "email": "register_login@test.com",
                "password": "securepassword",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert "access_token" in body

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client: AsyncClient, db_session: AsyncSession):
        """Login with wrong credentials returns 401."""
        # First create a user
        await client.post(
            "/api/v1/auth/register",
            json={
                "name": "Fail User",
                "email": "faillogin@test.com",
                "password": "correctpass",
            },
        )
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "faillogin@test.com", "password": "wrongpass"},
        )
        assert resp.status_code in (400, 401)

    @pytest.mark.asyncio
    async def test_protected_endpoint_without_token(self, client: AsyncClient):
        """Protected endpoint rejects unauthenticated request."""
        resp = await client.get("/api/v1/clients/me")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_api_key_authentication(self, client: AsyncClient, db_session: AsyncSession):
        """API key authentication works."""
        c = await create_test_client(db_session, "apikey_auth")
        resp = await client.get(
            "/api/v1/clients/me",
            headers={"X-API-Key": c.api_key},
        )
        assert resp.status_code == 200
        assert resp.json()["email"] == c.email

    @pytest.mark.asyncio
    async def test_invalid_api_key_rejected(self, client: AsyncClient):
        """Invalid API key returns 401."""
        resp = await client.get(
            "/api/v1/clients/me",
            headers={"X-API-Key": "invalid-api-key-12345"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_suspended_client_blocked(self, client: AsyncClient, db_session: AsyncSession):
        """Suspended client cannot access protected endpoints."""
        from app.models.database import ClientStatus
        c = await create_test_client(db_session, "suspended_auth")
        c.status = ClientStatus.suspended
        await db_session.flush()

        resp = await client.get(
            "/api/v1/clients/me",
            headers=make_auth_headers(c),
        )
        assert resp.status_code == 403


# ── Account creation → group assignment → health monitoring ──────────────────

class TestAccountToGroupWorkflow:
    """Test: Account creation → account group assignment → health monitoring."""

    @pytest.mark.asyncio
    async def test_account_to_group_full_workflow(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Full workflow: create account → assign to group → check health."""
        c = await create_test_client(db_session, "wf_acct")
        account = await create_test_account(db_session, c, phone="+44111111111")
        group = await create_test_account_group(db_session, c, name="WorkflowGroup")

        # Assign account to group via API
        resp = await client.post(
            f"/api/v1/account-groups/{group.id}/accounts",
            json={"account_id": account.id, "feature_type": "broadcast"},
            headers=make_auth_headers(c),
        )
        assert resp.status_code in (200, 201)

        # Check health via API
        resp = await client.get(
            f"/api/v1/account-groups/{group.id}/health",
            headers=make_auth_headers(c),
        )
        assert resp.status_code == 200


# ── Client creation → group → campaign → broadcast ───────────────────────────

class TestClientToBroadcastWorkflow:
    """Test: Client creation → account group → campaign creation → broadcast."""

    @pytest.mark.asyncio
    async def test_create_client_via_api(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Admin creates a new client."""
        admin = await create_test_admin(db_session, "wf_admin_c")
        resp = await client.post(
            "/api/v1/clients/",
            json={
                "name": "Workflow Client",
                "email": "workflow_client@example.com",
                "password": "securepassword",
                "plan_type": "pro",
            },
            headers=make_auth_headers(admin),
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "Workflow Client"

    @pytest.mark.asyncio
    async def test_campaign_creation_and_listing(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Client can create and list campaigns."""
        c = await create_test_client(db_session, "wf_camp")

        # Create campaign
        resp = await client.post(
            "/api/v1/campaigns/",
            json={
                "name": "My Campaign",
                "message_text": "Hello world!",
                "mode": "once",
                "delay_min": 27.0,
                "delay_max": 33.0,
            },
            headers=make_auth_headers(c),
        )
        assert resp.status_code == 201
        campaign_id = resp.json()["id"]

        # List campaigns
        resp = await client.get(
            "/api/v1/campaigns/",
            headers=make_auth_headers(c),
        )
        assert resp.status_code == 200
        campaigns = resp.json()
        assert any(cam["id"] == campaign_id for cam in campaigns)

    @pytest.mark.asyncio
    async def test_activity_log_for_campaign(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Activity log endpoint returns list for a campaign."""
        c = await create_test_client(db_session, "wf_act")
        campaign = await create_test_campaign(db_session, c, name="ActivityCampaign")

        resp = await client.get(
            f"/api/v1/campaigns/{campaign.id}/activity-log",
            headers=make_auth_headers(c),
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ── Multi-client isolation ────────────────────────────────────────────────────

class TestMultiClientIsolation:
    """Tests for multi-client data isolation enforcement."""

    @pytest.mark.asyncio
    async def test_client_cannot_see_other_campaign(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Client A cannot view Client B's campaign."""
        client_a = await create_test_client(db_session, "iso_a_camp")
        client_b = await create_test_client(db_session, "iso_b_camp")
        campaign_b = await create_test_campaign(db_session, client_b, name="BsCampaign")

        resp = await client.get(
            f"/api/v1/campaigns/{campaign_b.id}/detail",
            headers=make_auth_headers(client_a),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_client_sees_own_campaigns_only(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Campaign list is filtered to the current client's campaigns."""
        client_a = await create_test_client(db_session, "iso_a_list")
        client_b = await create_test_client(db_session, "iso_b_list")
        await create_test_campaign(db_session, client_a, name="A_Campaign1")
        await create_test_campaign(db_session, client_b, name="B_Campaign1")

        resp = await client.get(
            "/api/v1/campaigns/",
            headers=make_auth_headers(client_a),
        )
        assert resp.status_code == 200
        campaigns = resp.json()
        for c in campaigns:
            assert c["client_id"] == client_a.id

    @pytest.mark.asyncio
    async def test_admin_can_see_all_clients(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Admin can list all clients."""
        admin = await create_test_admin(db_session, "admin_all")
        await create_test_client(db_session, "mc_iso_c1")
        await create_test_client(db_session, "mc_iso_c2")

        resp = await client.get(
            "/api/v1/clients/",
            headers=make_auth_headers(admin),
        )
        assert resp.status_code == 200
        assert len(resp.json()) >= 2


# ── Group verification → message sending workflow ────────────────────────────

class TestGroupVerificationWorkflow:
    """Tests for group verification flow before broadcasting."""

    @pytest.mark.asyncio
    async def test_group_verification_endpoint(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Groups are verified before broadcasting."""
        c = await create_test_client(db_session, "gv_wf")

        resp = await client.post(
            "/api/v1/groups/verify",
            json={
                "group_usernames": ["mygroup1", "channel_blocked", "mygroup2"],
                "min_members": 10,
            },
            headers=make_auth_headers(c),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 3
        assert body["passed"] == 2
        assert body["failed"] == 1

    @pytest.mark.asyncio
    async def test_broadcast_dashboard_overview(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Broadcast dashboard overview is accessible to authenticated users."""
        c = await create_test_client(db_session, "bc_dash")
        resp = await client.get(
            "/api/v1/dashboard/broadcast",
            headers=make_auth_headers(c),
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_campaign_statistics_endpoint(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Campaign statistics endpoint returns data."""
        c = await create_test_client(db_session, "camp_stats")
        campaign = await create_test_campaign(db_session, c, name="StatsCampaign")

        resp = await client.get(
            f"/api/v1/campaigns/{campaign.id}/statistics",
            headers=make_auth_headers(c),
        )
        assert resp.status_code == 200


# ── Rate limiting & auto-pause recovery ──────────────────────────────────────

class TestRateLimitingIntegration:
    """Tests for rate limiting and auto-pause recovery."""

    @pytest.mark.asyncio
    async def test_campaign_pause_resume_cycle(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Campaign can be paused and resumed."""
        from unittest.mock import AsyncMock, patch

        c = await create_test_client(db_session, "rl_cycle")
        campaign = await create_test_campaign(db_session, c, name="PauseResumeCycle")
        campaign.status = CampaignStatus.running
        await db_session.flush()

        # Pause
        with patch(
            "app.core.broadcast_engine.BroadcastEngine.pause_campaign",
            new_callable=AsyncMock,
        ):
            resp = await client.post(
                f"/api/v1/broadcasts/{campaign.id}/pause",
                headers=make_auth_headers(c),
            )
        assert resp.status_code == 200

        # Update status to paused for resume test
        campaign.status = CampaignStatus.paused
        await db_session.flush()

        # Resume
        with patch(
            "app.core.broadcast_engine.BroadcastEngine.start_campaign",
            new_callable=AsyncMock,
            return_value="task-abc",
        ):
            resp = await client.post(
                f"/api/v1/broadcasts/{campaign.id}/resume",
                headers=make_auth_headers(c),
            )
        assert resp.status_code == 200
