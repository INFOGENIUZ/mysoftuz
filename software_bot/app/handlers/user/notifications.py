import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.config import settings
from app.database.engine import async_session_maker
from app.services.notification_service import NotificationService
from app.services.update_service import UpdateService
from app.services.program_service import ProgramService
from app.keyboards.user.inline import build_user_notifications_keyboard, build_program_detail_keyboard

logger = logging.getLogger(__name__)
router = Router(name="user_notifications_router")


@router.message(F.text.startswith("🔔 Bildirishnomalar"))
@router.callback_query(F.data == "notification:list")
async def user_notifications_center_handler(event: Message | CallbackQuery):
    if not event.from_user:
        return

    if isinstance(event, CallbackQuery):
        await event.answer()

    user_id = event.from_user.id
    async with async_session_maker() as session:
        notif_service = NotificationService(session)
        notifs, total_pages = await notif_service.get_user_notifications_paginated(user_id, page=1, page_size=5)
        unread_count = await notif_service.get_unread_count(user_id)

    if not notifs:
        empty_text = (
            "🔔 **BILDIRISHNOMALAR MARKAZI**\n\n"
            "Sizda hozircha bildirishnomalar mavjud emas."
        )
        kb = build_user_notifications_keyboard([], current_page=1, total_pages=1)
        if isinstance(event, Message):
            await event.answer(empty_text, reply_markup=kb, parse_mode="Markdown")
        elif isinstance(event, CallbackQuery) and event.message:
            await event.message.edit_text(empty_text, reply_markup=kb, parse_mode="Markdown")
        return

    unread_str = f"🔴 **{unread_count} ta yangi**\n\n" if unread_count > 0 else "🟢 Barchasi o'qilgan\n\n"
    text = f"🔔 **BILDIRISHNOMALAR MARKAZI**\n\n{unread_str}Bildirishnomalar ro'yxati:"
    kb = build_user_notifications_keyboard(notifs, current_page=1, total_pages=total_pages)

    if isinstance(event, Message):
        await event.answer(text=text, reply_markup=kb, parse_mode="Markdown")
    elif isinstance(event, CallbackQuery) and event.message:
        await event.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("notification:page:"))
async def notification_page_handler(callback: CallbackQuery):
    await callback.answer()
    try:
        page = int(callback.data.split(":")[-1])
    except ValueError:
        page = 1

    if not callback.from_user:
        return

    user_id = callback.from_user.id
    async with async_session_maker() as session:
        notif_service = NotificationService(session)
        notifs, total_pages = await notif_service.get_user_notifications_paginated(user_id, page=page, page_size=5)
        unread_count = await notif_service.get_unread_count(user_id)

    unread_str = f"🔴 **{unread_count} ta yangi**\n\n" if unread_count > 0 else "🟢 Barchasi o'qilgan\n\n"
    text = f"🔔 **BILDIRISHNOMALAR MARKAZI** (Sahifa {page}/{total_pages})\n\n{unread_str}Bildirishnomalar ro'yxati:"
    kb = build_user_notifications_keyboard(notifs, current_page=page, total_pages=total_pages)

    if callback.message:
        await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("notification:view:"))
async def notification_view_detail_handler(callback: CallbackQuery):
    await callback.answer()
    try:
        notif_id = int(callback.data.split(":")[-1])
    except ValueError:
        return

    async with async_session_maker() as session:
        notif_service = NotificationService(session)
        notif = await notif_service.get_notification_by_id(notif_id)

    if not notif:
        await callback.answer("⚠️ Bildirishnoma topilmadi.", show_alert=True)
        return

    created_str = notif.created_at.strftime("%d.%m.%Y %H:%M") if notif.created_at else ""
    text = (
        f"🔔 **{notif.title.upper()}**\n"
        f"📅 _{created_str}_\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{notif.message}"
    )

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    if notif.program_id:
        builder.row(InlineKeyboardButton(text="💻 Dastur sahifasiga o'tish", callback_data=f"program:view:{notif.program_id}"))
    builder.row(InlineKeyboardButton(text="🔙 Bildirishnomalar", callback_data="notification:list"))

    if callback.message:
        await callback.message.edit_text(text=text, reply_markup=builder.as_markup(), parse_mode="Markdown")


@router.callback_query(F.data == "notification:mark_all_read")
async def notification_mark_all_read_handler(callback: CallbackQuery):
    if not callback.from_user:
        return

    user_id = callback.from_user.id
    async with async_session_maker() as session:
        notif_service = NotificationService(session)
        count = await notif_service.mark_all_as_read(user_id)

    await callback.answer(f"✅ {count} ta bildirishnoma o'qilgan deb belgilandi!", show_alert=True)
    await user_notifications_center_handler(callback)


@router.callback_query(F.data.startswith("sub:on:"))
async def subscription_on_handler(callback: CallbackQuery):
    try:
        program_id = int(callback.data.split(":")[-1])
    except ValueError:
        return

    if not callback.from_user:
        return

    user_id = callback.from_user.id
    async with async_session_maker() as session:
        update_service = UpdateService(session)
        prog_service = ProgramService(session)

        await update_service.subscribe_to_updates(user_id, program_id)
        program = await prog_service.get_program_by_id(program_id)

    await callback.answer("🔔 Dastur yangilanishlariga obuna bo'lindi!", show_alert=False)

    if callback.message and program:
        kb = build_program_detail_keyboard(program, is_subscribed=True)
        try:
            await callback.message.edit_reply_markup(reply_markup=kb)
        except Exception:
            pass


@router.callback_query(F.data.startswith("sub:off:"))
async def subscription_off_handler(callback: CallbackQuery):
    try:
        program_id = int(callback.data.split(":")[-1])
    except ValueError:
        return

    if not callback.from_user:
        return

    user_id = callback.from_user.id
    async with async_session_maker() as session:
        update_service = UpdateService(session)
        prog_service = ProgramService(session)

        await update_service.unsubscribe_from_updates(user_id, program_id)
        program = await prog_service.get_program_by_id(program_id)

    await callback.answer("🔕 Yangilanishlar obunasi o'chirildi.", show_alert=False)

    if callback.message and program:
        kb = build_program_detail_keyboard(program, is_subscribed=False)
        try:
            await callback.message.edit_reply_markup(reply_markup=kb)
        except Exception:
            pass
