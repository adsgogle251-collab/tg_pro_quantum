# TG PRO QUANTUM v7.0.0

Professional multi-client **Telegram Broadcast-as-a-Service** platform built with FastAPI, PostgreSQL, Celery, and Redis.

---

## 🚀 Features

| Category | Details |
|---|---|
| **Multi-tenant** | Isolated data per client, per-client API keys |
| **Authentication** | JWT Bearer + X-API-Key header, OTP SMS via SMS Activate |
| **Broadcast modes** | Once, round-robin, loop, 24/7 cron schedule |
| **Campaign management** | CRUD, status tracking, configurable delays |
| **Account management** | Multiple Telegram accounts per client, health monitoring |
| **Group management** | Auto-join, member scraping, bulk import |
| **Analytics** | Per-campaign & per-client delivery metrics |
| **Task queue** | Celery + Redis for background jobs and scheduling |
| **Database** | PostgreSQL with async SQLAlchemy |
| **Docker** | Full Docker Compose setup |

---

## 📦 Tech Stack

- **Framework**: FastAPI (async)
- **Database**: PostgreSQL 16 + SQLAlchemy 2 (asyncpg)
- **Task Queue**: Celery 5 + Redis 7
- **ORM**: SQLAlchemy with Alembic migrations
- **Validation**: Pydantic v2
- **Authentication**: JWT (python-jose) + bcrypt (passlib) + OTP SMS
- **Telegram**: Telethon

---

## 🗂️ Project Structure

```
app/
├── main.py                  # FastAPI entry point
├── config.py                # Settings (pydantic-settings)
├── database.py              # PostgreSQL async engine
├── api/
│   ├── dependencies.py      # JWT / API-key auth
│   └── routes/
│       ├── auth.py          # Register, login, refresh, OTP
│       ├── clients.py       # Client management
│       ├── accounts.py      # Telegram account management
│       ├── groups.py        # Group management
│       ├── campaigns.py     # Campaign CRUD
│       ├── broadcasts.py    # Start/pause/stop + dashboard
│       └── analytics.py     # Stats & history
├── models/
│   ├── database.py          # SQLAlchemy ORM models
│   └── schemas.py           # Pydantic request/response schemas
├── core/
│   ├── broadcast_engine.py  # Multi-account broadcast orchestrator
│   ├── campaign_scheduler.py# Celery Beat integration
│   ├── otp_manager.py       # OTP lifecycle
│   ├── account_manager.py   # Health checks, rotation
│   ├── group_manager.py     # Auto-join, scraping
│   └── analytics_engine.py  # Metrics calculations
├── services/
│   ├── telegram_service.py  # Telethon wrapper
│   ├── sms_activate_service.py # SMS Activate API
│   └── email_service.py     # SMTP notifications
├── middleware/
│   └── error_handler.py     # Global exception handler
└── utils/
    ├── logger.py
    └── helpers.py
tasks/
├── broadcast_tasks.py       # Celery broadcast worker
└── scheduler_tasks.py       # Celery Beat periodic tasks
```

---

## ⚡ Quick Start

### 1. Clone & configure

```bash
git clone https://github.com/adsgogle251-collab/tg_pro_quantum.git
cd tg_pro_quantum
cp .env.example .env
# Edit .env with your values
```

### 2. Docker Compose (recommended)

```bash
docker compose up --build
```

API available at: **http://localhost:8000**  
Swagger UI: **http://localhost:8000/docs**

### 3. Local development

```bash
pip install -r requirements.txt

# Start PostgreSQL & Redis (or use Docker)
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=tg_quantum postgres:16-alpine
docker run -d -p 6379:6379 redis:7-alpine

# Run FastAPI
uvicorn app.main:app --reload

# Run Celery worker (separate terminal)
celery -A tasks.broadcast_tasks.celery_app worker --loglevel=info

# Run Celery Beat scheduler (separate terminal)
celery -A tasks.scheduler_tasks.celery_app beat --loglevel=info
```

---

## 🔐 Authentication

### Register
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "name": "Acme Corp",
  "email": "admin@acme.com",
  "password": "strongpassword"
}
```

### Login
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "admin@acme.com",
  "password": "strongpassword"
}
```

Response:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

Use the token in subsequent requests:
```
Authorization: Bearer <access_token>
```
or
```
X-API-Key: <your_api_key>
```

---

## 📡 API Endpoints

### Authentication (`/api/v1/auth`)

| Method | Endpoint | Description |
|---|---|---|
| POST | `/register` | Register new client |
| POST | `/login` | Login |
| POST | `/refresh` | Refresh access token |
| GET | `/me` | Get current client info |
| POST | `/otp/request` | Request OTP SMS |
| POST | `/otp/verify` | Verify OTP code |

### Clients (`/api/v1/clients`)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | List all clients (admin) |
| POST | `/` | Create client (admin) |
| GET | `/me` | Get own profile |
| GET | `/{id}` | Get client |
| PATCH | `/{id}` | Update client |
| DELETE | `/{id}` | Delete client (admin) |
| POST | `/{id}/regenerate-api-key` | Regenerate API key |

### Telegram Accounts (`/api/v1/accounts`)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | List accounts |
| POST | `/` | Add account |
| GET | `/{id}` | Get account |
| PATCH | `/{id}` | Update account |
| DELETE | `/{id}` | Delete account |
| POST | `/{id}/health-check` | Run health check |

### Groups (`/api/v1/groups`)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | List groups |
| POST | `/` | Add group |
| GET | `/{id}` | Get group |
| PATCH | `/{id}` | Update group |
| DELETE | `/{id}` | Delete group |
| POST | `/{id}/auto-join` | Auto-join group |
| POST | `/bulk-import` | Bulk import groups |

### Campaigns (`/api/v1/campaigns`)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | List campaigns |
| POST | `/` | Create campaign |
| GET | `/{id}` | Get campaign |
| PATCH | `/{id}` | Update campaign |
| DELETE | `/{id}` | Delete campaign |

### Broadcasts (`/api/v1/broadcasts`)

| Method | Endpoint | Description |
|---|---|---|
| POST | `/start` | Start campaign |
| POST | `/{id}/pause` | Pause campaign |
| POST | `/{id}/resume` | Resume campaign |
| POST | `/{id}/stop` | Stop campaign |
| GET | `/{id}/dashboard` | Real-time dashboard |
| GET | `/{id}/logs` | Broadcast logs |

### Analytics (`/api/v1/analytics`)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/campaigns` | Per-campaign stats |
| GET | `/overview` | Client overview |
| GET | `/history` | Campaign history |

---

## 📊 Campaign Modes

| Mode | Description |
|---|---|
| `once` | Single run through all target groups |
| `round_robin` | Distribute messages across accounts in rotation |
| `loop` | Repeat campaign with configurable interval |
| `schedule_24_7` | Cron-based 24/7 scheduling |

### Example: Create a 24/7 campaign

```http
POST /api/v1/campaigns
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Daily Promo",
  "message_text": "🔥 Special offer today!",
  "mode": "schedule_24_7",
  "cron_expression": "0 9 * * *",
  "target_group_ids": [1, 2, 3],
  "account_ids": [1, 2],
  "delay_min": 3.0,
  "delay_max": 8.0
}
```

---

## 🔧 Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL connection |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis URL |
| `SECRET_KEY` | — | JWT signing secret (required) |
| `SMS_ACTIVATE_API_KEY` | — | SMS Activate API key |
| `TELEGRAM_API_ID` | — | Default Telegram API ID |
| `TELEGRAM_API_HASH` | — | Default Telegram API hash |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | JWT access token lifetime |
| `DEFAULT_DELAY_MIN` | `3.0` | Min delay between messages (s) |
| `DEFAULT_DELAY_MAX` | `8.0` | Max delay between messages (s) |

See `.env.example` for the full list.

---

## 🐳 Docker Services

| Service | Port | Description |
|---|---|---|
| `app` | 8000 | FastAPI application |
| `db` | 5432 | PostgreSQL 16 |
| `redis` | 6379 | Redis 7 |
| `celery_worker` | — | Celery broadcast worker |
| `celery_beat` | — | Celery Beat scheduler |

---

## 📝 License

MIT
