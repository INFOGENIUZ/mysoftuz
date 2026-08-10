import time
import logging
from typing import Dict, Tuple, Callable, Awaitable, Any
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

logger = logging.getLogger(__name__)


class AntiSpamMiddleware(BaseMiddleware):
    """
    Middleware that enforces basic rate limiting per Telegram user ID
    to protect against flood spam and abnormal request rates.
    """
    def __init__(self, rate_limit_seconds: float = 0.5):
        super().__init__()
        self.rate_limit_seconds = rate_limit_seconds
        # In-memory timestamp storage: {user_id: last_request_time}
        self.user_timestamps: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user: User = data.get("event_from_user")
        if not user:
            return await handler(event, data)

        now = time.time()
        user_id = user.id
        last_time = self.user_timestamps.get(user_id, 0.0)

        # Check rate limit
        if now - last_time < self.rate_limit_seconds:
            logger.warning(f"AntiSpam: User {user_id} throttled (request rate too fast)")
            # Quietly drop or answer query to prevent server overload
            if hasattr(event, "answer") and callable(event.answer):
                try:
                    await event.answer("⏳ Iltimos, biroz kuting...", show_alert=True)
                except Exception:
                    pass
            return None

        self.user_timestamps[user_id] = now
        return await handler(event, data)
