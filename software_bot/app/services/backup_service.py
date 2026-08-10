import os
import shutil
import logging
import aiosqlite
from datetime import datetime, timedelta, timezone
from typing import Tuple, List, Dict, Any
from app.config import settings

logger = logging.getLogger(__name__)


class BackupService:
    @staticmethod
    def get_db_file_path() -> str:
        """Extracts relative/absolute DB file path from DATABASE_URL."""
        return settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")

    @classmethod
    async def create_backup(cls, backup_dir: str = "backups") -> Tuple[bool, str]:
        """
        Creates a safe SQLite database backup using aiosqlite Online Backup API or file copy.
        Returns tuple: (is_success, backup_file_path_or_error_msg)
        """
        db_path = cls.get_db_file_path()
        if not os.path.exists(db_path):
            return False, f"Source DB file not found: {db_path}"

        os.makedirs(backup_dir, exist_ok=True)
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
        backup_filename = f"backup_{now_str}.db"
        backup_path = os.path.join(backup_dir, backup_filename)

        try:
            # Use SQLite Online Backup API via aiosqlite to prevent corruption during writes
            async with aiosqlite.connect(db_path) as src:
                async with aiosqlite.connect(backup_path) as dst:
                    await src.backup(dst)

            logger.info(f"Database backup created successfully: {backup_path}")
            return True, backup_path

        except Exception as e:
            logger.error(f"Failed Online Backup API, falling back to safe file copy: {e}")
            try:
                shutil.copy2(db_path, backup_path)
                logger.info(f"Database backup copied successfully: {backup_path}")
                return True, backup_path
            except Exception as copy_err:
                logger.error(f"Backup failed completely: {copy_err}")
                return False, str(copy_err)

    @classmethod
    async def clean_old_backups(cls, backup_dir: str = "backups", retention_days: int = 7) -> int:
        """
        Cleans backup files older than retention_days, ensuring at least 1 recent backup remains.
        Returns count of removed backup files.
        """
        if not os.path.exists(backup_dir):
            return 0

        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        files = [
            os.path.join(backup_dir, f)
            for f in os.listdir(backup_dir)
            if f.startswith("backup_") and f.endswith(".db")
        ]

        if len(files) <= 1:
            # Guarantee at least 1 latest backup is preserved
            return 0

        files.sort(key=lambda x: os.path.getmtime(x))
        removed_count = 0

        # Don't delete the newest file
        for file_path in files[:-1]:
            mtime = datetime.fromtimestamp(os.path.getmtime(file_path), tz=timezone.utc)
            if mtime < cutoff:
                try:
                    os.remove(file_path)
                    removed_count += 1
                    logger.info(f"Removed old backup: {file_path}")
                except Exception as err:
                    logger.error(f"Failed to remove backup {file_path}: {err}")

        return removed_count

    @classmethod
    async def list_backups(cls, backup_dir: str = "backups") -> List[Dict[str, Any]]:
        """Returns metadata list of available database backups."""
        if not os.path.exists(backup_dir):
            return []

        result = []
        files = [
            f for f in os.listdir(backup_dir)
            if f.startswith("backup_") and f.endswith(".db")
        ]

        for f in files:
            p = os.path.join(backup_dir, f)
            stat = os.stat(p)
            result.append({
                "filename": f,
                "file_path": p,
                "size_bytes": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
            })

        result.sort(key=lambda x: x["created_at"], reverse=True)
        return result
