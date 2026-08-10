import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TelegramUser
from app.database.engine import async_session_maker
from app.services.user_service import UserService
from app.config import settings

logger = logging.getLogger(__name__)


class UserTrackingMiddleware(BaseMiddleware):
    """
    Outer middleware that automatically registers new users and updates
    their profile fields (first_name, last_name, username, last_activity)
    on every Telegram interaction.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        telegram_user: TelegramUser = data.get("event_from_user")
        if telegram_user:
            try:
                is_admin = telegram_user.id in settings.ADMIN_IDS
                async with async_session_maker() as session:
                    user_service = UserService(session)
                    await user_service.get_or_create_user(
                        telegram_id=telegram_user.id,
                        first_name=telegram_user.first_name or "",
                        last_name=telegram_user.last_name,
                        username=telegram_user.username,
                        language_code=telegram_user.language_code,
                        is_admin=is_admin
                    )
            except Exception as tracking_err:
                logger.error(f"UserTrackingMiddleware error for user {telegram_user.id}: {tracking_err}")

        return await handler(event, data)
