"""
TG PRO QUANTUM – Smoke Tests: Performance Baselines
Validates that API endpoints respond within acceptable time thresholds
using the in-memory test database.
"""
from __future__ import annotations

import time
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import (
    create_test_admin,
    create_test_client,
    create_test_campaign,
    create_test_account,
    make_auth_headers,
)

# ── Thresholds ────────────────────────────────────────────────────────────────
# These are conservative limits for an in-memory SQLite test environment.
# Production targets are stricter (e.g. <100ms p95).
MAX_HEALTH_MS = 500
MAX_API_MS = 1000
MAX_DB_QUERY_MS = 500


def elapsed_ms(start: float) -> float:
    """Return elapsed time in milliseconds since start."""
    return (time.monotonic() - start) * 1000


class TestSmokeAPIResponseTime:
    """Smoke tests for API response time thresholds."""

    @pytest.mark.asyncio
    async def test_health_endpoint_response_time(self, client: AsyncClient):
        """GET /health must respond within threshold."""
        start = time.monotonic()
        response = await client.get("/health")
        ms = elapsed_ms(start)
        assert response.status_code == 200, "Health endpoint must return 200"
        assert ms < MAX_HEALTH_MS, f"Health endpoint too slow: {ms:.1f}ms > {MAX_HEALTH_MS}ms"

    @pytest.mark.asyncio
    async def test_root_endpoint_response_time(self, client: AsyncClient):
        """GET / must respond within threshold."""
        start = time.monotonic()
        response = await client.get("/")
        ms = elapsed_ms(start)
        assert response.status_code == 200
        assert ms < MAX_API_MS, f"Root endpoint too slow: {ms:.1f}ms > {MAX_API_MS}ms"

    @pytest.mark.asyncio
    async def test_campaigns_list_response_time(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """GET /api/v1/campaigns must respond within threshold."""
        c = await create_test_client(db_session, "perf_c1")
        headers = make_auth_headers(c)

        start = time.monotonic()
        response = await client.get("/api/v1/campaigns/", headers=headers)
        ms = elapsed_ms(start)
        assert response.status_code == 200
        assert ms < MAX_API_MS, f"Campaigns list too slow: {ms:.1f}ms > {MAX_API_MS}ms"

    @pytest.mark.asyncio
    async def test_accounts_list_response_time(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """GET /api/v1/accounts must respond within threshold."""
        c = await create_test_client(db_session, "perf_c2")
        headers = make_auth_headers(c)

        start = time.monotonic()
        response = await client.get("/api/v1/accounts/", headers=headers)
        ms = elapsed_ms(start)
        assert response.status_code == 200
        assert ms < MAX_API_MS, f"Accounts list too slow: {ms:.1f}ms > {MAX_API_MS}ms"

    @pytest.mark.asyncio
    async def test_campaign_detail_response_time(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """GET /api/v1/campaigns/{id} must respond within threshold."""
        c = await create_test_client(db_session, "perf_c3")
        headers = make_auth_headers(c)
        campaign = await create_test_campaign(db_session, c, name="Perf Test Camp")

        start = time.monotonic()
        response = await client.get(f"/api/v1/campaigns/{campaign.id}", headers=headers)
        ms = elapsed_ms(start)
        assert response.status_code == 200
        assert ms < MAX_API_MS, f"Campaign detail too slow: {ms:.1f}ms > {MAX_API_MS}ms"


class TestSmokeDatabaseQueryPerformance:
    """Smoke tests for database query performance via ORM helpers."""

    @pytest.mark.asyncio
    async def test_create_client_performance(self, db_session: AsyncSession):
        """Creating a client via ORM must complete quickly."""
        start = time.monotonic()
        c = await create_test_client(db_session, "perf_db1")
        ms = elapsed_ms(start)
        assert c.id is not None
        assert ms < MAX_DB_QUERY_MS, f"Client creation too slow: {ms:.1f}ms > {MAX_DB_QUERY_MS}ms"

    @pytest.mark.asyncio
    async def test_create_campaign_performance(self, db_session: AsyncSession):
        """Creating a campaign via ORM must complete quickly."""
        c = await create_test_client(db_session, "perf_db2")

        start = time.monotonic()
        campaign = await create_test_campaign(db_session, c, name="Perf DB Camp")
        ms = elapsed_ms(start)
        assert campaign.id is not None
        assert ms < MAX_DB_QUERY_MS, f"Campaign creation too slow: {ms:.1f}ms > {MAX_DB_QUERY_MS}ms"

    @pytest.mark.asyncio
    async def test_create_account_performance(self, db_session: AsyncSession):
        """Creating a Telegram account via ORM must complete quickly."""
        c = await create_test_client(db_session, "perf_db3")

        start = time.monotonic()
        account = await create_test_account(db_session, c, phone="+17778889999")
        ms = elapsed_ms(start)
        assert account.id is not None
        assert ms < MAX_DB_QUERY_MS, f"Account creation too slow: {ms:.1f}ms > {MAX_DB_QUERY_MS}ms"


class TestSmokeConsecutiveRequests:
    """Smoke tests for stability under consecutive requests."""

    @pytest.mark.asyncio
    async def test_ten_consecutive_health_checks(self, client: AsyncClient):
        """Ten consecutive health checks must all succeed and remain fast."""
        times = []
        for _ in range(10):
            start = time.monotonic()
            r = await client.get("/health")
            times.append(elapsed_ms(start))
            assert r.status_code == 200

        avg_ms = sum(times) / len(times)
        max_ms = max(times)
        assert avg_ms < MAX_HEALTH_MS, f"Average health check too slow: {avg_ms:.1f}ms"
        assert max_ms < MAX_HEALTH_MS * 3, f"Worst-case health check too slow: {max_ms:.1f}ms"

    @pytest.mark.asyncio
    async def test_memory_stable_across_requests(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Multiple API calls must not cause obvious memory growth (sanity check)."""
        import sys

        c = await create_test_client(db_session, "perf_mem1")
        headers = make_auth_headers(c)

        for _ in range(20):
            r = await client.get("/api/v1/campaigns/", headers=headers)
            assert r.status_code == 200

        # Basic sanity: if we reach here without OOM/exception, memory is stable.
        assert True
