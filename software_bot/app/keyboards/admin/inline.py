from typing import List, Tuple, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.keyboards.components.factory import ButtonFactory
from app.database.models import Category, Program, User
from app.utils.pagination import get_pagination, build_pagination_keyboard_row


# -----------------------------------------------------------------------------
# Admin Dashboard Keyboards
# -----------------------------------------------------------------------------
def build_admin_dashboard_keyboard() -> InlineKeyboardMarkup:
    """Builds quick action inline keyboard for Admin Dashboard."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Dastur qo'shish", callback_data="admin:program:select_category"),
        InlineKeyboardButton(text="➕ Kategoriya qo'shish", callback_data="admin:category:create")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Batafsil statistika", callback_data="admin:stats:overview")
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Yangilash", callback_data="admin:dashboard:refresh")
    )
    return builder.as_markup()


def build_admin_program_category_select_keyboard(categories: List[Category]) -> InlineKeyboardMarkup:
    """Builds inline keyboard for selecting a category when creating a new program."""
    builder = InlineKeyboardBuilder()
    for cat in categories:
        icon_str = f"{cat.icon} " if cat.icon else ""
        btn_text = f"📂 {icon_str}{cat.name}"
        builder.row(
            InlineKeyboardButton(text=btn_text, callback_data=f"admin:program:create:{cat.id}")
        )
    builder.row(InlineKeyboardButton(text="🔙 Admin panel", callback_data="admin:menu"))
    return builder.as_markup()



# -----------------------------------------------------------------------------
# Admin Category Keyboards
# -----------------------------------------------------------------------------
def build_admin_categories_keyboard(
    categories_with_counts: List[Tuple[Category, int]], current_page: int = 1, total_pages: int = 1
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Kategoriya qo'shish", callback_data="admin:category:create")
    )

    for cat, count in categories_with_counts:
        icon_str = f"{cat.icon} " if cat.icon else "📂 "
        btn_text = f"{icon_str}{cat.name} ({count} ta)"
        builder.row(
            InlineKeyboardButton(text=btn_text, callback_data=f"admin:category:view:{cat.id}")
        )

    pagination = get_pagination(total_items=total_pages * 10, page=current_page, per_page=10)
    pagination.total_pages = total_pages
    pagination.has_previous = current_page > 1
    pagination.has_next = current_page < total_pages

    nav_row = build_pagination_keyboard_row(pagination, callback_prefix="admin:categories:page")
    if nav_row:
        builder.row(*nav_row)

    builder.row(InlineKeyboardButton(text="🔙 Admin panel", callback_data="admin:menu"))
    return builder.as_markup()


def build_admin_category_detail_keyboard(
    category: Category, program_count: int, user_role: str = "admin"
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    is_moderator = user_role == "moderator"

    builder.row(
        InlineKeyboardButton(text="➕ Dastur qo'shish", callback_data=f"admin:program:create:{category.id}"),
        InlineKeyboardButton(text="📋 Dasturlar", callback_data=f"admin:programs:list:{category.id}")
    )

    if not is_moderator:
        builder.row(
            InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"admin:category:edit:{category.id}")
        )

        if category.is_active:
            builder.row(
                InlineKeyboardButton(text="🔴 Nofaol qilish", callback_data=f"admin:category:deactivate:{category.id}")
            )
        else:
            builder.row(
                InlineKeyboardButton(text="🟢 Faollashtirish", callback_data=f"admin:category:activate:{category.id}")
            )

        builder.row(
            InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"admin:category:delete:{category.id}")
        )

    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin:categories:list"))
    return builder.as_markup()


def build_admin_category_preview_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Saqlash", callback_data="admin:category:save_confirm"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin:category:cancel_create")
    )
    return builder.as_markup()


def build_admin_category_edit_keyboard(category_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📝 Nom", callback_data=f"admin:category:edit_field:{category_id}:name"),
        InlineKeyboardButton(text="📄 Tavsif", callback_data=f"admin:category:edit_field:{category_id}:description")
    )
    builder.row(
        InlineKeyboardButton(text="🎨 Icon", callback_data=f"admin:category:edit_field:{category_id}:icon"),
        InlineKeyboardButton(text="🖼 Rasm", callback_data=f"admin:category:edit_field:{category_id}:image")
    )
    builder.row(
        InlineKeyboardButton(text="🔢 Tartib", callback_data=f"admin:category:edit_field:{category_id}:sort_order")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"admin:category:view:{category_id}")
    )
    return builder.as_markup()


def build_admin_category_deactivate_confirm_keyboard(category_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Ha, nofaol qilish", callback_data=f"admin:category:deactivate_confirm:{category_id}"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"admin:category:view:{category_id}")
    )
    return builder.as_markup()


def build_admin_category_activate_confirm_keyboard(category_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Ha, faollashtirish", callback_data=f"admin:category:activate_confirm:{category_id}"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"admin:category:view:{category_id}")
    )
    return builder.as_markup()


def build_admin_category_delete_confirm_keyboard(category_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🗑 Ha, o'chirish", callback_data=f"admin:category:delete_confirm:{category_id}"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"admin:category:view:{category_id}")
    )
    return builder.as_markup()


# -----------------------------------------------------------------------------
# Admin Program Keyboards
# -----------------------------------------------------------------------------
def build_admin_programs_keyboard(
    programs: List[Program], category_id: int, current_page: int = 1, total_pages: int = 1
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Dastur qo'shish", callback_data=f"admin:program:create:{category_id}")
    )

    for prog in programs:
        ver_str = f" ({prog.version})" if prog.version else ""
        btn_text = f"💻 {prog.name}{ver_str}"
        builder.row(
            InlineKeyboardButton(text=btn_text, callback_data=f"admin:program:view:{prog.id}")
        )

    pagination = get_pagination(total_items=total_pages * 10, page=current_page, per_page=10)
    pagination.total_pages = total_pages
    pagination.has_previous = current_page > 1
    pagination.has_next = current_page < total_pages

    nav_row = build_pagination_keyboard_row(pagination, callback_prefix=f"admin:programs:page:{category_id}")
    if nav_row:
        builder.row(*nav_row)

    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"admin:category:view:{category_id}"))
    return builder.as_markup()


def build_admin_program_detail_keyboard(program: Program, user_role: str = "admin") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    is_moderator = user_role == "moderator"

    builder.row(
        InlineKeyboardButton(text="📥 Test yuklab olish", callback_data=f"admin:program:test_download:{program.id}"),
        InlineKeyboardButton(text="📦 Versiyalar", callback_data=f"admin:version:list:{program.id}")
    )

    if not is_moderator:
        builder.row(
            InlineKeyboardButton(text="➕ Yangi versiya", callback_data=f"admin:version:create:{program.id}"),
            InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"admin:program:edit:{program.id}")
        )

        if program.is_active:
            builder.row(
                InlineKeyboardButton(text="🔴 Nofaol qilish", callback_data=f"admin:program:deactivate:{program.id}")
            )
        else:
            builder.row(
                InlineKeyboardButton(text="🟢 Faollashtirish", callback_data=f"admin:program:activate:{program.id}")
            )

        builder.row(
            InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"admin:program:delete:{program.id}")
        )

    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"admin:programs:list:{program.category_id}"))
    return builder.as_markup()


def build_admin_program_versions_keyboard(
    program_id: int, versions: List, current_page: int = 1, total_pages: int = 1
) -> InlineKeyboardMarkup:
    """Builds inline keyboard listing program versions for admin management."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Yangi versiya qo'shish", callback_data=f"admin:version:create:{program_id}")
    )

    for v in versions:
        status_mark = "🟢 CURRENT " if v.is_current else "⚪ "
        builder.row(
            InlineKeyboardButton(
                text=f"{status_mark}{v.version} ({v.created_at.strftime('%d.%m.%Y') if v.created_at else ''})",
                callback_data=f"admin:version:detail:{v.id}"
            )
        )

    pagination = get_pagination(total_items=total_pages * 10, page=current_page, per_page=10)
    pagination.total_pages = total_pages
    pagination.has_previous = current_page > 1
    pagination.has_next = current_page < total_pages

    nav_row = build_pagination_keyboard_row(pagination, callback_prefix=f"admin:versions:page:{program_id}")
    if nav_row:
        builder.row(*nav_row)

    builder.row(InlineKeyboardButton(text="🔙 Admin Program", callback_data=f"admin:program:view:{program_id}"))
    return builder.as_markup()


def build_admin_version_publish_keyboard(version_id: int, program_id: int) -> InlineKeyboardMarkup:
    """Builds confirmation keyboard for publishing a new version."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🚀 Nashr qilish (Faqat saqlash)", callback_data=f"admin:version:publish:{version_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="🚀 Nashr qilish va xabar yuborish", callback_data=f"admin:version:publish_notify:{version_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"admin:version:delete:{version_id}"),
        InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"admin:version:list:{program_id}")
    )
    return builder.as_markup()


def build_admin_architecture_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="x64", callback_data="arch:x64"),
        InlineKeyboardButton(text="x86", callback_data="arch:x86")
    )
    builder.row(
        InlineKeyboardButton(text="ARM64", callback_data="arch:ARM64"),
        InlineKeyboardButton(text="Universal", callback_data="arch:Universal")
    )
    builder.row(
        InlineKeyboardButton(text="Boshqa", callback_data="arch:other"),
        InlineKeyboardButton(text="⏭ O'tkazib yuborish", callback_data="arch:skip")
    )
    return builder.as_markup()


def build_admin_program_preview_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ SAQLASH", callback_data="admin:program:save_confirm"),
        InlineKeyboardButton(text="❌ BEKOR QILISH", callback_data="admin:program:cancel_create")
    )
    return builder.as_markup()


def build_admin_program_edit_keyboard(program_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📝 Nom", callback_data=f"admin:program:edit_field:{program_id}:name"),
        InlineKeyboardButton(text="📄 Qisqa tavsif", callback_data=f"admin:program:edit_field:{program_id}:short_description")
    )
    builder.row(
        InlineKeyboardButton(text="📃 To'liq tavsif", callback_data=f"admin:program:edit_field:{program_id}:description"),
        InlineKeyboardButton(text="🔢 Versiya", callback_data=f"admin:program:edit_field:{program_id}:version")
    )
    builder.row(
        InlineKeyboardButton(text="💻 Arxitektura", callback_data=f"admin:program:edit_field:{program_id}:architecture"),
        InlineKeyboardButton(text="🖥 Tizim talablari", callback_data=f"admin:program:edit_field:{program_id}:system_requirements")
    )
    builder.row(
        InlineKeyboardButton(text="🌐 Rasmiy sayt", callback_data=f"admin:program:edit_field:{program_id}:official_url"),
        InlineKeyboardButton(text="🖼 Rasm", callback_data=f"admin:program:edit_field:{program_id}:image_file_id")
    )
    builder.row(
        InlineKeyboardButton(text="📦 Fayl", callback_data=f"admin:program:edit_field:{program_id}:file"),
        InlineKeyboardButton(text="📂 Kategoriya", callback_data=f"admin:program:edit_category_select:{program_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"admin:program:view:{program_id}")
    )
    return builder.as_markup()


def build_admin_program_category_select_keyboard(
    categories: List[Category], current_category_id: int
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for cat in categories:
        mark = " (Hozirgi)" if cat.id == current_category_id else ""
        builder.row(
            InlineKeyboardButton(text=f"📂 {cat.name}{mark}", callback_data=f"admin:program:set_category:{cat.id}")
        )

    builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin:program:cancel_edit"))
    return builder.as_markup()


def build_admin_program_deactivate_confirm_keyboard(program_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Ha, nofaol qilish", callback_data=f"admin:program:deactivate_confirm:{program_id}"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"admin:program:view:{program_id}")
    )
    return builder.as_markup()


def build_admin_program_activate_confirm_keyboard(program_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Ha, faollashtirish", callback_data=f"admin:program:activate_confirm:{program_id}"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"admin:program:view:{program_id}")
    )
    return builder.as_markup()


def build_admin_program_delete_confirm_keyboard(program_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🗑 HA, O'CHIRISH", callback_data=f"admin:program:delete_confirm:{program_id}"),
        InlineKeyboardButton(text="❌ BEKOR QILISH", callback_data=f"admin:program:view:{program_id}")
    )
    return builder.as_markup()


# -----------------------------------------------------------------------------
# Admin User Management Keyboards
# -----------------------------------------------------------------------------
def build_admin_users_keyboard(
    users: List[User], current_page: int = 1, total_pages: int = 1
) -> InlineKeyboardMarkup:
    """Builds inline keyboard for user management list."""
    builder = InlineKeyboardBuilder()

    for u in users:
        status_icon = "🔴" if u.is_blocked else "🟢"
        name_str = f"{u.first_name} (@{u.username})" if u.username else u.first_name
        builder.row(
            InlineKeyboardButton(text=f"{status_icon} {name_str}", callback_data=f"admin:user:view:{u.id}")
        )

    pagination = get_pagination(total_items=total_pages * 10, page=current_page, per_page=10)
    pagination.total_pages = total_pages
    pagination.has_previous = current_page > 1
    pagination.has_next = current_page < total_pages

    nav_row = build_pagination_keyboard_row(pagination, callback_prefix="admin:users:page")
    if nav_row:
        builder.row(*nav_row)

    builder.row(
        InlineKeyboardButton(text="🔎 Qidirish", callback_data="admin:user:search_prompt"),
        InlineKeyboardButton(text="🔙 Admin panel", callback_data="admin:menu")
    )
    return builder.as_markup()


def build_admin_user_detail_keyboard(user: User, user_role: str = "admin") -> InlineKeyboardMarkup:
    """Builds action keyboard for Admin User Detail page."""
    builder = InlineKeyboardBuilder()
    is_moderator = user_role == "moderator"

    builder.row(
        InlineKeyboardButton(text="📥 Yuklab olishlar", callback_data=f"admin:user:downloads:{user.id}")
    )

    if not is_moderator:
        if user.is_blocked:
            builder.row(
                InlineKeyboardButton(text="🟢 Blokdan chiqarish", callback_data=f"admin:user:unblock:{user.id}")
            )
        else:
            builder.row(
                InlineKeyboardButton(text="🔴 Bloklash", callback_data=f"admin:user:block:{user.id}")
            )

    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin:users:list"))
    return builder.as_markup()


def build_admin_user_block_confirm_keyboard(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔴 Ha, bloklash", callback_data=f"admin:user:block_confirm:{user_id}"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"admin:user:view:{user_id}")
    )
    return builder.as_markup()


def build_admin_user_unblock_confirm_keyboard(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🟢 Ha, blokdan chiqarish", callback_data=f"admin:user:unblock_confirm:{user_id}"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"admin:user:view:{user_id}")
    )
    return builder.as_markup()


# -----------------------------------------------------------------------------
# Admin Settings & Broadcast Keyboards
# -----------------------------------------------------------------------------
def build_admin_settings_keyboard(maintenance_mode: bool = False) -> InlineKeyboardMarkup:
    """Builds inline keyboard for Admin Bot Settings."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📝 Welcome matni", callback_data="admin:settings:edit:welcome_text"),
        InlineKeyboardButton(text="ℹ️ About matni", callback_data="admin:settings:edit:about_text")
    )
    builder.row(
        InlineKeyboardButton(text="💬 Support", callback_data="admin:settings:edit:support_username"),
        InlineKeyboardButton(text="📢 Kanal", callback_data="admin:settings:edit:channel_username")
    )

    maint_btn_text = "🟢 Maintenance O'CHIRISH" if maintenance_mode else "🔴 Maintenance YOQISH"
    builder.row(
        InlineKeyboardButton(text=f"🚧 {maint_btn_text}", callback_data="admin:settings:toggle_maintenance")
    )
    builder.row(
        InlineKeyboardButton(text="📦 Fayl limitlari", callback_data="admin:settings:file_limits"),
        InlineKeyboardButton(text="🔢 Pagination", callback_data="admin:settings:pagination_limits")
    )
    builder.row(InlineKeyboardButton(text="🔙 Admin panel", callback_data="admin:menu"))
    return builder.as_markup()


def build_admin_broadcast_preview_keyboard() -> InlineKeyboardMarkup:
    """Builds preview confirmation keyboard for Super Admin broadcast."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ YUBORISH", callback_data="admin:broadcast:confirm"),
        InlineKeyboardButton(text="❌ BEKOR QILISH", callback_data="admin:broadcast:cancel")
    )
    return builder.as_markup()


# -----------------------------------------------------------------------------
# Admin Analytics & Intelligence Keyboards
# -----------------------------------------------------------------------------
def build_admin_analytics_menu_keyboard(current_period: str = "7d") -> InlineKeyboardMarkup:
    """Builds main inline navigation keyboard for Admin Analytics Dashboard."""
    builder = InlineKeyboardBuilder()

    period_labels = {
        "today": "Bugun", "yesterday": "Kecha", "7d": "7 kun", "30d": "30 kun", "90d": "90 kun", "1y": "1 yil", "custom": "Custom"
    }
    cur_p_label = period_labels.get(current_period, "7 kun")

    builder.row(
        InlineKeyboardButton(text=f"📅 Davr: [{cur_p_label}]", callback_data="admin:analytics:period_menu")
    )
    builder.row(
        InlineKeyboardButton(text="👥 Users", callback_data="admin:analytics:section:users"),
        InlineKeyboardButton(text="📥 Downloads", callback_data="admin:analytics:section:downloads")
    )
    builder.row(
        InlineKeyboardButton(text="🔎 Search", callback_data="admin:analytics:section:search"),
        InlineKeyboardButton(text="⭐ Engagement", callback_data="admin:analytics:section:engagement")
    )
    builder.row(
        InlineKeyboardButton(text="🔔 Notifications", callback_data="admin:analytics:section:notifications"),
        InlineKeyboardButton(text="⚠️ Health Alerts", callback_data="admin:analytics:section:alerts")
    )
    builder.row(InlineKeyboardButton(text="🔙 Admin panel", callback_data="admin:menu"))
    return builder.as_markup()


def build_admin_analytics_period_keyboard(current_period: str = "7d") -> InlineKeyboardMarkup:
    """Builds period selector menu for Admin Analytics."""
    builder = InlineKeyboardBuilder()
    periods = [
        ("today", "Bugun"),
        ("yesterday", "Kecha"),
        ("7d", "7 kun"),
        ("30d", "30 kun"),
        ("90d", "90 kun"),
        ("1y", "1 yil"),
        ("custom", "📅 Maxsus sana"),
    ]
    for p_val, label in periods:
        check = " ✅" if p_val == current_period else ""
        builder.row(InlineKeyboardButton(text=f"{label}{check}", callback_data=f"admin:analytics:set_period:{p_val}"))

    builder.row(InlineKeyboardButton(text="🔙 Analytics", callback_data="admin:analytics:menu"))
    return builder.as_markup()


def build_admin_analytics_section_keyboard() -> InlineKeyboardMarkup:
    """Builds back button keyboard for sub-analytics sections."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Analytics Menu", callback_data="admin:analytics:menu"))
    return builder.as_markup()
