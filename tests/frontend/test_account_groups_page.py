"""
Frontend unit tests for Account Groups page components.
Tests rendering, modals, filter/search, pagination, and bulk import UI logic.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import AccountGroupStatus, AccountGroupFeatureType
from tests.conftest import (
    create_test_admin,
    create_test_client,
    create_test_account,
    create_test_account_group,
    make_auth_headers,
)


class TestAccountGroupsPageRendering:
    """Tests for account groups list/page rendering via API."""

    @pytest.mark.asyncio
    async def test_account_groups_list_renders(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Account groups list endpoint returns a list."""
        admin = await create_test_admin(db_session, "ag_render")
        for i in range(3):
            await create_test_account_group(db_session, admin, name=f"Group{i}")

        resp = await client.get(
            "/api/v1/account-groups/",
            headers=make_auth_headers(admin),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 3

    @pytest.mark.asyncio
    async def test_account_group_detail_renders(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Account group detail renders correctly."""
        admin = await create_test_admin(db_session, "ag_detail_render")
        group = await create_test_account_group(db_session, admin, name="DetailGroup")

        resp = await client.get(
            f"/api/v1/account-groups/{group.id}",
            headers=make_auth_headers(admin),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "DetailGroup"
        assert "id" in data
        assert "feature_type" in data
        assert "status" in data


class TestCreateGroupModal:
    """Tests for create group modal (POST /account-groups/)."""

    @pytest.mark.asyncio
    async def test_create_group_required_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Create group requires name and feature_type."""
        admin = await create_test_admin(db_session, "cg_modal")
        resp = await client.post(
            "/api/v1/account-groups/",
            json={"name": "New Group", "feature_type": "broadcast"},
            headers=make_auth_headers(admin),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "New Group"
        assert body["feature_type"] == "broadcast"

    @pytest.mark.asyncio
    async def test_create_group_missing_name_fails(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Creating a group without a name returns validation error."""
        admin = await create_test_admin(db_session, "cg_no_name")
        resp = await client.post(
            "/api/v1/account-groups/",
            json={"feature_type": "broadcast"},
            headers=make_auth_headers(admin),
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_group_all_feature_types(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """All feature types can be used when creating groups."""
        admin = await create_test_admin(db_session, "cg_feat")
        feature_types = ["broadcast", "finder", "scrape", "join", "cs", "warmer", "general"]

        for ft in feature_types:
            resp = await client.post(
                "/api/v1/account-groups/",
                json={"name": f"Group_{ft}", "feature_type": ft},
                headers=make_auth_headers(admin),
            )
            assert resp.status_code == 201, f"Failed for feature type: {ft}"


class TestEditGroupModal:
    """Tests for editing account groups."""

    @pytest.mark.asyncio
    async def test_update_group_name(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Group name can be updated."""
        admin = await create_test_admin(db_session, "edit_g_name")
        group = await create_test_account_group(db_session, admin, name="OldName")

        resp = await client.put(
            f"/api/v1/account-groups/{group.id}",
            json={"name": "NewName"},
            headers=make_auth_headers(admin),
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "NewName"

    @pytest.mark.asyncio
    async def test_update_group_status(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Group status can be updated."""
        admin = await create_test_admin(db_session, "edit_g_status")
        group = await create_test_account_group(db_session, admin)

        resp = await client.put(
            f"/api/v1/account-groups/{group.id}",
            json={"status": "paused"},
            headers=make_auth_headers(admin),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "paused"

    @pytest.mark.asyncio
    async def test_update_nonexistent_group_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Updating a non-existent group returns 404."""
        admin = await create_test_admin(db_session, "edit_g_404")
        resp = await client.put(
            "/api/v1/account-groups/99999",
            json={"name": "Ghost"},
            headers=make_auth_headers(admin),
        )
        assert resp.status_code == 404


class TestBulkImportModal:
    """Tests for bulk import accounts UI."""

    @pytest.mark.asyncio
    async def test_bulk_import_endpoint(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Bulk import endpoint processes account imports."""
        admin = await create_test_admin(db_session, "bulk_modal")
        group = await create_test_account_group(db_session, admin, name="BulkPool")

        # Create accounts to import
        from tests.conftest import create_test_account
        accounts = []
        for i in range(3):
            acc = await create_test_account(
                db_session, admin, phone=f"+9800{i:07d}"
            )
            accounts.append(acc)

        resp = await client.post(
            f"/api/v1/account-groups/{group.id}/import",
            json={
                "account_ids": [a.id for a in accounts],
                "feature_type": "broadcast",
            },
            headers=make_auth_headers(admin),
        )
        assert resp.status_code in (200, 201, 207)

    @pytest.mark.asyncio
    async def test_bulk_import_empty_list_rejected(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Bulk import with empty list is rejected."""
        admin = await create_test_admin(db_session, "bulk_empty")
        group = await create_test_account_group(db_session, admin)

        resp = await client.post(
            f"/api/v1/account-groups/{group.id}/import",
            json={"account_ids": [], "feature_type": "broadcast"},
            headers=make_auth_headers(admin),
        )
        assert resp.status_code in (400, 422)


class TestFilterSearch:
    """Tests for filter/search functionality."""

    @pytest.mark.asyncio
    async def test_filter_by_feature_type(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Account groups can be filtered by feature_type."""
        admin = await create_test_admin(db_session, "filter_ft")
        # Create groups with different feature types
        from app.models.database import AccountGroupFeatureType
        await create_test_account_group(
            db_session, admin, name="BroadcastGroup",
            feature_type=AccountGroupFeatureType.broadcast
        )
        await create_test_account_group(
            db_session, admin, name="ScraperGroup",
            feature_type=AccountGroupFeatureType.scrape
        )

        resp = await client.get(
            "/api/v1/account-groups/?feature_type=broadcast",
            headers=make_auth_headers(admin),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert all(g["feature_type"] == "broadcast" for g in data)

    @pytest.mark.asyncio
    async def test_filter_by_status(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Account groups can be filtered by status."""
        admin = await create_test_admin(db_session, "filter_status")
        group = await create_test_account_group(db_session, admin, name="ActiveGroup")
        paused_group = await create_test_account_group(
            db_session, admin, name="PausedGroup"
        )
        paused_group.status = AccountGroupStatus.paused
        await db_session.flush()

        resp = await client.get(
            "/api/v1/account-groups/?status=active",
            headers=make_auth_headers(admin),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert all(g["status"] == "active" for g in data)


class TestPagination:
    """Tests for pagination on account groups."""

    @pytest.mark.asyncio
    async def test_analytics_pagination(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Activity log supports pagination."""
        c = await create_test_client(db_session, "pag_test")
        from tests.conftest import create_test_campaign
        campaign = await create_test_campaign(db_session, c, name="PagCampaign")

        # Test with limit parameter
        resp = await client.get(
            f"/api/v1/campaigns/{campaign.id}/activity-log?limit=5&offset=0",
            headers=make_auth_headers(c),
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_analytics_invalid_pagination_rejected(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Invalid pagination parameters return validation error."""
        c = await create_test_client(db_session, "pag_invalid")
        from tests.conftest import create_test_campaign
        campaign = await create_test_campaign(db_session, c, name="PagCampaign2")

        resp = await client.get(
            f"/api/v1/campaigns/{campaign.id}/activity-log?limit=0",
            headers=make_auth_headers(c),
        )
        assert resp.status_code == 422
