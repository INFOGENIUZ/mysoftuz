import logging
import shutil
import time
from enum import Enum
from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.engine import run_database_integrity_check

logger = logging.getLogger(__name__)

# Global Application Startup Timestamp
STARTUP_TIME = time.time()


class SystemState(str, Enum):
    STARTING = "STARTING"
    READY = "READY"
    DEGRADED = "DEGRADED"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"


_current_system_state: SystemState = SystemState.READY


def set_system_state(state: SystemState) -> None:
    global _current_system_state
    _current_system_state = state


def get_system_state() -> SystemState:
    return _current_system_state


def get_uptime_seconds() -> float:
    return time.time() - STARTUP_TIME


def format_uptime() -> str:
    secs = int(get_uptime_seconds())
    days, remainder = divmod(secs, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    else:
        return f"{minutes}m {seconds}s"


class HealthService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def check_database(self) -> bool:
        """Lightweight database connectivity check using SELECT 1."""
        try:
            res = await self.session.execute(text("SELECT 1;"))
            return res.scalar() == 1
        except Exception as e:
            logger.error(f"Health check DB error: {e}")
            return False

    async def check_database_integrity(self) -> bool:
        """Full SQLite file integrity check."""
        try:
            is_ok, msg = await run_database_integrity_check(self.session)
            return is_ok
        except Exception as e:
            logger.error(f"Health check DB integrity error: {e}")
            return False

    def check_disk_usage(self) -> Dict[str, Any]:
        """Checks available disk space percentage."""
        try:
            total, used, free = shutil.disk_usage(".")
            used_pct = round((used / total) * 100.0, 1)
            is_warning = used_pct >= settings.DISK_WARNING_PERCENT
            is_critical = used_pct >= settings.DISK_CRITICAL_PERCENT
            return {
                "total_gb": round(total / (1024 ** 3), 1),
                "used_gb": round(used / (1024 ** 3), 1),
                "free_gb": round(free / (1024 ** 3), 1),
                "used_pct": used_pct,
                "is_warning": is_warning,
                "is_critical": is_critical
            }
        except Exception as e:
            logger.error(f"Disk check error: {e}")
            return {"used_pct": 0.0, "is_warning": False, "is_critical": False}

    async def get_health_status(self) -> Dict[str, Any]:
        """
        Executes complete production system health check and returns status report.
        """
        db_ok = await self.check_database()
        disk_data = self.check_disk_usage()
        sys_state = get_system_state()

        overall_status = "OK" if (db_ok and sys_state == SystemState.READY and not disk_data["is_critical"]) else "UNHEALTHY"

        return {
            "status": overall_status,
            "system_state": sys_state.value,
            "version": settings.APP_VERSION,
            "uptime": format_uptime(),
            "db_status": "OK" if db_ok else "UNHEALTHY",
            "disk_status": "CRITICAL" if disk_data["is_critical"] else ("WARNING" if disk_data["is_warning"] else "OK"),
            "disk_used_pct": disk_data.get("used_pct", 0.0),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
