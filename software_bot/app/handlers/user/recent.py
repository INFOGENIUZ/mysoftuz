import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from app.config import settings
from app.database.engine import async_session_maker
from app.services.recent_service import RecentService
from app.keyboards.user.inline import build_recently_viewed_keyboard
from app.utils.navigation import NavigationContext

logger = logging.getLogger(__name__)
router = Router(name="user_recent_router")


@router.message(F.text == "🕘 Yaqinda ko'rganlarim")
@router.callback_query(F.data == "recent:list")
async def user_recent_menu_handler(event: Message | CallbackQuery, state: FSMContext):
    if not event.from_user:
        return

    if isinstance(event, CallbackQuery):
        await event.answer()

    user_id = event.from_user.id
    async with async_session_maker() as session:
        recent_service = RecentService(session)
        programs, total_pages = await recent_service.get_recently_viewed_paginated(
            user_telegram_id=user_id, page=1, page_size=settings.PROGRAMS_PER_PAGE
        )

    await NavigationContext.save_nav_context(state, source="recent", page=1)

    if not programs:
        empty_text = (
            "🕘 **YAQINDA KO'RILGANLAR**\n\n"
            "Siz hali hech qanday dastur ko'rmagansiz."
        )
        kb = build_recently_viewed_keyboard([], current_page=1, total_pages=1)
        if isinstance(event, Message):
            await event.answer(empty_text, reply_markup=kb, parse_mode="Markdown")
        elif isinstance(event, CallbackQuery) and event.message:
            await event.message.edit_text(empty_text, reply_markup=kb, parse_mode="Markdown")
        return

    text = "🕘 **YAQINDA KO'RILGAN DASTURLAR**\n\nOxirgi ko'rgan dasturlaringiz:"
    kb = build_recently_viewed_keyboard(programs, current_page=1, total_pages=total_pages)

    if isinstance(event, Message):
        await event.answer(text=text, reply_markup=kb, parse_mode="Markdown")
    elif isinstance(event, CallbackQuery) and event.message:
        await event.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("recent:page:"))
async def user_recent_page_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        page = int(callback.data.split(":")[-1])
    except ValueError:
        page = 1

    if not callback.from_user:
        return

    async with async_session_maker() as session:
        recent_service = RecentService(session)
        programs, total_pages = await recent_service.get_recently_viewed_paginated(
            user_telegram_id=callback.from_user.id, page=page, page_size=settings.PROGRAMS_PER_PAGE
        )

    await NavigationContext.save_nav_context(state, source="recent", page=page)

    text = f"🕘 **YAQINDA KO'RILGAN DASTURLAR** (Sahifa {page}/{total_pages})\n\nOxirgi ko'rgan dasturlaringiz:"
    kb = build_recently_viewed_keyboard(programs, current_page=page, total_pages=total_pages)

    if callback.message:
        await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")
