"""
TG PRO QUANTUM – Smoke Tests: Monitoring & Observability
Validates that monitoring-related endpoints and configurations are accessible.
Since full Prometheus/Grafana/ELK stacks are not spun up in unit test mode,
these tests verify the API's own health/metrics exposure and configuration
file validity.
"""
from __future__ import annotations

import json
import os
import yaml
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import create_test_admin, make_auth_headers

# Path to deploy/staging config files
STAGING_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "deploy", "staging"
)


class TestSmokeMonitoringEndpoints:
    """Validates in-process monitoring/health endpoints."""

    @pytest.mark.asyncio
    async def test_health_endpoint_available(self, client: AsyncClient):
        """GET /health must be available (Prometheus scrape target check)."""
        r = await client.get("/health")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_health_detailed_database_check(self, client: AsyncClient):
        """GET /health/detailed must report database status."""
        r = await client.get("/health/detailed")
        assert r.status_code in (200, 503)
        data = r.json()
        assert "checks" in data
        assert "database" in data["checks"]
        db_check = data["checks"]["database"]
        assert "status" in db_check

    @pytest.mark.asyncio
    async def test_health_detailed_includes_version(self, client: AsyncClient):
        """GET /health/detailed must include application version."""
        r = await client.get("/health/detailed")
        data = r.json()
        assert "version" in data
        assert data["version"]

    @pytest.mark.asyncio
    async def test_openapi_schema_has_health_paths(self, client: AsyncClient):
        """OpenAPI schema must expose /health and /health/detailed paths."""
        r = await client.get("/openapi.json")
        assert r.status_code == 200
        schema = r.json()
        paths = schema.get("paths", {})
        assert "/health" in paths
        assert "/health/detailed" in paths


class TestSmokeConfigFileValidity:
    """Validates that staging deployment configuration files are well-formed."""

    def test_prometheus_config_is_valid_yaml(self):
        """prometheus.staging.yml must be valid YAML."""
        config_path = os.path.join(STAGING_DIR, "prometheus.staging.yml")
        assert os.path.exists(config_path), f"Missing: {config_path}"
        with open(config_path) as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict)
        assert "scrape_configs" in data
        assert "global" in data

    def test_prometheus_rules_is_valid_yaml(self):
        """prometheus-rules.staging.yml must be valid YAML with alert groups."""
        rules_path = os.path.join(STAGING_DIR, "prometheus-rules.staging.yml")
        assert os.path.exists(rules_path), f"Missing: {rules_path}"
        with open(rules_path) as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict)
        assert "groups" in data
        assert len(data["groups"]) > 0

    def test_alertmanager_config_is_valid_yaml(self):
        """alertmanager-staging.yml must be valid YAML with route and receivers."""
        am_path = os.path.join(STAGING_DIR, "alertmanager-staging.yml")
        assert os.path.exists(am_path), f"Missing: {am_path}"
        with open(am_path) as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict)
        assert "route" in data
        assert "receivers" in data

    def test_grafana_dashboard_is_valid_json(self):
        """grafana-dashboards.staging.json must be valid JSON with panels."""
        gf_path = os.path.join(STAGING_DIR, "grafana-dashboards.staging.json")
        assert os.path.exists(gf_path), f"Missing: {gf_path}"
        with open(gf_path) as f:
            data = json.load(f)
        assert isinstance(data, dict)
        assert "panels" in data
        assert len(data["panels"]) > 0
        assert "title" in data

    def test_filebeat_config_is_valid_yaml(self):
        """filebeat-staging.yml must be valid YAML."""
        fb_path = os.path.join(STAGING_DIR, "filebeat-staging.yml")
        assert os.path.exists(fb_path), f"Missing: {fb_path}"
        with open(fb_path) as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict)
        assert "filebeat.inputs" in data
        assert "output.elasticsearch" in data

    def test_docker_compose_is_valid_yaml(self):
        """docker-compose.staging.yml must be valid YAML with required services."""
        dc_path = os.path.join(STAGING_DIR, "docker-compose.staging.yml")
        assert os.path.exists(dc_path), f"Missing: {dc_path}"
        with open(dc_path) as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict)
        assert "services" in data
        services = data["services"]
        required_services = {"db", "redis", "app", "nginx", "prometheus", "grafana"}
        for svc in required_services:
            assert svc in services, f"Missing service: {svc}"

    def test_nginx_config_exists_and_nonempty(self):
        """nginx.staging.conf must exist and be non-empty."""
        nginx_path = os.path.join(STAGING_DIR, "nginx.staging.conf")
        assert os.path.exists(nginx_path), f"Missing: {nginx_path}"
        content = open(nginx_path).read()
        assert len(content) > 100
        assert "upstream" in content
        assert "ssl" in content

    def test_redis_config_exists_and_has_maxmemory(self):
        """redis-staging.conf must exist and configure maxmemory."""
        redis_path = os.path.join(STAGING_DIR, "redis-staging.conf")
        assert os.path.exists(redis_path), f"Missing: {redis_path}"
        content = open(redis_path).read()
        assert "maxmemory" in content
        assert "requirepass" in content
        assert "appendonly" in content


class TestSmokeAlertRulesCompleteness:
    """Validates that all required alert rules are present."""

    REQUIRED_ALERTS = [
        "HighErrorRate",
        "HighResponseTime",
        "APIDown",
        "HighMemoryUsage",
        "HighCPUUsage",
        "LowDiskSpace",
        "DatabaseDown",
        "RedisDown",
        "WebSocketLatencyHigh",
        "CampaignSuccessRateLow",
    ]

    def test_all_required_alerts_defined(self):
        """All required Prometheus alert rules must be defined."""
        rules_path = os.path.join(STAGING_DIR, "prometheus-rules.staging.yml")
        with open(rules_path) as f:
            content = f.read()

        for alert in self.REQUIRED_ALERTS:
            assert alert in content, f"Missing required alert rule: {alert}"

    def test_alerts_have_severity_labels(self):
        """Alert rules must include severity labels."""
        rules_path = os.path.join(STAGING_DIR, "prometheus-rules.staging.yml")
        with open(rules_path) as f:
            data = yaml.safe_load(f)

        for group in data["groups"]:
            for rule in group.get("rules", []):
                if "alert" in rule:
                    assert "severity" in rule.get("labels", {}), (
                        f"Alert '{rule['alert']}' missing severity label"
                    )
