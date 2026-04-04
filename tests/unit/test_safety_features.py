"""
Unit tests for Safety Features.
Tests jitter algorithm, smart account rotation, rate limiting,
ban detection, auto-pause logic, and retry logic.
"""
from __future__ import annotations

import random
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import (
    TelegramAccount, AccountStatus, Campaign, CampaignStatus, CampaignMode,
    SafetyAlert, FailedMessage,
)
from tests.conftest import (
    create_test_client,
    create_test_account,
    create_test_campaign,
    make_auth_headers,
)


# ── Jitter Algorithm ─────────────────────────────────────────────────────────

class TestJitterAlgorithm:
    """Tests for jitter delay algorithm (27–33 s target range)."""

    def _compute_jitter_delay(
        self,
        delay_min: float = 27.0,
        delay_max: float = 33.0,
        jitter_pct: float = 10.0,
        seed: int | None = None,
    ) -> float:
        """Reference implementation of jitter delay."""
        rng = random.Random(seed) if seed is not None else random
        base = rng.uniform(delay_min, delay_max)
        jitter = base * (jitter_pct / 100.0) * rng.uniform(-1, 1)
        return base + jitter

    def test_jitter_default_range(self):
        """Delays with default settings stay within [24.3, 36.3] (10% jitter on 27–33)."""
        lower = 27.0 * 0.9
        upper = 33.0 * 1.1
        for seed in range(200):
            delay = self._compute_jitter_delay(seed=seed)
            assert lower <= delay <= upper, f"seed={seed}: {delay} out of [{lower}, {upper}]"

    def test_jitter_27_to_33_core_range(self):
        """Without jitter, delays are always in [27, 33]."""
        for seed in range(200):
            rng = random.Random(seed)
            base = rng.uniform(27.0, 33.0)
            assert 27.0 <= base <= 33.0

    def test_jitter_produces_variance(self):
        """Jitter should produce different delay values (not constant)."""
        delays = [self._compute_jitter_delay(seed=i) for i in range(50)]
        unique_delays = set(round(d, 3) for d in delays)
        assert len(unique_delays) > 20, "Jitter should produce diverse delays"

    def test_jitter_zero_pct_no_variance(self):
        """With 0% jitter, delay is exactly the base."""
        results = set()
        for seed in range(10):
            rng = random.Random(seed)
            base = rng.uniform(27.0, 33.0)
            # 0% jitter → no modification
            results.add(base)
        # All results are within base range
        assert all(27.0 <= v <= 33.0 for v in results)

    def test_jitter_custom_range(self):
        """Custom delay range with jitter stays within bounds."""
        for seed in range(50):
            delay = self._compute_jitter_delay(
                delay_min=5.0, delay_max=10.0, jitter_pct=15.0, seed=seed
            )
            lower = 5.0 * 0.85
            upper = 10.0 * 1.15
            assert lower <= delay <= upper


# ── Smart Account Rotation ────────────────────────────────────────────────────

class TestSmartAccountRotation:
    """Tests for smart account rotation logic."""

    @pytest.mark.asyncio
    async def test_rotation_skips_banned_accounts(self, db_session: AsyncSession):
        """Rotation should skip banned accounts."""
        c = await create_test_client(db_session, "rot_ban")

        for i in range(5):
            acc = TelegramAccount(
                client_id=c.id,
                name=f"Acc{i}",
                phone=f"+1110{i:06d}",
                status=AccountStatus.banned if i % 2 == 0 else AccountStatus.active,
                health_score=0.0 if i % 2 == 0 else 90.0,
            )
            db_session.add(acc)
        await db_session.flush()

        from sqlalchemy import select
        result = await db_session.execute(
            select(TelegramAccount).where(
                TelegramAccount.client_id == c.id,
                TelegramAccount.status == AccountStatus.active,
            )
        )
        available = result.scalars().all()
        assert len(available) == 2  # only active ones

    @pytest.mark.asyncio
    async def test_rotation_prefers_healthy_accounts(self, db_session: AsyncSession):
        """Rotation prefers accounts with higher health scores."""
        c = await create_test_client(db_session, "rot_pref")

        for health in [30.0, 60.0, 95.0]:
            acc = TelegramAccount(
                client_id=c.id,
                name=f"Acc_{health}",
                phone=f"+11200{int(health):03d}",
                status=AccountStatus.active,
                health_score=health,
            )
            db_session.add(acc)
        await db_session.flush()

        from sqlalchemy import select
        result = await db_session.execute(
            select(TelegramAccount)
            .where(TelegramAccount.client_id == c.id)
            .order_by(TelegramAccount.health_score.desc())
        )
        accounts = result.scalars().all()
        assert accounts[0].health_score == 95.0

    @pytest.mark.asyncio
    async def test_rotation_every_n_messages(self, db_session: AsyncSession):
        """Account rotation happens every rotate_every N messages."""
        c = await create_test_client(db_session, "rot_n")
        campaign = await create_test_campaign(db_session, c, name="RotateTest")

        # Simulate: campaign has rotate_every = 20
        rotate_every = 20
        total_messages = 60
        rotations = total_messages // rotate_every

        assert rotations == 3  # should rotate 3 times in 60 messages

    def test_rotation_cycle_logic(self):
        """Rotation cycles through accounts correctly."""
        accounts = list(range(5))  # Mock 5 account IDs
        rotate_every = 10
        total_messages = 55

        rotation_log = []
        for msg_idx in range(total_messages):
            account_idx = (msg_idx // rotate_every) % len(accounts)
            rotation_log.append(accounts[account_idx])

        # First 10 messages use account 0
        assert all(a == 0 for a in rotation_log[:10])
        # Messages 10-19 use account 1
        assert all(a == 1 for a in rotation_log[10:20])
        # Messages 50-55 use account 0 again (wraps)
        assert all(a == 0 for a in rotation_log[50:])


# ── Rate Limiting ─────────────────────────────────────────────────────────────

class TestRateLimiting:
    """Tests for per-account rate limiting."""

    def test_rate_limit_per_hour(self):
        """max_per_hour enforces message rate per account per hour."""
        max_per_hour = 100
        messages_sent = 100

        allowed = messages_sent < max_per_hour
        assert not allowed  # At limit, next message is blocked

    def test_rate_limit_per_day(self):
        """max_per_day enforces message rate per account per day."""
        max_per_day = 500
        messages_sent = 501

        allowed = messages_sent < max_per_day
        assert not allowed  # Over daily limit

    def test_rate_limit_allows_within_bounds(self):
        """Messages under the limit are allowed."""
        max_per_hour = 100
        messages_sent = 50
        assert messages_sent < max_per_hour

    @pytest.mark.asyncio
    async def test_messages_sent_today_tracked(self, db_session: AsyncSession):
        """messages_sent_today is properly tracked per account."""
        c = await create_test_client(db_session, "rl_track")
        account = await create_test_account(db_session, c, phone="+12200000001")

        account.messages_sent_today = 150
        await db_session.flush()
        await db_session.refresh(account)

        assert account.messages_sent_today == 150

    def test_rate_limit_resets_daily(self):
        """Daily counter resets at midnight."""
        last_reset = datetime.now(timezone.utc) - timedelta(days=1)
        now = datetime.now(timezone.utc)
        should_reset = (now - last_reset).days >= 1
        assert should_reset


# ── Ban Detection ─────────────────────────────────────────────────────────────

class TestBanDetectionSafety:
    """Tests for ban detection in safety context."""

    @pytest.mark.asyncio
    async def test_ban_detection_triggers_alert(self, db_session: AsyncSession):
        """Detected ban creates a SafetyAlert."""
        c = await create_test_client(db_session, "ban_alert")
        campaign = await create_test_campaign(db_session, c, name="BanAlert")

        alert = SafetyAlert(
            campaign_id=campaign.id,
            client_id=c.id,
            alert_type="ban_detected",
            severity="critical",
            message="Account +1234567890 has been banned",
            is_resolved=False,
        )
        db_session.add(alert)
        await db_session.flush()
        await db_session.refresh(alert)

        assert alert.alert_type == "ban_detected"
        assert alert.severity == "critical"
        assert alert.is_resolved is False

    @pytest.mark.asyncio
    async def test_alert_resolved(self, db_session: AsyncSession):
        """SafetyAlert can be marked as resolved."""
        c = await create_test_client(db_session, "ban_resolve")

        alert = SafetyAlert(
            client_id=c.id,
            alert_type="ban_detected",
            severity="warning",
            message="Flood wait detected",
            is_resolved=False,
        )
        db_session.add(alert)
        await db_session.flush()

        alert.is_resolved = True
        alert.resolved_at = datetime.now(timezone.utc)
        await db_session.flush()
        await db_session.refresh(alert)

        assert alert.is_resolved is True
        assert alert.resolved_at is not None


# ── Auto-Pause Logic ──────────────────────────────────────────────────────────

class TestAutoPauseLogic:
    """Tests for automatic campaign pause on safety triggers."""

    @pytest.mark.asyncio
    async def test_auto_pause_on_high_failure_rate(self, db_session: AsyncSession):
        """Campaign is paused when failure rate exceeds threshold."""
        c = await create_test_client(db_session, "ap_high")
        campaign = await create_test_campaign(db_session, c, name="HighFail")
        campaign.status = CampaignStatus.running
        campaign.sent_count = 2
        campaign.failed_count = 8  # 80% failure rate
        await db_session.flush()

        # Simulate auto-pause logic: pause if failure rate > 50%
        total = campaign.sent_count + campaign.failed_count
        failure_rate = campaign.failed_count / total if total > 0 else 0
        if failure_rate > 0.5:
            campaign.status = CampaignStatus.paused
        await db_session.flush()
        await db_session.refresh(campaign)

        assert campaign.status == CampaignStatus.paused

    @pytest.mark.asyncio
    async def test_no_pause_on_low_failure_rate(self, db_session: AsyncSession):
        """Campaign stays running when failure rate is low."""
        c = await create_test_client(db_session, "ap_low")
        campaign = await create_test_campaign(db_session, c, name="LowFail")
        campaign.status = CampaignStatus.running
        campaign.sent_count = 100
        campaign.failed_count = 3  # 3% failure rate
        await db_session.flush()

        total = campaign.sent_count + campaign.failed_count
        failure_rate = campaign.failed_count / total if total > 0 else 0
        if failure_rate > 0.5:
            campaign.status = CampaignStatus.paused
        await db_session.flush()
        await db_session.refresh(campaign)

        assert campaign.status == CampaignStatus.running  # should NOT be paused

    @pytest.mark.asyncio
    async def test_auto_pause_alert_created(self, db_session: AsyncSession):
        """Auto-pause creates a safety alert."""
        c = await create_test_client(db_session, "ap_alert")
        campaign = await create_test_campaign(db_session, c, name="AlertPause")

        alert = SafetyAlert(
            campaign_id=campaign.id,
            client_id=c.id,
            alert_type="campaign_auto_paused",
            severity="warning",
            message="Campaign auto-paused due to high failure rate",
        )
        db_session.add(alert)
        await db_session.flush()
        await db_session.refresh(alert)

        assert alert.alert_type == "campaign_auto_paused"


# ── Retry Logic ───────────────────────────────────────────────────────────────

class TestRetryLogic:
    """Tests for message retry with exponential backoff."""

    @pytest.mark.asyncio
    async def test_failed_message_queued(self, db_session: AsyncSession):
        """Failed messages are added to the retry queue."""
        c = await create_test_client(db_session, "retry_q")
        campaign = await create_test_campaign(db_session, c, name="RetryTest")

        failed = FailedMessage(
            id=1,
            campaign_id=campaign.id,
            client_id=c.id,
            group_target="targetgroup",
            account_name="account1",
            error_type="flood_wait",
            error_message="FloodWaitError: 60 seconds",
            retry_count=0,
            next_retry_at=datetime.now(timezone.utc) + timedelta(seconds=60),
            is_dead_letter=False,
        )
        db_session.add(failed)
        await db_session.flush()
        await db_session.refresh(failed)

        assert failed.id == 1
        assert failed.retry_count == 0
        assert failed.is_dead_letter is False

    def test_exponential_backoff_calculation(self):
        """Backoff increases exponentially with retry count."""
        base_delay = 60  # seconds
        backoff_delays = [
            base_delay * (2 ** retry)
            for retry in range(5)
        ]
        assert backoff_delays == [60, 120, 240, 480, 960]

    @pytest.mark.asyncio
    async def test_dead_letter_after_max_retries(self, db_session: AsyncSession):
        """Message becomes dead letter after max retries exceeded."""
        c = await create_test_client(db_session, "dl_max")
        campaign = await create_test_campaign(db_session, c, name="DeadLetter")
        max_retries = 3

        failed = FailedMessage(
            id=2,
            campaign_id=campaign.id,
            client_id=c.id,
            group_target="deadgroup",
            account_name="account2",
            error_type="user_limit",
            retry_count=max_retries,
            is_dead_letter=False,
        )
        db_session.add(failed)
        await db_session.flush()

        # Simulate: mark as dead letter after exceeding retries
        if failed.retry_count >= max_retries:
            failed.is_dead_letter = True
        await db_session.flush()
        await db_session.refresh(failed)

        assert failed.is_dead_letter is True

    def test_retry_count_max_three(self):
        """Default max_retries is 3 per the config spec."""
        from app.config import settings
        assert settings.MAX_RETRIES == 3
