import logging
from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault

logger = logging.getLogger(__name__)


async def set_default_commands(bot: Bot) -> None:
    """Sets standard menu commands in Telegram UI."""
    commands = [
        BotCommand(command="start", description="🤖 Botni ishga tushirish"),
        BotCommand(command="help", description="ℹ️ Yordam va ma'lumot"),
        BotCommand(command="search", description="🔎 Dastur qidirish"),
        BotCommand(command="profile", description="👤 Profil va Shaxsiy kabinet"),
        BotCommand(command="premium", description="⭐ Premium obuna"),
        BotCommand(command="admin", description="👑 Admin panel"),
    ]
    try:
        await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
        logger.info("Bot default menu commands configured successfully.")
    except Exception as e:
        logger.warning(f"Failed to set bot menu commands: {e}")
