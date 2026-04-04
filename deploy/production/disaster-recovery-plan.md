# Disaster Recovery Plan

## TG PRO QUANTUM – Production Disaster Recovery Plan

**Version:** 1.0  
**RTO (Recovery Time Objective):** 15 minutes  
**RPO (Recovery Point Objective):** 1 hour  
**Last Updated:** 2024  
**Owner:** Operations Team

---

## 1. Overview

This document describes the procedures for recovering the TG PRO QUANTUM production system from various disaster scenarios.

---

## 2. Recovery Objectives

| Metric | Target |
|--------|--------|
| **RTO** (Maximum downtime) | 15 minutes |
| **RPO** (Maximum data loss) | 1 hour |
| **MTTR** (Mean time to recover) | <30 minutes |

---

## 3. Backup Locations

| Backup Type | Location | Retention |
|-------------|----------|-----------|
| Daily database backup | `/var/backups/tgpq/YYYYMMDD/daily/` | 30 days |
| Pre-deploy backup | `/var/backups/tgpq/YYYYMMDD/pre-deploy_*/` | 30 days |
| Weekly archive | `/var/backups/tgpq-archive/YYYY_W*/` | 26 weeks |
| S3 daily | `s3://tgpq-prod-backups/YYYYMMDD/daily/` | 30 days |
| S3 weekly (Glacier) | `s3://tgpq-prod-backups/weekly/YYYY_W*/` | 6 months |

---

## 4. Recovery Scenarios

### 4.1 Application Service Failure

**Symptoms:** All API instances down, health checks failing.

**RTO:** 5 minutes

**Steps:**
```bash
# 1. Check container status
docker ps --filter "name=tgpq-prod-app"

# 2. Restart blue environment
docker compose --env-file .env.production \
  -f docker-compose.production.yml \
  --profile blue restart

# 3. Verify health
./verify-production-health.sh

# 4. If still failing, rollback to previous image
./rollback-production.sh --reason "service_failure"
```

---

### 4.2 Database Primary Failure

**Symptoms:** PostgreSQL primary unreachable, database errors in application.

**RTO:** 10 minutes

**Steps:**
```bash
# 1. Check primary status
docker inspect tgpq-prod-db-primary

# 2. Attempt restart
docker restart tgpq-prod-db-primary
sleep 30
docker exec tgpq-prod-db-primary pg_isready -U tgpq_prod

# 3. If restart fails, promote replica
docker exec tgpq-prod-db-replica pg_ctl promote -D /var/lib/postgresql/data

# 4. Update DATABASE_URL to point to replica
sed -i 's/db-primary/db-replica/' .env.production
docker compose --env-file .env.production \
  -f docker-compose.production.yml restart app-blue-1 app-blue-2 app-blue-3

# 5. Restore from backup if replica also failed
./restore-production-database.sh
```

---

### 4.3 Complete Host/Infrastructure Failure

**Symptoms:** Entire server unreachable.

**RTO:** 15 minutes (with pre-configured standby)

**Steps:**
1. Provision new server (use infrastructure-as-code or cloud console)
2. Install Docker and Docker Compose
3. Clone repository:
   ```bash
   git clone https://github.com/adsgogle251-collab/tg_pro_quantum.git /opt/tgpq
   ```
4. Restore configuration and secrets:
   ```bash
   cp .env.production /opt/tgpq/deploy/production/
   # Restore SSL certificates
   aws s3 cp s3://tgpq-prod-backups/ssl/ /opt/tgpq/deploy/production/ssl/ --recursive
   ```
5. Start infrastructure:
   ```bash
   cd /opt/tgpq/deploy/production
   docker compose --env-file .env.production -f docker-compose.production.yml up -d
   ```
6. Restore database:
   ```bash
   aws s3 cp s3://tgpq-prod-backups/$(date +%Y%m%d)/daily/ /var/backups/tgpq/ --recursive
   ./restore-production-database.sh --yes
   ```
7. Verify health:
   ```bash
   ./verify-production-health.sh
   ```

---

### 4.4 Data Corruption

**Symptoms:** Application errors related to data integrity, inconsistent results.

**RTO:** 15 minutes

**Steps:**
```bash
# 1. Identify corruption scope
docker exec tgpq-prod-db-primary psql -U tgpq_prod tg_quantum_prod -c \
  "SELECT schemaname, tablename FROM pg_tables WHERE schemaname='public';"

# 2. Run integrity checks
docker exec tgpq-prod-db-primary psql -U tgpq_prod tg_quantum_prod -c \
  "SELECT * FROM pg_stat_user_tables WHERE n_dead_tup > 0 ORDER BY n_dead_tup DESC LIMIT 10;"

# 3. Restore from last known-good backup
./restore-production-database.sh

# 4. Verify after restore
./verify-production-health.sh
```

---

### 4.5 Security Incident

**Symptoms:** Unauthorized access, data breach indicators.

**RTO:** Immediate containment, 30 minutes for recovery

**Steps:**
1. **Immediate:** Block all external traffic via firewall / nginx
2. **Immediate:** Revoke all API keys and session tokens:
   ```bash
   docker exec tgpq-prod-redis-1 redis-cli -a "${REDIS_PASSWORD}" FLUSHDB
   ```
3. Rotate all secrets (DB passwords, SECRET_KEY, API keys)
4. Preserve logs for forensics:
   ```bash
   docker logs tgpq-prod-nginx > /tmp/nginx_forensics_$(date +%s).log
   docker logs tgpq-prod-app-blue-1 > /tmp/app_forensics_$(date +%s).log
   ```
5. Contact security team
6. Restore from clean backup after investigation

---

## 5. Team Responsibilities

| Role | Primary | Backup |
|------|---------|--------|
| Incident Commander | On-call engineer | Team Lead |
| Database Recovery | DBA | On-call engineer |
| Security Incidents | Security Team | Team Lead |
| Client Communication | Support Team | Operations |

---

## 6. Communication Plan

1. **Internal Alert:** Slack `#tgpq-prod-critical` (automatic via AlertManager)
2. **Status Page Update:** https://status.tg-pro-quantum.app (update within 5 min)
3. **Client Notification:** Email affected clients if downtime >5 minutes
4. **Post-Incident:** Schedule post-mortem within 24 hours

---

## 7. Testing Schedule

| Test Type | Frequency | Owner |
|-----------|-----------|-------|
| Backup restore test | Weekly (automated in backup-production-weekly.sh) | Ops |
| DR drill | Monthly | Ops Team |
| Security incident response drill | Quarterly | Security + Ops |
| Full DR exercise | Bi-annually | All Teams |

---

## 8. Contact Information

| Contact | Details |
|---------|---------|
| Operations Team | ops@tg-pro-quantum.app |
| On-Call Rotation | See on-call-procedures.md |
| Cloud Provider Support | support.cloud-provider.com |
| Database Support | dba@tg-pro-quantum.app |
| Security Team | security@tg-pro-quantum.app |
