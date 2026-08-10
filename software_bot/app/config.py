import sys
import logging
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    APP_VERSION: str = "1.0.0"
    BOT_TOKEN: str = ""
    ADMIN_IDS: List[int] = [8887751785]
    DATABASE_URL: str = "sqlite+aiosqlite:///data/software_bot.db"

    # Production & Logging
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "production"  # "development" | "staging" | "production"
    MAINTENANCE_MODE: bool = False

    LOG_MAX_MB: int = 20
    LOG_BACKUP_COUNT: int = 5
    BACKUP_RETENTION_DAYS: int = 7
    MAX_RETRIES: int = 3

    MAX_FILE_SIZE_MB: int = 4096
    PROGRAMS_PER_PAGE: int = 10
    CATEGORIES_PER_PAGE: int = 10
    ALLOWED_EXTENSIONS: List[str] = [".exe", ".msi", ".zip", ".rar", ".7z"]

    # Thresholds & Worker Config
    NOTIFICATION_BATCH_SIZE: int = 50
    NOTIFICATION_MAX_RETRIES: int = 3
    WORKER_POLL_INTERVAL: int = 1
    FSM_TTL_MINUTES: int = 30

    SLOW_QUERY_THRESHOLD_MS: int = 300
    SLOW_HANDLER_THRESHOLD_MS: int = 1000
    DISK_WARNING_PERCENT: int = 80
    DISK_CRITICAL_PERCENT: int = 90

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("ADMIN_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, value: Union[str, List[int], int]) -> List[int]:
        parsed = []
        if isinstance(value, str):
            if value.strip():
                parsed = [int(item.strip()) for item in value.split(",") if item.strip().isdigit()]
        elif isinstance(value, int):
            parsed = [value]
        elif isinstance(value, list):
            parsed = [int(x) for x in value]

        if not parsed:
            parsed = [8887751785]
        return parsed

    @field_validator("ALLOWED_EXTENSIONS", mode="before")
    @classmethod
    def parse_allowed_extensions(cls, value: Union[str, List[str]]) -> List[str]:
        if isinstance(value, str):
            return [ext.strip().lower() for ext in value.split(",") if ext.strip()]
        elif isinstance(value, list):
            return [str(ext).strip().lower() for ext in value]
        return [".exe", ".msi", ".zip", ".rar", ".7z"]


settings = Settings()


def validate_environment() -> bool:
    """
    Validates essential environment configuration on startup.
    Fails fast if critical variables like BOT_TOKEN or ADMIN_IDS (in production) are missing.
    Returns True if valid, else raises ValueError or exits.
    """
    if not settings.BOT_TOKEN or settings.BOT_TOKEN in ("your_bot_token_here", "YOUR_BOT_TOKEN_HERE"):
        logger.critical("❌ BOT_TOKEN is not configured in .env!")
        return False

    if not settings.ADMIN_IDS:
        if settings.ENVIRONMENT.lower() == "production":
            logger.critical("❌ No admin users configured in production mode!")
            return False
        else:
            logger.warning("⚠️ Warning: No admin users configured in ADMIN_IDS (Development mode).")

    return True
