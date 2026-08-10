from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from app.config import settings
from app.database.engine import async_session_maker
from app.services.download_service import DownloadService
from app.keyboards.user.inline import build_downloads_keyboard
from app.utils.navigation import NavigationContext

router = Router(name="user_downloads_router")


@router.message(F.text == "📥 Yuklab olishlarim")
async def user_downloads_menu_handler(message: Message, state: FSMContext):
    if not message.from_user:
        return

    async with async_session_maker() as session:
        download_service = DownloadService(session)
        downloads_list, total_pages = await download_service.get_user_downloads_unique_paginated(
            user_telegram_id=message.from_user.id, page=1, page_size=settings.PROGRAMS_PER_PAGE
        )

    await NavigationContext.save_nav_context(state, source="downloads", page=1)

    if not downloads_list:
        await message.answer("📥 Siz hali hech qanday dastur yuklab olmagansiz.")
        return

    text = "📥 **YUKLAB OLISHLARIM**\n\nSiz ilgari yuklab olgan dasturlar:"
    kb = build_downloads_keyboard(downloads_list, current_page=1, total_pages=total_pages)
    await message.answer(text=text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("downloads:page:"))
async def user_downloads_page_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        page = int(callback.data.split(":")[-1])
    except ValueError:
        page = 1

    if not callback.from_user:
        return

    async with async_session_maker() as session:
        download_service = DownloadService(session)
        downloads_list, total_pages = await download_service.get_user_downloads_unique_paginated(
            user_telegram_id=callback.from_user.id, page=page, page_size=settings.PROGRAMS_PER_PAGE
        )

    await NavigationContext.save_nav_context(state, source="downloads", page=page)

    text = f"📥 **YUKLAB OLISHLARIM** (Sahifa {page}/{total_pages})\n\nSiz ilgari yuklab olgan dasturlar:"
    kb = build_downloads_keyboard(downloads_list, current_page=page, total_pages=total_pages)

    if callback.message:
        await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")
