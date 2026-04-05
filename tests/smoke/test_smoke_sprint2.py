"""
TG PRO QUANTUM – Sprint 2 Feature Tests

Tests for new Sprint 2 endpoints:
- /users/me profile endpoints
- /settings endpoints
- /notifications endpoint
- /analytics/dashboard, /analytics/charts, /analytics/timeline
- /admin/users management
- /admin/stats
- /admin/audit-logs
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import (
    create_test_admin,
    create_test_client,
    create_test_campaign,
    make_auth_headers,
)


class TestProfileEndpoints:
    """Tests for /users/me endpoints."""

    @pytest.mark.asyncio
    async def test_get_profile(self, client: AsyncClient, db_session: AsyncSession):
        """GET /users/me returns current user profile."""
        user = await create_test_client(db_session, "profile1")
        headers = make_auth_headers(user)
        resp = await client.get("/api/v1/users/me", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == user.email
        assert data["id"] == user.id

    @pytest.mark.asyncio
    async def test_update_profile_name(self, client: AsyncClient, db_session: AsyncSession):
        """PATCH /users/me updates the user's name."""
        user = await create_test_client(db_session, "profile2")
        headers = make_auth_headers(user)
        resp = await client.patch(
            "/api/v1/users/me",
            json={"name": "Updated Name"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_change_password(self, client: AsyncClient, db_session: AsyncSession):
        """POST /users/me/change-password changes the password."""
        user = await create_test_client(db_session, "profile3")
        headers = make_auth_headers(user)
        resp = await client.post(
            "/api/v1/users/me/change-password",
            json={"current_password": "clientpass", "new_password": "NewPass@456"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, client: AsyncClient, db_session: AsyncSession):
        """POST /users/me/change-password with wrong current password returns 400."""
        user = await create_test_client(db_session, "profile4")
        headers = make_auth_headers(user)
        resp = await client.post(
            "/api/v1/users/me/change-password",
            json={"current_password": "wrongpass", "new_password": "NewPass@456"},
            headers=headers,
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_list_api_keys(self, client: AsyncClient, db_session: AsyncSession):
        """GET /users/me/api-keys returns list."""
        user = await create_test_client(db_session, "profile5")
        headers = make_auth_headers(user)
        resp = await client.get("/api/v1/users/me/api-keys", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_create_api_key(self, client: AsyncClient, db_session: AsyncSession):
        """POST /users/me/api-keys creates a new API key."""
        user = await create_test_client(db_session, "profile6")
        headers = make_auth_headers(user)
        resp = await client.post("/api/v1/users/me/api-keys", json={}, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert "api_key" in data or "key_preview" in data

    @pytest.mark.asyncio
    async def test_profile_unauthenticated(self, client: AsyncClient):
        """GET /users/me without token returns 401."""
        resp = await client.get("/api/v1/users/me")
        assert resp.status_code == 401


class TestSettingsEndpoints:
    """Tests for /settings endpoints."""

    @pytest.mark.asyncio
    async def test_get_settings(self, client: AsyncClient, db_session: AsyncSession):
        """GET /settings returns default settings."""
        user = await create_test_client(db_session, "settings1")
        headers = make_auth_headers(user)
        resp = await client.get("/api/v1/settings/", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "theme" in data
        assert "language" in data

    @pytest.mark.asyncio
    async def test_update_settings(self, client: AsyncClient, db_session: AsyncSession):
        """PUT /settings updates user settings."""
        user = await create_test_client(db_session, "settings2")
        headers = make_auth_headers(user)
        resp = await client.put(
            "/api/v1/settings/",
            json={"theme": "light", "language": "id"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Settings updated"

    @pytest.mark.asyncio
    async def test_get_preferences(self, client: AsyncClient, db_session: AsyncSession):
        """GET /settings/preferences returns notification and privacy prefs."""
        user = await create_test_client(db_session, "settings3")
        headers = make_auth_headers(user)
        resp = await client.get("/api/v1/settings/preferences", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "notifications" in data
        assert "privacy" in data

    @pytest.mark.asyncio
    async def test_update_preferences(self, client: AsyncClient, db_session: AsyncSession):
        """PUT /settings/preferences updates notification preferences."""
        user = await create_test_client(db_session, "settings4")
        headers = make_auth_headers(user)
        resp = await client.put(
            "/api/v1/settings/preferences",
            json={"notifications": {"email": False}},
            headers=headers,
        )
        assert resp.status_code == 200


class TestAnalyticsEndpoints:
    """Tests for new analytics endpoints."""

    @pytest.mark.asyncio
    async def test_analytics_dashboard(self, client: AsyncClient, db_session: AsyncSession):
        """GET /analytics/dashboard returns dashboard stats."""
        user = await create_test_client(db_session, "analytics1")
        headers = make_auth_headers(user)
        resp = await client.get("/api/v1/analytics/dashboard", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_campaigns" in data
        assert "total_accounts" in data
        assert "total_sent" in data

    @pytest.mark.asyncio
    async def test_analytics_dashboard_with_data(self, client: AsyncClient, db_session: AsyncSession):
        """Analytics dashboard counts are correct after adding campaign."""
        user = await create_test_client(db_session, "analytics2")
        await create_test_campaign(db_session, user, name="Analytics Test Camp")
        headers = make_auth_headers(user)
        resp = await client.get("/api/v1/analytics/dashboard", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_campaigns"] >= 1

    @pytest.mark.asyncio
    async def test_analytics_charts(self, client: AsyncClient, db_session: AsyncSession):
        """GET /analytics/charts returns chart data."""
        user = await create_test_client(db_session, "analytics3")
        headers = make_auth_headers(user)
        resp = await client.get("/api/v1/analytics/charts", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "bar" in data
        assert "pie" in data
        assert "line" in data

    @pytest.mark.asyncio
    async def test_analytics_timeline(self, client: AsyncClient, db_session: AsyncSession):
        """GET /analytics/timeline returns list."""
        user = await create_test_client(db_session, "analytics4")
        headers = make_auth_headers(user)
        resp = await client.get("/api/v1/analytics/timeline", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestAdminUserManagement:
    """Tests for /admin/users endpoints."""

    @pytest.mark.asyncio
    async def test_list_users_admin(self, client: AsyncClient, db_session: AsyncSession):
        """GET /admin/users returns paginated list for admin."""
        admin = await create_test_admin(db_session, "admgmt1")
        await create_test_client(db_session, "admgmt1u")
        headers = make_auth_headers(admin)
        resp = await client.get("/api/v1/admin/users", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert data["total"] >= 2

    @pytest.mark.asyncio
    async def test_list_users_non_admin_forbidden(self, client: AsyncClient, db_session: AsyncSession):
        """GET /admin/users returns 403 for non-admin."""
        user = await create_test_client(db_session, "admgmt2")
        headers = make_auth_headers(user)
        resp = await client.get("/api/v1/admin/users", headers=headers)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_create_user_admin(self, client: AsyncClient, db_session: AsyncSession):
        """POST /admin/users creates a new user (admin only)."""
        admin = await create_test_admin(db_session, "admgmt3")
        headers = make_auth_headers(admin)
        resp = await client.post(
            "/api/v1/admin/users",
            json={
                "name": "New User Via Admin",
                "email": "newuser_admin@test.com",
                "password": "SecurePass123!",
                "plan_type": "starter",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "newuser_admin@test.com"
        assert not data["is_admin"]

    @pytest.mark.asyncio
    async def test_get_user_admin(self, client: AsyncClient, db_session: AsyncSession):
        """GET /admin/users/{id} returns user details."""
        admin = await create_test_admin(db_session, "admgmt4")
        user = await create_test_client(db_session, "admgmt4u")
        headers = make_auth_headers(admin)
        resp = await client.get(f"/api/v1/admin/users/{user.id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == user.id

    @pytest.mark.asyncio
    async def test_suspend_user(self, client: AsyncClient, db_session: AsyncSession):
        """PUT /admin/users/{id}/suspend suspends a user."""
        admin = await create_test_admin(db_session, "admgmt5")
        user = await create_test_client(db_session, "admgmt5u")
        headers = make_auth_headers(admin)
        resp = await client.put(f"/api/v1/admin/users/{user.id}/suspend", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "suspended"

    @pytest.mark.asyncio
    async def test_restore_user(self, client: AsyncClient, db_session: AsyncSession):
        """PUT /admin/users/{id}/restore restores a suspended user."""
        admin = await create_test_admin(db_session, "admgmt6")
        user = await create_test_client(db_session, "admgmt6u")
        headers = make_auth_headers(admin)
        # Suspend first
        await client.put(f"/api/v1/admin/users/{user.id}/suspend", headers=headers)
        # Then restore
        resp = await client.put(f"/api/v1/admin/users/{user.id}/restore", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

    @pytest.mark.asyncio
    async def test_delete_user(self, client: AsyncClient, db_session: AsyncSession):
        """DELETE /admin/users/{id} deletes a user."""
        admin = await create_test_admin(db_session, "admgmt7")
        user = await create_test_client(db_session, "admgmt7u")
        headers = make_auth_headers(admin)
        resp = await client.delete(f"/api/v1/admin/users/{user.id}", headers=headers)
        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_admin_cannot_delete_self(self, client: AsyncClient, db_session: AsyncSession):
        """DELETE /admin/users/{id} returns 400 when admin tries to delete themselves."""
        admin = await create_test_admin(db_session, "admgmt8")
        headers = make_auth_headers(admin)
        resp = await client.delete(f"/api/v1/admin/users/{admin.id}", headers=headers)
        assert resp.status_code == 400


class TestAdminStats:
    """Tests for /admin/stats endpoint."""

    @pytest.mark.asyncio
    async def test_admin_stats(self, client: AsyncClient, db_session: AsyncSession):
        """GET /admin/stats returns system statistics."""
        admin = await create_test_admin(db_session, "admstats1")
        headers = make_auth_headers(admin)
        resp = await client.get("/api/v1/admin/stats", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_users" in data
        assert "active_users" in data
        assert "total_campaigns" in data
        assert "system_health" in data

    @pytest.mark.asyncio
    async def test_admin_stats_non_admin_forbidden(self, client: AsyncClient, db_session: AsyncSession):
        """GET /admin/stats returns 403 for non-admin."""
        user = await create_test_client(db_session, "admstats2")
        headers = make_auth_headers(user)
        resp = await client.get("/api/v1/admin/stats", headers=headers)
        assert resp.status_code == 403


class TestAdminAuditLogs:
    """Tests for /admin/audit-logs endpoint."""

    @pytest.mark.asyncio
    async def test_admin_audit_logs(self, client: AsyncClient, db_session: AsyncSession):
        """GET /admin/audit-logs returns paginated audit logs."""
        admin = await create_test_admin(db_session, "admaudit1")
        headers = make_auth_headers(admin)
        resp = await client.get("/api/v1/admin/audit-logs", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_admin_audit_logs_non_admin_forbidden(self, client: AsyncClient, db_session: AsyncSession):
        """GET /admin/audit-logs returns 403 for non-admin."""
        user = await create_test_client(db_session, "admaudit2")
        headers = make_auth_headers(user)
        resp = await client.get("/api/v1/admin/audit-logs", headers=headers)
        assert resp.status_code == 403


class TestNotificationsEndpoints:
    """Tests for /notifications endpoints."""

    @pytest.mark.asyncio
    async def test_list_notifications(self, client: AsyncClient, db_session: AsyncSession):
        """GET /notifications returns a list."""
        user = await create_test_client(db_session, "notif1")
        headers = make_auth_headers(user)
        resp = await client.get("/api/v1/notifications/", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_mark_notification_read(self, client: AsyncClient, db_session: AsyncSession):
        """PATCH /notifications/{id}/read returns success."""
        user = await create_test_client(db_session, "notif2")
        headers = make_auth_headers(user)
        resp = await client.patch("/api/v1/notifications/1/read", headers=headers)
        assert resp.status_code == 200
        assert "message" in resp.json()
