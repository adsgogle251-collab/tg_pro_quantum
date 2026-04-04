# Client Documentation Pack

## TG PRO QUANTUM – Client Documentation

**Version:** 1.0  
**Production URL:** https://api.tg-pro-quantum.app  

---

## 1. Quick Start Guide

### Step 1: Authentication

All API requests require an API key in the header:

```http
Authorization: Bearer YOUR_API_KEY
```

### Step 2: Create an Account Group

```http
POST /api/v1/account-groups
Content-Type: application/json

{
  "name": "My Campaign Accounts",
  "description": "Accounts for marketing campaigns",
  "rotation_strategy": "round_robin"
}
```

### Step 3: Create a Campaign

```http
POST /api/v1/campaigns
Content-Type: application/json

{
  "name": "My First Campaign",
  "message": "Hello from TG PRO QUANTUM!",
  "account_group_id": "GROUP_ID",
  "max_per_hour": 100,
  "jitter_pct": 10
}
```

### Step 4: Add Groups to Campaign

```http
POST /api/v1/campaigns/{campaign_id}/groups
Content-Type: application/json

{
  "group_ids": ["GROUP_LINK_1", "GROUP_LINK_2"]
}
```

### Step 5: Start Broadcast

```http
POST /api/v1/campaigns/{campaign_id}/start
```

### Step 6: Monitor in Real-Time

Connect to WebSocket for live updates:

```javascript
const ws = new WebSocket('wss://api.tg-pro-quantum.app/ws');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Campaign update:', data);
};
```

---

## 2. API Documentation

**Full API docs:** https://api.tg-pro-quantum.app/docs

### Base URL
```
https://api.tg-pro-quantum.app/api/v1
```

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | System health status |
| POST | `/auth/token` | Get access token |
| GET | `/campaigns` | List campaigns |
| POST | `/campaigns` | Create campaign |
| POST | `/campaigns/{id}/start` | Start broadcast |
| POST | `/campaigns/{id}/stop` | Stop broadcast |
| GET | `/campaigns/{id}/stats` | Get campaign statistics |
| GET | `/account-groups` | List account groups |
| POST | `/account-groups` | Create account group |

### Rate Limits

| Plan | Requests/min | Campaigns | Accounts |
|------|-------------|-----------|----------|
| Starter | 60 | 5 | 10 |
| Professional | 120 | 20 | 50 |
| Enterprise | Custom | Unlimited | Unlimited |

---

## 3. Best Practices

### Message Rate Limits
- **Recommended:** 50-100 messages/hour per account
- **Maximum:** 200 messages/hour per account
- **Safety:** Use `jitter_pct: 10-20` to randomize timing

### Account Rotation
- Use **round_robin** for balanced load distribution
- Set `rotate_every: 50-100` messages
- Monitor account health via dashboard

### Group Verification
- Always verify groups before broadcasting (channels are auto-filtered)
- Use the built-in group verification feature
- Review verification results before starting campaign

### Safety Features
- Enable `ban_detection: true` to auto-pause on ban detection
- Enable `rate_limit_detection: true` for automatic slowdown
- Review `safety_alerts` regularly

---

## 4. Troubleshooting Guide

### Common Issues

**Campaign not starting:**
- Check account group has active accounts
- Verify API key is valid
- Check rate limit hasn't been exceeded

**High failure rate:**
- Check account health in dashboard
- Reduce messages-per-hour setting
- Enable `jitter_pct` to add randomization

**WebSocket disconnecting:**
- Implement reconnect logic with exponential backoff
- WebSocket sessions timeout after 1 hour of inactivity

**API returning 429 (Too Many Requests):**
- You've exceeded rate limits
- Implement request queuing
- Contact support for rate limit increase

---

## 5. SLA Documentation

| Metric | Commitment |
|--------|-----------|
| **API Uptime** | 99.9% monthly |
| **API Response Time** | <100ms p95 |
| **WebSocket Latency** | <1s p95 |
| **Campaign Success Rate** | >95% |
| **Support Response** | P1: 15 min, P2: 1 hour |

---

## 6. Support

| Channel | Contact | Hours |
|---------|---------|-------|
| Email | support@tg-pro-quantum.app | 24/7 |
| Status Page | https://status.tg-pro-quantum.app | - |
| Documentation | https://docs.tg-pro-quantum.app | - |

---

## 7. Account Management

**Dashboard:** https://app.tg-pro-quantum.app  
**API Keys:** Manage in Dashboard → Settings → API Keys  
**Usage Statistics:** Dashboard → Analytics  
**Billing:** Dashboard → Billing  

---

*TG PRO QUANTUM Client Documentation – Version 1.0*  
*For questions: support@tg-pro-quantum.app*
