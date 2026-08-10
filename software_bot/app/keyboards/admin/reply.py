from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


from typing import Optional, Set
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from app.core.permissions import get_role_permissions, Permission, Role


def get_admin_main_keyboard(role: Optional[str] = None, permissions: Optional[Set[str]] = None) -> ReplyKeyboardMarkup:
    """
    Returns role & permission aware main menu ReplyKeyboard for administrators.
    Options are filtered based on backend permissions granted to the admin's role.
    """
    if permissions is None:
        effective_role = role if role else Role.SUPER_ADMIN.value
        permissions = get_role_permissions(effective_role)

    builder = ReplyKeyboardBuilder()
    row_buttons = []

    # Categories & Programs management
    if Permission.CATEGORIES_MANAGE.value in permissions:
        row_buttons.append(KeyboardButton(text="📂 Kategoriyalar"))
    if Permission.PROGRAMS_MANAGE.value in permissions:
        row_buttons.append(KeyboardButton(text="💻 Dasturlar"))

    if row_buttons:
        builder.row(*row_buttons)
        row_buttons = []

    # Users & Statistics
    if Permission.USERS_READ.value in permissions:
        row_buttons.append(KeyboardButton(text="👥 Foydalanuvchilar"))
    if Permission.STATISTICS_READ.value in permissions:
        row_buttons.append(KeyboardButton(text="📊 Statistika"))

    if row_buttons:
        builder.row(*row_buttons)
        row_buttons = []

    # Analytics & Broadcast/Reklama
    if Permission.ANALYTICS_READ.value in permissions:
        row_buttons.append(KeyboardButton(text="📊 Analytics"))
    if Permission.BROADCAST_SEND.value in permissions:
        row_buttons.append(KeyboardButton(text="📢 Reklama"))

    if row_buttons:
        builder.row(*row_buttons)
        row_buttons = []

    # System Settings
    if Permission.SETTINGS_MANAGE.value in permissions:
        builder.row(KeyboardButton(text="⚙️ Sozlamalar"))

    return builder.as_markup(resize_keyboard=True, is_persistent=True)



def get_admin_cancel_keyboard(show_skip: bool = False) -> ReplyKeyboardMarkup:
    """Returns cancel/skip keyboard for Admin FSM inputs."""
    builder = ReplyKeyboardBuilder()
    if show_skip:
        builder.row(KeyboardButton(text="⏭ O'tkazib yuborish"))
    builder.row(KeyboardButton(text="❌ Bekor qilish"))
    return builder.as_markup(resize_keyboard=True)
