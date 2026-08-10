import os
import logging
from dataclasses import dataclass
from typing import List
from dotenv import load_dotenv

from software_bot.app.config import settings as app_settings

load_dotenv()
logger = logging.getLogger(__name__)


@dataclass
class Config:
    bot_token: str
    admin_ids: List[int]
    db_name: str
    environment: str = "production"


def load_config() -> Config:
    token = os.getenv("BOT_TOKEN", app_settings.BOT_TOKEN)
    admins_str = os.getenv("ADMINS", os.getenv("ADMIN_IDS", ""))

    admin_ids = app_settings.ADMIN_IDS
    if admins_str:
        parsed_ids = []
        for admin in admins_str.split(","):
            admin = admin.strip()
            if admin.isdigit():
                parsed_ids.append(int(admin))
        if parsed_ids:
            admin_ids = parsed_ids

    db_name = os.getenv("DB_NAME", app_settings.DATABASE_URL.replace("sqlite+aiosqlite:///", ""))

    return Config(
        bot_token=token,
        admin_ids=admin_ids,
        db_name=db_name,
        environment=os.getenv("ENVIRONMENT", app_settings.ENVIRONMENT)
    )


config = load_config()
