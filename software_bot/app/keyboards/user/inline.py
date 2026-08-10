from typing import List, Tuple, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.keyboards.components.factory import ButtonFactory
from app.database.models import (
    Category,
    Program,
    Download,
    ProgramReview,
    ProgramVersion,
    UserNotification,
    ProgramRating,
    UserNotificationSetting,
)
from app.services.search_service import SearchFilters
from app.utils.pagination import get_pagination, build_pagination_keyboard_row


# -----------------------------------------------------------------------------
# User Profile & Dashboard Keyboards
# -----------------------------------------------------------------------------
def build_user_profile_dashboard_keyboard(unread_notifications_count: int = 0) -> InlineKeyboardMarkup:
    """Builds main inline navigation keyboard for User Profile Dashboard."""
    builder = InlineKeyboardBuilder()

    notif_label = f"🔔 Bildirishnomalar ({unread_notifications_count})" if unread_notifications_count > 0 else "🔔 Bildirishnomalar"

    builder.row(
        InlineKeyboardButton(text="📥 Yuklab olishlarim", callback_data="profile:downloads"),
        InlineKeyboardButton(text="⭐ Sevimlilarim", callback_data="profile:favorites")
    )
    builder.row(
        InlineKeyboardButton(text="🕘 Yaqinda ko'rilganlar", callback_data="profile:recent"),
        InlineKeyboardButton(text="⭐ Baholarim", callback_data="profile:ratings")
    )
    builder.row(
        InlineKeyboardButton(text="💬 Sharhlarim", callback_data="profile:reviews"),
        InlineKeyboardButton(text=notif_label, callback_data="notification:list")
    )
    builder.row(
        InlineKeyboardButton(text="🎯 Siz uchun tavsiyalar", callback_data="profile:recommendations"),
        InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="profile:settings")
    )
    builder.row(InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="back:main"))
    return builder.as_markup()


def build_user_ratings_keyboard(
    ratings: List[ProgramRating], current_page: int = 1, total_pages: int = 1
) -> InlineKeyboardMarkup:
    """Builds inline keyboard for User Ratings List."""
    builder = InlineKeyboardBuilder()

    for r in ratings:
        prog_name = r.program.name if r.program else "Dastur"
        stars = "⭐" * r.rating
        builder.row(
            InlineKeyboardButton(text=f"💻 {prog_name} — {stars} ({r.rating}/5)", callback_data=f"profile:rating:detail:{r.id}")
        )

    pagination = get_pagination(total_items=total_pages * 5, page=current_page, per_page=5)
    pagination.total_pages = total_pages
    pagination.has_previous = current_page > 1
    pagination.has_next = current_page < total_pages

    nav_row = build_pagination_keyboard_row(pagination, callback_prefix="profile:ratings:page")
    if nav_row:
        builder.row(*nav_row)

    builder.row(InlineKeyboardButton(text="🔙 Profilga qaytish", callback_data="profile:main"))
    return builder.as_markup()


def build_user_rating_detail_keyboard(rating_id: int, program_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ Bahoni o'zgartirish", callback_data=f"rating:select:{program_id}"),
        InlineKeyboardButton(text="🗑 Bahoni o'chirish", callback_data=f"profile:rating:delete:{rating_id}")
    )
    builder.row(
        InlineKeyboardButton(text="💻 Dastur sahifasi", callback_data=f"program:view:{program_id}"),
        InlineKeyboardButton(text="🔙 Baholarim", callback_data="profile:ratings")
    )
    return builder.as_markup()


def build_user_reviews_keyboard(
    reviews: List[ProgramReview], current_page: int = 1, total_pages: int = 1
) -> InlineKeyboardMarkup:
    """Builds inline keyboard for User Reviews List with status badges."""
    builder = InlineKeyboardBuilder()

    for rev in reviews:
        prog_name = rev.program.name if rev.program else "Dastur"
        if rev.status == "APPROVED":
            status_icon = "🟢"
        elif rev.status == "REJECTED":
            status_icon = "🔴"
        else:
            status_icon = "🕐"

        snippet = rev.text[:20] + "..." if len(rev.text) > 20 else rev.text
        builder.row(
            InlineKeyboardButton(text=f"{status_icon} {prog_name}: {snippet}", callback_data=f"profile:review:detail:{rev.id}")
        )

    pagination = get_pagination(total_items=total_pages * 5, page=current_page, per_page=5)
    pagination.total_pages = total_pages
    pagination.has_previous = current_page > 1
    pagination.has_next = current_page < total_pages

    nav_row = build_pagination_keyboard_row(pagination, callback_prefix="profile:reviews:page")
    if nav_row:
        builder.row(*nav_row)

    builder.row(InlineKeyboardButton(text="🔙 Profilga qaytish", callback_data="profile:main"))
    return builder.as_markup()


def build_user_review_detail_keyboard(review_id: int, program_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"review:add:{program_id}"),
        InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"profile:review:delete:{review_id}")
    )
    builder.row(
        InlineKeyboardButton(text="💻 Dastur sahifasi", callback_data=f"program:view:{program_id}"),
        InlineKeyboardButton(text="🔙 Sharhlarim", callback_data="profile:reviews")
    )
    return builder.as_markup()


def build_user_settings_keyboard(setting: UserNotificationSetting) -> InlineKeyboardMarkup:
    """Builds inline keyboard for User Settings management."""
    builder = InlineKeyboardBuilder()
    upd_mark = "🟢" if setting.software_updates else "🔴"
    new_mark = "🟢" if setting.new_programs else "🔴"
    ann_mark = "🟢" if setting.important_announcements else "🔴"

    builder.row(
        InlineKeyboardButton(text=f"🔔 Dastur yangilanishlari: {upd_mark}", callback_data="profile:setting:toggle:software_updates")
    )
    builder.row(
        InlineKeyboardButton(text=f"🆕 Yangi dasturlar: {new_mark}", callback_data="profile:setting:toggle:new_programs")
    )
    builder.row(
        InlineKeyboardButton(text=f"📢 Muhim xabarlar: {ann_mark}", callback_data="profile:setting:toggle:important_announcements")
    )
    builder.row(
        InlineKeyboardButton(text="🌐 Til: 🇺🇿 O'zbekcha", callback_data="profile:setting:language"),
        InlineKeyboardButton(text="🔒 Maxfiylik", callback_data="profile:setting:privacy")
    )
    builder.row(InlineKeyboardButton(text="🔙 Profilga qaytish", callback_data="profile:main"))
    return builder.as_markup()


def build_recent_clear_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🗑 Ha, tozalash", callback_data="profile:recent:clear_confirm"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="profile:recent")
    )
    return builder.as_markup()


# -----------------------------------------------------------------------------
# User Categories Keyboards
# -----------------------------------------------------------------------------
def build_categories_keyboard(
    categories: List[Category], current_page: int = 1, total_pages: int = 1
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for cat in categories:
        icon_str = f"{cat.icon} " if cat.icon else "📂 "
        builder.row(
            InlineKeyboardButton(
                text=f"{icon_str}{cat.name}",
                callback_data=f"category:view:{cat.id}"
            )
        )

    pagination = get_pagination(total_items=total_pages * 10, page=current_page, per_page=10)
    pagination.total_pages = total_pages
    pagination.has_previous = current_page > 1
    pagination.has_next = current_page < total_pages

    nav_row = build_pagination_keyboard_row(pagination, callback_prefix="categories:page")
    if nav_row:
        builder.row(*nav_row)

    builder.row(InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="back:main"))
    return builder.as_markup()


def build_category_programs_keyboard(
    programs: List[Program], category_id: int, current_page: int = 1, total_pages: int = 1
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for prog in programs:
        ver_str = f" ({prog.version})" if prog.version else ""
        builder.row(
            InlineKeyboardButton(
                text=f"💻 {prog.name}{ver_str}",
                callback_data=f"program:view:{prog.id}"
            )
        )

    pagination = get_pagination(total_items=total_pages * 10, page=current_page, per_page=10)
    pagination.total_pages = total_pages
    pagination.has_previous = current_page > 1
    pagination.has_next = current_page < total_pages

    nav_row = build_pagination_keyboard_row(pagination, callback_prefix=f"category:page:{category_id}")
    if nav_row:
        builder.row(*nav_row)

    builder.row(InlineKeyboardButton(text="🔙 Kategoriyalar", callback_data="categories:list"))
    return builder.as_markup()


# -----------------------------------------------------------------------------
# User Search, Multi-Filter & Sort Keyboards
# -----------------------------------------------------------------------------
def build_search_results_keyboard(
    programs: List[Program], current_page: int = 1, total_pages: int = 1, active_filters_count: int = 0
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for prog in programs:
        ver_str = f" ({prog.version})" if prog.version else ""
        builder.row(
            InlineKeyboardButton(
                text=f"💻 {prog.name}{ver_str}",
                callback_data=f"program:view:{prog.id}"
            )
        )

    pagination = get_pagination(total_items=total_pages * 10, page=current_page, per_page=10)
    pagination.total_pages = total_pages
    pagination.has_previous = current_page > 1
    pagination.has_next = current_page < total_pages

    nav_row = build_pagination_keyboard_row(pagination, callback_prefix="search:page")
    if nav_row:
        builder.row(*nav_row)

    filter_btn_text = f"🎛 Filtrlash ({active_filters_count})" if active_filters_count > 0 else "🎛 Filtrlash"
    builder.row(
        InlineKeyboardButton(text=filter_btn_text, callback_data="search:filter:menu"),
        InlineKeyboardButton(text="↕️ Saralash", callback_data="search:sort:menu")
    )
    builder.row(InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="back:main"))
    return builder.as_markup()


def build_search_filter_menu_keyboard(filters: SearchFilters) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📂 Kategoriya", callback_data="search:filter:open:category"),
        InlineKeyboardButton(text="💻 Arxitektura", callback_data="search:filter:open:arch")
    )
    builder.row(
        InlineKeyboardButton(text="📜 Litsenziya", callback_data="search:filter:open:license"),
        InlineKeyboardButton(text="💾 Hajm", callback_data="search:filter:open:size")
    )
    builder.row(
        InlineKeyboardButton(text="⭐ Reyting", callback_data="search:filter:open:rating"),
        InlineKeyboardButton(
            text="🆓 Faqat bepul" if not filters.only_free else "✅ Faqat bepul [ON]",
            callback_data="search:filter:toggle_free"
        )
    )

    if filters.active_count() > 0:
        builder.row(InlineKeyboardButton(text="🔄 Filtrlarni tozalash", callback_data="search:filter:reset"))

    builder.row(
        InlineKeyboardButton(text="✅ Natijalarni ko'rish", callback_data="search:filter:apply"),
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="search:back_results")
    )
    return builder.as_markup()


def build_search_sort_keyboard(current_sort: str = "relevance") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    sorts = [
        ("relevance", "🎯 Mosligi"),
        ("popular", "🔥 Mashhurligi"),
        ("new", "🆕 Yangiligi"),
        ("rating", "⭐ Reytingi"),
        ("name", "🔤 Alifbo bo'yicha"),
        ("size", "💾 Hajmi bo'yicha"),
    ]
    for mode, label in sorts:
        check = " ✅" if mode == current_sort else ""
        builder.row(InlineKeyboardButton(text=f"{label}{check}", callback_data=f"search:sort:set:{mode}"))

    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="search:back_results"))
    return builder.as_markup()


def build_search_arch_filter_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="x64", callback_data="search:filter:set_arch:x64"),
        InlineKeyboardButton(text="x86", callback_data="search:filter:set_arch:x86")
    )
    builder.row(
        InlineKeyboardButton(text="ARM64", callback_data="search:filter:set_arch:ARM64"),
        InlineKeyboardButton(text="Universal", callback_data="search:filter:set_arch:Universal")
    )
    builder.row(
        InlineKeyboardButton(text="Hammasi", callback_data="search:filter:set_arch:all"),
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="search:filter:menu")
    )
    return builder.as_markup()


def build_search_license_filter_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🆓 Free", callback_data="search:filter:set_license:Free"),
        InlineKeyboardButton(text="🔓 Open Source", callback_data="search:filter:set_license:Open Source")
    )
    builder.row(
        InlineKeyboardButton(text="🟢 Freemium", callback_data="search:filter:set_license:Freemium"),
        InlineKeyboardButton(text="⏳ Trial", callback_data="search:filter:set_license:Trial")
    )
    builder.row(
        InlineKeyboardButton(text="Hammasi", callback_data="search:filter:set_license:all"),
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="search:filter:menu")
    )
    return builder.as_markup()


def build_search_size_filter_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="< 100 MB", callback_data="search:filter:set_size:100M"),
        InlineKeyboardButton(text="100–500 MB", callback_data="search:filter:set_size:500M")
    )
    builder.row(
        InlineKeyboardButton(text="500 MB–1 GB", callback_data="search:filter:set_size:1G"),
        InlineKeyboardButton(text="> 1 GB", callback_data="search:filter:set_size:gt1G")
    )
    builder.row(
        InlineKeyboardButton(text="Hammasi", callback_data="search:filter:set_size:all"),
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="search:filter:menu")
    )
    return builder.as_markup()


def build_search_rating_filter_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⭐ 4.5+", callback_data="search:filter:set_rating:4.5"),
        InlineKeyboardButton(text="⭐ 4.0+", callback_data="search:filter:set_rating:4.0")
    )
    builder.row(
        InlineKeyboardButton(text="⭐ 3.0+", callback_data="search:filter:set_rating:3.0"),
        InlineKeyboardButton(text="Hammasi", callback_data="search:filter:set_rating:all")
    )
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="search:filter:menu"))
    return builder.as_markup()


def build_search_empty_keyboard(suggestions: Optional[List[Program]] = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if suggestions:
        for prog in suggestions:
            builder.row(
                InlineKeyboardButton(text=f"💡 {prog.name}", callback_data=f"program:view:{prog.id}")
            )
    builder.row(
        InlineKeyboardButton(text="🎛 Filtrlarni tozalash", callback_data="search:filter:reset"),
        InlineKeyboardButton(text="📂 Kategoriyalar", callback_data="categories:list")
    )
    builder.row(InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="back:main"))
    return builder.as_markup()


# -----------------------------------------------------------------------------
# User Program Detail Keyboard
# -----------------------------------------------------------------------------
def build_program_detail_keyboard(
    program: Program, is_favorite: bool = False, is_subscribed: bool = False
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📥 YUKLAB OLISH", callback_data=f"program:download:{program.id}")
    )

    fav_btn_text = "💔 Sevimlilardan olib tashlash" if is_favorite else "⭐ Sevimlilarga qo'shish"
    fav_cb = f"favorite:remove:{program.id}" if is_favorite else f"favorite:add:{program.id}"
    builder.row(InlineKeyboardButton(text=fav_btn_text, callback_data=fav_cb))

    sub_btn_text = "🔕 Yangilanishlarni o'chirish" if is_subscribed else "🔔 Yangilanishlarni olish"
    sub_cb = f"sub:off:{program.id}" if is_subscribed else f"sub:on:{program.id}"
    builder.row(InlineKeyboardButton(text=sub_btn_text, callback_data=sub_cb))

    builder.row(
        InlineKeyboardButton(text="📦 Versiyalar", callback_data=f"version:list:{program.id}"),
        InlineKeyboardButton(text="💬 Sharhlar", callback_data=f"reviews:list:{program.id}")
    )
    builder.row(
        InlineKeyboardButton(text="⭐ Reyting berish", callback_data=f"rating:select:{program.id}"),
        InlineKeyboardButton(text="🔗 O'xshash dasturlar", callback_data=f"related:view:{program.id}")
    )

    if program.official_url and program.official_url.startswith("http"):
        builder.row(InlineKeyboardButton(text="🌐 Rasmiy sayt", url=program.official_url))

    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="back:auto"))
    return builder.as_markup()


# -----------------------------------------------------------------------------
# Version History & Notification Keyboards
# -----------------------------------------------------------------------------
def build_versions_history_keyboard(
    program_id: int, versions: List[ProgramVersion], current_page: int = 1, total_pages: int = 1
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for v in versions:
        badge = "🟢 Joriy " if v.is_current else ""
        builder.row(
            InlineKeyboardButton(
                text=f"📦 {badge}{v.version} ({v.created_at.strftime('%d.%m.%Y') if v.created_at else ''})",
                callback_data=f"version:view:{v.id}"
            )
        )

    pagination = get_pagination(total_items=total_pages * 10, page=current_page, per_page=10)
    pagination.total_pages = total_pages
    pagination.has_previous = current_page > 1
    pagination.has_next = current_page < total_pages

    nav_row = build_pagination_keyboard_row(pagination, callback_prefix=f"version:page:{program_id}")
    if nav_row:
        builder.row(*nav_row)

    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"program:view:{program_id}"))
    return builder.as_markup()


def build_user_notifications_keyboard(
    notifications: List[UserNotification], current_page: int = 1, total_pages: int = 1
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for n in notifications:
        unread_mark = "🔴 " if not n.is_read else ""
        snippet = n.title[:30]
        builder.row(
            InlineKeyboardButton(text=f"{unread_mark}{snippet}", callback_data=f"notification:view:{n.id}")
        )

    pagination = get_pagination(total_items=total_pages * 5, page=current_page, per_page=5)
    pagination.total_pages = total_pages
    pagination.has_previous = current_page > 1
    pagination.has_next = current_page < total_pages

    nav_row = build_pagination_keyboard_row(pagination, callback_prefix="notification:page")
    if nav_row:
        builder.row(*nav_row)

    builder.row(
        InlineKeyboardButton(text="✅ Barchasini o'qilgan qilish", callback_data="notification:mark_all_read"),
        InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="back:main")
    )
    return builder.as_markup()


# -----------------------------------------------------------------------------
# Ratings & Reviews Keyboards
# -----------------------------------------------------------------------------
def build_rating_selection_keyboard(program_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⭐ 1", callback_data=f"rating:set:{program_id}:1"),
        InlineKeyboardButton(text="⭐ 2", callback_data=f"rating:set:{program_id}:2"),
        InlineKeyboardButton(text="⭐ 3", callback_data=f"rating:set:{program_id}:3"),
        InlineKeyboardButton(text="⭐ 4", callback_data=f"rating:set:{program_id}:4"),
        InlineKeyboardButton(text="⭐ 5", callback_data=f"rating:set:{program_id}:5")
    )
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"program:view:{program_id}"))
    return builder.as_markup()


def build_reviews_keyboard(
    program_id: int, reviews: List[ProgramReview], current_page: int = 1, total_pages: int = 1
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for rev in reviews:
        author_name = f"@{rev.user.username}" if (rev.user and rev.user.username) else "Anonim"
        snippet = rev.text[:30] + "..." if len(rev.text) > 30 else rev.text
        builder.row(
            InlineKeyboardButton(text=f"💬 {author_name}: {snippet}", callback_data=f"review:view:{rev.id}")
        )

    pagination = get_pagination(total_items=total_pages * 5, page=current_page, per_page=5)
    pagination.total_pages = total_pages
    pagination.has_previous = current_page > 1
    pagination.has_next = current_page < total_pages

    nav_row = build_pagination_keyboard_row(pagination, callback_prefix=f"reviews:page:{program_id}")
    if nav_row:
        builder.row(*nav_row)

    builder.row(
        InlineKeyboardButton(text="✍️ Sharh qoldirish", callback_data=f"review:add:{program_id}"),
        InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"program:view:{program_id}")
    )
    return builder.as_markup()


# -----------------------------------------------------------------------------
# Favorites & Recently Viewed Keyboards
# -----------------------------------------------------------------------------
def build_favorites_keyboard(
    programs: List[Program], current_page: int = 1, total_pages: int = 1
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for prog in programs:
        ver_str = f" ({prog.version})" if prog.version else ""
        builder.row(
            InlineKeyboardButton(text=f"⭐ {prog.name}{ver_str}", callback_data=f"program:view:{prog.id}")
        )

    pagination = get_pagination(total_items=total_pages * 10, page=current_page, per_page=10)
    pagination.total_pages = total_pages
    pagination.has_previous = current_page > 1
    pagination.has_next = current_page < total_pages

    nav_row = build_pagination_keyboard_row(pagination, callback_prefix="favorites:page")
    if nav_row:
        builder.row(*nav_row)

    builder.row(InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="back:main"))
    return builder.as_markup()


def build_recently_viewed_keyboard(
    programs: List[Program], current_page: int = 1, total_pages: int = 1
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for prog in programs:
        ver_str = f" ({prog.version})" if prog.version else ""
        builder.row(
            InlineKeyboardButton(text=f"🕘 {prog.name}{ver_str}", callback_data=f"program:view:{prog.id}")
        )

    pagination = get_pagination(total_items=total_pages * 10, page=current_page, per_page=10)
    pagination.total_pages = total_pages
    pagination.has_previous = current_page > 1
    pagination.has_next = current_page < total_pages

    nav_row = build_pagination_keyboard_row(pagination, callback_prefix="recent:page")
    if nav_row:
        builder.row(*nav_row)

    builder.row(
        InlineKeyboardButton(text="🗑 Tarixni tozalash", callback_data="profile:recent:clear_confirm_ask"),
        InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="back:main")
    )
    return builder.as_markup()


def build_related_programs_keyboard(
    programs: List[Program], current_program_id: int
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for prog in programs:
        ver_str = f" ({prog.version})" if prog.version else ""
        builder.row(
            InlineKeyboardButton(text=f"🔗 {prog.name}{ver_str}", callback_data=f"program:view:{prog.id}")
        )

    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"program:view:{current_program_id}"))
    return builder.as_markup()


def build_popular_programs_keyboard(
    programs: List[Program], current_page: int = 1, total_pages: int = 1
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for prog in programs:
        ver_str = f" ({prog.version})" if prog.version else ""
        builder.row(InlineKeyboardButton(text=f"🔥 {prog.name}{ver_str}", callback_data=f"program:view:{prog.id}"))

    pagination = get_pagination(total_items=total_pages * 10, page=current_page, per_page=10)
    pagination.total_pages = total_pages
    pagination.has_previous = current_page > 1
    pagination.has_next = current_page < total_pages

    nav_row = build_pagination_keyboard_row(pagination, callback_prefix="popular:page")
    if nav_row:
        builder.row(*nav_row)

    builder.row(InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="back:main"))
    return builder.as_markup()


def build_new_programs_keyboard(
    programs: List[Program], current_page: int = 1, total_pages: int = 1
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for prog in programs:
        ver_str = f" ({prog.version})" if prog.version else ""
        builder.row(InlineKeyboardButton(text=f"🆕 {prog.name}{ver_str}", callback_data=f"program:view:{prog.id}"))

    pagination = get_pagination(total_items=total_pages * 10, page=current_page, per_page=10)
    pagination.total_pages = total_pages
    pagination.has_previous = current_page > 1
    pagination.has_next = current_page < total_pages

    nav_row = build_pagination_keyboard_row(pagination, callback_prefix="new:page")
    if nav_row:
        builder.row(*nav_row)

    builder.row(InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="back:main"))
    return builder.as_markup()


def build_downloads_keyboard(
    downloads_list: List[Tuple[Download, Program]], current_page: int = 1, total_pages: int = 1
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for download, prog in downloads_list:
        status_prefix = "" if prog.is_active else "🔴 "
        ver_str = f" ({prog.version})" if prog.version else ""
        builder.row(InlineKeyboardButton(text=f"{status_prefix}📥 {prog.name}{ver_str}", callback_data=f"program:view:{prog.id}"))

    pagination = get_pagination(total_items=total_pages * 10, page=current_page, per_page=10)
    pagination.total_pages = total_pages
    pagination.has_previous = current_page > 1
    pagination.has_next = current_page < total_pages

    nav_row = build_pagination_keyboard_row(pagination, callback_prefix="downloads:page")
    if nav_row:
        builder.row(*nav_row)

    builder.row(InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="back:main"))
    return builder.as_markup()
