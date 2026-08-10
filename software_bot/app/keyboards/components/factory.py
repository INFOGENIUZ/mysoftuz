import logging
from typing import Optional
from aiogram.types import InlineKeyboardButton

logger = logging.getLogger(__name__)


class ButtonFactory:
    """
    Centralized UI/UX Button Factory implementing Telegram-compatible
    Semantic Button Styling & Emoji Consistency.
    """

    @staticmethod
    def primary_button(text: str, callback_data: str, url: Optional[str] = None) -> InlineKeyboardButton:
        """
        Creates a Primary Action Button (Call-to-Action, Search, Buy, Select, Edit).
        """
        clean_text = text.strip()
        if url:
            return InlineKeyboardButton(text=clean_text, url=url)
        return InlineKeyboardButton(text=clean_text, callback_data=callback_data)

    @staticmethod
    def success_button(text: str, callback_data: str, url: Optional[str] = None) -> InlineKeyboardButton:
        """
        Creates a Success Action Button (Download, Confirm, Save, Approve, Unblock).
        """
        clean_text = text.strip()
        if url:
            return InlineKeyboardButton(text=clean_text, url=url)
        return InlineKeyboardButton(text=clean_text, callback_data=callback_data)

    @staticmethod
    def danger_button(text: str, callback_data: str) -> InlineKeyboardButton:
        """
        Creates a Destructive Action Button (Delete, Block, Refund, Cancel, Revoke).
        """
        clean_text = text.strip()
        return InlineKeyboardButton(text=clean_text, callback_data=callback_data)

    @staticmethod
    def secondary_button(text: str, callback_data: str, url: Optional[str] = None) -> InlineKeyboardButton:
        """
        Creates a Secondary Action Button (Back, Home, Info, Settings, Pagination).
        """
        clean_text = text.strip()
        if url:
            return InlineKeyboardButton(text=clean_text, url=url)
        return InlineKeyboardButton(text=clean_text, callback_data=callback_data)

    @staticmethod
    def format_price(amount: int, currency: str = "UZS") -> str:
        """Formats minor unit price into clean Uzbek currency string."""
        return f"{amount:,} {currency}"

    @staticmethod
    def format_access_badge(access_type: str, price: Optional[int] = None) -> str:
        """Returns standard visual status badge for program cards."""
        if access_type == "FREE":
            return "🆓 BEPUL"
        elif access_type == "PREMIUM":
            return "⭐ PREMIUM"
        elif access_type == "PAID" and price:
            return f"💰 {amount:,} UZS" if (amount := price) else "💰 PULLIK"
        return "🆓 BEPUL"
