from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from app.config import settings


class MaintenanceMiddleware(BaseMiddleware):
    """
    Global middleware enforcing MAINTENANCE_MODE.
    Allows administrators to continue using the bot during maintenance,
    while notifying regular users cleanly.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if settings.MAINTENANCE_MODE:
            is_admin = data.get("is_admin", False)
            if not is_admin:
                maintenance_text = (
                    "🔧 **Botda texnik ishlar olib borilmoqda.**\n\n"
                    "Iltimos, keyinroq qayta urinib ko'ring."
                )
                if isinstance(event, Message):
                    await event.answer(maintenance_text, parse_mode="Markdown")
                elif isinstance(event, CallbackQuery):
                    await event.answer("🔧 Botda texnik ishlar olib borilmoqda.", show_alert=True)
                return None

        return await handler(event, data)
