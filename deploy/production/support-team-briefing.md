# Support Team Briefing

## TG PRO QUANTUM – Support Team Briefing

**Version:** 1.0  
**For:** Customer Support Team  
**Updated:** 2024

---

## 1. System Architecture Overview

TG PRO QUANTUM is a multi-tenant Telegram broadcast management platform.

### Core Components

```
Client Layer:
  Web Dashboard (https://app.tg-pro-quantum.app)
  API (https://api.tg-pro-quantum.app/api/v1)
  WebSocket (wss://api.tg-pro-quantum.app/ws)

Application Layer:
  FastAPI backend (3 replicas for high availability)
  Celery workers (async task processing)
  Celery beat (scheduled tasks)

Data Layer:
  PostgreSQL (primary + replica for redundancy)
  Redis (3 nodes for caching and message queue)

Monitoring:
  Grafana: https://monitoring.tg-pro-quantum.app
  Kibana: https://logs.tg-pro-quantum.app
  Status: https://status.tg-pro-quantum.app
```

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Client** | A paying customer with their own isolated data |
| **Account Group** | A collection of Telegram accounts for a client |
| **Campaign** | A broadcast job with message, targets, and settings |
| **Broadcast** | The process of sending a campaign's message to Telegram groups |
| **Group Verification** | Checking that target groups are valid (not channels) |
| **Account Rotation** | Switching between accounts to distribute load |

---

## 2. Common Client Issues & Solutions

### Issue: "My campaign won't start"

**Causes & Solutions:**
1. **No active accounts** → Check account group in dashboard, verify accounts are healthy
2. **Campaign already running** → Stop previous campaign first
3. **API key invalid** → Client needs to regenerate key in Settings → API Keys
4. **Rate limit reached** → Wait or upgrade plan

**Support actions:**
```
1. Check client's account group status
2. Check campaign status in admin panel
3. Check API key validity
4. Check client's usage vs limits
```

---

### Issue: "High message failure rate"

**Causes & Solutions:**
1. **Accounts getting banned** → Reduce message rate, check `safety_alerts`
2. **Groups are channels** → Use group verification feature first
3. **Messages too fast** → Increase `jitter_pct` to 15-20
4. **Accounts need warm-up** → New accounts need gradual warm-up

**Support actions:**
```
1. Check safety alerts in dashboard
2. Review account health metrics
3. Recommend reducing max_per_hour
4. Advise enabling safety features
```

---

### Issue: "Real-time dashboard not updating"

**Causes & Solutions:**
1. **WebSocket disconnected** → Browser needs to refresh
2. **Browser compatibility** → Try Chrome or Firefox
3. **Network proxy blocking WebSocket** → Try different network

**Support actions:**
```
1. Ask client to refresh browser
2. Check if campaign is actually running (via API)
3. Verify WebSocket connectivity: wss://api.tg-pro-quantum.app/ws
```

---

### Issue: "API returning errors"

**Causes & Solutions:**
- `401 Unauthorized` → Invalid or expired API key
- `403 Forbidden` → Insufficient permissions
- `429 Too Many Requests` → Rate limit exceeded, implement backoff
- `500 Internal Server Error` → Escalate to engineering immediately

---

## 3. Escalation Procedures

| Issue Type | First Level | Escalate To |
|------------|-------------|-------------|
| Account/billing | Support team | Account manager |
| API issues | Support team | Engineering (if 500 errors) |
| Data concerns | Support team | Engineering immediately |
| Security | Support team | Security team immediately |
| Outage/downtime | Check status page | Engineering on-call |

### Escalation contacts:
- **Engineering on-call:** See on-call-procedures.md
- **Account manager:** accountmanager@tg-pro-quantum.app
- **Security:** security@tg-pro-quantum.app
- **Management escalation:** management@tg-pro-quantum.app

---

## 4. Checking System Status

Before responding to issues, always check:

1. **Status page:** https://status.tg-pro-quantum.app
   - If incident is posted, inform client and refer to status page

2. **Quick health check:**
   ```
   GET https://api.tg-pro-quantum.app/health
   ```
   Expected: `{"status": "ok", ...}`

3. **Grafana dashboard** (support team access):
   - https://monitoring.tg-pro-quantum.app
   - Check error rate panel
   - Check response time panel

---

## 5. Documentation References

| Document | Location |
|----------|----------|
| Client Quick Start | client-documentation-pack.md |
| API Docs | https://api.tg-pro-quantum.app/docs |
| Troubleshooting | production-troubleshooting-guide.md |
| Incident Runbook | incident-response-runbook.md |
| On-Call Procedures | on-call-procedures.md |

---

## 6. After-Hours Support

- **P1 incidents** (full outage): Page on-call engineer via PagerDuty
- **P2 incidents** (partial outage): Slack `#tgpq-prod-critical`
- **P3/P4** (minor issues): Queue for next business day

**After-hours support escalation:**
1. Check status page first
2. If active incident, refer client to status page
3. If no active incident and P1 symptoms, page on-call

---

## 7. Training Materials

- [ ] Watch system walkthrough video (link in internal wiki)
- [ ] Complete API documentation review
- [ ] Practice: Create test campaign in sandbox environment
- [ ] Shadow 3 client onboarding sessions
- [ ] Complete incident response drill

---

*TG PRO QUANTUM Support Team Briefing – Version 1.0*  
*Questions: ops@tg-pro-quantum.app*
