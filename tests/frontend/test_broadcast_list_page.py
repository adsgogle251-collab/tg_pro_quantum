"""
Frontend unit tests for Broadcast List page.
Tests campaign list rendering, client filtering, status filtering,
search functionality, and multi-client isolation.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import CampaignStatus
from tests.conftest import (
    create_test_admin,
    create_test_client,
    create_test_campaign,
    make_auth_headers,
)


class TestBroadcastListRendering:
    """Tests for broadcast list page rendering."""

    @pytest.mark.asyncio
    async def test_campaigns_list_returns_list(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Campaigns list endpoint returns a list."""
        c = await create_test_client(db_session, "bl_list")
        for i in range(3):
            await create_test_campaign(db_session, c, name=f"Campaign_{i}")

        resp = await client.get(
            "/api/v1/campaigns/",
            headers=make_auth_headers(c),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 3

    @pytest.mark.asyncio
    async def test_campaigns_list_item_structure(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Each campaign list item has required fields."""
        c = await create_test_client(db_session, "bl_struct")
        await create_test_campaign(db_session, c, name="StructCampaign")

        resp = await client.get(
            "/api/v1/campaigns/",
            headers=make_auth_headers(c),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        item = data[0]
        assert "id" in item
        assert "name" in item
        assert "status" in item
        assert "sent_count" in item
        assert "client_id" in item


class TestClientFiltering:
    """Tests for client-based filtering of campaigns."""

    @pytest.mark.asyncio
    async def test_non_admin_sees_own_campaigns_only(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Non-admin sees only their own campaigns."""
        c1 = await create_test_client(db_session, "cf_c1")
        c2 = await create_test_client(db_session, "cf_c2")
        await create_test_campaign(db_session, c1, name="C1_Camp1")
        await create_test_campaign(db_session, c1, name="C1_Camp2")
        await create_test_campaign(db_session, c2, name="C2_Camp1")

        resp = await client.get(
            "/api/v1/campaigns/",
            headers=make_auth_headers(c1),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert all(camp["client_id"] == c1.id for camp in data)
        assert not any(camp["client_id"] == c2.id for camp in data)

    @pytest.mark.asyncio
    async def test_admin_can_see_own_campaigns(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Admin can see campaigns assigned to them."""
        admin = await create_test_admin(db_session, "cf_admin")
        camp_admin = await create_test_campaign(db_session, admin, name="Admin_Camp")

        resp = await client.get(
            "/api/v1/campaigns/",
            headers=make_auth_headers(admin),
        )
        assert resp.status_code == 200
        data = resp.json()
        ids = {c["id"] for c in data}
        assert camp_admin.id in ids


class TestStatusFiltering:
    """Tests for campaign status filtering."""

    @pytest.mark.asyncio
    async def test_filter_by_status(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Campaigns can be filtered by status."""
        c = await create_test_client(db_session, "sf_status")
        draft = await create_test_campaign(db_session, c, name="DraftCamp")
        running = await create_test_campaign(db_session, c, name="RunningCamp")
        running.status = CampaignStatus.running
        await db_session.flush()

        resp = await client.get(
            "/api/v1/campaigns/?status=running",
            headers=make_auth_headers(c),
        )
        assert resp.status_code == 200
        data = resp.json()
        for camp in data:
            assert camp["status"] == "running"

    @pytest.mark.asyncio
    async def test_all_statuses_supported(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """All campaign statuses can be queried."""
        c = await create_test_client(db_session, "sf_all")
        for status in ["draft", "running", "paused", "completed"]:
            resp = await client.get(
                f"/api/v1/campaigns/?status={status}",
                headers=make_auth_headers(c),
            )
            assert resp.status_code == 200


class TestMultiClientIsolationList:
    """Tests for multi-client data isolation in broadcast list."""

    @pytest.mark.asyncio
    async def test_campaigns_not_leaked_between_clients(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Campaigns from one client are not visible to another."""
        c1 = await create_test_client(db_session, "mci_c1")
        c2 = await create_test_client(db_session, "mci_c2")
        camp1 = await create_test_campaign(db_session, c1, name="C1Secret")
        camp2 = await create_test_campaign(db_session, c2, name="C2Secret")

        # c1 sees only c1's campaigns
        resp1 = await client.get(
            "/api/v1/campaigns/",
            headers=make_auth_headers(c1),
        )
        ids1 = {c["id"] for c in resp1.json()}
        assert camp1.id in ids1
        assert camp2.id not in ids1

        # c2 sees only c2's campaigns
        resp2 = await client.get(
            "/api/v1/campaigns/",
            headers=make_auth_headers(c2),
        )
        ids2 = {c["id"] for c in resp2.json()}
        assert camp2.id in ids2
        assert camp1.id not in ids2

    @pytest.mark.asyncio
    async def test_campaign_detail_isolated(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Client cannot access another client's campaign detail."""
        c1 = await create_test_client(db_session, "mci_det_c1")
        c2 = await create_test_client(db_session, "mci_det_c2")
        camp_c2 = await create_test_campaign(db_session, c2, name="C2DetailCamp")

        resp = await client.get(
            f"/api/v1/campaigns/{camp_c2.id}/detail",
            headers=make_auth_headers(c1),
        )
        assert resp.status_code == 403
