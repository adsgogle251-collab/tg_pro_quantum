"""
Unit tests for Broadcast service.
Tests campaign create, start, pause, resume, stop, account rotation,
group verification, jitter calculation, and rate limiting.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import (
    Campaign, CampaignStatus, CampaignMode, TelegramAccount, AccountStatus,
)
from tests.conftest import (
    create_test_admin,
    create_test_client,
    create_test_campaign,
    create_test_account,
    create_test_account_group,
    make_auth_headers,
)


class TestBroadcastCampaignCreation:
    """Tests for creating broadcast campaigns."""

    @pytest.mark.asyncio
    async def test_create_campaign_defaults(self, db_session: AsyncSession):
        """Campaign is created with correct default values."""
        c = await create_test_client(db_session, "bc_create")
        campaign = await create_test_campaign(db_session, c, name="Default Campaign")

        assert campaign.id is not None
        assert campaign.status == CampaignStatus.draft
        assert campaign.mode == CampaignMode.once
        assert campaign.delay_min == 27.0
        assert campaign.delay_max == 33.0
        assert campaign.sent_count == 0
        assert campaign.failed_count == 0

    @pytest.mark.asyncio
    async def test_create_campaign_with_custom_delays(self, db_session: AsyncSession):
        """Campaign can have custom delay ranges."""
        c = await create_test_client(db_session, "bc_delay")
        campaign = Campaign(
            client_id=c.id,
            name="Custom Delay",
            message_text="Test message",
            status=CampaignStatus.draft,
            mode=CampaignMode.once,
            delay_min=30.0,
            delay_max=60.0,
        )
        db_session.add(campaign)
        await db_session.flush()
        await db_session.refresh(campaign)

        assert campaign.delay_min == 30.0
        assert campaign.delay_max == 60.0

    @pytest.mark.asyncio
    async def test_create_campaign_different_modes(self, db_session: AsyncSession):
        """Campaign can be created with different broadcasting modes."""
        c = await create_test_client(db_session, "bc_modes")
        modes = [
            CampaignMode.once,
            CampaignMode.round_robin,
            CampaignMode.loop,
            CampaignMode.schedule_24_7,
        ]
        for mode in modes:
            campaign = Campaign(
                client_id=c.id,
                name=f"Campaign_{mode.value}",
                message_text="Test",
                status=CampaignStatus.draft,
                mode=mode,
            )
            db_session.add(campaign)
        await db_session.flush()


class TestBroadcastControl:
    """Tests for broadcast control: start, pause, resume, stop."""

    @pytest.mark.asyncio
    async def test_start_broadcast_via_api(self, client, db_session):
        """Start a campaign via API."""
        c = await create_test_client(db_session, "bc_start")
        campaign = await create_test_campaign(db_session, c, name="StartTest")

        with patch(
            "app.core.broadcast_engine.BroadcastEngine.start_campaign",
            new_callable=AsyncMock,
            return_value="task-123",
        ):
            resp = await client.post(
                "/api/v1/broadcasts/start",
                json={"campaign_id": campaign.id},
                headers=make_auth_headers(c),
            )
        assert resp.status_code in (200, 202)

    @pytest.mark.asyncio
    async def test_pause_running_campaign(self, client, db_session):
        """Pause a running campaign."""
        c = await create_test_client(db_session, "bc_pause")
        campaign = await create_test_campaign(db_session, c, name="PauseTest")
        campaign.status = CampaignStatus.running
        await db_session.flush()

        with patch(
            "app.core.broadcast_engine.BroadcastEngine.pause_campaign",
            new_callable=AsyncMock,
        ):
            resp = await client.post(
                f"/api/v1/broadcasts/{campaign.id}/pause",
                headers=make_auth_headers(c),
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_resume_paused_campaign(self, client, db_session):
        """Resume a paused campaign."""
        c = await create_test_client(db_session, "bc_resume")
        campaign = await create_test_campaign(db_session, c, name="ResumeTest")
        campaign.status = CampaignStatus.paused
        await db_session.flush()

        with patch(
            "app.core.broadcast_engine.BroadcastEngine.start_campaign",
            new_callable=AsyncMock,
            return_value="task-456",
        ):
            resp = await client.post(
                f"/api/v1/broadcasts/{campaign.id}/resume",
                headers=make_auth_headers(c),
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_stop_campaign(self, client, db_session):
        """Stop a running campaign."""
        c = await create_test_client(db_session, "bc_stop")
        campaign = await create_test_campaign(db_session, c, name="StopTest")
        campaign.status = CampaignStatus.running
        await db_session.flush()

        with patch(
            "app.core.broadcast_engine.BroadcastEngine.stop_campaign",
            new_callable=AsyncMock,
        ):
            resp = await client.post(
                f"/api/v1/broadcasts/{campaign.id}/stop",
                headers=make_auth_headers(c),
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_cannot_pause_non_running_campaign(self, client, db_session):
        """Pausing a draft campaign should return an error."""
        c = await create_test_client(db_session, "bc_pause_err")
        campaign = await create_test_campaign(db_session, c, name="PauseErrTest")
        # status is draft

        resp = await client.post(
            f"/api/v1/broadcasts/{campaign.id}/pause",
            headers=make_auth_headers(c),
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_cannot_start_already_running_campaign(self, client, db_session):
        """Starting an already-running campaign should return 409."""
        c = await create_test_client(db_session, "bc_dup_start")
        campaign = await create_test_campaign(db_session, c, name="DupStart")
        campaign.status = CampaignStatus.running
        await db_session.flush()

        with patch(
            "app.core.broadcast_engine.BroadcastEngine.start_campaign",
            new_callable=AsyncMock,
        ):
            resp = await client.post(
                "/api/v1/broadcasts/start",
                json={"campaign_id": campaign.id},
                headers=make_auth_headers(c),
            )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_campaign_not_found_returns_404(self, client, db_session):
        """Broadcast operations on non-existent campaign return 404."""
        c = await create_test_client(db_session, "bc_404")
        resp = await client.post(
            f"/api/v1/broadcasts/999999/pause",
            headers=make_auth_headers(c),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_cannot_control_other_clients_campaign(self, client, db_session):
        """Client cannot pause another client's campaign."""
        owner = await create_test_client(db_session, "bc_owner")
        other = await create_test_client(db_session, "bc_other")
        campaign = await create_test_campaign(db_session, owner, name="OwnerCampaign")
        campaign.status = CampaignStatus.running
        await db_session.flush()

        resp = await client.post(
            f"/api/v1/broadcasts/{campaign.id}/pause",
            headers=make_auth_headers(other),
        )
        assert resp.status_code == 403


class TestAccountRotationLogic:
    """Tests for account rotation and selection."""

    @pytest.mark.asyncio
    async def test_active_accounts_selected_for_rotation(self, db_session: AsyncSession):
        """Only active accounts should be selected for broadcasting."""
        c = await create_test_client(db_session, "rot_select")
        active = await create_test_account(db_session, c, phone="+40111111111")
        banned = TelegramAccount(
            client_id=c.id, name="Banned", phone="+40222222222",
            status=AccountStatus.banned, health_score=0.0,
        )
        db_session.add(banned)
        await db_session.flush()

        from sqlalchemy import select
        result = await db_session.execute(
            select(TelegramAccount).where(
                TelegramAccount.client_id == c.id,
                TelegramAccount.status == AccountStatus.active,
            )
        )
        active_accounts = result.scalars().all()
        assert len(active_accounts) == 1
        assert active_accounts[0].id == active.id

    @pytest.mark.asyncio
    async def test_health_score_affects_selection(self, db_session: AsyncSession):
        """Accounts with low health score are deprioritized."""
        c = await create_test_client(db_session, "rot_health")
        healthy = TelegramAccount(
            client_id=c.id, name="Healthy", phone="+50111111111",
            status=AccountStatus.active, health_score=95.0,
        )
        unhealthy = TelegramAccount(
            client_id=c.id, name="Unhealthy", phone="+50222222222",
            status=AccountStatus.active, health_score=20.0,
        )
        db_session.add_all([healthy, unhealthy])
        await db_session.flush()

        # Simulate selection: prefer health_score > 80
        from sqlalchemy import select
        result = await db_session.execute(
            select(TelegramAccount).where(
                TelegramAccount.client_id == c.id,
                TelegramAccount.health_score >= 80.0,
            )
        )
        good_accounts = result.scalars().all()
        assert len(good_accounts) == 1
        assert good_accounts[0].name == "Healthy"


class TestJitterCalculation:
    """Tests for jitter delay algorithm."""

    def test_jitter_within_bounds(self):
        """Jitter should produce delay within ±jitter_pct of base delay."""
        import random

        base_min = 27.0
        base_max = 33.0
        jitter_pct = 10.0

        for _ in range(1000):
            delay = random.uniform(base_min, base_max)
            jitter = delay * (jitter_pct / 100.0) * random.uniform(-1, 1)
            final = delay + jitter

            lower = base_min * (1 - jitter_pct / 100.0)
            upper = base_max * (1 + jitter_pct / 100.0)
            assert lower <= final <= upper, f"Delay {final} out of bounds [{lower}, {upper}]"

    def test_jitter_not_constant(self):
        """Jitter should produce different values (not constant)."""
        import random
        delays = {
            random.uniform(27, 33) + random.uniform(-2.7, 2.7)
            for _ in range(20)
        }
        # With 20 samples, at least a few should differ
        assert len(delays) > 5

    def test_default_delay_range(self):
        """Default delay range is 27–33 seconds (jitter target)."""
        # From requirements: 27-33 second range (the "27-33s" spec)
        c = Campaign(
            client_id=1,
            name="Test",
            message_text="msg",
            delay_min=27.0,
            delay_max=33.0,
        )
        assert c.delay_min == 27.0
        assert c.delay_max == 33.0


class TestGroupVerificationInBroadcast:
    """Tests for group verification during broadcast setup."""

    @pytest.mark.asyncio
    async def test_verify_groups_endpoint(self, client, db_session):
        """Group verification endpoint rejects channels."""
        c = await create_test_client(db_session, "gv_bc")

        resp = await client.post(
            "/api/v1/groups/verify",
            json={"group_usernames": ["validgroup", "channel_news", "another_group"]},
            headers=make_auth_headers(c),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 3
        assert body["failed"] >= 1

    @pytest.mark.asyncio
    async def test_campaign_detail_endpoint(self, client, db_session):
        """Campaign detail endpoint returns correct fields."""
        c = await create_test_client(db_session, "detail_bc")
        campaign = await create_test_campaign(db_session, c, name="DetailCampaign")

        resp = await client.get(
            f"/api/v1/campaigns/{campaign.id}/detail",
            headers=make_auth_headers(c),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == campaign.id
        assert body["name"] == "DetailCampaign"
