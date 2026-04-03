# TG Pro Quantum — FastAPI Broadcast Service

Production-ready **FastAPI** multi-client Telegram broadcast service layered on top of the existing Tkinter GUI application.

---

## Architecture Overview

```
tg_pro_quantum/
├── app/                        # NEW – FastAPI service
│   ├── main.py                 # FastAPI app factory + lifespan
│   ├── config.py               # Pydantic-Settings configuration
│   ├── database.py             # SQLAlchemy async engine + session
│   ├── models/
│   │   ├── database.py         # All ORM models
│   │   └── schemas.py          # Pydantic request/response schemas
│   ├── api/
│   │   ├── dependencies.py     # JWT auth, rate limiter, client guard
│   │   └── routes/
│   │       ├── auth.py         # /api/v1/auth/*
│   │       ├── clients.py      # /api/v1/clients/*
│   │       ├── accounts.py     # /api/v1/clients/{id}/accounts/*
│   │       ├── groups.py       # /api/v1/clients/{id}/groups/*
│   │       ├── campaigns.py    # /api/v1/clients/{id}/campaigns/*
│   │       ├── broadcasts.py   # /api/v1/campaigns/{id}/broadcast/*  + WS
│   │       └── analytics.py    # /api/v1/campaigns/{id}/analytics/*
│   ├── core/
│   │   ├── broadcast_engine.py  # Multi-account engine with anti-ban delays
│   │   ├── campaign_scheduler.py# Celery Beat scheduling + loop mode
│   │   ├── otp_manager.py       # SMS Activate integration
│   │   ├── account_manager.py   # Session lifecycle + health checks
│   │   ├── group_manager.py     # Auto-join + member scraping
│   │   └── analytics_engine.py  # Metrics, CSV/JSON export
│   ├── services/
│   │   ├── telegram_service.py  # Telethon client wrapper
│   │   ├── sms_activate_service.py
│   │   └── email_service.py
│   ├── middleware/
│   │   ├── auth.py              # JWT middleware + rate limiting
│   │   └── error_handler.py     # Global exception handlers
│   └── utils/
│       ├── logger.py            # Structured logging setup
│       └── helpers.py           # bcrypt, JWT helpers, API key gen
├── tasks/
│   ├── broadcast_tasks.py       # Celery broadcast tasks
│   └── scheduler_tasks.py       # Celery periodic tasks
├── alembic/                     # Database migrations
├── celery_app.py                # Celery application
├── docker-compose.yml
├── Dockerfile
├── .env.example
└── requirements.txt
```

---

## Quick Start

### 1. Copy environment file
```bash
cp .env.example .env
# Edit .env with your credentials
```

### 2. Docker Compose (recommended)
```bash
docker-compose up --build -d
```

Services started:
| Service | Port |
|---------|------|
| FastAPI | 8000 |
| PostgreSQL | 5432 |
| Redis | 6379 |
| Celery Worker | — |
| Celery Beat | — |

### 3. Local development
```bash
pip install -r requirements.txt

# Apply migrations
alembic upgrade head

# Start API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start Celery worker (separate terminal)
celery -A celery_app worker --loglevel=info

# Start Celery Beat scheduler (separate terminal)
celery -A celery_app beat --loglevel=info
```

---

## API Documentation

Visit **http://localhost:8000/docs** for Swagger UI or **/redoc** for ReDoc.

### Authentication
All protected endpoints require:
```
Authorization: Bearer <access_token>
```

### Key Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Register admin user |
| POST | `/api/v1/auth/login` | Login, receive JWT tokens |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| GET | `/api/v1/clients/` | List clients |
| POST | `/api/v1/clients/` | Create client |
| GET | `/api/v1/clients/{id}/accounts/` | List Telegram accounts |
| POST | `/api/v1/clients/{id}/accounts/` | Add account |
| POST | `.../accounts/{id}/request-otp` | Request SMS OTP |
| POST | `.../accounts/{id}/verify-otp` | Verify OTP, activate account |
| GET | `/api/v1/clients/{id}/groups/` | List groups |
| POST | `.../groups/auto-join` | Auto-join groups |
| POST | `.../groups/scrape-members` | Scrape group members |
| GET | `/api/v1/clients/{id}/campaigns/` | List campaigns |
| POST | `/api/v1/clients/{id}/campaigns/` | Create campaign |
| POST | `.../campaigns/{id}/schedule` | Schedule campaign |
| POST | `/api/v1/campaigns/{id}/broadcast/send` | Start broadcast |
| GET | `/api/v1/campaigns/{id}/broadcast/status` | Broadcast status |
| POST | `/api/v1/campaigns/{id}/broadcast/pause` | Pause broadcast |
| POST | `/api/v1/campaigns/{id}/broadcast/resume` | Resume broadcast |
| GET | `/api/v1/campaigns/{id}/analytics/` | Campaign analytics |
| GET | `/api/v1/clients/{id}/analytics/export` | Export CSV/JSON |
| WS | `/ws/campaigns/{id}/live` | Real-time progress feed |
| GET | `/health` | Health check |

---

## Database Migrations

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "description"

# Apply pending migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1
```

---

## Broadcast Engine Features

- **Multi-account round-robin** — distributes load across active accounts
- **Anti-ban delays** — random `delay_min`–`delay_max` second pauses between sends
- **Loop mode** — repeat campaigns N times or infinitely
- **Retry logic** — up to 3 retries per failed message with exponential back-off
- **Real-time WebSocket** — live progress via `/ws/campaigns/{id}/live`
- **Celery Beat scheduling** — cron-based execution for 24/7 operation

---

## Environment Variables

See [`.env.example`](.env.example) for a full list. Key variables:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL async DSN |
| `REDIS_URL` | Redis DSN |
| `JWT_SECRET_KEY` | JWT signing secret (change in prod!) |
| `TELEGRAM_API_ID` | Default Telegram API ID |
| `TELEGRAM_API_HASH` | Default Telegram API Hash |
| `SMS_ACTIVATE_API_KEY` | SMS Activate API key for OTP |
| `CELERY_BROKER_URL` | Celery broker (Redis) |
