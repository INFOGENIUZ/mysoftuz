import os
import sys
import logging
from contextlib import asynccontextmanager
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

# Include Routers
main_router = setup_routers()
dp.include_router(main_router)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Telegram Bot on Vercel Serverless...")
    try:
        if config.bot_token and config.bot_token not in (
            "YOUR_TELEGRAM_BOT_TOKEN_HERE",
            "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ",
            "123456789:PlaceholderTokenForBuildOnly"
        ):
            await db.connect()
            await set_default_commands(bot)
        else:
            logger.warning("BOT_TOKEN is missing or set to default placeholder.")
    except Exception as err:
        logger.error(f"Lifespan DB initialization error: {err}")
    yield
    try:
        await bot.session.close()
    except Exception:
        pass


app = FastAPI(title="Telegram Software Store Bot", lifespan=lifespan)


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
            data = await request.json()
            update = types.Update(**data)
            await dp.feed_update(bot=bot, update=update)
            return {"status": "ok"}
        except Exception as err:
            logger.error(f"Error handling update in webhook: {err}", exc_info=True)
            return Response(content=str(err), status_code=500)
    return {"status": "Webhook endpoint active"}
