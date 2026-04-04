"""
Unit tests for Account Groups service / API routes.
Tests CRUD operations, bulk import, health, analytics, and client isolation.
"""
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import (
    AccountGroup, AccountAssignment, AccountHealth, GroupAnalytics,
    AccountGroupFeatureType, AccountGroupStatus, TelegramAccount, AccountStatus,
)
from tests.conftest import (
    create_test_admin,
    create_test_client,
    create_test_account,
    create_test_account_group,
    make_auth_headers,
)


class TestAccountGroupCRUD:
    """Tests for AccountGroup create/read/update/delete."""

    @pytest.mark.asyncio
    async def test_create_account_group(self, db_session: AsyncSession):
        """Create an account group and verify persisted fields."""
        client = await create_test_client(db_session, "ag_create")
        group = await create_test_account_group(db_session, client, name="BroadcastPool")

        assert group.id is not None
        assert group.name == "BroadcastPool"
        assert group.feature_type == AccountGroupFeatureType.broadcast
        assert group.status == AccountGroupStatus.active
        assert group.client_id == client.id

    @pytest.mark.asyncio
    async def test_update_account_group(self, db_session: AsyncSession):
        """Update name and status of an account group."""
        client = await create_test_client(db_session, "ag_update")
        group = await create_test_account_group(db_session, client)

        group.name = "UpdatedPool"
        group.status = AccountGroupStatus.paused
        await db_session.flush()
        await db_session.refresh(group)

        assert group.name == "UpdatedPool"
        assert group.status == AccountGroupStatus.paused

    @pytest.mark.asyncio
    async def test_delete_account_group(self, db_session: AsyncSession):
        """Delete an account group and verify it is removed."""
        client = await create_test_client(db_session, "ag_del")
        group = await create_test_account_group(db_session, client, name="ToDelete")
        group_id = group.id

        await db_session.delete(group)
        await db_session.flush()

        result = await db_session.execute(
            select(AccountGroup).where(AccountGroup.id == group_id)
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_bulk_import_accounts(self, db_session: AsyncSession):
        """Bulk-assign 1000+ accounts to a group."""
        client = await create_test_client(db_session, "ag_bulk")
        group = await create_test_account_group(db_session, client, name="BulkPool")

        accounts = []
        for i in range(1100):
            acc = TelegramAccount(
                client_id=client.id,
                name=f"BulkAcc{i}",
                phone=f"+2000{i:06d}",
                status=AccountStatus.active,
                health_score=100.0,
            )
            db_session.add(acc)
            accounts.append(acc)

        await db_session.flush()

        assignments = [
            AccountAssignment(
                account_id=acc.id,
                account_group_id=group.id,
                feature_type="broadcast",
                status="active",
            )
            for acc in accounts
        ]
        for asgn in assignments:
            db_session.add(asgn)
        await db_session.flush()

        result = await db_session.execute(
            select(AccountAssignment).where(
                AccountAssignment.account_group_id == group.id
            )
        )
        assert len(result.scalars().all()) == 1100

    @pytest.mark.asyncio
    async def test_get_group_health(self, db_session: AsyncSession):
        """Retrieve health records for a group."""
        client = await create_test_client(db_session, "ag_health")
        account = await create_test_account(db_session, client, phone="+31111111111")
        group = await create_test_account_group(db_session, client)

        health = AccountHealth(
            account_id=account.id,
            account_group_id=group.id,
            health_score=85.5,
            warnings=1,
            is_banned=False,
            details={"reason": "minor_flood"},
        )
        db_session.add(health)
        await db_session.flush()

        result = await db_session.execute(
            select(AccountHealth).where(
                AccountHealth.account_group_id == group.id
            )
        )
        records = result.scalars().all()
        assert len(records) == 1
        assert records[0].health_score == 85.5
        assert records[0].warnings == 1

    @pytest.mark.asyncio
    async def test_get_group_analytics(self, db_session: AsyncSession):
        """Retrieve analytics records for a group."""
        from datetime import datetime, timezone
        client = await create_test_client(db_session, "ag_analytics")
        group = await create_test_account_group(db_session, client)

        analytics = GroupAnalytics(
            account_group_id=group.id,
            messages_sent=500,
            success_rate=0.92,
            health_avg=95.0,
            period_start=datetime.now(timezone.utc),
        )
        db_session.add(analytics)
        await db_session.flush()

        result = await db_session.execute(
            select(GroupAnalytics).where(
                GroupAnalytics.account_group_id == group.id
            )
        )
        records = result.scalars().all()
        assert len(records) == 1
        assert records[0].messages_sent == 500
        assert records[0].success_rate == pytest.approx(0.92)

    @pytest.mark.asyncio
    async def test_client_isolation_account_groups(self, db_session: AsyncSession):
        """Two clients cannot see each other's account groups."""
        client_a = await create_test_client(db_session, "iso_a")
        client_b = await create_test_client(db_session, "iso_b")

        group_a = await create_test_account_group(db_session, client_a, name="GroupA")
        group_b = await create_test_account_group(db_session, client_b, name="GroupB")

        result_a = await db_session.execute(
            select(AccountGroup).where(AccountGroup.client_id == client_a.id)
        )
        result_b = await db_session.execute(
            select(AccountGroup).where(AccountGroup.client_id == client_b.id)
        )

        groups_a = result_a.scalars().all()
        groups_b = result_b.scalars().all()

        assert all(g.client_id == client_a.id for g in groups_a)
        assert all(g.client_id == client_b.id for g in groups_b)
        assert group_b.id not in {g.id for g in groups_a}
        assert group_a.id not in {g.id for g in groups_b}

    @pytest.mark.asyncio
    async def test_different_feature_types(self, db_session: AsyncSession):
        """Account groups can have different feature types."""
        client = await create_test_client(db_session, "ft")
        feature_types = [
            AccountGroupFeatureType.broadcast,
            AccountGroupFeatureType.scrape,
            AccountGroupFeatureType.join,
            AccountGroupFeatureType.finder,
            AccountGroupFeatureType.warmer,
            AccountGroupFeatureType.cs,
            AccountGroupFeatureType.general,
        ]
        for ft in feature_types:
            group = AccountGroup(
                name=f"Group_{ft.value}",
                feature_type=ft,
                status=AccountGroupStatus.active,
                client_id=client.id,
            )
            db_session.add(group)
        await db_session.flush()

        result = await db_session.execute(
            select(AccountGroup).where(AccountGroup.client_id == client.id)
        )
        created = result.scalars().all()
        assert len(created) == len(feature_types)

    @pytest.mark.asyncio
    async def test_cascade_delete_removes_assignments(self, db_session: AsyncSession):
        """Deleting an AccountGroup cascades to AccountAssignment rows."""
        client = await create_test_client(db_session, "casc")
        account = await create_test_account(db_session, client, phone="+49999999999")
        group = await create_test_account_group(db_session, client, name="CascGroup")

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


class TestAccountGroupAPI:
    """Integration-style tests for account groups API endpoints."""

    @pytest.mark.asyncio
    async def test_list_account_groups_admin(self, client, db_session):
        admin = await create_test_admin(db_session, "list_ag")
        await create_test_account_group(db_session, admin, name="AdminPool")

        resp = await client.get(
            "/api/v1/account-groups/",
            headers=make_auth_headers(admin),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_create_account_group_via_api(self, client, db_session):
        admin = await create_test_admin(db_session, "create_ag_api")

        payload = {
            "name": "API Pool",
            "feature_type": "broadcast",
            "config": {},
        }
        resp = await client.post(
            "/api/v1/account-groups/",
            json=payload,
            headers=make_auth_headers(admin),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "API Pool"
        assert body["feature_type"] == "broadcast"

    @pytest.mark.asyncio
    async def test_get_account_group_by_id(self, client, db_session):
        admin = await create_test_admin(db_session, "get_ag")
        group = await create_test_account_group(db_session, admin, name="GetPool")

        resp = await client.get(
            f"/api/v1/account-groups/{group.id}",
            headers=make_auth_headers(admin),
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "GetPool"

    @pytest.mark.asyncio
    async def test_nonexistent_group_returns_404(self, client, db_session):
        admin = await create_test_admin(db_session, "404ag")
        resp = await client.get(
            "/api/v1/account-groups/999999",
            headers=make_auth_headers(admin),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_unauthenticated_request_returns_401(self, client):
        resp = await client.get("/api/v1/account-groups/")
        assert resp.status_code == 401
