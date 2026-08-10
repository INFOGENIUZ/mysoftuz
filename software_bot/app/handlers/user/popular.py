from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from app.config import settings
from app.database.engine import async_session_maker
from app.services.program_service import ProgramService
from app.keyboards.user.inline import build_popular_programs_keyboard
from app.utils.navigation import NavigationContext

router = Router(name="user_popular_router")


@router.message(F.text == "🔥 Mashhur dasturlar")
@router.callback_query(F.data.in_({"popular:list", "popular:main"}))
async def user_popular_programs_handler(event: Message | CallbackQuery, state: FSMContext):
    if isinstance(event, CallbackQuery):
        await event.answer()
    async with async_session_maker() as session:
        prog_service = ProgramService(session)
        programs, total_pages = await prog_service.get_popular_programs_paginated(
            page=1, page_size=settings.PROGRAMS_PER_PAGE
        )

    await NavigationContext.save_nav_context(state, source="popular", page=1)

    if not programs:
        empty_text = "🔥 **ENG KO'P YUKLAB OLINGAN DASTURLAR**\n\nHozircha mashhur dasturlar ro'yxati bo'sh."
        if isinstance(event, Message):
            await event.answer(empty_text)
        elif isinstance(event, CallbackQuery) and event.message:
            await event.message.edit_text(empty_text, parse_mode="Markdown")
        return

    text = "🔥 **ENG KO'P YUKLAB OLINGAN DASTURLAR**\n\nEng ko'p yuklab olingan dasturlar ro'yxati:"
    kb = build_popular_programs_keyboard(programs, current_page=1, total_pages=total_pages)
    if isinstance(event, Message):
        await event.answer(text=text, reply_markup=kb, parse_mode="Markdown")
    elif isinstance(event, CallbackQuery) and event.message:
        await event.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")


popular_menu_handler = user_popular_programs_handler


@router.callback_query(F.data.startswith("popular:page:"))
async def user_popular_programs_page_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        page = int(callback.data.split(":")[-1])
    except ValueError:
        page = 1

    async with async_session_maker() as session:
        prog_service = ProgramService(session)
        programs, total_pages = await prog_service.get_popular_programs_paginated(
            page=page, page_size=settings.PROGRAMS_PER_PAGE
        )

    await NavigationContext.save_nav_context(state, source="popular", page=page)

    text = f"🔥 **ENG KO'P YUKLAB OLINGAN DASTURLAR** (Sahifa {page}/{total_pages})\n\nEng ko'p yuklab olingan dasturlar:"
    kb = build_popular_programs_keyboard(programs, current_page=page, total_pages=total_pages)

    if callback.message:
        await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")
