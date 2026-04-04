# Production Incident Response Runbook

## TG PRO QUANTUM – Incident Response Runbook

**Version:** 1.0  
**Environment:** Production  
**Updated:** 2024

---

## Severity Levels

| Level | Definition | Response SLA |
|-------|-----------|-------------|
| **P1 – Critical** | Full service outage or data loss | Ack: 5 min, Resolution: 15 min |
| **P2 – High** | Partial outage or >2% error rate | Ack: 15 min, Resolution: 1 hour |
| **P3 – Medium** | Degraded performance, <2% errors | Ack: 30 min, Resolution: 4 hours |
| **P4 – Low** | Minor issues, no user impact | Next business day |

---

## 1. CRITICAL INCIDENT – Error Rate > 2%

### Trigger
- Prometheus alert `ErrorRateCritical` fires
- Manual escalation from support team

### Response Steps

**Step 1: Alert received (T+0)**
```
☐ Acknowledge alert in PagerDuty/Slack
☐ Open incident in tracking system
☐ Check Grafana dashboard: https://monitoring.tg-pro-quantum.app
```

**Step 2: On-call engineer notified (T+5 min)**
```
☐ On-call engineer acknowledges
☐ Join incident Slack channel #incident-YYYYMMDD
☐ Initial assessment:
    - docker ps --filter "name=tgpq-prod"
    - curl -sf http://localhost/health
    - Check error logs: docker logs --tail=200 tgpq-prod-app-blue-1
```

**Step 3: Create incident (T+10 min)**
```
☐ Create incident record (use post-incident-template.md)
☐ Set severity level
☐ Notify stakeholders
☐ Post to #tgpq-prod-critical Slack channel
☐ Update status page: https://status.tg-pro-quantum.app
```

**Step 4: Investigation (T+10-20 min)**
```
☐ Identify root cause:
    - Check application logs: docker logs tgpq-prod-app-blue-1
    - Check database: docker exec tgpq-prod-db-primary pg_isready
    - Check Redis: docker exec tgpq-prod-redis-1 redis-cli ping
    - Check recent deployments: git log --oneline -10
    - Check Kibana: https://logs.tg-pro-quantum.app
```

**Step 5: Rollback (if needed) (T+15-20 min)**
```bash
# If root cause is recent deployment:
./rollback-production.sh --reason "P1_error_rate_$(date +%s)"

# Verify rollback
./verify-production-health.sh
```

**Step 6: Client communication (T+20 min)**
```
☐ Send status update to clients if downtime >5 minutes
☐ Update status page with ETA
☐ Keep 15-minute updates flowing
```

**Step 7: Post-mortem (T+24 hours)**
```
☐ Schedule post-mortem within 24 hours
☐ Complete post-incident-template.md
☐ Implement prevention measures
☐ Update runbook if needed
```

---

## 2. PERFORMANCE INCIDENT – Response Time > 1s (p95)

### Trigger
- Prometheus alert `ResponseTimeCritical` fires
- User complaints about slowness

### Response Steps

**Step 1: Analyze performance metrics**
```bash
# Check Prometheus
curl -s "http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,sum(rate(http_request_duration_seconds_bucket[5m]))by(le,handler))" | python3 -m json.tool

# Check slowest endpoints in Kibana
# Filter: duration_ms > 500 | Group by: path
```

**Step 2: Root cause analysis**
```bash
# Check database slow queries
docker exec tgpq-prod-db-primary psql -U tgpq_prod tg_quantum_prod -c \
  "SELECT query, mean_exec_time, calls FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# Check Redis performance
docker exec tgpq-prod-redis-1 redis-cli -a "${REDIS_PASSWORD}" slowlog get 10

# Check CPU/Memory
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemPerc}}"
```

**Step 3: Apply scaling if CPU-bound**
```bash
# Scale additional workers (if supported)
docker compose --env-file .env.production -f docker-compose.production.yml \
  scale celery-worker=4
```

**Step 4: Notify clients if SLA affected**
```
☐ If p95 > 1s for >5 minutes, notify clients
☐ Update status page
```

**Step 5: Resolution & prevention**
```
☐ Add missing database indexes
☐ Optimize slow queries
☐ Review caching strategy
☐ Document in post-incident report
```

---

## 3. DATA INCIDENT – Database Issues

### Trigger
- Prometheus alert `DatabaseDown` fires
- Application returns database errors

### Response Steps

**Step 1: Assess database status**
```bash
docker inspect -f '{{.State.Health.Status}}' tgpq-prod-db-primary
docker exec tgpq-prod-db-primary pg_isready -U tgpq_prod
docker logs --tail=100 tgpq-prod-db-primary
```

**Step 2: Attempt restart**
```bash
docker restart tgpq-prod-db-primary
sleep 30
docker exec tgpq-prod-db-primary pg_isready -U tgpq_prod
```

**Step 3: Failover to replica (if primary unrecoverable)**
```bash
# Promote replica to primary
docker exec tgpq-prod-db-replica \
  pg_ctl promote -D /var/lib/postgresql/data

# Update application to use replica
sed -i 's/db-primary/db-replica/' .env.production
docker compose --env-file .env.production -f docker-compose.production.yml \
  restart app-blue-1 app-blue-2 app-blue-3
```

**Step 4: Verify data integrity**
```bash
docker exec tgpq-prod-db-primary psql -U tgpq_prod tg_quantum_prod -c \
  "SELECT schemaname, tablename, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC;"
```

**Step 5: Restore from backup if needed**
```bash
./restore-production-database.sh
```

---

## 4. SECURITY INCIDENT

### Trigger
- Unusual access patterns detected
- Security scan alert
- External report of breach

### Response Steps

**Step 1: Automatic blocking (T+0)**
```bash
# Block all non-essential traffic immediately
docker exec tgpq-prod-nginx sh -c \
  "echo 'deny all;' >> /etc/nginx/conf.d/emergency-block.conf && nginx -s reload"
```

**Step 2: Alert security team (T+2 min)**
```
☐ Page security team immediately
☐ Create P1 incident
☐ Do NOT communicate externally until security team assesses
```

**Step 3: Isolate affected systems (T+10 min)**
```bash
# Rotate all secrets
# 1. Generate new SECRET_KEY
NEW_SECRET=$(openssl rand -hex 64)
sed -i "s/^SECRET_KEY=.*/SECRET_KEY=${NEW_SECRET}/" .env.production

# 2. Flush all sessions
docker exec tgpq-prod-redis-1 redis-cli -a "${REDIS_PASSWORD}" FLUSHDB

# 3. Restart application with new secrets
docker compose --env-file .env.production -f docker-compose.production.yml restart
```

**Step 4: Preserve forensic evidence**
```bash
FORENSICS_DIR="/tmp/forensics_$(date +%s)"
mkdir -p "${FORENSICS_DIR}"
docker logs tgpq-prod-nginx > "${FORENSICS_DIR}/nginx.log"
docker logs tgpq-prod-app-blue-1 > "${FORENSICS_DIR}/app.log"
docker exec tgpq-prod-db-primary psql -U tgpq_prod -c \
  "SELECT * FROM pg_stat_activity;" > "${FORENSICS_DIR}/db_activity.txt"
tar -czf "/tmp/forensics_$(date +%s).tar.gz" "${FORENSICS_DIR}"
```

**Step 5: Communication (after security team assessment)**
```
☐ Internal stakeholders notified
☐ Regulatory notifications if required (GDPR, etc.)
☐ Affected clients notified
☐ Public communication if necessary
```

**Step 6: Security review (within 48 hours)**
```
☐ Full security audit
☐ Penetration test
☐ Review and update security policies
☐ Post-incident report
```

---

## 5. Quick Reference Commands

```bash
# Check all production containers
docker ps --filter "name=tgpq-prod" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Check production health
./verify-production-health.sh

# View live logs
docker logs -f tgpq-prod-app-blue-1

# Rollback immediately
./rollback-production.sh --auto --reason "emergency"

# Check error rate (last 5min)
curl -s "http://localhost:9090/api/v1/query?query=sum(rate(http_requests_total{status=~\"5..\"}[5m]))/sum(rate(http_requests_total[5m]))*100" | python3 -c "import sys,json; d=json.load(sys.stdin); v=d.get('data',{}).get('result',[]); print(f'Error rate: {float(v[0][\"value\"][1]):.2f}%' if v else 'No data')"
```
