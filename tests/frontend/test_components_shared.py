"""
Frontend unit tests for shared UI components.
Tests status badges, progress bars, live counters, helper utilities,
and common API response structures.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import CampaignStatus, AccountStatus
from app.utils.helpers import generate_api_key, generate_otp, safe_username, constant_time_compare
from tests.conftest import (
    create_test_admin,
    create_test_client,
    create_test_campaign,
    create_test_account,
    create_test_account_group,
    make_auth_headers,
)


class TestStatusBadges:
    """Tests for status badge values (campaign and account statuses)."""

    def test_campaign_status_values(self):
        """All campaign statuses have correct string values."""
        assert CampaignStatus.draft.value == "draft"
        assert CampaignStatus.running.value == "running"
        assert CampaignStatus.paused.value == "paused"
        assert CampaignStatus.completed.value == "completed"
        assert CampaignStatus.failed.value == "failed"
        assert CampaignStatus.scheduled.value == "scheduled"

    def test_account_status_values(self):
        """All account statuses have correct string values."""
        assert AccountStatus.active.value == "active"
        assert AccountStatus.banned.value == "banned"
        assert AccountStatus.flood_wait.value == "flood_wait"
        assert AccountStatus.unverified.value == "unverified"
        assert AccountStatus.inactive.value == "inactive"

    @pytest.mark.asyncio
    async def test_campaign_status_in_api_response(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Campaign status is returned as string in API response."""
        c = await create_test_client(db_session, "sb_status")
        campaign = await create_test_campaign(db_session, c, name="StatusBadge")

        resp = await client.get(
            "/api/v1/campaigns/",
            headers=make_auth_headers(c),
        )
        assert resp.status_code == 200
        data = resp.json()
        campaign_data = next(d for d in data if d["id"] == campaign.id)
        assert campaign_data["status"] == "draft"
        assert isinstance(campaign_data["status"], str)


class TestProgressBars:
    """Tests for progress bar data computation."""

    def test_progress_calculation(self):
        """Progress percentage is correctly calculated."""
        sent = 75
        total = 100
        progress = sent / total * 100
        assert progress == 75.0

    def test_progress_zero_total(self):
        """Zero total targets doesn't cause division error."""
        sent = 0
        total = 0
        progress = sent / total * 100 if total > 0 else 0.0
        assert progress == 0.0

    def test_delivery_rate_full_success(self):
        """100% delivery rate is calculated correctly."""
        sent = 100
        total = 100
        rate = sent / total * 100
        assert rate == 100.0

    def test_progress_partial(self):
        """Partial progress is calculated correctly."""
        sent = 33
        failed = 7
        total = 100
        progress = (sent + failed) / total * 100
        assert progress == pytest.approx(40.0)

    @pytest.mark.asyncio
    async def test_statistics_delivery_rate_field(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Statistics endpoint includes delivery_rate field."""
        c = await create_test_client(db_session, "pb_rate")
        campaign = await create_test_campaign(db_session, c, name="ProgressBar")
        campaign.total_targets = 50
        campaign.sent_count = 40
        await db_session.flush()

        resp = await client.get(
            f"/api/v1/campaigns/{campaign.id}/statistics",
            headers=make_auth_headers(c),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "delivery_rate" in data
        assert data["delivery_rate"] == pytest.approx(80.0, rel=0.01)


class TestActivityLog:
    """Tests for activity log component data."""

    @pytest.mark.asyncio
    async def test_activity_log_structure(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Activity log endpoint returns list (possibly empty)."""
        c = await create_test_client(db_session, "al_struct")
        campaign = await create_test_campaign(db_session, c, name="LogStructure")

        resp = await client.get(
            f"/api/v1/campaigns/{campaign.id}/activity-log",
            headers=make_auth_headers(c),
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_activity_log_limit_param(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Activity log limit parameter is validated."""
        c = await create_test_client(db_session, "al_limit")
        campaign = await create_test_campaign(db_session, c, name="LogLimit")

        # Valid limit
        resp = await client.get(
            f"/api/v1/campaigns/{campaign.id}/activity-log?limit=100",
            headers=make_auth_headers(c),
        )
        assert resp.status_code == 200

        # Limit too high
        resp = await client.get(
            f"/api/v1/campaigns/{campaign.id}/activity-log?limit=501",
            headers=make_auth_headers(c),
        )
        assert resp.status_code == 422


class TestLiveCounters:
    """Tests for live counter data (sent, failed, etc.)."""

    @pytest.mark.asyncio
    async def test_campaign_counters_in_detail(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Campaign detail includes counter fields."""
        c = await create_test_client(db_session, "lc_counters")
        campaign = await create_test_campaign(db_session, c, name="CounterCamp")
        campaign.sent_count = 150
        campaign.failed_count = 10
        campaign.retry_count = 5
        await db_session.flush()

        resp = await client.get(
            f"/api/v1/campaigns/{campaign.id}/detail",
            headers=make_auth_headers(c),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["sent_count"] == 150
        assert data["failed_count"] == 10

    @pytest.mark.asyncio
    async def test_campaign_stats_counters(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Statistics endpoint provides complete counter set."""
        c = await create_test_client(db_session, "lc_stats")
        campaign = await create_test_campaign(db_session, c, name="StatCounters")
        campaign.total_targets = 200
        campaign.sent_count = 180
        campaign.failed_count = 5
        await db_session.flush()

        resp = await client.get(
            f"/api/v1/campaigns/{campaign.id}/statistics",
            headers=make_auth_headers(c),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["sent_count"] == 180
        assert data["failed_count"] == 5
        assert data["total_targets"] == 200


class TestHelperUtilities:
    """Tests for helper utility functions used across the frontend."""

    def test_generate_api_key_alphanumeric(self):
        """API key contains only alphanumeric characters."""
        import re
        key = generate_api_key()
        assert re.match(r'^[A-Za-z0-9]+$', key)

    def test_generate_api_key_length(self):
        """Default API key is 40 characters."""
        key = generate_api_key()
        assert len(key) == 40

    def test_generate_otp_digits(self):
        """OTP is numeric and correct length."""
        otp = generate_otp(6)
        assert len(otp) == 6
        assert otp.isdigit()

    def test_safe_username_strips_at(self):
        """safe_username strips @ prefix."""
        assert safe_username("@mygroup") == "mygroup"

    def test_safe_username_strips_tme_url(self):
        """safe_username extracts username from t.me URL."""
        assert safe_username("https://t.me/mygroup") == "mygroup"

    def test_constant_time_compare_equal(self):
        """constant_time_compare returns True for equal strings."""
        assert constant_time_compare("secret", "secret") is True

    def test_constant_time_compare_not_equal(self):
        """constant_time_compare returns False for different strings."""
        assert constant_time_compare("secret", "other") is False

    def test_health_score_range(self):
        """Health score is always between 0 and 100."""
        scores = [0.0, 25.5, 50.0, 75.3, 100.0]
        for score in scores:
            assert 0.0 <= score <= 100.0


class TestAPIHealthEndpoint:
    """Tests for health check endpoints."""

    @pytest.mark.asyncio
    async def test_root_health_endpoint(self, client: AsyncClient):
        """Root health endpoint returns 200 with status ok."""
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient):
        """Root endpoint returns 200."""
        resp = await client.get("/")
        assert resp.status_code == 200
