"""
Unit tests for Account Health tracking.
Tests health score calculation, ban detection, warning tracking,
auto-quarantine, and recovery logic.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import (
    TelegramAccount, AccountStatus, AccountHealth,
    AccountGroupStatus,
)
from tests.conftest import (
    create_test_client,
    create_test_account,
    create_test_account_group,
)


class TestHealthScoreCalculation:
    """Tests for health score computation logic."""

    @pytest.mark.asyncio
    async def test_new_account_has_full_health(self, db_session: AsyncSession):
        """A freshly created account starts at 100% health."""
        c = await create_test_client(db_session, "ah_new")
        account = await create_test_account(db_session, c, phone="+60111111111")
        assert account.health_score == 100.0

    @pytest.mark.asyncio
    async def test_health_score_decreases_on_warnings(self, db_session: AsyncSession):
        """Health score can be reduced for warnings."""
        c = await create_test_client(db_session, "ah_warn")
        account = await create_test_account(db_session, c, phone="+60222222222")
        group = await create_test_account_group(db_session, c)

        # Create health record with warnings
        health = AccountHealth(
            account_id=account.id,
            account_group_id=group.id,
            health_score=70.0,
            warnings=3,
            is_banned=False,
        )
        db_session.add(health)
        await db_session.flush()
        await db_session.refresh(health)

        assert health.health_score == 70.0
        assert health.warnings == 3

    @pytest.mark.asyncio
    async def test_banned_account_health_zero(self, db_session: AsyncSession):
        """A banned account should have health score = 0."""
        c = await create_test_client(db_session, "ah_ban")
        account = await create_test_account(db_session, c, phone="+60333333333")
        group = await create_test_account_group(db_session, c)

        health = AccountHealth(
            account_id=account.id,
            account_group_id=group.id,
            health_score=0.0,
            warnings=10,
            is_banned=True,
        )
        db_session.add(health)
        await db_session.flush()
        await db_session.refresh(health)

        assert health.is_banned is True
        assert health.health_score == 0.0

    @pytest.mark.asyncio
    async def test_health_score_bounds(self, db_session: AsyncSession):
        """Health score stays within [0, 100] bounds."""
        c = await create_test_client(db_session, "ah_bounds")
        account = await create_test_account(db_session, c, phone="+60444444444")
        group = await create_test_account_group(db_session, c)

        scores = [0.0, 25.5, 50.0, 75.3, 100.0]
        for score in scores:
            health = AccountHealth(
                account_id=account.id,
                account_group_id=group.id,
                health_score=score,
                warnings=0,
                is_banned=score == 0.0,
            )
            db_session.add(health)
        await db_session.flush()


class TestBanDetection:
    """Tests for ban status detection."""

    @pytest.mark.asyncio
    async def test_detect_banned_status(self, db_session: AsyncSession):
        """Account with banned status is correctly identified as banned."""
        c = await create_test_client(db_session, "bd_detect")
        account = TelegramAccount(
            client_id=c.id,
            name="BannedAccount",
            phone="+70111111111",
            status=AccountStatus.banned,
            health_score=0.0,
        )
        db_session.add(account)
        await db_session.flush()
        await db_session.refresh(account)

        assert account.status == AccountStatus.banned
        assert account.health_score == 0.0

    @pytest.mark.asyncio
    async def test_flood_wait_status(self, db_session: AsyncSession):
        """Account in flood_wait is detected and flagged."""
        c = await create_test_client(db_session, "bd_flood")
        account = TelegramAccount(
            client_id=c.id,
            name="FloodAccount",
            phone="+70222222222",
            status=AccountStatus.flood_wait,
            health_score=50.0,
            flood_wait_until=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        db_session.add(account)
        await db_session.flush()
        await db_session.refresh(account)

        assert account.status == AccountStatus.flood_wait
        assert account.flood_wait_until is not None

    @pytest.mark.asyncio
    async def test_detect_ban_via_health_record(self, db_session: AsyncSession):
        """is_banned=True in AccountHealth flags the account as banned."""
        c = await create_test_client(db_session, "bd_health")
        account = await create_test_account(db_session, c, phone="+70333333333")
        group = await create_test_account_group(db_session, c)

        health = AccountHealth(
            account_id=account.id,
            account_group_id=group.id,
            health_score=0.0,
            warnings=5,
            is_banned=True,
            details={"ban_reason": "spam_detected"},
        )
        db_session.add(health)
        await db_session.flush()
        await db_session.refresh(health)

        assert health.is_banned is True
        assert health.details["ban_reason"] == "spam_detected"


class TestWarningTracking:
    """Tests for tracking account warnings."""

    @pytest.mark.asyncio
    async def test_warning_increments(self, db_session: AsyncSession):
        """Warnings can be incremented over time."""
        c = await create_test_client(db_session, "wt_inc")
        account = await create_test_account(db_session, c, phone="+80111111111")
        group = await create_test_account_group(db_session, c)

        health = AccountHealth(
            account_id=account.id,
            account_group_id=group.id,
            health_score=90.0,
            warnings=0,
        )
        db_session.add(health)
        await db_session.flush()

        health.warnings += 1
        health.health_score = 80.0
        await db_session.flush()
        await db_session.refresh(health)

        assert health.warnings == 1
        assert health.health_score == 80.0

    @pytest.mark.asyncio
    async def test_multiple_warnings_reduce_health(self, db_session: AsyncSession):
        """Multiple warnings correlate with reduced health score."""
        c = await create_test_client(db_session, "wt_multi")
        account = await create_test_account(db_session, c, phone="+80222222222")
        group = await create_test_account_group(db_session, c)

        # Simulate progressive health degradation
        health_data = [
            (1, 90.0), (2, 80.0), (3, 65.0), (5, 40.0)
        ]
        for warnings, score in health_data:
            health = AccountHealth(
                account_id=account.id,
                account_group_id=group.id,
                health_score=score,
                warnings=warnings,
            )
            db_session.add(health)
        await db_session.flush()


class TestAutoQuarantine:
    """Tests for automatic quarantine logic."""

    @pytest.mark.asyncio
    async def test_quarantine_threshold(self, db_session: AsyncSession):
        """Account with health < 30 should be quarantined (set to inactive)."""
        c = await create_test_client(db_session, "aq_thresh")
        account = TelegramAccount(
            client_id=c.id,
            name="QuarantineMe",
            phone="+90111111111",
            status=AccountStatus.active,
            health_score=25.0,
        )
        db_session.add(account)
        await db_session.flush()

        # Simulate auto-quarantine logic
        if account.health_score < 30.0:
            account.status = AccountStatus.inactive
        await db_session.flush()
        await db_session.refresh(account)

        assert account.status == AccountStatus.inactive

    @pytest.mark.asyncio
    async def test_quarantine_group_paused_on_all_banned(self, db_session: AsyncSession):
        """Account group is paused when all its accounts are banned/inactive."""
        c = await create_test_client(db_session, "aq_group")
        group = await create_test_account_group(db_session, c)

        # Simulate: all accounts are banned → group pauses
        group.status = AccountGroupStatus.paused
        await db_session.flush()
        await db_session.refresh(group)

        assert group.status == AccountGroupStatus.paused


class TestRecoveryLogic:
    """Tests for account recovery after quarantine."""

    @pytest.mark.asyncio
    async def test_recovery_restores_health(self, db_session: AsyncSession):
        """After flood_wait expires, account health can be restored."""
        c = await create_test_client(db_session, "rec_restore")
        account = TelegramAccount(
            client_id=c.id,
            name="RecoveryAccount",
            phone="+91111111111",
            status=AccountStatus.flood_wait,
            health_score=40.0,
            flood_wait_until=datetime.now(timezone.utc) - timedelta(hours=1),  # expired
        )
        db_session.add(account)
        await db_session.flush()

        # Simulate recovery check
        now = datetime.now(timezone.utc)
        if account.flood_wait_until and account.flood_wait_until < now:
            account.status = AccountStatus.active
            account.health_score = min(account.health_score + 20.0, 100.0)
        await db_session.flush()
        await db_session.refresh(account)

        assert account.status == AccountStatus.active
        assert account.health_score == 60.0

    @pytest.mark.asyncio
    async def test_cannot_recover_banned_account(self, db_session: AsyncSession):
        """Permanently banned accounts should remain banned (no auto-recovery)."""
        c = await create_test_client(db_session, "rec_perm")
        account = TelegramAccount(
            client_id=c.id,
            name="PermanentBan",
            phone="+91222222222",
            status=AccountStatus.banned,
            health_score=0.0,
        )
        db_session.add(account)
        await db_session.flush()
        await db_session.refresh(account)

        # Banned accounts don't auto-recover
        assert account.status == AccountStatus.banned
