import logging
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.config import settings
from app.database.engine import async_session_maker
from app.services.search_service import SearchService, SearchFilters
from app.services.category_service import CategoryService
from app.states.user_search import SearchStates
from app.keyboards.user.reply import get_user_main_keyboard, get_search_cancel_keyboard
from app.keyboards.user.inline import (
    build_search_results_keyboard,
    build_search_filter_menu_keyboard,
    build_search_sort_keyboard,
    build_search_arch_filter_keyboard,
    build_search_license_filter_keyboard,
    build_search_size_filter_keyboard,
    build_search_rating_filter_keyboard,
    build_search_empty_keyboard,
)
from app.utils.navigation import NavigationContext

logger = logging.getLogger(__name__)
router = Router(name="user_search_router")


def parse_filters_from_dict(data: dict) -> SearchFilters:
    return SearchFilters(
        category_id=data.get("filter_category_id"),
        architecture=data.get("filter_architecture"),
        operating_system=data.get("filter_operating_system"),
        license_type=data.get("filter_license_type"),
        min_rating=data.get("filter_min_rating"),
        min_size=data.get("filter_min_size"),
        max_size=data.get("filter_max_size"),
        only_free=data.get("filter_only_free")
    )


# -----------------------------------------------------------------------------
# Cancel / Reset Search FSM
# -----------------------------------------------------------------------------
@router.message(F.text == "🔙 Bekor qilish", StateFilter(SearchStates.waiting_for_query))
@router.message(F.text == "/cancel", StateFilter(SearchStates.waiting_for_query))
async def user_search_cancel_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Qidiruv bekor qilindi.", reply_markup=get_user_main_keyboard())


# -----------------------------------------------------------------------------
# Start Search Prompt
# -----------------------------------------------------------------------------
@router.message(F.text == "🔎 Qidirish")
@router.callback_query(F.data == "search:retry")
async def user_search_start_handler(event: Message | CallbackQuery, state: FSMContext):
    await state.set_state(SearchStates.waiting_for_query)
    prompt = (
        "🔎 **DASTUR QIDIRISH**\n\n"
        "Kerakli dastur nomini yoki kalit so'zni yozing.\n\n"
        "Masalan:\nPhotoshop\nChrome\nVideo montaj\nAntivirus"
    )
    if isinstance(event, CallbackQuery):
        await event.answer()
        if event.message:
            await event.message.answer(prompt, reply_markup=get_search_cancel_keyboard(), parse_mode="Markdown")
    elif isinstance(event, Message):
        await event.answer(prompt, reply_markup=get_search_cancel_keyboard(), parse_mode="Markdown")


search_menu_handler = user_search_start_handler


# -----------------------------------------------------------------------------
# Process Query Input
# -----------------------------------------------------------------------------
@router.message(SearchStates.waiting_for_query, F.text)
async def user_search_query_process(message: Message, state: FSMContext):
    query_raw = message.text.strip() if message.text else ""

    if len(query_raw) < 2:
        await message.answer("⚠️ Kamida 2 ta belgi kiriting.")
        return

    data = await state.get_data()
    filters = parse_filters_from_dict(data)
    sort_mode = data.get("sort_mode", "relevance")

    async with async_session_maker() as session:
        search_service = SearchService(session)
        result = await search_service.search_programs(
            query=query_raw, filters=filters, sort_mode=sort_mode, page=1, per_page=settings.PROGRAMS_PER_PAGE
        )

        if result.total == 0:
            suggestions = await search_service.get_search_suggestions(query_raw, limit=3)
            empty_text = (
                f"🔎 **NATIJA TOPILMADI**\n\n"
                f"“**{query_raw}**” bo'yicha hech qanday dastur topilmadi.\n\n"
                "Quyidagilarni sinab ko'ring:\n"
                "• Dastur nomini to'liqroq yozing\n"
                "• Filtrlarni tozalang\n"
                "• Kategoriya bo'yicha izlang"
            )
            kb = build_search_empty_keyboard(suggestions=suggestions)
            await message.answer(empty_text, reply_markup=kb, parse_mode="Markdown")
            return

    await NavigationContext.save_nav_context(state, source="search", query=query_raw, page=1)
    await state.update_data(query=query_raw, page=1)

    text = f"🔎 **QIDIRUV NATIJALARI**\n\n“**{query_raw}**” bo'yicha **{result.total} ta** dastur topildi."
    kb = build_search_results_keyboard(result.programs, current_page=1, total_pages=result.total_pages, active_filters_count=filters.active_count())
    await message.answer(text=text, reply_markup=kb, parse_mode="Markdown")


# -----------------------------------------------------------------------------
# Search Pagination & Results Redisplay
# -----------------------------------------------------------------------------
@router.callback_query(F.data.startswith("search:page:"))
@router.callback_query(F.data == "search:back_results")
async def user_search_back_results(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    query = data.get("query")

    page = 1
    if callback.data and callback.data.startswith("search:page:"):
        try:
            page = int(callback.data.split(":")[-1])
        except ValueError:
            page = 1
    else:
        page = data.get("page", 1)

    await callback.answer()
    filters = parse_filters_from_dict(data)
    sort_mode = data.get("sort_mode", "relevance")

    async with async_session_maker() as session:
        search_service = SearchService(session)
        result = await search_service.search_programs(
            query=query, filters=filters, sort_mode=sort_mode, page=page, per_page=settings.PROGRAMS_PER_PAGE
        )

    await NavigationContext.save_nav_context(state, source="search", query=query, page=page)
    await state.update_data(page=page)

    query_str = f"“**{query}**” bo'yicha " if query else ""
    text = f"🔎 **QIDIRUV NATIJALARI** (Sahifa {page}/{result.total_pages})\n\n{query_str}**{result.total} ta** dastur topildi."
    kb = build_search_results_keyboard(result.programs, current_page=page, total_pages=result.total_pages, active_filters_count=filters.active_count())

    if callback.message:
        await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")


user_search_page_handler = user_search_back_results


# -----------------------------------------------------------------------------
# Multi-Filters Menu & Controls
# -----------------------------------------------------------------------------
@router.callback_query(F.data.in_({"search:filter:menu", "search:open_filter"}))
async def filter_menu_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    filters = parse_filters_from_dict(data)

    text = (
        "🎛 **DASTURLARNI FILTRLASH**\n\n"
        f"📂 Kategoriya: **{data.get('filter_category_name', 'Barchasi')}**\n"
        f"💻 Arxitektura: **{filters.architecture or 'Barchasi'}**\n"
        f"📜 Litsenziya: **{filters.license_type or 'Barchasi'}**\n"
        f"💾 Hajm: **{data.get('filter_size_label', 'Barchasi')}**\n"
        f"⭐ Reyting: **{f'{filters.min_rating}+' if filters.min_rating else 'Barchasi'}**\n"
        f"🆓 Faqat bepul: **{'Ha' if filters.only_free else 'Yo\'q'}**\n\n"
        f"Faol filterlar soni: **{filters.active_count()} ta**"
    )
    kb = build_search_filter_menu_keyboard(filters)
    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("search:filter:open:"))
async def filter_open_sub_menu(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    sub = callback.data.split(":")[-1]

    if sub == "arch":
        text = "💻 **ARXITEKTURA BO'YICHA FILTRLASH**"
        kb = build_search_arch_filter_keyboard()
    elif sub == "license":
        text = "📜 **LITSENZIYA TURI BO'YICHA FILTRLASH**"
        kb = build_search_license_filter_keyboard()
    elif sub == "size":
        text = "💾 **FAYL HAJMI BO'YICHA FILTRLASH**"
        kb = build_search_size_filter_keyboard()
    elif sub == "rating":
        text = "⭐ **REYTING BO'YICHA FILTRLASH**"
        kb = build_search_rating_filter_keyboard()
    else:
        await filter_menu_handler(callback, state)
        return

    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("search:filter:set_arch:"))
async def filter_set_arch(callback: CallbackQuery, state: FSMContext):
    val = callback.data.split(":")[-1]
    arch_val = None if val == "all" else val
    await state.update_data(filter_architecture=arch_val)
    await callback.answer(f"💻 Arxitektura: {val}")
    await filter_menu_handler(callback, state)


@router.callback_query(F.data.startswith("search:filter:set_license:"))
async def filter_set_license(callback: CallbackQuery, state: FSMContext):
    val = callback.data.split(":")[-1]
    lic_val = None if val == "all" else val
    await state.update_data(filter_license_type=lic_val)
    await callback.answer(f"📜 Litsenziya: {val}")
    await filter_menu_handler(callback, state)


@router.callback_query(F.data.startswith("search:filter:set_size:"))
async def filter_set_size(callback: CallbackQuery, state: FSMContext):
    val = callback.data.split(":")[-1]
    label = "Barchasi"
    min_s, max_s = None, None

    if val == "100M":
        max_s = 100 * 1024 * 1024
        label = "< 100 MB"
    elif val == "500M":
        min_s = 100 * 1024 * 1024
        max_s = 500 * 1024 * 1024
        label = "100–500 MB"
    elif val == "1G":
        min_s = 500 * 1024 * 1024
        max_s = 1024 * 1024 * 1024
        label = "500 MB–1 GB"
    elif val == "gt1G":
        min_s = 1024 * 1024 * 1024
        label = "> 1 GB"

    await state.update_data(filter_min_size=min_s, filter_max_size=max_s, filter_size_label=label)
    await callback.answer(f"💾 Hajm: {label}")
    await filter_menu_handler(callback, state)


@router.callback_query(F.data.startswith("search:filter:set_rating:"))
async def filter_set_rating(callback: CallbackQuery, state: FSMContext):
    val = callback.data.split(":")[-1]
    rating_val = None if val == "all" else float(val)
    await state.update_data(filter_min_rating=rating_val)
    await callback.answer(f"⭐ Reyting: {val}+")
    await filter_menu_handler(callback, state)


@router.callback_query(F.data == "search:filter:toggle_free")
async def filter_toggle_free(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    curr = data.get("filter_only_free", False)
    new_val = not curr
    await state.update_data(filter_only_free=new_val)
    await callback.answer(f"🆓 Faqat bepul: {'ON' if new_val else 'OFF'}")
    await filter_menu_handler(callback, state)


@router.callback_query(F.data == "search:filter:reset")
async def filter_reset_handler(callback: CallbackQuery, state: FSMContext):
    await state.update_data(
        filter_category_id=None,
        filter_category_name=None,
        filter_architecture=None,
        filter_operating_system=None,
        filter_license_type=None,
        filter_min_rating=None,
        filter_min_size=None,
        filter_max_size=None,
        filter_size_label=None,
        filter_only_free=None
    )
    await callback.answer("🔄 Barcha filterlar tozalandi!")
    await user_search_back_results(callback, state)


@router.callback_query(F.data == "search:filter:apply")
async def filter_apply_handler(callback: CallbackQuery, state: FSMContext):
    await state.update_data(page=1)
    await user_search_back_results(callback, state)


# -----------------------------------------------------------------------------
# Sort Modes Menu & Selection
# -----------------------------------------------------------------------------
@router.callback_query(F.data.in_({"search:sort:menu", "search:open_sort"}))
async def sort_menu_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    curr_sort = data.get("sort_mode", "relevance")
    text = "↕️ **DASTURLARNI SARALASH**\n\nQuyidagi tartiblardan birini tanlang:"
    kb = build_search_sort_keyboard(curr_sort)
    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("search:sort:set:"))
@router.callback_query(F.data.startswith("search:sort:"))
async def sort_set_handler(callback: CallbackQuery, state: FSMContext):
    if callback.data in ("search:sort:menu", "search:open_sort"):
        return await sort_menu_handler(callback, state)
    sort_mode = callback.data.split(":")[-1]
    await state.update_data(sort_mode=sort_mode, page=1)
    await callback.answer("↕️ Saralash yangilandi!")
    await user_search_back_results(callback, state)
