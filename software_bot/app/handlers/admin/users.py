import logging
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, or_, func

from app.config import settings
from app.database.engine import async_session_maker
from app.database.models import User
from app.services.user_service import UserService
from app.services.download_service import DownloadService
from app.services.admin_log_service import AdminLogService
from app.states.admin_panel import AdminUserSearchStates
from app.keyboards.admin.reply import get_admin_main_keyboard, get_admin_cancel_keyboard
from app.keyboards.admin.inline import (
    build_admin_users_keyboard,
    build_admin_user_detail_keyboard,
    build_admin_user_block_confirm_keyboard,
    build_admin_user_unblock_confirm_keyboard,
)
from app.utils.callback_factory import safe_answer_callback

logger = logging.getLogger(__name__)
router = Router(name="admin_users_router")


# -----------------------------------------------------------------------------
# Cancel FSM
# -----------------------------------------------------------------------------
@router.message(F.text == "❌ Bekor qilish", StateFilter(AdminUserSearchStates))
@router.message(F.text == "/cancel", StateFilter(AdminUserSearchStates))
async def admin_user_cancel_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Foydalanuvchilar amali bekor qilindi.", reply_markup=get_admin_main_keyboard())


# -----------------------------------------------------------------------------
# Users List & Pagination
# -----------------------------------------------------------------------------
@router.message(F.text == "👥 Foydalanuvchilar")
@router.callback_query(F.data == "admin:users:list")
async def admin_users_list_handler(event: Message | CallbackQuery, is_admin: bool = False):
    if not is_admin:
        if isinstance(event, Message):
            await event.answer("⛔ Sizda ushbu bo'limga kirish huquqi yo'q.")
        elif isinstance(event, CallbackQuery):
            await event.answer("⛔ Sizda ushbu bo'limga kirish huquqi yo'q.", show_alert=True)
        return

    if isinstance(event, CallbackQuery):
        await event.answer()

    async with async_session_maker() as session:
        user_service = UserService(session)
        users, total_pages = await user_service.get_users_paginated(page=1, page_size=settings.PROGRAMS_PER_PAGE)

    text = "👥 **FOYDALANUVCHILARNI BOSHQARISH**\n\nFoydalanuvchilar ro'yxati:"
    kb = build_admin_users_keyboard(users, current_page=1, total_pages=total_pages)

    if isinstance(event, Message):
        await event.answer(text=text, reply_markup=kb, parse_mode="Markdown")
    elif isinstance(event, CallbackQuery) and event.message:
        await event.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("admin:users:page:"))
async def admin_users_page_handler(callback: CallbackQuery, is_admin: bool = False):
    if not is_admin:
        await callback.answer("⛔ Sizda ushbu bo'limga kirish huquqi yo'q.", show_alert=True)
        return
    await callback.answer()

    try:
        page = int(callback.data.split(":")[-1])
    except ValueError:
        page = 1

    async with async_session_maker() as session:
        user_service = UserService(session)
        users, total_pages = await user_service.get_users_paginated(page=page, page_size=settings.PROGRAMS_PER_PAGE)

    text = f"👥 **FOYDALANUVCHILARNI BOSHQARISH** (Sahifa {page}/{total_pages})\n\nFoydalanuvchilar ro'yxati:"
    kb = build_admin_users_keyboard(users, current_page=page, total_pages=total_pages)

    if callback.message:
        await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")


# -----------------------------------------------------------------------------
# User Detail View
# -----------------------------------------------------------------------------
@router.callback_query(F.data.startswith("admin:user:view:"))
async def admin_user_view_handler(callback: CallbackQuery, is_admin: bool = False, admin_role: str = "admin"):
    if not is_admin:
        await callback.answer("⛔ Sizda ushbu bo'limga kirish huquqi yo'q.", show_alert=True)
        return
    await callback.answer()

    try:
        user_db_id = int(callback.data.split(":")[-1])
    except ValueError:
        return

    async with async_session_maker() as session:
        user_service = UserService(session)
        dl_service = DownloadService(session)

        user = await user_service.get_user_by_id(user_db_id)
        if not user:
            await safe_answer_callback(callback, "⚠️ Foydalanuvchi topilmadi")
            return

        dl_count = await dl_service.get_user_download_count(user.telegram_id)

    status_str = "🔴 Bloklangan" if user.is_blocked else "🟢 Faol"
    reg_date = user.created_at.strftime("%d.%m.%Y %H:%M") if user.created_at else "Noma'lum"
    last_act = user.last_activity.strftime("%d.%m.%Y %H:%M") if user.last_activity else "Noma'lum"

    detail_text = (
        f"👤 **FOYDALANUVCHI TAFSILOTLARI**\n\n"
        f"• Ism: **{user.first_name or 'Noma\'lum'}**\n"
        f"• Familiya: **{user.last_name or 'Kiritilmagan'}**\n"
        f"• Username: **@{user.username or 'mavjud emas'}**\n"
        f"• Telegram ID: **{user.telegram_id}**\n\n"
        f"🟢 Holati: **{status_str}**\n"
        f"📅 Ro'yxatdan o'tgan: **{reg_date}**\n"
        f"⚡ Oxirgi faollik: **{last_act}**\n"
        f"📥 Yuklab olishlar soni: **{dl_count} ta**\n\n"
        f"🆔 DB ID: **{user.id}**"
    )


    kb = build_admin_user_detail_keyboard(user, user_role=admin_role)

    if callback.message:
        await callback.message.edit_text(text=detail_text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("admin:user:downloads:"))
async def admin_user_downloads_handler(callback: CallbackQuery, is_admin: bool = False):
    if not is_admin:
        await callback.answer("⛔ Sizda ushbu bo'limga kirish huquqi yo'q.", show_alert=True)
        return
    await callback.answer()

    try:
        user_db_id = int(callback.data.split(":")[-1])
    except ValueError:
        return

    async with async_session_maker() as session:
        user_service = UserService(session)
        dl_service = DownloadService(session)

        user = await user_service.get_user_by_id(user_db_id)
        if not user:
            await safe_answer_callback(callback, "⚠️ Foydalanuvchi topilmadi")
            return

        downloads_list, total_pages = await dl_service.get_user_downloads_unique_paginated(
            user_telegram_id=user.telegram_id, page=1, page_size=20
        )

    name_display = user.first_name or "Foydalanuvchi"
    if not downloads_list:
        text = f"📥 **{name_display.upper()} YUKLAB OLISHLARI**\n\nUshbu foydalanuvchi hali hech qanday dastur yuklab olmagan."
    else:
        text = f"📥 **{name_display.upper()} YUKLAB OLISHLARI ({len(downloads_list)} ta):**\n\n"
        for dl, prog in downloads_list:
            created_str = dl.created_at.strftime("%d.%m.%Y %H:%M") if dl.created_at else ""
            text += f"• 💻 **{prog.name}** (`v{prog.version or '1.0'}`) — _{created_str}_\n"

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Foydalanuvchiga qaytish", callback_data=f"admin:user:view:{user.id}"))

    if callback.message:
        await callback.message.edit_text(text=text, reply_markup=builder.as_markup(), parse_mode="Markdown")


# -----------------------------------------------------------------------------
# User Search
# -----------------------------------------------------------------------------
@router.callback_query(F.data == "admin:user:search_prompt")
async def admin_user_search_prompt(callback: CallbackQuery, state: FSMContext, is_admin: bool = False):
    if not is_admin:
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    await callback.answer()

    await state.set_state(AdminUserSearchStates.waiting_for_query)
    prompt = "🔎 **Foydalanuvchi qidirish:**\n\nUsername, ism yoki Telegram ID kiriting:"
    if callback.message:
        await callback.message.answer(prompt, reply_markup=get_admin_cancel_keyboard(), parse_mode="Markdown")


@router.message(AdminUserSearchStates.waiting_for_query)
async def admin_user_search_process(message: Message, state: FSMContext):
    query = message.text.strip() if message.text else ""
    if not query:
        await message.answer("⚠️ Qidiruv so'rovini kiriting:")
        return

    async with async_session_maker() as session:
        like_q = f"%{query}%"
        stmt = select(User).where(
            or_(
                User.username.ilike(like_q),
                User.first_name.ilike(like_q),
                User.last_name.ilike(like_q),
                func.cast(User.telegram_id, String).ilike(like_q)
            )
        ).limit(10)

        res = await session.execute(stmt)
        users = list(res.scalars().all())

    await state.clear()

    if not users:
        await message.answer("🔎 **Hetch qanday foydalanuvchi topilmadi.**", reply_markup=get_admin_main_keyboard(), parse_mode="Markdown")
        return

    text = f"🔎 **QIDIRUV NATIJALARI** ({len(users)} ta topildi):"
    kb = build_admin_users_keyboard(users, current_page=1, total_pages=1)
    await message.answer(text=text, reply_markup=kb, parse_mode="Markdown")


# -----------------------------------------------------------------------------
# User Block / Unblock Flow
# -----------------------------------------------------------------------------
@router.callback_query(F.data.startswith("admin:user:block:"))
async def admin_user_block_prompt(callback: CallbackQuery, admin_role: str = "admin"):
    if admin_role == "moderator":
        await callback.answer("⛔ Moderatorlarda foydalanuvchini bloklash huquqi yo'q.", show_alert=True)
        return
    await callback.answer()
    user_db_id = int(callback.data.split(":")[-1])

    async with async_session_maker() as session:
        user_service = UserService(session)
        user = await user_service.get_user_by_id(user_db_id)

    if not user:
        return

    text = f"⚠️ **Ushbu foydalanuvchini bloklashni tasdiqlaysizmi?**\n\n👤 **{user.first_name}** (@{user.username or 'no_user'})"
    kb = build_admin_user_block_confirm_keyboard(user_db_id)
    if callback.message:
        await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("admin:user:block_confirm:"))
async def admin_user_block_confirm(callback: CallbackQuery, admin_role: str = "admin"):
    if admin_role == "moderator":
        await callback.answer("⛔ Moderatorlarda ruxsat yo'q.", show_alert=True)
        return
    user_db_id = int(callback.data.split(":")[-1])

    async with async_session_maker() as session:
        user_service = UserService(session)
        log_service = AdminLogService(session)

        user = await user_service.get_user_by_id(user_db_id)
        if user:
            user.is_blocked = True
            await session.commit()
            await log_service.log_action(
                admin_id=callback.from_user.id,
                action="USER_BLOCKED",
                entity_type="User",
                entity_id=user.telegram_id,
                details=f"Blocked user @{user.username or user.first_name}"
            )

    await callback.answer("🔴 Foydalanuvchi bloklandi!", show_alert=True)
    await admin_user_view_handler(callback, is_admin=True, admin_role=admin_role)


@router.callback_query(F.data.startswith("admin:user:unblock:"))
async def admin_user_unblock_prompt(callback: CallbackQuery, admin_role: str = "admin"):
    if admin_role == "moderator":
        await callback.answer("⛔ Moderatorlarda ruxsat yo'q.", show_alert=True)
        return
    await callback.answer()
    user_db_id = int(callback.data.split(":")[-1])

    async with async_session_maker() as session:
        user_service = UserService(session)
        user = await user_service.get_user_by_id(user_db_id)

    if not user:
        return

    text = f"🟢 **Foydalanuvchi blokdan chiqarilsinmi?**\n\n👤 **{user.first_name}** (@{user.username or 'no_user'})"
    kb = build_admin_user_unblock_confirm_keyboard(user_db_id)
    if callback.message:
        await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("admin:user:unblock_confirm:"))
async def admin_user_unblock_confirm(callback: CallbackQuery, admin_role: str = "admin"):
    if admin_role == "moderator":
        await callback.answer("⛔ Moderatorlarda ruxsat yo'q.", show_alert=True)
        return
    user_db_id = int(callback.data.split(":")[-1])

    async with async_session_maker() as session:
        user_service = UserService(session)
        log_service = AdminLogService(session)

        user = await user_service.get_user_by_id(user_db_id)
        if user:
            user.is_blocked = False
            await session.commit()
            await log_service.log_action(
                admin_id=callback.from_user.id,
                action="USER_UNBLOCKED",
                entity_type="User",
                entity_id=user.telegram_id,
                details=f"Unblocked user @{user.username or user.first_name}"
            )

    await callback.answer("🟢 Foydalanuvchi blokdan chiqarildi!", show_alert=True)
    await admin_user_view_handler(callback, is_admin=True, admin_role=admin_role)
