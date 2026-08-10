# TELEGRAM SOFTWARE STORE BOT — PRODUCTION RUNBOOK

---

## 1. System Architecture Overview

Telegram Software Store Bot is built on **Python (Aiogram 3)** and **SQLAlchemy (SQLite WAL Mode)** with **In-Memory TTL Caching** and background worker process for notifications and updates delivery.

- **Application Mode**: Production (`ENVIRONMENT=production`)
- **Version**: `v1.0.0`
- **Database**: SQLite 3 with `PRAGMA journal_mode=WAL;` and `PRAGMA busy_timeout=5000;`
- **Cache**: In-Memory Thread-Safe TTL Cache Layer (`CacheService`)

---

## 2. Startup & Shutdown Commands

### Starting the Bot in Production
```bash
# Set production environment variables
export ENVIRONMENT=production
export BOT_TOKEN="your_production_token"
export ADMIN_IDS="123456789"
export DATABASE_URL="sqlite+aiosqlite:///data/software_store.db"

# Run main application
python -m app.main
```

### Graceful Shutdown
To stop the bot safely without interrupting active notification workers or database transactions:
```bash
# Send SIGINT (Ctrl+C) or SIGTERM signal
kill -SIGTERM <PID>
```

---

## 3. Environment Variables Reference

| Key | Description | Default |
| :--- | :--- | :--- |
| `ENVIRONMENT` | Runtime mode (`development`, `staging`, `production`) | `production` |
| `APP_VERSION` | Application Version Tag | `1.0.0` |
| `BOT_TOKEN` | Production Telegram Bot Token (Required) | *None* |
| `ADMIN_IDS` | Comma-separated Administrator Telegram User IDs | *None* |
| `DATABASE_URL` | SQLAlchemy Connection URL | `sqlite+aiosqlite:///data/software_bot.db` |
| `LOG_LEVEL` | Python Logger Threshold (`INFO`, `WARNING`, `ERROR`) | `INFO` |
| `SLOW_QUERY_THRESHOLD_MS` | Warning threshold for slow DB queries (ms) | `300` |

---

## 4. Operational Health & Diagnostics

Administrators can monitor real-time system status inside Telegram via:
- Admin Panel -> `🩺 Health Check`
- Real-time Uptime, Database Status (`SELECT 1;`), Disk Usage %, and Version metadata.
