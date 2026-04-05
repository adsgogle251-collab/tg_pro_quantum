"""
TG PRO QUANTUM – Smoke Tests: Integration Scenarios
Validates multi-client isolation, account rotation, group verification,
safety features, and error recovery paths.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import (
    Campaign, CampaignStatus, CampaignMode,
    AccountGroupFeatureType, AccountGroupStatus,
    AccountStatus, GroupAnalytics,
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


class TestSmokeMultiClientIsolation:
    """Validates that clients cannot see each other's data."""

    @pytest.mark.asyncio
    async def test_clients_cannot_see_each_others_campaigns(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Client A's campaigns are not visible to Client B."""
        client_a = await create_test_client(db_session, "mci_a1")
        client_b = await create_test_client(db_session, "mci_b1")

        camp_a = await create_test_campaign(db_session, client_a, name="Campaign A")
        camp_b = await create_test_campaign(db_session, client_b, name="Campaign B")

        headers_a = make_auth_headers(client_a)
        headers_b = make_auth_headers(client_b)

        # A fetches own campaign → should succeed
        r = await client.get(f"/api/v1/campaigns/{camp_a.id}", headers=headers_a)
        assert r.status_code == 200

        # A tries to access B's campaign → should be forbidden
        r = await client.get(f"/api/v1/campaigns/{camp_b.id}", headers=headers_a)
        assert r.status_code in (403, 404)

        # B fetches own campaign → should succeed
        r = await client.get(f"/api/v1/campaigns/{camp_b.id}", headers=headers_b)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_clients_cannot_see_each_others_accounts(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Client A cannot list accounts belonging to Client B."""
        client_a = await create_test_client(db_session, "mci_a2")
        client_b = await create_test_client(db_session, "mci_b2")

        await create_test_account(db_session, client_b, phone="+60123456789")

        headers_a = make_auth_headers(client_a)
        r = await client.get("/api/v1/accounts/", headers=headers_a)
        assert r.status_code == 200
        accounts = r.json()
        # None of Client B's accounts should appear in Client A's list
        for acc in accounts:
            assert acc.get("client_id") != client_b.id

    @pytest.mark.asyncio
    async def test_three_clients_isolated(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Three clients' campaigns are fully isolated from each other."""
        clients = [
            await create_test_client(db_session, f"mci3_{i}") for i in range(3)
        ]
        campaigns = [
            await create_test_campaign(db_session, c, name=f"Camp3_{i}")
            for i, c in enumerate(clients)
        ]

        for i, owner in enumerate(clients):
            headers = make_auth_headers(owner)
            # Can access own campaign
            r = await client.get(f"/api/v1/campaigns/{campaigns[i].id}", headers=headers)
            assert r.status_code == 200
            # Cannot access others'
            for j, other_camp in enumerate(campaigns):
                if j != i:
                    r = await client.get(f"/api/v1/campaigns/{other_camp.id}", headers=headers)
                    assert r.status_code in (403, 404)


class TestSmokeGroupVerification:
    """Validates that groups are stored and retrieved correctly."""

    @pytest.mark.asyncio
    async def test_create_and_list_groups(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Client can create and list groups."""
        c = await create_test_client(db_session, "gv_smoke1")
        headers = make_auth_headers(c)

        await create_test_group(db_session, c, username="testgroup_smoke")

        r = await client.get("/api/v1/groups/", headers=headers)
        assert r.status_code == 200
        groups = r.json()
        assert any(g["username"] == "testgroup_smoke" for g in groups)

    @pytest.mark.asyncio
    async def test_group_belongs_to_correct_client(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Group created for Client A is not visible to Client B."""
        client_a = await create_test_client(db_session, "gv_a1")
        client_b = await create_test_client(db_session, "gv_b1")

        await create_test_group(db_session, client_a, username="group_for_a")

        headers_b = make_auth_headers(client_b)
        r = await client.get("/api/v1/groups/", headers=headers_b)
        assert r.status_code == 200
        groups = r.json()
        assert not any(g["username"] == "group_for_a" for g in groups)


class TestSmokeSafetyFeatures:
    """Validates safety-related campaign settings are persisted."""

    @pytest.mark.asyncio
    async def test_campaign_stores_jitter_settings(self, db_session: AsyncSession):
        """Campaign stores delay_min and delay_max (jitter) correctly."""
        c = await create_test_client(db_session, "sf_jitter1")
        campaign = await create_test_campaign(db_session, c, name="Jitter Test")

        # Default jitter from conftest: 27-33s
        assert campaign.delay_min == 27.0
        assert campaign.delay_max == 33.0

    @pytest.mark.asyncio
    async def test_campaign_custom_delay_persists(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Campaign created via API preserves custom delay range."""
        c = await create_test_client(db_session, "sf_delay1")
        headers = make_auth_headers(c)

        payload = {
            "name": "Custom Delay Campaign",
            "message_text": "Safety test",
            "mode": "once",
            "delay_min": 27.0,
            "delay_max": 33.0,
        }
        r = await client.post("/api/v1/campaigns/", json=payload, headers=headers)
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["delay_min"] == 27.0
        assert data["delay_max"] == 33.0

    @pytest.mark.asyncio
    async def test_account_health_score_tracked(self, db_session: AsyncSession):
        """Telegram account has a health_score field."""
        c = await create_test_client(db_session, "sf_health1")
        account = await create_test_account(db_session, c, phone="+19990001111")
        assert account.health_score is not None
        assert 0.0 <= account.health_score <= 100.0


class TestSmokeErrorRecovery:
    """Validates graceful error handling and recovery patterns."""

    @pytest.mark.asyncio
    async def test_404_for_nonexistent_campaign(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """GET /api/v1/campaigns/999999 returns 404."""
        c = await create_test_client(db_session, "er_smoke1")
        headers = make_auth_headers(c)
        r = await client.get("/api/v1/campaigns/999999", headers=headers)
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_json_returns_422(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Sending invalid JSON to campaign create returns 422."""
        c = await create_test_client(db_session, "er_smoke2")
        headers = make_auth_headers(c)
        r = await client.post(
            "/api/v1/campaigns/",
            content=b"not-json",
            headers={**headers, "Content-Type": "application/json"},
        )
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_required_fields_returns_422(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Campaign creation without required fields returns 422."""
        c = await create_test_client(db_session, "er_smoke3")
        headers = make_auth_headers(c)
        r = await client.post("/api/v1/campaigns/", json={}, headers=headers)
        assert r.status_code == 422
