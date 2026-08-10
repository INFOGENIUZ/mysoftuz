import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from app.keyboards.user.reply import get_user_main_keyboard
from app.utils.navigation import NavigationContext
from app.utils.callback_factory import safe_answer_callback

logger = logging.getLogger(__name__)
router = Router(name="user_navigation_router")


@router.callback_query(F.data == "back:main")
async def back_to_main_menu_handler(callback: CallbackQuery, state: FSMContext):
    """Resets FSM state and sends main ReplyKeyboard menu."""
    await callback.answer()
    await state.clear()

    main_text = (
        "🏠 **BOSH MENYU**\n\n"
        "Kerakli bo'limni tanlang:"
    )

    if callback.message:
        await callback.message.answer(text=main_text, reply_markup=get_user_main_keyboard(), parse_mode="Markdown")


back_to_main_handler = back_to_main_menu_handler


@router.callback_query(F.data == "back:auto")
async def back_auto_handler(callback: CallbackQuery, state: FSMContext):
    """
    Intelligently routes the user back to their specific source section and page
    (Category list, Search results, Popular, New, Downloads) using FSM NavigationContext.
    """
    nav_ctx = await NavigationContext.get_nav_context(state)
    source = nav_ctx.get("source")

    if not source:
        # Fallback to categories list if context is missing
        from app.handlers.user.categories import user_categories_list_handler
        await user_categories_list_handler(callback)
        return

    await callback.answer()

    if source == "category":
        from app.handlers.user.categories import user_category_programs_page_handler
        category_id = nav_ctx.get("category_id")
        page = nav_ctx.get("page", 1)
        cb_copy = callback.model_copy(update={"data": f"category:page:{category_id}:{page}"})
        await user_category_programs_page_handler(cb_copy, state)

    elif source == "search":
        from app.handlers.user.search import user_search_back_results
        await user_search_back_results(callback, state)

    elif source == "popular":
        from app.handlers.user.popular import user_popular_programs_page_handler
        page = nav_ctx.get("page", 1)
        cb_copy = callback.model_copy(update={"data": f"popular:page:{page}"})
        await user_popular_programs_page_handler(cb_copy, state)

    elif source == "new":
        from app.handlers.user.new_programs import user_new_programs_page_handler
        page = nav_ctx.get("page", 1)
        cb_copy = callback.model_copy(update={"data": f"new:page:{page}"})
        await user_new_programs_page_handler(cb_copy, state)

    elif source == "downloads":
        from app.handlers.user.downloads import user_downloads_page_handler
        page = nav_ctx.get("page", 1)
        cb_copy = callback.model_copy(update={"data": f"downloads:page:{page}"})
        await user_downloads_page_handler(cb_copy, state)

    elif source == "favorites":
        from app.handlers.user.favorites import user_favorites_page_handler
        page = nav_ctx.get("page", 1)
        cb_copy = callback.model_copy(update={"data": f"favorites:page:{page}"})
        await user_favorites_page_handler(cb_copy, state)

    elif source == "recent":
        from app.handlers.user.recent import user_recent_page_handler
        page = nav_ctx.get("page", 1)
        cb_copy = callback.model_copy(update={"data": f"recent:page:{page}"})
        await user_recent_page_handler(cb_copy, state)

    else:
        from app.handlers.user.categories import user_categories_list_handler
        await user_categories_list_handler(callback)



back_to_categories_handler = back_auto_handler


@router.callback_query(F.data == "ignore")
async def ignore_callback_handler(callback: CallbackQuery):
    """Handles static pagination indicator buttons gracefully without spinner freeze."""
    await safe_answer_callback(callback)
