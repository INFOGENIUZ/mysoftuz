import logging
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from app.database.engine import async_session_maker
from app.services.user_service import UserService
from app.keyboards.user import get_user_main_keyboard
from app.config import settings

logger = logging.getLogger(__name__)
router = Router(name="user_start_router")


@router.message(CommandStart())
async def user_start_handler(message: Message):
    if not message.from_user:
        return

    telegram_id = message.from_user.id
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    username = message.from_user.username
    language_code = message.from_user.language_code
    is_admin = telegram_id in settings.ADMIN_IDS

    async with async_session_maker() as session:
        user_service = UserService(session)
        user, created = await user_service.get_or_create_user(
            telegram_id=telegram_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
            language_code=language_code,
            is_admin=is_admin
        )

    welcome_text = (
        f"👋 Assalomu alaykum, **{first_name}**!\n\n"
        "🖥 **Software Store botiga xush kelibsiz.**\n\n"
        "Bu yerda kompyuter uchun kerakli dasturlarni "
        "qulay katalog orqali topishingiz va yuklab olishingiz mumkin.\n\n"
        "📂 Kategoriyani tanlang yoki 🔎 qidiruvdan foydalaning."
    )

    await message.answer(
        text=welcome_text,
        reply_markup=get_user_main_keyboard(),
        parse_mode="Markdown"
    )


@router.message(Command("admin"))
async def non_admin_command_rejection(message: Message):
    """Rejects non-admin users attempting /admin command with 403 Forbidden."""
    await message.answer("⛔ Sizda ushbu bo'limga kirish huquqi yo'q.")


@router.callback_query(F.data.startswith("admin:"))
async def non_admin_callback_rejection(callback: CallbackQuery):
    """Rejects non-admin users attempting admin inline callbacks with 403 Forbidden alert."""
    await callback.answer("⛔ Sizda ushbu bo'limga kirish huquqi yo'q.", show_alert=True)

