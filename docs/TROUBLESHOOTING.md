# TG PRO QUANTUM — Troubleshooting Guide

## Table of Contents
1. [Common Startup Errors](#common-startup-errors)
2. [Telegram API Errors](#telegram-api-errors)
3. [Database Issues](#database-issues)
4. [WebSocket Issues](#websocket-issues)
5. [Account Ban Prevention](#account-ban-prevention)
6. [Performance Tuning](#performance-tuning)

---

## Common Startup Errors

### `dotenv / .env file not found`
```
Solution: cp .env.example .env
Then fill in TELEGRAM_API_ID, TELEGRAM_API_HASH, and SECRET_KEY.
```

### `Address already in use (port 8000)`
Another process is using the port. Find and stop it:
```bash
lsof -ti:8000 | xargs kill
```

### `ModuleNotFoundError`
```bash
pip install -r requirements.txt
```
If using Docker: `docker-compose build --no-cache`

### `alembic.util.exc.CommandError: Can't locate revision`
Reset migrations:
```bash
python -m alembic stamp head
python -m alembic upgrade head
```

---

## Telegram API Errors

### `FLOOD_WAIT_X`
Telegram is rate-limiting the account. The `X` value is the required wait in seconds.

- **Cause**: Too many requests in a short period.
- **Fix**: Increase the delay between messages. The app respects this automatically and retries after the wait.
- **Prevention**: Use multiple accounts to distribute load; set `delay_min` ≥ 3 seconds.

---

### `AUTH_KEY_UNREGISTERED`
The session file is no longer valid (account logged out or banned).

- **Fix**: Delete the session file from `./sessions/` and re-authenticate the account.
```bash
rm sessions/<phone>.session
```

---

### `PHONE_NUMBER_BANNED`
The Telegram account has been banned.

- **Fix**: The account cannot be recovered. Remove it from the system and replace it.

---

### `USER_PRIVACY_RESTRICTED`
The target user has privacy settings that prevent DMs.

- **Fix**: This is expected for some users. The broadcast skips them automatically; check failed count in analytics.

---

### `CHAT_WRITE_FORBIDDEN`
You are not allowed to write in the target group.

- **Fix**: Ensure the sending account is a member of the group and has write permissions.

---

### `SESSION_REVOKED`
Another device logged out this session.

- **Fix**: Re-authenticate the account via **Accounts → Verify**.

---

### `CONNECTION_DEVICE_MODEL_DEPRECATED`
Outdated Telethon version.

- **Fix**:
```bash
pip install --upgrade telethon
```

---

## Database Issues

### `asyncpg.exceptions.ConnectionDoesNotExistError`
Database connection dropped.

- **Fix**: Check that PostgreSQL is running and `DATABASE_URL` is correct.
```bash
pg_isready -h localhost -p 5432
```

### `relation "accounts" does not exist`
Migrations have not been applied.
```bash
python -m alembic upgrade head
```

### `too many connections`
PostgreSQL connection pool exhausted.

- **Fix**: Reduce `--workers` in the `uvicorn` startup command, or increase PostgreSQL's `max_connections`:
```sql
ALTER SYSTEM SET max_connections = 200;
SELECT pg_reload_conf();
```

---

## WebSocket Issues

### `WebSocket connection failed`
- Verify `VITE_WS_URL` in the frontend `.env` points to the running backend.
- Check browser console for CORS errors; add the frontend origin to `ALLOWED_ORIGINS`.

### `WebSocket keeps disconnecting`
- The Nginx proxy must pass `Upgrade` and `Connection` headers (see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)).
- Check Nginx `proxy_read_timeout` — increase to at least `3600s` for long-lived connections.

---

## Account Ban Prevention

Follow these guidelines to minimise ban risk:

1. **Use delays**: Set `delay_min` ≥ 3 and `delay_max` ≤ 10 seconds between messages.
2. **Rotate accounts**: Never send more than ~50 DMs per account per hour.
3. **Warm up new accounts**: Before mass messaging, use an account normally for at least 7 days.
4. **Avoid spam keywords**: Do not include phrases Telegram's spam filter flags (short URLs, aggressive call-to-actions).
5. **Respect FLOOD_WAIT**: Let the app wait out flood timers — do not force-restart.
6. **Session files**: Store session files securely; sharing sessions across IPs triggers security checks.

---

## Performance Tuning

### Increase Celery concurrency
```bash
celery -A tasks.broadcast_tasks.celery_app worker --concurrency=8
```

### Tune uvicorn workers
```bash
uvicorn main:app --workers $(nproc) --host 0.0.0.0 --port 8000
```

### Redis memory limit
Set a memory cap to prevent runaway usage:
```conf
# /etc/redis/redis.conf
maxmemory 512mb
maxmemory-policy allkeys-lru
```

### Database connection pool
Adjust `pool_size` in `DATABASE_URL` or the SQLAlchemy engine config:
```python
create_async_engine(DATABASE_URL, pool_size=20, max_overflow=10)
```
