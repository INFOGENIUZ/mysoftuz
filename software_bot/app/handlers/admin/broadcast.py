import logging
import asyncio
from aiogram import Router, F, Bot
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from app.database.engine import async_session_maker
from app.database.models import User
from app.services.admin_log_service import AdminLogService
from app.states.admin_panel import AdminBroadcastState
from app.keyboards.admin.reply import get_admin_main_keyboard, get_admin_cancel_keyboard
from app.keyboards.admin.inline import build_admin_broadcast_preview_keyboard

logger = logging.getLogger(__name__)
router = Router(name="admin_broadcast_router")


# -----------------------------------------------------------------------------
# Cancel FSM
# -----------------------------------------------------------------------------
@router.message(F.text == "❌ Bekor qilish", StateFilter(AdminBroadcastState))
@router.message(F.text == "/cancel", StateFilter(AdminBroadcastState))
async def admin_broadcast_cancel_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Reklama xabari bekor qilindi.", reply_markup=get_admin_main_keyboard())


# -----------------------------------------------------------------------------
# Broadcast Start (Super Admin Only)
# -----------------------------------------------------------------------------
@router.message(F.text == "📢 Reklama")
@router.callback_query(F.data == "admin:broadcast:start")
async def admin_broadcast_start_handler(event: Message | CallbackQuery, state: FSMContext, admin_role: str = "admin"):
    if admin_role != "super_admin":
        msg = "⛔ Reklama yuborish faqat Super Admin uchun ruxsat etilgan."
        if isinstance(event, Message):
            await event.answer(msg)
        elif isinstance(event, CallbackQuery):
            await event.answer(msg, show_alert=True)
        return

    if isinstance(event, CallbackQuery):
        await event.answer()

    await state.set_state(AdminBroadcastState.waiting_for_message)

    prompt = (
        "📢 **OMMAVIY REKLAMA YUBORISH**\n\n"
        "Foydalanuvchilarga yubormoqchi bo'lgan reklamangizni kiriting.\n\n"
        "Matn, rasm yoki boshqa har qanday Telegram xabari bo'lishi mumkin."
    )

    if isinstance(event, Message):
        await event.answer(prompt, reply_markup=get_admin_cancel_keyboard(), parse_mode="Markdown")
    elif isinstance(event, CallbackQuery) and event.message:
        await event.message.answer(prompt, reply_markup=get_admin_cancel_keyboard(), parse_mode="Markdown")


# -----------------------------------------------------------------------------
# Receive & Preview Broadcast Message
# -----------------------------------------------------------------------------
@router.message(AdminBroadcastState.waiting_for_message)
async def admin_broadcast_receive_message(message: Message, state: FSMContext):
    await state.update_data(
        broadcast_chat_id=message.chat.id,
        broadcast_message_id=message.message_id
    )
    await state.set_state(AdminBroadcastState.waiting_for_confirm)

    preview_text = "👁 **REKLAMA XABARI PREVIEW**\n\nQuyidagi xabar barcha faol foydalanuvchilarga yuborilsinmi?"
    kb = build_admin_broadcast_preview_keyboard()

    # Forward or copy message preview to admin
    await message.copy_to(chat_id=message.chat.id, reply_markup=None)
    await message.answer(preview_text, reply_markup=kb, parse_mode="Markdown")


# -----------------------------------------------------------------------------
# Confirm & Execute Broadcast Delivery Loop
# -----------------------------------------------------------------------------
@router.callback_query(F.data == "admin:broadcast:confirm", AdminBroadcastState.waiting_for_confirm)
async def admin_broadcast_confirm_send(callback: CallbackQuery, state: FSMContext, bot: Bot, admin_role: str = "admin"):
    if admin_role != "super_admin":
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    await callback.answer()

    data = await state.get_data()
    chat_id = data.get("broadcast_chat_id")
    msg_id = data.get("broadcast_message_id")

    if not chat_id or not msg_id:
        await callback.answer("❌ Xabar topilmadi.", show_alert=True)
        await state.clear()
        return

    async with async_session_maker() as session:
        # Fetch non-blocked, active users
        stmt = select(User.telegram_id).where(User.is_blocked == False, User.is_active == True)
        res = await session.execute(stmt)
        user_ids = list(res.scalars().all())

    await state.clear()
    total_users = len(user_ids)

    if callback.message:
        await callback.message.answer(f"⏳ **Reklama {total_users} ta foydalanuvchiga yuborilmoqda...**", parse_mode="Markdown")

    sent_count = 0
    failed_count = 0

    # Delivery Loop with Rate Limiting (0.05s delay = 20 msg/sec max to comply with Telegram Limits)
    for target_id in user_ids:
        try:
            await bot.copy_message(
                chat_id=target_id,
                from_chat_id=chat_id,
                message_id=msg_id
            )
            sent_count += 1
        except Exception as err:
            logger.warning(f"Broadcast failed for user {target_id}: {err}")
            failed_count += 1

        await asyncio.sleep(0.05)

    # Log Audit Record
    async with async_session_maker() as session:
        log_service = AdminLogService(session)
        await log_service.log_action(
            admin_id=callback.from_user.id,
            action="BROADCAST_SENT",
            entity_type="Broadcast",
            details=f"Sent to {sent_count} users, failed {failed_count}"
        )

    summary_text = (
        "📢 **REKLAMA YUKLAB YUBORILDI!**\n\n"
        f"👥 Jami mo'ljallangan: **{total_users:,}**\n"
        f"✅ Muvaffaqiyatli yuborildi: **{sent_count:,}**\n"
        f"❌ Xatolik berdi: **{failed_count:,}**"
    )

    if callback.message:
        await callback.message.answer(summary_text, reply_markup=get_admin_main_keyboard(), parse_mode="Markdown")


@router.callback_query(F.data == "admin:broadcast:cancel", StateFilter("*"))
async def admin_broadcast_cancel_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer("❌ Reklama bekor qilindi.")
    await state.clear()
    if callback.message:
        await callback.message.answer("❌ Reklama yuborish bekor qilindi.", reply_markup=get_admin_main_keyboard())
