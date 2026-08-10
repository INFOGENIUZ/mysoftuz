import html
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from app.config import settings
from app.database.engine import async_session_maker
from app.services.category_service import CategoryService
from app.services.program_service import ProgramService
from app.keyboards.user.inline import build_categories_keyboard, build_category_programs_keyboard
from app.utils.callback_factory import safe_answer_callback
from app.utils.navigation import NavigationContext

router = Router(name="user_categories_router")


@router.message(F.text == "📂 Kategoriyalar")
@router.callback_query(F.data == "categories:list")
async def user_categories_list_handler(event: Message | CallbackQuery):
    if isinstance(event, CallbackQuery):
        await event.answer()

    async with async_session_maker() as session:
        cat_service = CategoryService(session)
        categories, total_pages = await cat_service.get_categories_paginated(
            page=1, page_size=settings.CATEGORIES_PER_PAGE
        )

    text = "📂 <b>DASTUR KATEGORIYALARI</b>\n\nKerakli kategoriyani tanlang:"
    kb = build_categories_keyboard(categories, current_page=1, total_pages=total_pages)

    if isinstance(event, Message):
        await event.answer(text=text, reply_markup=kb, parse_mode="HTML")
    elif isinstance(event, CallbackQuery) and event.message:
        await event.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")


categories_menu_handler = user_categories_list_handler


@router.callback_query(F.data.startswith("categories:page:"))
async def categories_page_handler(callback: CallbackQuery):
    await callback.answer()
    try:
        page = int(callback.data.split(":")[-1])
    except ValueError:
        page = 1

    async with async_session_maker() as session:
        cat_service = CategoryService(session)
        categories, total_pages = await cat_service.get_categories_paginated(
            page=page, page_size=settings.CATEGORIES_PER_PAGE
        )

    text = f"📂 <b>DASTUR KATEGORIYALARI</b> (Sahifa {page}/{total_pages})\n\nKerakli kategoriyani tanlang:"
    kb = build_categories_keyboard(categories, current_page=page, total_pages=total_pages)

    if callback.message:
        await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("category:view:"))
async def category_view_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        category_id = int(callback.data.split(":")[-1])
    except ValueError:
        await safe_answer_callback(callback, "⚠️ Noto'g'ri kategoriya")
        return

    async with async_session_maker() as session:
        cat_service = CategoryService(session)
        prog_service = ProgramService(session)

        category = await cat_service.get_category_by_id(category_id)
        if not category or not category.is_active:
            await safe_answer_callback(callback, "⚠️ Bu kategoriya mavjud emas yoki nofaol qilingan.")
            return

        cat_name = category.name or "Kategoriya"
        programs, total_pages = await prog_service.get_programs_by_category_paginated(
            category_id=category_id, page=1, page_size=settings.PROGRAMS_PER_PAGE
        )
        kb = build_category_programs_keyboard(programs, category_id=category_id, current_page=1, total_pages=total_pages)

    # Save Navigation Context
    await NavigationContext.save_nav_context(state, source="category", category_id=category_id, page=1)

    safe_cat_name = html.escape(cat_name)
    if not programs:
        text = f"📂 <b>{safe_cat_name.upper()}</b>\n\n📂 Bu kategoriyada hozircha dasturlar mavjud emas."
    else:
        text = f"📂 <b>{safe_cat_name.upper()}</b>\n\nUshbu kategoriyada mavjud dasturlar:"

    if callback.message:
        await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("category:page:"))
async def user_category_programs_page_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    parts = callback.data.split(":")
    if len(parts) < 4:
        return
    try:
        category_id = int(parts[2])
        page = int(parts[3])
    except ValueError:
        return

    async with async_session_maker() as session:
        cat_service = CategoryService(session)
        prog_service = ProgramService(session)

        category = await cat_service.get_category_by_id(category_id)
        if not category or not category.is_active:
            await safe_answer_callback(callback, "⚠️ Bu kategoriya mavjud emas.")
            return

        cat_name = category.name or "Kategoriya"
        programs, total_pages = await prog_service.get_programs_by_category_paginated(
            category_id=category_id, page=page, page_size=settings.PROGRAMS_PER_PAGE
        )
        kb = build_category_programs_keyboard(programs, category_id=category_id, current_page=page, total_pages=total_pages)

    # Save Navigation Context
    await NavigationContext.save_nav_context(state, source="category", category_id=category_id, page=page)

    safe_cat_name = html.escape(cat_name)
    text = f"📂 <b>{safe_cat_name.upper()}</b> (Sahifa {page}/{total_pages})\n\nUshbu kategoriyada mavjud dasturlar:"

    if callback.message:
        await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
