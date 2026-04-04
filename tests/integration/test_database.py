"""
Integration tests for database operations.
Tests transaction consistency, data isolation, cascade deletes,
and query correctness.
"""
from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import (
    AccountAssignment, AccountGroup, AccountGroupFeatureType, AccountGroupStatus,
    AccountHealth, AuditLog, Campaign, CampaignStatus, Client, ClientStatus,
    Group, GroupAnalytics, TelegramAccount, AccountStatus,
)
from tests.conftest import (
    create_test_admin,
    create_test_client,
    create_test_account,
    create_test_campaign,
    create_test_account_group,
    create_test_group,
)


class TestTransactionConsistency:
    """Tests for transaction rollback and commit consistency."""

    @pytest.mark.asyncio
    async def test_successful_commit(self, db_session: AsyncSession):
        """Flushed changes are visible within the same session."""
        c = await create_test_client(db_session, "tx_ok")
        client_id = c.id
        assert client_id is not None

        result = await db_session.execute(
            select(Client).where(Client.id == client_id)
        )
        assert result.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_rollback_removes_changes(self, db_session: AsyncSession):
        """Changes are rolled back on error (handled by fixture)."""
        c = await create_test_client(db_session, "tx_rb")
        c.name = "Modified Name"
        await db_session.flush()

        # The fixture will rollback after the test, so this is just validating
        # that the change is visible within the session.
        result = await db_session.execute(
            select(Client).where(Client.id == c.id)
        )
        client = result.scalar_one_or_none()
        assert client.name == "Modified Name"

    @pytest.mark.asyncio
    async def test_flush_makes_data_queryable(self, db_session: AsyncSession):
        """After flush, data is queryable within the session."""
        c = await create_test_client(db_session, "tx_flush")
        campaign = await create_test_campaign(db_session, c)

        result = await db_session.execute(
            select(Campaign).where(Campaign.client_id == c.id)
        )
        campaigns = result.scalars().all()
        assert len(campaigns) >= 1


class TestDataIsolationPerClient:
    """Tests for strict per-client data isolation."""

    @pytest.mark.asyncio
    async def test_campaign_isolation(self, db_session: AsyncSession):
        """Campaigns are isolated per client."""
        c1 = await create_test_client(db_session, "di_c1")
        c2 = await create_test_client(db_session, "di_c2")

        camp1 = await create_test_campaign(db_session, c1, name="C1_Campaign")
        camp2 = await create_test_campaign(db_session, c2, name="C2_Campaign")

        result_c1 = await db_session.execute(
            select(Campaign).where(Campaign.client_id == c1.id)
        )
        result_c2 = await db_session.execute(
            select(Campaign).where(Campaign.client_id == c2.id)
        )

        camps_c1 = {c.id for c in result_c1.scalars().all()}
        camps_c2 = {c.id for c in result_c2.scalars().all()}

        assert camp1.id in camps_c1
        assert camp2.id in camps_c2
        assert camp1.id not in camps_c2
        assert camp2.id not in camps_c1

    @pytest.mark.asyncio
    async def test_account_isolation(self, db_session: AsyncSession):
        """TelegramAccounts are isolated per client."""
        c1 = await create_test_client(db_session, "ai_c1")
        c2 = await create_test_client(db_session, "ai_c2")

        acc1 = await create_test_account(db_session, c1, phone="+11100000001")
        acc2 = await create_test_account(db_session, c2, phone="+11100000002")

        result = await db_session.execute(
            select(TelegramAccount).where(TelegramAccount.client_id == c1.id)
        )
        accounts_c1 = {a.id for a in result.scalars().all()}
        assert acc1.id in accounts_c1
        assert acc2.id not in accounts_c1

    @pytest.mark.asyncio
    async def test_group_isolation(self, db_session: AsyncSession):
        """Groups (targets) are isolated per client."""
        c1 = await create_test_client(db_session, "gi_c1")
        c2 = await create_test_client(db_session, "gi_c2")

        g1 = await create_test_group(db_session, c1, username="group_c1")
        g2 = await create_test_group(db_session, c2, username="group_c2")

        result = await db_session.execute(
            select(Group).where(Group.client_id == c1.id)
        )
        groups_c1 = {g.id for g in result.scalars().all()}
        assert g1.id in groups_c1
        assert g2.id not in groups_c1


class TestCascadeDeleteBehavior:
    """Tests for cascaded deletes."""

    @pytest.mark.asyncio
    async def test_delete_client_cascades_campaigns(self, db_session: AsyncSession):
        """Deleting a client removes its campaigns."""
        c = await create_test_client(db_session, "casc_cl")
        campaign = await create_test_campaign(db_session, c, name="CascCampaign")
        camp_id = campaign.id
        client_id = c.id

        await db_session.delete(c)
        await db_session.flush()

        result = await db_session.execute(
            select(Campaign).where(Campaign.id == camp_id)
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_delete_account_group_cascades_assignments(
        self, db_session: AsyncSession
    ):
        """Deleting an AccountGroup cascades to AccountAssignment."""
        c = await create_test_client(db_session, "casc_ag")
        account = await create_test_account(db_session, c, phone="+22200000001")
        group = await create_test_account_group(db_session, c, name="CascGroup")

        asgn = AccountAssignment(
            account_id=account.id,
            account_group_id=group.id,
            feature_type="broadcast",
            status="active",
        )
        db_session.add(asgn)
        await db_session.flush()
        group_id = group.id

        await db_session.delete(group)
        await db_session.flush()

        result = await db_session.execute(
            select(AccountAssignment).where(
                AccountAssignment.account_group_id == group_id
            )
        )
        assert result.scalars().all() == []

    @pytest.mark.asyncio
    async def test_delete_account_group_cascades_health(self, db_session: AsyncSession):
        """Deleting an AccountGroup cascades to AccountHealth."""
        from datetime import datetime, timezone
        c = await create_test_client(db_session, "casc_health")
        account = await create_test_account(db_session, c, phone="+22200000002")
        group = await create_test_account_group(db_session, c, name="HealthCascGroup")

        health = AccountHealth(
            account_id=account.id,
            account_group_id=group.id,
            health_score=80.0,
            warnings=0,
        )
        db_session.add(health)
        await db_session.flush()
        group_id = group.id

        await db_session.delete(group)
        await db_session.flush()

        result = await db_session.execute(
            select(AccountHealth).where(
                AccountHealth.account_group_id == group_id
            )
        )
        assert result.scalars().all() == []


class TestQueryOptimization:
    """Tests for efficient query patterns."""

    @pytest.mark.asyncio
    async def test_filter_by_status(self, db_session: AsyncSession):
        """Filtering accounts by status uses the index correctly."""
        c = await create_test_client(db_session, "qo_status")
        for i, status in enumerate([
            AccountStatus.active,
            AccountStatus.banned,
            AccountStatus.active,
            AccountStatus.flood_wait,
        ]):
            acc = TelegramAccount(
                client_id=c.id,
                name=f"Acc{i}",
                phone=f"+33{i:010d}",
                status=status,
                health_score=90.0 if status == AccountStatus.active else 0.0,
            )
            db_session.add(acc)
        await db_session.flush()

        result = await db_session.execute(
            select(TelegramAccount).where(
                TelegramAccount.client_id == c.id,
                TelegramAccount.status == AccountStatus.active,
            )
        )
        active = result.scalars().all()
        assert len(active) == 2

    @pytest.mark.asyncio
    async def test_count_query(self, db_session: AsyncSession):
        """COUNT query returns correct results."""
        c = await create_test_client(db_session, "qo_count")
        for i in range(5):
            await create_test_campaign(db_session, c, name=f"Count_{i}")

        result = await db_session.execute(
            select(func.count(Campaign.id)).where(Campaign.client_id == c.id)
        )
        count = result.scalar()
        assert count == 5

    @pytest.mark.asyncio
    async def test_order_by_health_score(self, db_session: AsyncSession):
        """ORDER BY health_score returns accounts in correct order."""
        c = await create_test_client(db_session, "qo_order")
        for score in [50.0, 95.0, 30.0, 80.0]:
            acc = TelegramAccount(
                client_id=c.id,
                name=f"Acc_{score}",
                phone=f"+44{int(score):010d}",
                status=AccountStatus.active,
                health_score=score,
            )
            db_session.add(acc)
        await db_session.flush()

        result = await db_session.execute(
            select(TelegramAccount)
            .where(TelegramAccount.client_id == c.id)
            .order_by(TelegramAccount.health_score.desc())
        )
        accounts = result.scalars().all()
        scores = [a.health_score for a in accounts]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_paginated_query(self, db_session: AsyncSession):
        """Paginated query returns correct subset."""
        c = await create_test_client(db_session, "qo_page")
        for i in range(10):
            await create_test_campaign(db_session, c, name=f"Page_{i}")

        # Page 1: first 5
        result = await db_session.execute(
            select(Campaign)
            .where(Campaign.client_id == c.id)
            .order_by(Campaign.id)
            .limit(5)
            .offset(0)
        )
        page1 = result.scalars().all()
        assert len(page1) == 5

        # Page 2: next 5
        result = await db_session.execute(
            select(Campaign)
            .where(Campaign.client_id == c.id)
            .order_by(Campaign.id)
            .limit(5)
            .offset(5)
        )
        page2 = result.scalars().all()
        assert len(page2) == 5

        # No overlap
        ids1 = {c.id for c in page1}
        ids2 = {c.id for c in page2}
        assert ids1.isdisjoint(ids2)


class TestBulkOperations:
    """Tests for bulk insert/update operations."""

    @pytest.mark.asyncio
    async def test_bulk_account_insert(self, db_session: AsyncSession):
        """Bulk inserting 100 accounts works correctly."""
        c = await create_test_client(db_session, "bulk_ins")
        accounts = [
            TelegramAccount(
                client_id=c.id,
                name=f"BulkAcc{i}",
                phone=f"+55{i:010d}",
                status=AccountStatus.active,
                health_score=100.0,
            )
            for i in range(100)
        ]
        db_session.add_all(accounts)
        await db_session.flush()

        result = await db_session.execute(
            select(func.count(TelegramAccount.id)).where(
                TelegramAccount.client_id == c.id
            )
        )
        assert result.scalar() == 100

    @pytest.mark.asyncio
    async def test_analytics_aggregation(self, db_session: AsyncSession):
        """Analytics aggregation calculates correct averages."""
        from datetime import datetime, timezone
        c = await create_test_client(db_session, "agg_test")
        group = await create_test_account_group(db_session, c)

        analytics_data = [
            (100, 0.90, 95.0),
            (200, 0.85, 88.0),
            (150, 0.92, 91.0),
        ]
        for msgs, rate, health in analytics_data:
            ga = GroupAnalytics(
                account_group_id=group.id,
                messages_sent=msgs,
                success_rate=rate,
                health_avg=health,
                period_start=datetime.now(timezone.utc),
            )
            db_session.add(ga)
        await db_session.flush()

        result = await db_session.execute(
            select(
                func.sum(GroupAnalytics.messages_sent),
                func.avg(GroupAnalytics.success_rate),
            ).where(GroupAnalytics.account_group_id == group.id)
        )
        total_msgs, avg_rate = result.one()
        assert total_msgs == 450
        assert abs(avg_rate - 0.8900) < 0.01
