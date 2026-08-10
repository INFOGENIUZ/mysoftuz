# EMERGENCY INCIDENT RESPONSE RUNBOOK

---

## Incident Scenarios & Action Plans

### 1. Telegram API 429 Rate Limit (Too Many Requests)
- **Symptom**: Logs show `TelegramRetryAfter` warnings.
- **Action**: Handled automatically by `TelegramDeliveryService`. The delivery service sleeps for `retry_after` seconds and retries gracefully without dropping messages.

### 2. Database Locked (`sqlite3.OperationalError: database is locked`)
- **Symptom**: Concurrency lock error on SQLite.
- **Action**: Verified `PRAGMA busy_timeout = 5000;` and `PRAGMA journal_mode = WAL;` are active. Retry queue handles transient locks.

### 3. Disk Space Full Alert (>90%)
- **Symptom**: Admin Health Check displays `🔴 Disk Status: CRITICAL`.
- **Action**: Run log rotation and old backup retention cleanup:
  - Delete backups older than 30 days in `data/backups/`.
  - Compress rotated application log files.

### 4. Telegram Bot Token Compromised / Leaked
- **Symptom**: Unauthorized bot actions or token leak.
- **Action**:
  1. Revoke token via `@BotFather` immediately.
  2. Update `BOT_TOKEN` in `.env`.
  3. Restart bot process.
