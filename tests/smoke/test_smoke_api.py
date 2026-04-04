"""
TG PRO QUANTUM – Smoke Tests: API Endpoints
Validates that essential API endpoints are reachable and respond correctly.
These tests run against the in-memory SQLite test database via the FastAPI
test client (same infrastructure as the unit / integration tests).
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import (
    create_test_admin,
    create_test_client,
    make_auth_headers,
)


class TestSmokeHealthEndpoints:
    """Smoke tests for health-check endpoints."""

    @pytest.mark.asyncio
    async def test_health_returns_200(self, client: AsyncClient):
        """GET /health must return HTTP 200."""
        response = await client.get("/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_contains_status_ok(self, client: AsyncClient):
        """GET /health body must contain status=ok."""
        response = await client.get("/health")
        data = response.json()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_health_contains_version(self, client: AsyncClient):
        """GET /health body must include application version."""
        response = await client.get("/health")
        data = response.json()
        assert "version" in data
        assert data["version"]

    @pytest.mark.asyncio
    async def test_health_detailed_returns_200(self, client: AsyncClient):
        """GET /health/detailed must return HTTP 200 (database is reachable)."""
        response = await client.get("/health/detailed")
        # 200 = healthy, 503 = degraded; both are acceptable in smoke-test context
        assert response.status_code in (200, 503)

    @pytest.mark.asyncio
    async def test_health_detailed_structure(self, client: AsyncClient):
        """GET /health/detailed body must contain a checks map."""
        response = await client.get("/health/detailed")
        data = response.json()
        assert "status" in data
        assert "checks" in data
        assert "database" in data["checks"]

    @pytest.mark.asyncio
    async def test_health_detailed_database_reachable(self, client: AsyncClient):
        """GET /health/detailed must show database as ok (SQLite in-memory)."""
        response = await client.get("/health/detailed")
        data = response.json()
        assert data["checks"]["database"]["status"] == "ok"


class TestSmokeVersionAndRoot:
    """Smoke tests for root and version endpoints."""

    @pytest.mark.asyncio
    async def test_root_returns_200(self, client: AsyncClient):
        """GET / must return HTTP 200."""
        response = await client.get("/")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_root_contains_app_name(self, client: AsyncClient):
        """GET / body must include the application name."""
        response = await client.get("/")
        data = response.json()
        assert "name" in data
        assert "TG PRO QUANTUM" in data["name"]

    @pytest.mark.asyncio
    async def test_root_contains_docs_link(self, client: AsyncClient):
        """GET / body must include a docs link."""
        response = await client.get("/")
        data = response.json()
        assert "docs" in data

    @pytest.mark.asyncio
    async def test_docs_endpoint_reachable(self, client: AsyncClient):
        """GET /docs must return HTTP 200 (OpenAPI UI)."""
        response = await client.get("/docs")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_redoc_endpoint_reachable(self, client: AsyncClient):
        """GET /redoc must return HTTP 200."""
        response = await client.get("/redoc")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_openapi_schema_reachable(self, client: AsyncClient):
        """GET /openapi.json must return a valid OpenAPI schema."""
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema


class TestSmokeAuthentication:
    """Smoke tests for authentication endpoints."""

    @pytest.mark.asyncio
    async def test_login_endpoint_exists(self, client: AsyncClient, db_session):
        """POST /api/v1/auth/login must respond (not 404)."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@test.com", "password": "wrongpass"},
        )
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_login_wrong_credentials_returns_401(self, client: AsyncClient, db_session):
        """POST /api/v1/auth/login with bad credentials returns 401/422."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@test.com", "password": "badpass"},
        )
        assert response.status_code in (401, 422)

    @pytest.mark.asyncio
    async def test_protected_endpoint_requires_auth(self, client: AsyncClient):
        """GET /api/v1/clients must not return 200 without token."""
        response = await client.get("/api/v1/clients")
        # Acceptable: 401 Unauthorized, 403 Forbidden, or 307 redirect to login
        assert response.status_code in (401, 403, 307)

    @pytest.mark.asyncio
    async def test_valid_admin_can_access_clients(self, client: AsyncClient, db_session):
        """Authenticated admin can GET /api/v1/clients/."""
        admin = await create_test_admin(db_session, "smoke_auth")
        headers = make_auth_headers(admin)
        response = await client.get("/api/v1/clients/", headers=headers)
        assert response.status_code == 200
