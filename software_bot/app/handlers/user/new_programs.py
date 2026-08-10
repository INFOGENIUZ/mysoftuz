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
@router.callback_query(F.data.in_({"new:list", "new:main"}))
async def user_new_programs_handler(event: Message | CallbackQuery, state: FSMContext):
    if isinstance(event, CallbackQuery):
        await event.answer()

    async with async_session_maker() as session:
        prog_service = ProgramService(session)
        programs, total_pages = await prog_service.get_new_programs_paginated(
            page=1, page_size=settings.PROGRAMS_PER_PAGE
        )

    await NavigationContext.save_nav_context(state, source="new", page=1)

    if not programs:
        empty_text = "🆕 **YANGI SIFATIDA QO'SHILGAN DASTURLAR**\n\nHozircha yangi dasturlar mavjud emas."
        if isinstance(event, Message):
            await event.answer(empty_text)
        elif isinstance(event, CallbackQuery) and event.message:
            await event.message.edit_text(empty_text, parse_mode="Markdown")
        return

    text = "🆕 **YANGI SIFATIDA QO'SHILGAN DASTURLAR**\n\nEng oxirgi qo'shilgan dasturlar ro'yxati:"
    kb = build_new_programs_keyboard(programs, current_page=1, total_pages=total_pages)
    if isinstance(event, Message):
        await event.answer(text=text, reply_markup=kb, parse_mode="Markdown")
    elif isinstance(event, CallbackQuery) and event.message:
        await event.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")


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
