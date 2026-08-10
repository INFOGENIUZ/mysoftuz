import os
import re
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional
from app.config import settings


class SecretScrubberFilter(logging.Filter):
    """
    Logging Filter that automatically scrubs sensitive credentials (such as BOT_TOKEN)
    from log record messages.
    """
    def __init__(self, name: str = "", secrets: Optional[list] = None):
        super().__init__(name)
        self.secrets = [s for s in (secrets or []) if s and len(s) > 5]
        # Regex to catch typical Bot Token format: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz
        self.token_regex = re.compile(r"\d{8,10}:[A-Za-z0-9_-]{35}")

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            # Mask regex matched tokens
            record.msg = self.token_regex.sub("*****:BOT_TOKEN_MASHED*****", record.msg)
            # Mask explicit secrets
            for secret in self.secrets:
                if secret in record.msg:
                    record.msg = record.msg.replace(secret, "*****SECRET_SCRUBBED*****")
        return True


def setup_logging(log_dir: str = "logs") -> logging.Logger:
    """
    Sets up structured logging with RotatingFileHandler and secret scrubbing.
    - LOG_MAX_MB (default 20MB)
    - LOG_BACKUP_COUNT (default 5)
    """
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, "bot.log")

    logger = logging.getLogger()
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(log_level)

    # Clear existing handlers
    logger.handlers.clear()

    # Formatter
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Scrubber Filter
    secrets_to_scrub = []
    if hasattr(settings, "BOT_TOKEN") and settings.BOT_TOKEN:
        secrets_to_scrub.append(settings.BOT_TOKEN)
    scrub_filter = SecretScrubberFilter(secrets=secrets_to_scrub)

    # File Handler (Rotating)
    max_bytes = getattr(settings, "LOG_MAX_MB", 20) * 1024 * 1024
    backup_count = getattr(settings, "LOG_BACKUP_COUNT", 5)

    file_handler = RotatingFileHandler(
        log_file_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(scrub_filter)
    logger.addHandler(file_handler)

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(scrub_filter)
    logger.addHandler(console_handler)

    logger.info(f"Logging initialized. Level: {settings.LOG_LEVEL}, LogFile: {log_file_path}")
    return logger
