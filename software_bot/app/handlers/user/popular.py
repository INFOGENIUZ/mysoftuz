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
async def user_popular_programs_handler(message: Message, state: FSMContext):
    async with async_session_maker() as session:
        prog_service = ProgramService(session)
        programs, total_pages = await prog_service.get_popular_programs_paginated(
            page=1, page_size=settings.PROGRAMS_PER_PAGE
        )

    await NavigationContext.save_nav_context(state, source="popular", page=1)

    if not programs:
        await message.answer("🔥 **ENG KO'P YUKLAB OLINGAN DASTURLAR**\n\nHozircha mashhur dasturlar ro'yxati bo'sh.")
        return

    text = "🔥 **ENG KO'P YUKLAB OLINGAN DASTURLAR**\n\nEng ko'p yuklab olingan dasturlar ro'yxati:"
    kb = build_popular_programs_keyboard(programs, current_page=1, total_pages=total_pages)
    await message.answer(text=text, reply_markup=kb, parse_mode="Markdown")


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
