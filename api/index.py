import os
import sys
import logging
from fastapi import FastAPI, Request, Response
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

# Ensure project root & software_bot directory are in sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

software_bot_dir = os.path.join(root_dir, "software_bot")
if software_bot_dir not in sys.path:
    sys.path.insert(0, software_bot_dir)

from config import config
from database.db import db
from handlers import setup_routers
from utils.set_bot_commands import set_default_commands

from app.middlewares import (
    UserTrackingMiddleware,
    AntiSpamMiddleware,
    ThrottlingMiddleware,
    AdminMiddleware,
    MaintenanceMiddleware,
)
from app.handlers.errors import router as errors_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger("vercel_bot")

# Initialize Bot & Dispatcher
bot = Bot(
    token=config.bot_token or "123456789:PlaceholderTokenForBuildOnly",
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
)
dp = Dispatcher(storage=MemoryStorage())

# Register Global Errors Router
dp.include_router(errors_router)

# Register Middlewares (Order: UserTracking -> AntiSpam -> Throttling -> Admin -> Maintenance)
dp.message.outer_middleware(UserTrackingMiddleware())
dp.message.outer_middleware(AntiSpamMiddleware())
dp.message.outer_middleware(ThrottlingMiddleware())
dp.message.outer_middleware(AdminMiddleware())
dp.message.outer_middleware(MaintenanceMiddleware())

dp.callback_query.outer_middleware(UserTrackingMiddleware())
dp.callback_query.outer_middleware(AntiSpamMiddleware())
dp.callback_query.outer_middleware(ThrottlingMiddleware())
dp.callback_query.outer_middleware(AdminMiddleware())
dp.callback_query.outer_middleware(MaintenanceMiddleware())

# Include Main Routers
main_router = setup_routers()
dp.include_router(main_router)

_db_initialized = False


async def ensure_db_initialized():
    global _db_initialized
    if not _db_initialized:
        try:
            logger.info("Initializing database connection on Vercel Serverless request...")
            await db.connect()
            await set_default_commands(bot)
            _db_initialized = True
        except Exception as err:
            logger.error(f"Error initializing DB in serverless request: {err}", exc_info=True)


app = FastAPI(title="Telegram Software Store Bot")


@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "Telegram Software Store Bot",
        "mode": "Vercel Serverless Webhook"
    }


@app.get("/api/webhook")
@app.post("/api/webhook")
async def webhook(request: Request):
    if request.method == "POST":
        try:
            await ensure_db_initialized()
            data = await request.json()
            update = types.Update(**data)
            await dp.feed_update(bot=bot, update=update)
            return {"status": "ok"}
        except Exception as err:
            logger.error(f"Error handling update in webhook: {err}", exc_info=True)
            return Response(content=str(err), status_code=500)
    return {"status": "Webhook endpoint active"}
