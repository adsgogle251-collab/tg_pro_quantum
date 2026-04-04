# Client Onboarding Checklist

## TG PRO QUANTUM – New Client Onboarding Checklist

**Client Name:** ________________________  
**Onboarding Date:** ____________________  
**Account Manager:** ____________________  
**Technical Contact:** __________________

---

## Phase 1: Account Setup

- [ ] **Create client account** in admin panel
  - Client name, company, contact email
  - Set subscription tier and limits
  - Enable required features

- [ ] **Generate API keys**
  - Create production API key
  - Create sandbox/testing API key
  - Document key permissions and rate limits

- [ ] **Assign initial account groups**
  - Review client's Telegram accounts
  - Create account group(s)
  - Verify accounts are active and healthy
  - Set rotation strategy

- [ ] **Setup initial campaigns** (optional)
  - Create sample campaign with client's content
  - Configure message templates
  - Set schedule and rate limits

- [ ] **Configure webhooks** (if needed)
  - Collect webhook endpoint URL
  - Configure event types to receive
  - Test webhook delivery

---

## Phase 2: Technical Setup

- [ ] **Provide API credentials** to client
  - API key
  - API base URL: `https://api.tg-pro-quantum.app/api/v1`
  - WebSocket URL: `wss://api.tg-pro-quantum.app/ws`

- [ ] **Integration testing**
  - Test authentication (API key valid)
  - Test campaign creation via API
  - Test broadcast launch
  - Test real-time monitoring via WebSocket
  - Test webhook reception (if configured)

- [ ] **Setup support channel**
  - Add client to support Slack/Telegram channel
  - Introduce to support team
  - Provide support email: `support@tg-pro-quantum.app`

---

## Phase 3: Training & Documentation

- [ ] **Provide documentation pack** (see client-documentation-pack.md)
  - Quick start guide
  - API documentation link
  - Best practices guide

- [ ] **Conduct training session** (30-60 minutes)
  - Walk through dashboard
  - Demonstrate campaign creation
  - Demonstrate real-time monitoring
  - Q&A session

- [ ] **Review best practices**
  - Message rate limits
  - Account rotation best practices
  - Group verification
  - Safety features

---

## Phase 4: Go-Live Approval

- [ ] **Pre-go-live checklist**
  - Client has tested API integration
  - Client understands rate limits
  - Client has reviewed SLA
  - Support channel established

- [ ] **Go-live approval** – sign-off by:
  - [ ] Technical team
  - [ ] Account manager
  - [ ] Client representative

- [ ] **Post-go-live monitoring** (24 hours)
  - Monitor client's campaigns
  - Check error rates
  - Verify account health
  - Address any issues

---

## Notes

```
[Onboarding notes here]
```

---

*TG PRO QUANTUM Client Onboarding – Version 1.0*
