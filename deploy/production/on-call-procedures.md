# On-Call Procedures

## TG PRO QUANTUM – On-Call Engineer Procedures

**Version:** 1.0  
**Updated:** 2024

---

## 1. On-Call Rotation

| Week | Primary | Backup |
|------|---------|--------|
| Rotation 1 | Engineer A | Engineer B |
| Rotation 2 | Engineer B | Engineer C |
| Rotation 3 | Engineer C | Engineer A |

**Rotation length:** 1 week (Monday 09:00 → Monday 09:00 UTC)

**Handoff procedure:** See Section 7.

---

## 2. Alert Acknowledgment SLA

| Alert Severity | Acknowledgment SLA | Initial Response SLA |
|----------------|-------------------|---------------------|
| P1 – Critical | **5 minutes** | **15 minutes** |
| P2 – High | 15 minutes | 1 hour |
| P3 – Medium | 30 minutes | 4 hours |
| P4 – Low | Next business day | Next business day |

---

## 3. Alert Channels

Alerts are delivered via:
1. **PagerDuty** – P1/P2 alerts (phone + SMS)
2. **Slack** – All alerts (`#tgpq-prod-critical`, `#tgpq-prod-alerts`)
3. **Email** – P1/P2 alerts (team@tg-pro-quantum.app)

---

## 4. Initial Response Steps

When an alert fires:

```
1. ☐ Acknowledge the alert in PagerDuty within 5 minutes
2. ☐ Open the runbook: deploy/production/incident-response-runbook.md
3. ☐ Check Grafana dashboard: https://monitoring.tg-pro-quantum.app
4. ☐ Check application health: ./verify-production-health.sh
5. ☐ If P1: Create incident record immediately
6. ☐ If P1: Notify team lead via phone
7. ☐ Follow incident-response-runbook.md steps
```

---

## 5. Escalation Procedures

### When to escalate:
- Cannot resolve P1 incident within 15 minutes
- Data integrity concerns
- Security incident suspected
- Infrastructure failure requiring provider support

### Escalation path:
```
On-Call Engineer
    ↓ (if no response in 5 min or issue >15 min)
Team Lead / Engineering Manager
    ↓ (if no response or P1 continuing >30 min)
CTO / VP Engineering
    ↓ (for security incidents or major outages)
Legal / Communications team (for external communication)
```

---

## 6. After-Hours Support

**After-hours definition:** Outside 09:00–18:00 UTC, Monday–Friday.

**After-hours protocol:**
- P1/P2 alerts wake on-call engineer (PagerDuty phone/SMS)
- P3/P4 alerts queue for next business day
- Team lead receives copy of all P1 alerts

**On-call compensation:** Per company policy.

---

## 7. Handoff Procedures

### At end of on-call shift:

**Outgoing engineer tasks:**
```
☐ Document all open incidents
☐ Note any ongoing investigations
☐ Summarize current system state
☐ List any pending monitoring tuning
☐ Transfer PagerDuty on-call rotation
☐ Brief incoming engineer (15 min handoff call)
```

**Handoff template:**
```markdown
## On-Call Handoff – [DATE]

### System Status
- [ ] All services: HEALTHY / DEGRADED / DOWN
- Error rate: X%
- Response time p95: Xms

### Open Incidents
- [INCIDENT-ID]: [description] – Status: [in progress / monitoring]

### Recent Changes
- [list recent deployments or config changes]

### Ongoing Monitoring
- [anything being watched]

### Action Items for Incoming Engineer
- [ ] [task 1]
- [ ] [task 2]
```

---

## 8. Contact Information

| Role | Name | Phone | Slack | Email |
|------|------|-------|-------|-------|
| On-call (primary) | See rotation | PagerDuty | @oncall | oncall@tg-pro-quantum.app |
| Team Lead | - | - | @teamlead | teamlead@tg-pro-quantum.app |
| DBA | - | - | @dba | dba@tg-pro-quantum.app |
| Security | - | - | @security | security@tg-pro-quantum.app |
| Cloud Provider | - | Support portal | - | - |

---

## 9. Useful Resources

- **Runbook:** `deploy/production/incident-response-runbook.md`
- **Troubleshooting:** `deploy/production/production-troubleshooting-guide.md`
- **Grafana:** https://monitoring.tg-pro-quantum.app
- **Kibana:** https://logs.tg-pro-quantum.app
- **Status Page:** https://status.tg-pro-quantum.app
- **API Docs:** https://api.tg-pro-quantum.app/docs
- **Health:** https://api.tg-pro-quantum.app/health

---

## 10. Post-Incident

After every P1/P2 incident:
1. Complete `post-incident-template.md` within 24 hours
2. Hold post-mortem within 48 hours
3. Implement action items within agreed timeline
4. Update runbooks if needed
