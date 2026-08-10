from typing import List, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.database.models import Program, Category


def build_search_results_keyboard(
    programs: List[Program], current_page: int = 1, total_pages: int = 1
) -> InlineKeyboardMarkup:
    """Builds inline keyboard for search results with clean program labels and pagination."""
    builder = InlineKeyboardBuilder()

    for prog in programs:
        cat_icon = f"{prog.category.icon} " if prog.category and prog.category.icon else ""
        ver_str = f" ({prog.version})" if prog.version else ""
        label = f"💻 {cat_icon}{prog.name}{ver_str}"
        builder.row(
            InlineKeyboardButton(text=label, callback_data=f"program:view:{prog.id}")
        )

    # Sort & Filter row
    builder.row(
        InlineKeyboardButton(text="🎯 Saralash", callback_data="search:open_sort"),
        InlineKeyboardButton(text="📂 Filtrlash", callback_data="search:open_filter")
    )

    # Pagination row
    if total_pages > 1:
        nav_buttons = []
        if current_page > 1:
            nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"search:page:{current_page - 1}"))
        else:
            nav_buttons.append(InlineKeyboardButton(text="⏹", callback_data="search:page:1"))

        nav_buttons.append(InlineKeyboardButton(text=f"{current_page} / {total_pages}", callback_data="ignore"))

        if current_page < total_pages:
            nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"search:page:{current_page + 1}"))
        else:
            nav_buttons.append(InlineKeyboardButton(text="⏹", callback_data=f"search:page:{total_pages}"))

        builder.row(*nav_buttons)

    builder.row(
        InlineKeyboardButton(text="🔎 Yangi qidiruv", callback_data="search:retry"),
        InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="back:main")
    )
    return builder.as_markup()


def build_search_empty_keyboard(suggestions: Optional[List[Program]] = None) -> InlineKeyboardMarkup:
    """Builds keyboard when no results are found, presenting fuzzy suggestions if available."""
    builder = InlineKeyboardBuilder()

    if suggestions:
        for prog in suggestions:
            builder.row(
                InlineKeyboardButton(text=f"💡 {prog.name}", callback_data=f"program:view:{prog.id}")
            )

    builder.row(
        InlineKeyboardButton(text="🔎 Qayta qidirish", callback_data="search:retry"),
        InlineKeyboardButton(text="📂 Kategoriyalar", callback_data="categories:list")
    )
    builder.row(InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="back:main"))
    return builder.as_markup()


def build_search_sort_keyboard(current_sort: str = "relevance") -> InlineKeyboardMarkup:
    """Builds inline keyboard for changing search result sorting mode."""
    builder = InlineKeyboardBuilder()

    modes = [
        ("relevance", "🎯 Mosligi bo'yicha"),
        ("popular", "🔥 Mashhurligi bo'yicha"),
        ("new", "🆕 Yangiligi bo'yicha"),
        ("name", "🔤 Alifbo bo'yicha")
    ]

    for mode_key, mode_label in modes:
        mark = " ✅" if mode_key == current_sort else ""
        builder.row(
            InlineKeyboardButton(text=f"{mode_label}{mark}", callback_data=f"search:sort:{mode_key}")
        )

    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="search:back_results"))
    return builder.as_markup()


def build_search_category_filter_keyboard(categories: List[Category], selected_cat_id: Optional[int] = None) -> InlineKeyboardMarkup:
    """Builds inline keyboard for filtering search results by category."""
    builder = InlineKeyboardBuilder()

    mark_all = " ✅" if selected_cat_id is None else ""
    builder.row(
        InlineKeyboardButton(text=f"🌐 Barcha kategoriyalar{mark_all}", callback_data="search:filter_category:all")
    )

    for cat in categories:
        mark = " ✅" if cat.id == selected_cat_id else ""
        builder.row(
            InlineKeyboardButton(text=f"📂 {cat.name}{mark}", callback_data=f"search:filter_category:{cat.id}")
        )

    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="search:back_results"))
    return builder.as_markup()
