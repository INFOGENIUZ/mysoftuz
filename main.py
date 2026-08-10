import asyncio
import logging
import sys
import os

software_bot_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "software_bot"))
if software_bot_dir not in sys.path:
    sys.path.insert(0, software_bot_dir)

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from database.db import db
from handlers import setup_routers
from utils.set_bot_commands import set_default_commands

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger("main")

# Export FastAPI `app` for Vercel serverless function entrypoint compliance
try:
    from api.index import app
except Exception as exc:
    logger.warning(f"Could not import FastAPI app for serverless mode: {exc}")
    app = None


async def main():
    logger.info("Initializing Telegram Software Store Bot...")

    if not config.bot_token or config.bot_token in ("YOUR_TELEGRAM_BOT_TOKEN_HERE", "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ"):
        logger.critical("❌ Heavy error: BOT_TOKEN is missing or set to a placeholder! Please update .env with a valid Telegram bot token.")
        raise ValueError("BOT_TOKEN is invalid or using placeholder value.")

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )

    dp = Dispatcher(storage=MemoryStorage())

    # Initialize Production SQLite Database & Composite Indexes
    logger.info("Connecting SQLite WAL Mode database layer...")
    await db.connect()

    # Include Main Routers
    main_router = setup_routers()
    dp.include_router(main_router)

    # Set Default Bot Menu Commands
    await set_default_commands(bot)

    # Clear pending updates
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception as err:
        logger.warning(f"Webhook deletion skipped: {err}")

    logger.info("Telegram Software Store Bot successfully initialized and ready.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot execution stopped cleanly.")
