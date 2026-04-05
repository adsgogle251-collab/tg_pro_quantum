# TG PRO QUANTUM — API Documentation

## Overview

| Property | Value |
|---|---|
| **Base URL** | `http://localhost:8000/api/v1` |
| **Protocol** | HTTP/1.1, WebSocket |
| **Auth** | JWT Bearer token |
| **Content-Type** | `application/json` |

---

## Authentication

All protected endpoints require an `Authorization` header:

```
Authorization: Bearer <token>
```

Obtain a token via `POST /auth/login`. Tokens expire after **24 hours**.

---

## Endpoints

### Auth

#### POST /auth/register
Register a new admin user.

**Request**
```json
{ "username": "admin", "password": "s3cr3t" }
```

**Response `201`**
```json
{ "id": 1, "username": "admin", "created_at": "2024-01-01T00:00:00Z" }
```

---

#### POST /auth/login
Obtain a JWT token.

**Request**
```json
{ "username": "admin", "password": "s3cr3t" }
```

**Response `200`**
```json
{ "access_token": "<jwt>", "token_type": "bearer" }
```

---

### Accounts

#### GET /accounts/
List all Telegram accounts.

**Response `200`**
```json
[
  {
    "id": 1,
    "phone": "+14155552671",
    "status": "active",
    "username": "example_user",
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

---

#### POST /accounts/
Add a new Telegram account (initiates OTP flow).

**Request**
```json
{ "phone": "+14155552671" }
```

**Response `202`**
```json
{ "phone_code_hash": "abc123", "message": "OTP sent" }
```

---

#### POST /accounts/{id}/verify
Verify OTP to complete account login.

**Request**
```json
{ "phone_code_hash": "abc123", "code": "12345" }
```

**Response `200`**
```json
{ "id": 1, "status": "active" }
```

---

#### DELETE /accounts/{id}
Remove an account and delete its session.

**Response `204`** — No content.

---

### Campaigns

#### GET /campaigns/
List all campaigns.

**Response `200`**
```json
[
  {
    "id": 1,
    "name": "Q1 Promo",
    "type": "dm",
    "status": "active",
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

---

#### POST /campaigns/
Create a campaign.

**Request**
```json
{
  "name": "Q1 Promo",
  "type": "dm",
  "message": "Hey {first_name}, check this out!",
  "delay_min": 3,
  "delay_max": 8
}
```

**Response `201`**
```json
{ "id": 2, "name": "Q1 Promo", "status": "draft" }
```

---

#### DELETE /campaigns/{id}
Delete a campaign.

**Response `204`** — No content.

---

### Broadcasts

#### GET /broadcasts/
List broadcast jobs.

**Response `200`**
```json
[
  {
    "id": 1,
    "campaign_id": 1,
    "status": "running",
    "sent": 150,
    "failed": 3,
    "total": 500
  }
]
```

---

#### POST /broadcasts/
Start a broadcast.

**Request**
```json
{
  "campaign_id": 1,
  "account_ids": [1, 2],
  "target_list_id": 5
}
```

**Response `202`**
```json
{ "broadcast_id": 1, "status": "queued" }
```

---

#### POST /broadcasts/{id}/stop
Stop a running broadcast.

**Response `200`**
```json
{ "id": 1, "status": "stopped" }
```

---

### Analytics

#### GET /analytics/
Get aggregated analytics.

**Query Parameters**

| Param | Type | Description |
|---|---|---|
| `from` | ISO date | Start date (default: 7 days ago) |
| `to` | ISO date | End date (default: today) |
| `campaign_id` | int | Filter by campaign |

**Response `200`**
```json
{
  "total_sent": 4200,
  "total_failed": 87,
  "delivery_rate": 97.9,
  "by_day": [{ "date": "2024-01-01", "sent": 600 }]
}
```

---

### Groups

#### GET /groups/
List scraped groups.

**Response `200`**
```json
[
  {
    "id": 1,
    "username": "cryptotraders",
    "title": "Crypto Traders",
    "member_count": 45000
  }
]
```

---

## WebSocket

### ws://localhost:8000/ws/{client_id}

Real-time event stream for broadcast progress and scraping updates.

**Connect**
```js
const ws = new WebSocket('ws://localhost:8000/ws/my-client-id');
```

**Message Format**
```json
{
  "event": "broadcast_progress",
  "data": { "broadcast_id": 1, "sent": 51, "total": 500 }
}
```

**Event Types**
- `broadcast_progress` — live delivery stats
- `broadcast_complete` — broadcast finished
- `scrape_progress` — scraping progress
- `scrape_complete` — scraping finished
- `account_status` — account state change

---

## Error Codes

| HTTP Code | Meaning |
|---|---|
| `400` | Bad request / validation error |
| `401` | Missing or invalid token |
| `403` | Forbidden |
| `404` | Resource not found |
| `409` | Conflict (e.g. duplicate account) |
| `422` | Unprocessable entity |
| `429` | Rate limited |
| `500` | Internal server error |

**Error Response Format**
```json
{ "detail": "Account not found" }
```
