"""
Frontend unit tests for Broadcast Detail page components.
Tests campaign detail rendering, live progress, activity log,
action buttons, and real-time update structures.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import CampaignStatus, CampaignMode
from tests.conftest import (
    create_test_admin,
    create_test_client,
    create_test_campaign,
    make_auth_headers,
)


class TestCampaignDetailRendering:
    """Tests for campaign detail page rendering."""

    @pytest.mark.asyncio
    async def test_campaign_detail_endpoint_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Campaign detail returns all expected fields."""
        c = await create_test_client(db_session, "bd_fields")
        campaign = await create_test_campaign(db_session, c, name="Detail Campaign")

        resp = await client.get(
            f"/api/v1/campaigns/{campaign.id}/detail",
            headers=make_auth_headers(c),
        )
        assert resp.status_code == 200
        data = resp.json()
        # Verify key fields for the detail page
        assert "id" in data
        assert "name" in data
        assert "status" in data
        assert "sent_count" in data
        assert "failed_count" in data
        assert "total_targets" in data

    @pytest.mark.asyncio
    async def test_campaign_detail_not_found(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Non-existent campaign returns 404."""
        c = await create_test_client(db_session, "bd_notfound")
        resp = await client.get(
            "/api/v1/campaigns/99999/detail",
            headers=make_auth_headers(c),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_campaign_detail_forbidden_for_other_client(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Other client's campaign detail returns 403."""
        owner = await create_test_client(db_session, "bd_owner")
        other = await create_test_client(db_session, "bd_other")
        campaign = await create_test_campaign(db_session, owner, name="OwnerCamp")

        resp = await client.get(
            f"/api/v1/campaigns/{campaign.id}/detail",
            headers=make_auth_headers(other),
        )
        assert resp.status_code == 403


class TestLiveProgressBar:
    """Tests for live progress bar data."""

    @pytest.mark.asyncio
    async def test_campaign_stats_progress(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Statistics endpoint provides progress data for progress bar."""
        c = await create_test_client(db_session, "prog_bar")
        campaign = await create_test_campaign(db_session, c, name="Progress Campaign")
        campaign.total_targets = 100
        campaign.sent_count = 42
        campaign.failed_count = 3
        await db_session.flush()

        resp = await client.get(
            f"/api/v1/campaigns/{campaign.id}/statistics",
            headers=make_auth_headers(c),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["sent_count"] == 42
        assert data["failed_count"] == 3
        assert data["total_targets"] == 100
        assert "delivery_rate" in data

    @pytest.mark.asyncio
    async def test_delivery_rate_calculation(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Delivery rate is correctly calculated."""
        c = await create_test_client(db_session, "del_rate")
        campaign = await create_test_campaign(db_session, c, name="Rate Campaign")
        campaign.total_targets = 200
        campaign.sent_count = 180
        await db_session.flush()

        resp = await client.get(
            f"/api/v1/campaigns/{campaign.id}/statistics",
            headers=make_auth_headers(c),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["delivery_rate"] == pytest.approx(90.0, rel=0.01)


class TestLiveActivityLog:
    """Tests for live activity log."""

    @pytest.mark.asyncio
    async def test_activity_log_empty_on_new_campaign(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """New campaign has empty activity log."""
        c = await create_test_client(db_session, "act_empty")
        campaign = await create_test_campaign(db_session, c, name="Empty Activity")

        resp = await client.get(
            f"/api/v1/campaigns/{campaign.id}/activity-log",
            headers=make_auth_headers(c),
        )
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_activity_log_pagination_parameters(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Activity log accepts pagination parameters."""
        c = await create_test_client(db_session, "act_pag")
        campaign = await create_test_campaign(db_session, c, name="Activity Paged")

        resp = await client.get(
            f"/api/v1/campaigns/{campaign.id}/activity-log?limit=20&offset=0",
            headers=make_auth_headers(c),
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_activity_log_max_limit(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Activity log max limit is enforced (500)."""
        c = await create_test_client(db_session, "act_maxlim")
        campaign = await create_test_campaign(db_session, c, name="Activity Max")

        resp = await client.get(
            f"/api/v1/campaigns/{campaign.id}/activity-log?limit=501",
            headers=make_auth_headers(c),
        )
        assert resp.status_code == 422


class TestActionButtons:
    """Tests for pause/resume/stop action buttons."""

    @pytest.mark.asyncio
    async def test_pause_button_action(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Pause button calls pause endpoint."""
        c = await create_test_client(db_session, "btn_pause")
        campaign = await create_test_campaign(db_session, c, name="Pause Button")
        campaign.status = CampaignStatus.running
        await db_session.flush()

        with patch(
            "app.core.broadcast_engine.BroadcastEngine.pause_campaign",
            new_callable=AsyncMock,
        ):
            resp = await client.post(
                f"/api/v1/campaigns/{campaign.id}/pause",
                headers=make_auth_headers(c),
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_resume_button_action(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Resume button calls resume endpoint."""
        c = await create_test_client(db_session, "btn_resume")
        campaign = await create_test_campaign(db_session, c, name="Resume Button")
        campaign.status = CampaignStatus.paused
        await db_session.flush()

        with patch(
            "app.core.broadcast_engine.BroadcastEngine.start_campaign",
            new_callable=AsyncMock,
            return_value="task-xyz",
        ):
            resp = await client.post(
                f"/api/v1/campaigns/{campaign.id}/resume",
                headers=make_auth_headers(c),
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_stop_button_action(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Stop button calls stop endpoint."""
        c = await create_test_client(db_session, "btn_stop")
        campaign = await create_test_campaign(db_session, c, name="Stop Button")
        campaign.status = CampaignStatus.running
        await db_session.flush()

        with patch(
            "app.core.broadcast_engine.BroadcastEngine.stop_campaign",
            new_callable=AsyncMock,
        ):
            resp = await client.post(
                f"/api/v1/campaigns/{campaign.id}/stop",
                headers=make_auth_headers(c),
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_pause_already_paused_campaign_fails(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Cannot pause an already paused campaign."""
        c = await create_test_client(db_session, "btn_pause_fail")
        campaign = await create_test_campaign(db_session, c, name="AlreadyPaused")
        campaign.status = CampaignStatus.paused
        await db_session.flush()

        resp = await client.post(
            f"/api/v1/campaigns/{campaign.id}/pause",
            headers=make_auth_headers(c),
        )
        assert resp.status_code == 409
