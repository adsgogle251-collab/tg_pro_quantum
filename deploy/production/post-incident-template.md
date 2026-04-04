# Post-Incident Report Template

## Incident Title: [BRIEF DESCRIPTION]

**Incident ID:** INC-YYYY-MMDD-NNN  
**Date:** YYYY-MM-DD  
**Duration:** HH:MM – HH:MM UTC (X hours Y minutes)  
**Severity:** P1 / P2 / P3  
**Status:** Resolved / Monitoring / Open  
**Incident Commander:** [Name]  
**Report Author:** [Name]  
**Report Date:** YYYY-MM-DD  

---

## 1. Executive Summary

[2-3 sentence summary of what happened, the impact, and the resolution.]

---

## 2. Timeline of Events

| Time (UTC) | Event |
|------------|-------|
| HH:MM | [First symptom / alert fired] |
| HH:MM | [On-call engineer acknowledged] |
| HH:MM | [Initial diagnosis started] |
| HH:MM | [Root cause identified] |
| HH:MM | [Mitigation applied] |
| HH:MM | [Service restored] |
| HH:MM | [Incident closed] |

---

## 3. Root Cause Analysis

### What happened?

[Technical description of the root cause.]

### Why did it happen?

[Contributing factors and systemic causes.]

### Why wasn't it caught before production?

[Gaps in testing, monitoring, or deployment process.]

---

## 4. Impact Assessment

| Impact Area | Details |
|-------------|---------|
| **Downtime** | X minutes |
| **Affected clients** | X clients |
| **Error rate peak** | X% |
| **Response time peak** | Xms |
| **Data loss** | None / [describe] |
| **SLA breach** | Yes / No |

---

## 5. Mitigation & Resolution

### Immediate actions taken:
1. [Action 1]
2. [Action 2]
3. [Action 3]

### Root cause fix:
[Description of permanent fix applied.]

---

## 6. Prevention Measures

| Measure | Owner | Due Date | Status |
|---------|-------|----------|--------|
| [Monitoring improvement] | [Name] | YYYY-MM-DD | [ ] |
| [Code fix] | [Name] | YYYY-MM-DD | [ ] |
| [Process change] | [Name] | YYYY-MM-DD | [ ] |
| [Runbook update] | [Name] | YYYY-MM-DD | [ ] |

---

## 7. Follow-Up Action Items

- [ ] [Action item 1] – Owner: [Name], Due: YYYY-MM-DD
- [ ] [Action item 2] – Owner: [Name], Due: YYYY-MM-DD
- [ ] [Action item 3] – Owner: [Name], Due: YYYY-MM-DD
- [ ] Update runbook: `deploy/production/incident-response-runbook.md`
- [ ] Update monitoring alerts if false positive
- [ ] Schedule follow-up review in 2 weeks

---

## 8. Lessons Learned

### What went well:
- [Detection was fast because...]
- [On-call response was within SLA]
- [Rollback worked as expected]

### What could be improved:
- [Monitoring didn't catch X early enough]
- [Documentation was unclear about Y]
- [Communication took too long]

---

## 9. Appendix

### Relevant Log Excerpts

```
[Paste relevant log lines here]
```

### Metrics at Time of Incident

[Link to Grafana snapshot or paste key metrics]

---

*This report was created using the TG PRO QUANTUM Post-Incident Template.*
*See: deploy/production/post-incident-template.md*
