from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_user_main_keyboard() -> ReplyKeyboardMarkup:
    """
    Returns main menu ReplyKeyboard for regular users:
    📂 Kategoriyalar        🔎 Qidirish
    🔥 Mashhur dasturlar   🆕 Yangi dasturlar
    📥 Yuklab olishlarim   ⭐ Sevimlilarim
    👤 Profilim            ⭐ Premium
    🔔 Bildirishnomalar    ℹ️ Bot haqida
    """
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📂 Kategoriyalar"),
        KeyboardButton(text="🔎 Qidirish")
    )
    builder.row(
        KeyboardButton(text="🔥 Mashhur dasturlar"),
        KeyboardButton(text="🆕 Yangi dasturlar")
    )
    builder.row(
        KeyboardButton(text="📥 Yuklab olishlarim"),
        KeyboardButton(text="⭐ Sevimlilarim")
    )
    builder.row(
        KeyboardButton(text="👤 Profilim"),
        KeyboardButton(text="⭐ Premium")
    )
    builder.row(
        KeyboardButton(text="🔔 Bildirishnomalar"),
        KeyboardButton(text="ℹ️ Bot haqida")
    )
    return builder.as_markup(resize_keyboard=True, is_persistent=True)


def get_search_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Returns cancel keyboard for search input mode."""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="🔙 Bekor qilish"))
    return builder.as_markup(resize_keyboard=True)
