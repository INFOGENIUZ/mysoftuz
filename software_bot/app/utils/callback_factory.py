import logging
from typing import Optional
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery

logger = logging.getLogger(__name__)


class CategoryCallback(CallbackData, prefix="category"):
    action: str  # view, delete, page
    id: int


class ProgramCallback(CallbackData, prefix="program"):
    action: str  # view, download, delete, page
    id: int


async def safe_answer_callback(callback: CallbackQuery, text: str = "⚠️ Bu amal endi mavjud emas.", show_alert: bool = True) -> bool:
    """
    Safely answers a callback query to handle stale/replay inline buttons without throwing Telegram API errors.
    """
    try:
        await callback.answer(text=text, show_alert=show_alert)
        return True
    except Exception as e:
        logger.warning(f"Failed to answer callback query (stale button): {e}")
        return False
