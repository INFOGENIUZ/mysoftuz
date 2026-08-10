from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy import select
from app.database.engine import async_session_maker
from app.database.models import BotSetting

router = Router(name="user_about_router")


@router.message(F.text == "ℹ️ Bot haqida")
async def about_menu_handler(message: Message):
    support_username = "@admin_username"
    async with async_session_maker() as session:
        stmt = select(BotSetting).where(BotSetting.key == "support_username")
        res = await session.execute(stmt)
        setting = res.scalar_one_or_none()
        if setting and setting.value:
            support_username = setting.value

    about_text = (
        "ℹ️ **SOFTWARE STORE**\n\n"
        "🖥 Kompyuter dasturlarini qulay tarzda topish va yuklab olish uchun yaratilgan platforma.\n\n"
        "📦 Dasturlar kategoriyalar bo'yicha tartiblangan.\n\n"
        "🔐 Dasturlar administrator tomonidan boshqariladi.\n\n"
        f"💬 Qo'llab-quvvatlash: **{support_username}**"
    )
    await message.answer(about_text, parse_mode="Markdown")
