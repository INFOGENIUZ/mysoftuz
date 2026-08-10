import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.database.engine import async_session_maker
from app.services.review_service import ReviewService
from app.services.admin_log_service import AdminLogService
from app.utils.callback_factory import safe_answer_callback

logger = logging.getLogger(__name__)
router = Router(name="admin_reviews_router")


def build_admin_pending_reviews_keyboard(reviews, page: int = 1, total_pages: int = 1) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for rev in reviews:
        user_name = f"@{rev.user.username}" if (rev.user and rev.user.username) else "Anonim"
        snippet = rev.text[:25] + "..." if len(rev.text) > 25 else rev.text
        builder.row(
            InlineKeyboardButton(text=f"🕐 {user_name}: {snippet}", callback_data=f"admin:review:detail:{rev.id}")
        )
    builder.row(InlineKeyboardButton(text="🔙 Admin panel", callback_data="admin:menu"))
    return builder.as_markup()


def build_admin_review_detail_keyboard(review_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"admin:review:approve:{review_id}"),
        InlineKeyboardButton(text="❌ Rad etish", callback_data=f"admin:review:reject:{review_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"admin:review:delete:{review_id}"),
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin:reviews:pending")
    )
    return builder.as_markup()


@router.callback_query(F.data == "admin:reviews:pending")
async def admin_pending_reviews_list(callback: CallbackQuery, is_admin: bool = False):
    if not is_admin:
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    await callback.answer()

    async with async_session_maker() as session:
        review_service = ReviewService(session)
        reviews, total_pages = await review_service.get_pending_reviews_paginated(page=1, page_size=10)

    if not reviews:
        await callback.answer("✅ Kutilayotgan sharhlar mavjud emas.", show_alert=True)
        return

    text = f"💬 **KUTILAYOTGAN SHARHLAR MODERATSIYASI** ({len(reviews)} ta):"
    kb = build_admin_pending_reviews_keyboard(reviews, page=1, total_pages=total_pages)

    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("admin:review:detail:"))
async def admin_review_detail(callback: CallbackQuery, is_admin: bool = False):
    if not is_admin:
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    await callback.answer()

    try:
        review_id = int(callback.data.split(":")[-1])
    except ValueError:
        return

    async with async_session_maker() as session:
        review_service = ReviewService(session)
        review = (await session.execute(
            select(ProgramReview).where(ProgramReview.id == review_id)
        )).scalar_one_or_none() if False else None

        # Fetch explicitly
        from sqlalchemy import select
        from app.database.models import ProgramReview
        res = await session.execute(select(ProgramReview).where(ProgramReview.id == review_id))
        review = res.scalar_one_or_none()

    if not review:
        await safe_answer_callback(callback, "⚠️ Sharh topilmadi")
        return

    user_name = f"@{review.user.username}" if (review.user and review.user.username) else f"ID {review.user_id}"
    prog_name = review.program.name if review.program else f"ID {review.program_id}"
    created_str = review.created_at.strftime("%d.%m.%Y %H:%M") if review.created_at else ""

    detail_text = (
        f"💬 **SHARH MODERATSIYASI**\n\n"
        f"💻 Dastur: **{prog_name}**\n"
        f"👤 Muallif: **{user_name}**\n"
        f"📅 Sana: **{created_str}**\n\n"
        f"📝 Matn:\n“_{review.text}_”"
    )

    kb = build_admin_review_detail_keyboard(review_id)
    if callback.message:
        await callback.message.edit_text(detail_text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("admin:review:approve:"))
async def admin_review_approve(callback: CallbackQuery, is_admin: bool = False):
    if not is_admin:
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    try:
        review_id = int(callback.data.split(":")[-1])
    except ValueError:
        return

    async with async_session_maker() as session:
        review_service = ReviewService(session)
        log_service = AdminLogService(session)

        ok = await review_service.approve_review(review_id)
        if ok:
            await log_service.log_action(
                admin_id=callback.from_user.id,
                action="REVIEW_APPROVED",
                entity_type="Review",
                entity_id=review_id,
                details="Approved program review"
            )

    await callback.answer("✅ Sharh tasdiqlandi!", show_alert=True)
    await admin_pending_reviews_list(callback, is_admin=True)


@router.callback_query(F.data.startswith("admin:review:reject:"))
async def admin_review_reject(callback: CallbackQuery, is_admin: bool = False):
    if not is_admin:
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    try:
        review_id = int(callback.data.split(":")[-1])
    except ValueError:
        return

    async with async_session_maker() as session:
        review_service = ReviewService(session)
        log_service = AdminLogService(session)

        ok = await review_service.reject_review(review_id)
        if ok:
            await log_service.log_action(
                admin_id=callback.from_user.id,
                action="REVIEW_REJECTED",
                entity_type="Review",
                entity_id=review_id,
                details="Rejected program review"
            )

    await callback.answer("❌ Sharh rad etildi!", show_alert=True)
    await admin_pending_reviews_list(callback, is_admin=True)
