import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from app.config import settings
from app.database.engine import async_session_maker
from app.services.favorite_service import FavoriteService
from app.services.program_service import ProgramService
from app.keyboards.user.inline import build_favorites_keyboard, build_program_detail_keyboard
from app.utils.navigation import NavigationContext
from app.utils.callback_factory import safe_answer_callback

logger = logging.getLogger(__name__)
router = Router(name="user_favorites_router")


@router.message(F.text == "⭐ Sevimlilarim")
@router.callback_query(F.data.in_({"profile:favorites", "favorites:list"}))
async def user_favorites_menu_handler(event: Message | CallbackQuery, state: FSMContext):
    if not event.from_user:
        return

    if isinstance(event, CallbackQuery):
        await event.answer()

    user_id = event.from_user.id
    async with async_session_maker() as session:
        fav_service = FavoriteService(session)
        programs, total_pages = await fav_service.get_user_favorites_paginated(
            user_telegram_id=user_id, page=1, page_size=settings.PROGRAMS_PER_PAGE
        )

    await NavigationContext.save_nav_context(state, source="favorites", page=1)

    if not programs:
        empty_text = (
            "⭐ **SEVIMLILARIM**\n\n"
            "Hozircha sevimli dasturlaringiz yo'q.\n\n"
            "Kerakli dasturni ochib:\n"
            "⭐ **Sevimlilarga qo'shish** tugmasini bosing."
        )
        kb = build_favorites_keyboard([], current_page=1, total_pages=1)
        if isinstance(event, Message):
            await event.answer(empty_text, reply_markup=kb, parse_mode="Markdown")
        elif isinstance(event, CallbackQuery) and event.message:
            await event.message.edit_text(empty_text, reply_markup=kb, parse_mode="Markdown")
        return

    text = "⭐ **SEVIMLILARIM**\n\nSiz sevimlilarga qo'shgan dasturlar:"
    kb = build_favorites_keyboard(programs, current_page=1, total_pages=total_pages)

    if isinstance(event, Message):
        await event.answer(text=text, reply_markup=kb, parse_mode="Markdown")
    elif isinstance(event, CallbackQuery) and event.message:
        await event.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("favorites:page:"))
async def user_favorites_page_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        page = int(callback.data.split(":")[-1])
    except ValueError:
        page = 1

    if not callback.from_user:
        return

    async with async_session_maker() as session:
        fav_service = FavoriteService(session)
        programs, total_pages = await fav_service.get_user_favorites_paginated(
            user_telegram_id=callback.from_user.id, page=page, page_size=settings.PROGRAMS_PER_PAGE
        )

    await NavigationContext.save_nav_context(state, source="favorites", page=page)

    text = f"⭐ **SEVIMLILARIM** (Sahifa {page}/{total_pages})\n\nSiz sevimlilarga qo'shgan dasturlar:"
    kb = build_favorites_keyboard(programs, current_page=page, total_pages=total_pages)

    if callback.message:
        await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("favorite:add:"))
async def favorite_add_handler(callback: CallbackQuery):
    try:
        program_id = int(callback.data.split(":")[-1])
    except ValueError:
        return

    if not callback.from_user:
        return

    user_id = callback.from_user.id
    async with async_session_maker() as session:
        fav_service = FavoriteService(session)
        prog_service = ProgramService(session)

        added = await fav_service.add_favorite(user_id, program_id)
        program = await prog_service.get_program_by_id(program_id)

    if added:
        await callback.answer("⭐ Sevimlilarga qo'shildi!", show_alert=False)
    else:
        await callback.answer("⭐ Bu dastur allaqachon sevimlilarda bor.")

    if callback.message and program:
        kb = build_program_detail_keyboard(program, is_favorite=True)
        try:
            await callback.message.edit_reply_markup(reply_markup=kb)
        except Exception:
            pass


@router.callback_query(F.data.startswith("favorite:remove:"))
async def favorite_remove_handler(callback: CallbackQuery):
    try:
        program_id = int(callback.data.split(":")[-1])
    except ValueError:
        return

    if not callback.from_user:
        return

    user_id = callback.from_user.id
    async with async_session_maker() as session:
        fav_service = FavoriteService(session)
        prog_service = ProgramService(session)

        await fav_service.remove_favorite(user_id, program_id)
        program = await prog_service.get_program_by_id(program_id)

    await callback.answer("💔 Sevimlilardan olib tashlandi.", show_alert=False)

    if callback.message and program:
        kb = build_program_detail_keyboard(program, is_favorite=False)
        try:
            await callback.message.edit_reply_markup(reply_markup=kb)
        except Exception:
            pass
