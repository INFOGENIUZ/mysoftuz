import html
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select
from app.database.engine import async_session_maker
from app.database.models import BotSetting

router = Router(name="user_about_router")


@router.message(F.text.contains("Bot haqida"))
@router.message(F.text == "/about")
@router.callback_query(F.data == "about:main")
async def about_menu_handler(event: Message | CallbackQuery):
    if isinstance(event, CallbackQuery):
        await event.answer()

    support_username = "@admin_username"
    async with async_session_maker() as session:
        stmt = select(BotSetting).where(BotSetting.key == "support_username")
        res = await session.execute(stmt)
        setting = res.scalar_one_or_none()
        if setting and setting.value:
            support_username = setting.value

    sup_str = html.escape(support_username)

    about_text = (
        "ℹ️ <b>SOFTWARE STORE</b>\n\n"
        "🖥 Kompyuter dasturlarini qulay tarzda topish va yuklab olish uchun yaratilgan platforma.\n\n"
        "📦 Dasturlar kategoriyalar bo'yicha tartiblangan.\n\n"
        "🔐 Dasturlar administrator tomonidan boshqariladi.\n\n"
        f"💬 Qo'llab-quvvatlash: <b>{sup_str}</b>"
    )

    if isinstance(event, Message):
        await event.answer(about_text, parse_mode="HTML")
    elif isinstance(event, CallbackQuery) and event.message:
        await event.message.edit_text(about_text, parse_mode="HTML")

