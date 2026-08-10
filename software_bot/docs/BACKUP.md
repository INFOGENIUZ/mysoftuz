# BACKUP & DISASTER RECOVERY RUNBOOK

---

## 1. Backup Strategy

- **Backup Cadence**: Daily Automated Backup + Pre-Deployment Snapshot
- **Retention Policy**: 30 Days (`BACKUP_RETENTION_DAYS=30`)
- **Integrity Check**: Executed using SQLite `PRAGMA integrity_check;` before confirming backup file.

---

## 2. Recovery Objectives

- **Recovery Point Objective (RPO)**: Maximum 24 Hours data loss limit.
- **Recovery Time Objective (RTO)**: Target full system recovery in **< 1 Hour**.

---

## 3. Disaster Recovery Restore Instructions

```bash
# 1. Stop active bot process
kill -SIGTERM <PID>

# 2. Verify integrity of target backup file
sqlite3 data/backups/backup_2026-08-08_02-00.db "PRAGMA integrity_check;"

# 3. Replace main database file
cp data/backups/backup_2026-08-08_02-00.db data/software_bot.db

# 4. Restart bot service and verify status
python -m app.main
```
