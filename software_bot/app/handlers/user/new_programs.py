from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from app.config import settings
from app.database.engine import async_session_maker
from app.services.program_service import ProgramService
from app.keyboards.user.inline import build_new_programs_keyboard
from app.utils.navigation import NavigationContext

router = Router(name="user_new_programs_router")


@router.message(F.text == "🆕 Yangi dasturlar")
async def user_new_programs_handler(message: Message, state: FSMContext):
    async with async_session_maker() as session:
        prog_service = ProgramService(session)
        programs, total_pages = await prog_service.get_new_programs_paginated(
            page=1, page_size=settings.PROGRAMS_PER_PAGE
        )

    await NavigationContext.save_nav_context(state, source="new", page=1)

    if not programs:
        await message.answer("🆕 **YANGI SIFATIDA QO'SHILGAN DASTURLAR**\n\nHozircha yangi dasturlar mavjud emas.")
        return

    text = "🆕 **YANGI SIFATIDA QO'SHILGAN DASTURLAR**\n\nEng oxirgi qo'shilgan dasturlar ro'yxati:"
    kb = build_new_programs_keyboard(programs, current_page=1, total_pages=total_pages)
    await message.answer(text=text, reply_markup=kb, parse_mode="Markdown")


new_programs_menu_handler = user_new_programs_handler


@router.callback_query(F.data.startswith("new:page:"))
async def user_new_programs_page_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        page = int(callback.data.split(":")[-1])
    except ValueError:
        page = 1

    async with async_session_maker() as session:
        prog_service = ProgramService(session)
        programs, total_pages = await prog_service.get_new_programs_paginated(
            page=page, page_size=settings.PROGRAMS_PER_PAGE
        )

    await NavigationContext.save_nav_context(state, source="new", page=page)

    text = f"🆕 **YANGI SIFATIDA QO'SHILGAN DASTURLAR** (Sahifa {page}/{total_pages})\n\nEng oxirgi qo'shilgan dasturlar:"
    kb = build_new_programs_keyboard(programs, current_page=page, total_pages=total_pages)

    if callback.message:
        await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")
