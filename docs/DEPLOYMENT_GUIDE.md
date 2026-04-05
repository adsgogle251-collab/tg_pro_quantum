# TG PRO QUANTUM — Deployment Guide

## Table of Contents
1. [Docker Compose (Recommended)](#docker-compose-recommended)
2. [Manual Server Deployment](#manual-server-deployment)
3. [Environment Variables](#environment-variables)
4. [PostgreSQL Setup](#postgresql-setup)
5. [Redis Setup](#redis-setup)
6. [SSL/HTTPS with Nginx](#sslhttps-with-nginx)
7. [Health Monitoring](#health-monitoring)
8. [Backup Procedures](#backup-procedures)

---

## Docker Compose (Recommended)

### Requirements
- Docker 24+
- Docker Compose v2

### Steps

```bash
# Clone the repository
git clone https://github.com/your-org/tg_pro_quantum.git
cd tg_pro_quantum

# Create environment file
cp .env.example .env
# Edit .env with your credentials (see Environment Variables section)

# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f app
```

Services started:
| Service | Port | Description |
|---|---|---|
| `db` | 5432 | PostgreSQL database |
| `redis` | 6379 | Redis cache/broker |
| `app` | 8000 | FastAPI backend |
| `celery_worker` | — | Async task worker |
| `celery_beat` | — | Task scheduler |
| `frontend` | 3000 | React web dashboard |

### Updating
```bash
git pull
docker-compose build --no-cache
docker-compose up -d
```

---

## Manual Server Deployment

### Requirements
- Ubuntu 22.04 / Debian 12
- Python 3.9+
- Node.js 18+
- PostgreSQL 14+
- Redis 7+

### Steps

```bash
# Install system dependencies
sudo apt update && sudo apt install -y python3-pip nodejs npm postgresql redis-server

# Install Python dependencies
pip install -r requirements.txt

# Install and build frontend
cd frontend && npm install && npm run build && cd ..

# Run database migrations
python -m alembic upgrade head

# Start the API server (use a process manager like systemd or supervisor)
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# Start Celery worker
celery -A tasks.broadcast_tasks.celery_app worker --loglevel=info --concurrency=4

# Start Celery beat
celery -A tasks.scheduler_tasks.celery_app beat --loglevel=info
```

---

## Environment Variables

Copy `.env.example` to `.env` and set:

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_API_ID` | ✅ | From my.telegram.org |
| `TELEGRAM_API_HASH` | ✅ | From my.telegram.org |
| `SECRET_KEY` | ✅ | JWT signing key (generate with `openssl rand -hex 32`) |
| `DATABASE_URL` | ✅ | `postgresql+asyncpg://user:pass@host/db` |
| `REDIS_URL` | ✅ | `redis://localhost:6379/0` |
| `CELERY_BROKER_URL` | ✅ | Same as `REDIS_URL` |
| `CELERY_RESULT_BACKEND` | ✅ | `redis://localhost:6379/1` |
| `DEBUG` | — | `false` in production |
| `ALLOWED_ORIGINS` | — | Comma-separated CORS origins |

> ⚠️ **Never commit `.env` to version control.**

---

## PostgreSQL Setup

```sql
-- Create database and user (run as postgres superuser)
CREATE DATABASE tg_quantum;
CREATE USER tg_user WITH ENCRYPTED PASSWORD 'strongpassword';
GRANT ALL PRIVILEGES ON DATABASE tg_quantum TO tg_user;
```

Update `DATABASE_URL` accordingly, then run migrations:

```bash
python -m alembic upgrade head
```

---

## Redis Setup

Redis requires no special configuration for basic use. For production, enable persistence:

```conf
# /etc/redis/redis.conf
appendonly yes
appendfsync everysec
```

Restart Redis: `sudo systemctl restart redis`

---

## SSL/HTTPS with Nginx

```nginx
# /etc/nginx/sites-available/tg_quantum
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate     /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # Web dashboard
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
    }

    # API
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket
    location /ws/ {
        proxy_pass http://localhost:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
    }
}
```

Obtain a free certificate: `sudo certbot --nginx -d your-domain.com`

---

## Health Monitoring

The API exposes a health endpoint:

```bash
curl http://localhost:8000/health
# {"status": "ok", "db": "connected", "redis": "connected"}
```

Use this with your monitoring tool (UptimeRobot, Prometheus, etc.).

Docker healthchecks are already configured for `db` and `redis` services.

---

## Backup Procedures

### Database Backup
```bash
# Dump
docker exec tg_pro_quantum-db-1 pg_dump -U postgres tg_quantum > backup_$(date +%Y%m%d).sql

# Restore
docker exec -i tg_pro_quantum-db-1 psql -U postgres tg_quantum < backup_20240101.sql
```

### Session Files Backup
```bash
# Sessions are mounted at ./sessions — back up this directory
tar -czf sessions_backup_$(date +%Y%m%d).tar.gz sessions/
```

Schedule backups with cron:
```cron
0 3 * * * /path/to/backup-script.sh >> /var/log/tg_backup.log 2>&1
```
