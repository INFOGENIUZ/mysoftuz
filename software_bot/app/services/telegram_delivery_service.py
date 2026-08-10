import logging
import asyncio
from typing import Optional
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, Message
from aiogram.exceptions import TelegramRetryAfter

logger = logging.getLogger(__name__)


class TelegramDeliveryService:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        parse_mode: str = "Markdown",
        max_retries: int = 3
    ) -> Optional[Message]:
        """Safely sends text message handling Telegram 429 RetryAfter automatically."""
        for attempt in range(max_retries):
            try:
                msg = await self.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
                return msg
            except TelegramRetryAfter as tra:
                retry_seconds = tra.retry_after
                logger.warning(f"Telegram 429 RetryAfter: waiting {retry_seconds}s for chat {chat_id}")
                await asyncio.sleep(retry_seconds + 0.1)
            except Exception as e:
                err_str = str(e)
                if "retry after" in err_str.lower() and attempt < max_retries - 1:
                    logger.warning(f"Telegram rate limit detected: {err_str}, sleeping 2s...")
                    await asyncio.sleep(2.0)
                else:
                    logger.warning(f"TelegramDeliveryService failed for chat {chat_id}: {e}")
                    raise e
        return None

    async def send_document(
        self,
        chat_id: int,
        document_file_id: str,
        caption: Optional[str] = None,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        parse_mode: str = "Markdown",
        max_retries: int = 3
    ) -> Optional[Message]:
        """Safely sends document file using Telegram file_id reference with RetryAfter protection."""
        for attempt in range(max_retries):
            try:
                msg = await self.bot.send_document(
                    chat_id=chat_id,
                    document=document_file_id,
                    caption=caption,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
                return msg
            except TelegramRetryAfter as tra:
                retry_seconds = tra.retry_after
                logger.warning(f"Telegram 429 RetryAfter on document: waiting {retry_seconds}s for chat {chat_id}")
                await asyncio.sleep(retry_seconds + 0.1)
            except Exception as e:
                err_str = str(e)
                if "retry after" in err_str.lower() and attempt < max_retries - 1:
                    logger.warning(f"Telegram rate limit detected on document: {err_str}, sleeping 2s...")
                    await asyncio.sleep(2.0)
                else:
                    logger.warning(f"TelegramDeliveryService document failed for chat {chat_id}: {e}")
                    raise e
        return None
