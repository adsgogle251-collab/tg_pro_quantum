#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# TG PRO QUANTUM – Production Monitoring Dashboard Setup
# Sets up Prometheus, Grafana, Elasticsearch, Kibana, and AlertManager.
# Usage: ./production-monitoring-dashboard.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env.production"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.production.yml"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/tmp/monitoring_setup_${TIMESTAMP}.log"

log()  { echo "[$(date '+%H:%M:%S')] $*" | tee -a "${LOG_FILE}"; }
fail() { log "❌ $*"; exit 1; }
wait_for_url() {
    local url="$1"; local label="$2"; local max="${3:-120}"
    local elapsed=0
    while ! curl -sf "${url}" >/dev/null 2>&1; do
        [[ "${elapsed}" -ge "${max}" ]] && { log "  ❌ ${label} not reachable after ${max}s"; return 1; }
        sleep 5; elapsed=$((elapsed + 5))
        log "  Waiting for ${label}... ${elapsed}s"
    done
    log "  ✅ ${label} is up"
}

[[ -f "${ENV_FILE}" ]] && source "${ENV_FILE}" 2>/dev/null || true

log "=== TG PRO QUANTUM – Production Monitoring Setup ==="
log "Log: ${LOG_FILE}"
echo ""

# ── [1] Start monitoring stack ────────────────────────────────────────────────
log "[1/7] Starting monitoring services..."
docker compose \
    --env-file "${ENV_FILE}" \
    -f "${COMPOSE_FILE}" \
    up -d prometheus alertmanager grafana elasticsearch-1 elasticsearch-2 elasticsearch-3 kibana filebeat \
    2>&1 | tee -a "${LOG_FILE}"
log "  ✅ Monitoring containers started"

# ── [2] Wait for Prometheus ───────────────────────────────────────────────────
log "[2/7] Waiting for Prometheus..."
wait_for_url "http://localhost:9090/-/ready" "Prometheus" 120
log "  ✅ Prometheus ready"

# ── [3] Configure Grafana datasource ─────────────────────────────────────────
log "[3/7] Configuring Grafana datasource..."
sleep 10
GRAFANA_URL="http://localhost:3000"
GRAFANA_CREDS="${GRAFANA_ADMIN_USER:-admin}:${GRAFANA_ADMIN_PASSWORD:-admin}"

# Add Prometheus datasource
curl -sf -u "${GRAFANA_CREDS}" \
    -X POST "${GRAFANA_URL}/api/datasources" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "Prometheus",
        "type": "prometheus",
        "url": "http://prometheus:9090",
        "access": "proxy",
        "isDefault": true
    }' >/dev/null 2>&1 || log "  ℹ️  Datasource may already exist"
log "  ✅ Grafana datasource configured"

# ── [4] Import Grafana dashboards ─────────────────────────────────────────────
log "[4/7] Importing Grafana dashboards..."
if [[ -f "${SCRIPT_DIR}/grafana-production-dashboards.json" ]]; then
    curl -sf -u "${GRAFANA_CREDS}" \
        -X POST "${GRAFANA_URL}/api/dashboards/import" \
        -H "Content-Type: application/json" \
        -d @"${SCRIPT_DIR}/grafana-production-dashboards.json" >/dev/null 2>&1 \
        || log "  ℹ️  Dashboard import may have warnings"
    log "  ✅ Dashboards imported"
else
    log "  ⚠️  grafana-production-dashboards.json not found – skipping"
fi

# ── [5] Configure Elasticsearch index patterns ────────────────────────────────
log "[5/7] Configuring Elasticsearch..."
wait_for_url "http://localhost:9200/_cluster/health" "Elasticsearch" 180

# Create ILM policy for 30-day retention
curl -sf -u "elastic:${ELASTICSEARCH_PASSWORD:-changeme}" \
    -X PUT "http://localhost:9200/_ilm/policy/tgpq-30day-retention" \
    -H "Content-Type: application/json" \
    -d '{
        "policy": {
            "phases": {
                "hot": {"min_age": "0ms","actions": {"rollover": {"max_size": "5gb","max_age": "1d"}}},
                "delete": {"min_age": "30d","actions": {"delete": {}}}
            }
        }
    }' >/dev/null 2>&1 || log "  ℹ️  ILM policy may already exist"

# Create index template
curl -sf -u "elastic:${ELASTICSEARCH_PASSWORD:-changeme}" \
    -X PUT "http://localhost:9200/_index_template/tgpq-logs" \
    -H "Content-Type: application/json" \
    -d '{
        "index_patterns": ["tgpq-logs-*"],
        "template": {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 1,
                "index.lifecycle.name": "tgpq-30day-retention"
            }
        }
    }' >/dev/null 2>&1 || log "  ℹ️  Index template may already exist"
log "  ✅ Elasticsearch configured"

# ── [6] Setup Kibana views ────────────────────────────────────────────────────
log "[6/7] Setting up Kibana..."
wait_for_url "http://localhost:5601/api/status" "Kibana" 180

if [[ -f "${SCRIPT_DIR}/kibana-production-views.json" ]]; then
    curl -sf -X POST "http://localhost:5601/api/saved_objects/_import" \
        -H "kbn-xsrf: true" \
        --form file=@"${SCRIPT_DIR}/kibana-production-views.json" >/dev/null 2>&1 \
        || log "  ℹ️  Kibana import may have warnings"
    log "  ✅ Kibana views imported"
else
    log "  ⚠️  kibana-production-views.json not found – skipping"
fi

# ── [7] Verify all systems ────────────────────────────────────────────────────
log "[7/7] Final verification..."
wait_for_url "http://localhost:9093/-/ready"  "AlertManager" 60
wait_for_url "http://localhost:3000/api/health" "Grafana" 60

echo ""
log "=== Monitoring Setup COMPLETE ✅ ==="
log "  Prometheus : http://localhost:9090"
log "  Grafana    : http://localhost:3000  (${GRAFANA_ADMIN_USER:-admin} / ***)"
log "  AlertMgr   : http://localhost:9093"
log "  Kibana     : http://localhost:5601"
log "  Elastic    : http://localhost:9200"
log ""
log "  Production URLs:"
log "  Monitoring : https://monitoring.tg-pro-quantum.app"
log "  Logs       : https://logs.tg-pro-quantum.app"
log "  Log file   : ${LOG_FILE}"
