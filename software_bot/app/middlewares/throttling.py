import time
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery


class ThrottlingMiddleware(BaseMiddleware):
    """
    In-memory rate limiting / anti-spam middleware.
    Prevents flooding callbacks and message handlers.
    """

    def __init__(self, limit_seconds: float = 0.5):
        self.limit_seconds = limit_seconds
        self.user_timestamps: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        telegram_user = data.get("event_from_user")
        if telegram_user:
            user_id = telegram_user.id
            now = time.time()
            last_time = self.user_timestamps.get(user_id, 0.0)

            if now - last_time < self.limit_seconds:
                if isinstance(event, Message):
                    await event.answer("⏳ Juda tez harakat qilyapsiz. Bir oz kuting.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("⏳ Juda tez harakat qilyapsiz. Bir oz kuting.", show_alert=True)
                return None

            self.user_timestamps[user_id] = now

            # Clean up old records periodically
            if len(self.user_timestamps) > 10000:
                self.user_timestamps = {
                    uid: ts for uid, ts in self.user_timestamps.items() if now - ts < 60
                }

        return await handler(event, data)
