# Production Troubleshooting Guide

## TG PRO QUANTUM – Production Troubleshooting Reference

**Version:** 1.0  
**Environment:** Production  
**Updated:** 2024

---

## 1. Common Issues & Solutions

### 1.1 Service Unresponsive / 502 Bad Gateway

**Symptoms:** Nginx returns 502, health check fails.

**Diagnosis:**
```bash
# Check container status
docker ps --filter "name=tgpq-prod-app"

# Check health status
docker inspect -f '{{.State.Health.Status}}' tgpq-prod-app-blue-1

# Check recent logs
docker logs --tail=100 tgpq-prod-app-blue-1

# Check if process is running inside container
docker exec tgpq-prod-app-blue-1 ps aux
```

**Resolution:**
```bash
# Restart specific instance
docker restart tgpq-prod-app-blue-1

# If all instances down, restart full blue stack
docker compose --env-file .env.production -f docker-compose.production.yml \
  --profile blue restart

# If still failing, run rollback
./rollback-production.sh --reason "service_unresponsive"
```

---

### 1.2 High Error Rate (>0.5%)

**Symptoms:** Prometheus alert `ErrorRateWarning` firing.

**Diagnosis:**
```bash
# Check Prometheus error rate
curl -s "http://localhost:9090/api/v1/query?query=sum(rate(http_requests_total{status=~\"5..\"}[5m]))/sum(rate(http_requests_total[5m]))*100" \
  | python3 -m json.tool

# Find error endpoints in Kibana:
# Index: tgpq-logs-*
# Filter: level:error AND service:fastapi
# Sort: @timestamp desc

# Check recent application errors
docker logs --tail=200 tgpq-prod-app-blue-1 2>&1 | grep -i "error\|exception\|traceback"
```

**Resolution:**
- If database errors: check Section 1.4
- If Redis errors: check Section 1.5
- If application errors: check application logs and redeploy if needed
- If persistent >2%: trigger rollback

---

### 1.3 High Response Time (>200ms p95)

**Symptoms:** API responses slow, users complaining.

**Diagnosis:**
```bash
# Check Prometheus response time
curl -s "http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,sum(rate(http_request_duration_seconds_bucket[5m]))by(le))*1000"

# Find slow endpoints (Kibana query):
# Index: tgpq-logs-*
# Filter: duration_ms > 200
# Group by: path

# Check database slow queries
docker exec tgpq-prod-db-primary psql -U tgpq_prod tg_quantum_prod -c \
  "SELECT query, mean_exec_time, calls FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# Check Redis latency
docker exec tgpq-prod-redis-1 redis-cli -a "${REDIS_PASSWORD}" --latency
```

**Resolution:**
- Add database indexes for slow queries
- Check Redis cache hit rate (target >90%)
- Review N+1 query patterns in application code
- Scale up worker replicas if CPU-bound

---

### 1.4 Database Issues

**Symptoms:** `DatabaseDown` alert, connection errors in logs.

**Diagnosis:**
```bash
# Check PostgreSQL status
docker exec tgpq-prod-db-primary pg_isready -U tgpq_prod

# Check active connections
docker exec tgpq-prod-db-primary psql -U tgpq_prod tg_quantum_prod -c \
  "SELECT count(*), state FROM pg_stat_activity GROUP BY state;"

# Check for locks
docker exec tgpq-prod-db-primary psql -U tgpq_prod tg_quantum_prod -c \
  "SELECT pid, query, state, wait_event FROM pg_stat_activity WHERE wait_event IS NOT NULL;"

# Check replication lag
docker exec tgpq-prod-db-primary psql -U tgpq_prod -c \
  "SELECT client_addr, state, sent_lsn, replay_lsn, (sent_lsn - replay_lsn) AS replication_lag FROM pg_stat_replication;"
```

**Resolution:**
```bash
# Restart primary if needed
docker restart tgpq-prod-db-primary

# Kill blocking queries
docker exec tgpq-prod-db-primary psql -U tgpq_prod tg_quantum_prod -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state='idle in transaction' AND query_start < NOW() - INTERVAL '5 min';"

# Promote replica (disaster recovery)
./restore-production-database.sh
```

---

### 1.5 Redis Issues

**Symptoms:** `RedisDown` alert, cache misses spike.

**Diagnosis:**
```bash
# Check Redis status
docker exec tgpq-prod-redis-1 redis-cli -a "${REDIS_PASSWORD}" ping

# Check Redis info
docker exec tgpq-prod-redis-1 redis-cli -a "${REDIS_PASSWORD}" info server | head -20
docker exec tgpq-prod-redis-1 redis-cli -a "${REDIS_PASSWORD}" info memory
docker exec tgpq-prod-redis-1 redis-cli -a "${REDIS_PASSWORD}" info replication

# Check slow log
docker exec tgpq-prod-redis-1 redis-cli -a "${REDIS_PASSWORD}" slowlog get 10
```

**Resolution:**
```bash
# Restart Redis node
docker restart tgpq-prod-redis-1

# Clear cache if corrupted (WARNING: cache miss spike expected)
docker exec tgpq-prod-redis-1 redis-cli -a "${REDIS_PASSWORD}" flushdb async

# Check and fix replica sync
docker exec tgpq-prod-redis-2 redis-cli -a "${REDIS_PASSWORD}" replicaof redis-1 6379
```

---

### 1.6 WebSocket Connection Issues

**Symptoms:** Clients disconnecting, real-time features not working.

**Diagnosis:**
```bash
# Check WebSocket logs
docker logs tgpq-prod-app-blue-1 2>&1 | grep -i "websocket\|ws"

# Check nginx WebSocket config
docker exec tgpq-prod-nginx nginx -t

# Test WebSocket connectivity (requires wscat)
wscat -c "wss://api.tg-pro-quantum.app/ws" -H "Authorization: Bearer TOKEN"

# Check active WebSocket connections metric
curl -s "http://localhost:9090/api/v1/query?query=websocket_connections_active"
```

**Resolution:**
- Check nginx `proxy_read_timeout` is set to 3600s
- Verify `Upgrade` and `Connection` headers passed through
- Check application heartbeat interval matches client

---

## 2. Log Search Patterns (Kibana/Elasticsearch)

```
# All errors in last 1 hour
level:error AND @timestamp:[now-1h TO now]

# Specific client errors
level:error AND client_id:"CLIENT_ID"

# Slow API requests
duration_ms:>200

# Authentication failures
action:login AND result:failure

# Campaign errors
service:broadcast AND level:error

# 5xx HTTP responses
status_code:>=500

# Database connection errors
message:*connection*refused* OR message:*too many connections*
```

---

## 3. Performance Troubleshooting

### Quick Performance Snapshot
```bash
# API response time distribution
curl -s "http://localhost:9090/api/v1/query?query=histogram_quantile(0.99,sum(rate(http_request_duration_seconds_bucket[10m]))by(le,handler))" | python3 -m json.tool

# Top 10 slowest endpoints
docker logs tgpq-prod-app-blue-1 2>&1 | python3 -c "
import sys, json
entries = []
for line in sys.stdin:
    try:
        d = json.loads(line)
        if 'duration_ms' in d:
            entries.append(d)
    except: pass
entries.sort(key=lambda x: x.get('duration_ms', 0), reverse=True)
for e in entries[:10]:
    print(f\"{e.get('duration_ms',0):6.1f}ms  {e.get('method','')} {e.get('path','')}\")
"
```

---

## 4. Error Code Reference

| Code | Meaning | Action |
|------|---------|--------|
| `DB_CONN_ERR` | Database connection failed | Check PostgreSQL, see 1.4 |
| `REDIS_CONN_ERR` | Redis connection failed | Check Redis, see 1.5 |
| `WS_TIMEOUT` | WebSocket timeout | Check nginx timeout, see 1.6 |
| `RATE_LIMIT` | Rate limit exceeded | Check rate limit config |
| `AUTH_FAIL` | Authentication failed | Check credentials/token |
| `CAMPAIGN_FAIL` | Campaign execution failed | Check broadcast logs |

---

## 5. Debug Mode Activation

```bash
# Enable debug logging temporarily (DO NOT leave enabled in production)
docker exec tgpq-prod-app-blue-1 \
  sh -c "kill -USR1 1"  # Send SIGUSR1 to toggle debug if implemented

# Or restart with DEBUG=true (emergency only)
docker compose --env-file .env.production -f docker-compose.production.yml \
  -e DEBUG=true up -d app-blue-1
```

---

## 6. Escalation Contacts

| Role | Contact | SLA |
|------|---------|-----|
| On-Call Engineer | See on-call-procedures.md | 5 min ack, 15 min response |
| DBA | dba@tg-pro-quantum.app | 30 min |
| Security | security@tg-pro-quantum.app | Immediate for P1 |
| Support | support@tg-pro-quantum.app | 1 hour |
