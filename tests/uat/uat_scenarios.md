# TG PRO QUANTUM – User Acceptance Testing (UAT) Scenarios
# Version: 1.0 | Environment: Staging
# Domain: https://api-staging.tg-pro-quantum.app

---

## Prerequisites
- Staging environment is live and all health checks pass
- Test data has been loaded via `uat_test_data.sql`
- Tester has admin credentials for the staging environment
- API documentation is accessible at `https://api-staging.tg-pro-quantum.app/docs`

---

## SCENARIO 1: Basic Account Group Management

**Objective:** Verify that an admin can create, populate, and inspect an account group.

**Steps:**
1. Login as admin → `POST /api/v1/auth/login`
2. Create account group `Broadcast_Pro` → `POST /api/v1/account-groups`
3. Assign 10 accounts to the group → `POST /api/v1/account-groups/{id}/accounts`
4. Retrieve the group → `GET /api/v1/account-groups/{id}`
5. Verify group health summary shows account count

**Expected Result:**
- Group created with status `active`
- Account count reflects 10 assigned accounts
- Group health score > 0

**Pass Criteria:** All 5 steps succeed without errors.

---

## SCENARIO 2: Client Onboarding

**Objective:** Verify full client onboarding workflow.

**Steps:**
1. Login as admin
2. Create new client → `POST /api/v1/clients`
3. Verify client receives unique `api_key`
4. Assign account group to client
5. Login as the new client
6. Create a campaign → `POST /api/v1/campaigns`

**Expected Result:**
- Client created with status `active`
- `api_key` field is populated and unique
- Client can create campaigns after login

**Pass Criteria:** All 6 steps succeed.

---

## SCENARIO 3: Broadcast Workflow – Full Cycle

**Objective:** Verify complete broadcast campaign lifecycle.

**Steps:**
1. Login as client
2. Create campaign → `POST /api/v1/campaigns`
3. Add 5 groups to campaign
4. Start broadcast → `POST /api/v1/broadcasts/{id}/start`
5. Poll status → `GET /api/v1/broadcasts/{id}/status` (3 times, 10s apart)
6. Stop broadcast → `POST /api/v1/broadcasts/{id}/stop`
7. Verify final status is `stopped` or `completed`

**Expected Result:**
- Campaign transitions: `draft` → `running` → `stopped`/`completed`
- `sent_count` > 0 (at least one message attempted)
- No 5xx errors during the workflow

**Pass Criteria:** Campaign lifecycle completes without errors.

---

## SCENARIO 4: Multi-Client Isolation

**Objective:** Verify that client data is fully isolated.

**Steps:**
1. Create Client A and Client B via admin
2. Client A creates Campaign_A
3. Client B creates Campaign_B
4. Authenticate as Client A
5. Attempt to access Campaign_B → expect 403/404
6. Authenticate as Client B
7. Attempt to access Campaign_A → expect 403/404

**Expected Result:**
- Cross-client access is blocked with 403 or 404
- No data leakage between clients

**Pass Criteria:** Both cross-access attempts return 403/404.

---

## SCENARIO 5: Error Handling & Recovery

**Objective:** Verify graceful error handling.

**Steps:**
1. Send invalid JSON to `POST /api/v1/campaigns` → expect 422
2. Access non-existent campaign → `GET /api/v1/campaigns/999999` → expect 404
3. Start campaign without groups → expect 400/422
4. Use expired/invalid JWT → expect 401
5. Verify error responses include a descriptive `detail` field

**Expected Result:**
- All error responses have correct HTTP status codes
- Error responses include `detail` describing the problem
- No 500 errors for expected bad inputs

**Pass Criteria:** All 5 error cases return expected codes with details.

---

## SCENARIO 6: Safety Features – Delay Configuration

**Objective:** Verify jitter delay settings are enforced.

**Steps:**
1. Create campaign with `delay_min=27`, `delay_max=33`
2. Retrieve campaign → verify delay fields stored
3. Create campaign with `delay_min=5`, `delay_max=10`
4. Retrieve campaign → verify custom delays stored
5. Verify `delay_max >= delay_min` validation

**Expected Result:**
- Delay fields are persisted as set
- Setting `delay_max < delay_min` returns 422

**Pass Criteria:** All delay scenarios behave correctly.

---

## SCENARIO 7: Real-time Monitoring via Health Endpoint

**Objective:** Verify the detailed health endpoint reports all components.

**Steps:**
1. `GET /health` → expect `{"status": "ok"}`
2. `GET /health/detailed` → expect `{"checks": {"database": {"status": "ok"}}}`
3. Record response times (must be < 500ms)
4. Repeat 5 times to verify consistency

**Expected Result:**
- Both health endpoints return 200
- Database check shows `ok`
- Response times consistently < 500ms

**Pass Criteria:** 5/5 repetitions succeed within time threshold.

---

## SCENARIO 8: WebSocket Connection

**Objective:** Verify WebSocket endpoint is reachable.

**Steps:**
1. Connect to `wss://api-staging.tg-pro-quantum.app/ws/campaigns/1`
2. Verify connection is established (no immediate close with error code)
3. Wait 5 seconds for any initial messages
4. Disconnect cleanly

**Expected Result:**
- WebSocket connection established
- No error codes during connection
- Clean disconnect

**Pass Criteria:** Connection established and disconnected cleanly.

---

## SCENARIO 9: API Documentation Accessibility

**Objective:** Verify all API documentation endpoints are accessible.

**Steps:**
1. `GET /docs` → expect 200 (Swagger UI)
2. `GET /redoc` → expect 200 (ReDoc UI)
3. `GET /openapi.json` → expect valid OpenAPI 3.x JSON
4. Verify all major route groups appear in schema (auth, clients, campaigns, broadcasts)

**Expected Result:**
- All documentation endpoints return 200
- OpenAPI schema includes all route groups
- Schema version is 3.x

**Pass Criteria:** All 4 steps succeed.

---

## SCENARIO 10: Admin Privilege Enforcement

**Objective:** Verify admin-only endpoints are protected.

**Steps:**
1. Authenticate as regular client
2. Attempt `GET /api/v1/clients` (admin-only) → expect 403
3. Attempt `POST /api/v1/clients` (admin-only) → expect 403
4. Authenticate as admin
5. `GET /api/v1/clients` → expect 200

**Expected Result:**
- Regular clients cannot access admin endpoints
- Admin can access all endpoints

**Pass Criteria:** Steps 2–3 return 403, step 5 returns 200.

---

## SCENARIO 11: Campaign Pagination

**Objective:** Verify list endpoints support pagination.

**Steps:**
1. Create 15 campaigns as a single client
2. `GET /api/v1/campaigns?limit=5&offset=0` → expect 5 results
3. `GET /api/v1/campaigns?limit=5&offset=5` → expect 5 results
4. `GET /api/v1/campaigns?limit=5&offset=10` → expect 5 results
5. Verify no duplicates across pages

**Expected Result:**
- Pagination returns correct counts
- No duplicate campaigns across pages
- Total matches 15

**Pass Criteria:** All 3 pages return correct, non-duplicate results.

---

## SCENARIO 12: Account Status Management

**Objective:** Verify account status transitions.

**Steps:**
1. Create a Telegram account with status `active`
2. Retrieve account → verify `status = active`, `health_score >= 0`
3. Update account status to `inactive` (if endpoint available)
4. Verify status change persisted

**Expected Result:**
- Account created with `active` status
- Status transitions are persisted
- Health score is a numeric value 0–100

**Pass Criteria:** All steps complete without errors.

---

## SCENARIO 13: Group Management

**Objective:** Verify group CRUD operations.

**Steps:**
1. Create a group → `POST /api/v1/groups`
2. List groups → `GET /api/v1/groups` → verify group appears
3. Get specific group → `GET /api/v1/groups/{id}` → verify data
4. Verify group `is_active = true`

**Expected Result:**
- Group created and retrievable
- Group appears in list filtered by current client

**Pass Criteria:** All 4 steps succeed.

---

## SCENARIO 14: Analytics Endpoint

**Objective:** Verify analytics endpoints return data.

**Steps:**
1. Login as client with at least one campaign
2. `GET /api/v1/analytics/campaigns` → expect 200
3. Verify response includes campaign-level metrics
4. `GET /api/v1/analytics/accounts` → expect 200

**Expected Result:**
- Analytics endpoints return 200
- Response includes numeric metric fields

**Pass Criteria:** Both analytics endpoints return 200 with structured data.

---

## SCENARIO 15: Rate Limiting Behavior

**Objective:** Verify API behaves gracefully under rapid requests.

**Steps:**
1. Send 20 requests to `GET /health` within 10 seconds
2. Verify all or most return 200
3. Send 20 requests to `GET /api/v1/campaigns` within 10 seconds
4. If rate limiting kicks in, verify 429 response includes `Retry-After` header

**Expected Result:**
- Health endpoint handles rapid requests
- Rate-limited responses include retry guidance

**Pass Criteria:** No unexpected 500 errors; rate limit responses include proper headers.

---

## SCENARIO 16: Broadcast Campaign Mode – Scheduled

**Objective:** Verify scheduled campaign mode configuration.

**Steps:**
1. Create campaign with `mode = scheduled`, `scheduled_at` set to a future time
2. Retrieve campaign → verify mode and scheduled_at stored
3. Verify status remains `draft` until scheduled time

**Expected Result:**
- Scheduled campaigns are created with correct mode
- `scheduled_at` field is persisted

**Pass Criteria:** Campaign created and retrieved with correct scheduled mode.

---

## SCENARIO 17: Concurrent Client Sessions

**Objective:** Verify multiple clients can be authenticated simultaneously.

**Steps:**
1. Login as Client A → obtain JWT token A
2. Login as Client B → obtain JWT token B
3. Using token A: `GET /api/v1/campaigns` → expect Client A's data
4. Using token B: `GET /api/v1/campaigns` → expect Client B's data
5. Verify sessions are fully independent

**Expected Result:**
- Both tokens valid simultaneously
- Data returned is scoped to correct client

**Pass Criteria:** Both sessions work independently and return correct data.

---

## SCENARIO 18: CORS Headers

**Objective:** Verify CORS headers are present for staging domain.

**Steps:**
1. Send OPTIONS preflight to `https://api-staging.tg-pro-quantum.app/api/v1/campaigns`
   with `Origin: https://staging.tg-pro-quantum.app`
2. Verify response includes `Access-Control-Allow-Origin`
3. Verify allowed methods include POST, GET, DELETE

**Expected Result:**
- CORS preflight returns 204
- `Access-Control-Allow-Origin` matches staging domain

**Pass Criteria:** Preflight succeeds with correct CORS headers.

---

## SCENARIO 19: Database Persistence

**Objective:** Verify data persists across service restarts.

**Steps:**
1. Create a campaign as Client A
2. Restart the `app` container: `docker restart tgpq-staging-app`
3. Wait 30 seconds for service to become healthy
4. Retrieve the campaign created in step 1 → verify it still exists

**Expected Result:**
- Campaign data persists after container restart
- Service recovers within 30 seconds

**Pass Criteria:** Campaign retrieved successfully after restart.

---

## SCENARIO 20: Error Logging

**Objective:** Verify errors are logged and accessible.

**Steps:**
1. Trigger a 404 error: `GET /api/v1/campaigns/000000`
2. Trigger a 401 error: send request without auth token
3. Check application logs in Kibana (`https://logs-staging.tg-pro-quantum.app`)
4. Verify log entries exist for the triggered errors

**Expected Result:**
- Errors appear in log aggregation within 30 seconds
- Log entries include timestamp, status code, and request path

**Pass Criteria:** Both error events visible in Kibana logs.

---

## SCENARIO 21: Monitoring Dashboard Accessibility

**Objective:** Verify Grafana dashboards are accessible and showing data.

**Steps:**
1. Navigate to `https://monitoring-staging.tg-pro-quantum.app`
2. Login with Grafana admin credentials
3. Open "TG PRO QUANTUM – Staging" dashboard
4. Verify panels show data (API request rate, error rate, response time)
5. Verify no "No Data" panels for active services

**Expected Result:**
- Grafana accessible and shows the main dashboard
- Metrics panels show data after 1+ minute of traffic

**Pass Criteria:** Dashboard loads and at least 3 metric panels show data.

---

## SCENARIO 22: Prometheus Alerts Configuration

**Objective:** Verify Prometheus alert rules are loaded.

**Steps:**
1. Navigate to `http://staging-host:9090/rules` (Prometheus UI)
2. Verify all 10 required alert rules are listed
3. Check that rules are in `inactive` state (no active alerts on healthy system)
4. Manually trigger `HighErrorRate` by sending 50 bad requests

**Expected Result:**
- All 10 alert rules visible in Prometheus
- Alerts are inactive on healthy system
- High error rate alert fires within 2 minutes of trigger

**Pass Criteria:** All alerts configured; HighErrorRate alert fires on trigger.

---

## UAT Sign-off Checklist

| # | Scenario | Tester | Date | Result | Notes |
|---|----------|--------|------|--------|-------|
| 1 | Basic Account Group Management | | | ☐ Pass ☐ Fail | |
| 2 | Client Onboarding | | | ☐ Pass ☐ Fail | |
| 3 | Broadcast Workflow | | | ☐ Pass ☐ Fail | |
| 4 | Multi-Client Isolation | | | ☐ Pass ☐ Fail | |
| 5 | Error Handling & Recovery | | | ☐ Pass ☐ Fail | |
| 6 | Safety Features – Delay | | | ☐ Pass ☐ Fail | |
| 7 | Real-time Monitoring | | | ☐ Pass ☐ Fail | |
| 8 | WebSocket Connection | | | ☐ Pass ☐ Fail | |
| 9 | API Documentation | | | ☐ Pass ☐ Fail | |
| 10 | Admin Privilege Enforcement | | | ☐ Pass ☐ Fail | |
| 11 | Campaign Pagination | | | ☐ Pass ☐ Fail | |
| 12 | Account Status Management | | | ☐ Pass ☐ Fail | |
| 13 | Group Management | | | ☐ Pass ☐ Fail | |
| 14 | Analytics Endpoint | | | ☐ Pass ☐ Fail | |
| 15 | Rate Limiting Behavior | | | ☐ Pass ☐ Fail | |
| 16 | Scheduled Campaign Mode | | | ☐ Pass ☐ Fail | |
| 17 | Concurrent Client Sessions | | | ☐ Pass ☐ Fail | |
| 18 | CORS Headers | | | ☐ Pass ☐ Fail | |
| 19 | Database Persistence | | | ☐ Pass ☐ Fail | |
| 20 | Error Logging | | | ☐ Pass ☐ Fail | |
| 21 | Monitoring Dashboard | | | ☐ Pass ☐ Fail | |
| 22 | Prometheus Alerts | | | ☐ Pass ☐ Fail | |

**Total Passed:** ___ / 22  
**Total Failed:** ___ / 22

**UAT Approval:**  
Sign-off by: ___________________________  
Date: ___________________________  
Status: ☐ Approved for Production ☐ Conditional Approval ☐ Rejected
