import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.database.engine import async_session_maker
from app.services.user_profile_service import UserProfileService
from app.services.user_settings_service import UserSettingsService
from app.services.recent_service import RecentService
from app.services.recommendation_service import RecommendationService
from app.keyboards.user.inline import (
    build_user_profile_dashboard_keyboard,
    build_user_ratings_keyboard,
    build_user_rating_detail_keyboard,
    build_user_reviews_keyboard,
    build_user_review_detail_keyboard,
    build_user_settings_keyboard,
    build_recent_clear_confirm_keyboard,
)

logger = logging.getLogger(__name__)
router = Router(name="user_profile_router")


# -----------------------------------------------------------------------------
# Main Profile Dashboard View
# -----------------------------------------------------------------------------
@router.message(F.text.startswith("👤 Profilim"))
@router.callback_query(F.data == "profile:main")
async def user_profile_main_handler(event: Message | CallbackQuery):
    if not event.from_user:
        return

    if isinstance(event, CallbackQuery):
        await event.answer()

    tg_user = event.from_user
    user_id = tg_user.id
    async with async_session_maker() as session:
        from app.services.user_service import UserService
        user_service = UserService(session)
        await user_service.get_or_create_user(
            telegram_id=user_id,
            first_name=tg_user.first_name or "Foydalanuvchi",
            last_name=tg_user.last_name,
            username=tg_user.username,
            language_code=tg_user.language_code
        )

        profile_service = UserProfileService(session)
        summary = await profile_service.get_profile_summary(user_id)

    name_str = summary.user.first_name or "Foydalanuvchi"
    username_str = f"@{summary.user.username}" if summary.user.username else "Mavjud emas"
    created_str = summary.user.created_at.strftime("%d.%m.%Y") if summary.user.created_at else "Noma'lum"

    dashboard_text = (
        f"👤 **SHAXSIY KABINET**\n\n"
        f"👤 **Ism:** {name_str}\n"
        f"🌐 **Username:** {username_str}\n"
        f"🆔 **ID:** `{user_id}`\n\n"
        f"📊 **FAOLIYAT VA STATISTIKA:**\n"
        f"📥 Yuklab olishlar: **{summary.downloads_count}**\n"
        f"⭐ Sevimlilar: **{summary.favorites_count}**\n"
        f"⭐ Baholar: **{summary.ratings_count}**\n"
        f"💬 Sharhlar: **{summary.reviews_count}**\n"
        f"🔔 Yangi bildirishnomalar: **{summary.unread_notifications_count}**\n\n"
        f"📅 **Ro'yxatdan o'tgan sana:** {created_str}"
    )

    kb = build_user_profile_dashboard_keyboard(summary.unread_notifications_count)

    if isinstance(event, Message):
        await event.answer(dashboard_text, reply_markup=kb, parse_mode="Markdown")
    elif isinstance(event, CallbackQuery) and event.message:
        await event.message.edit_text(dashboard_text, reply_markup=kb, parse_mode="Markdown")


# -----------------------------------------------------------------------------
# Ratings History & Management
# -----------------------------------------------------------------------------
@router.callback_query(F.data == "profile:ratings")
@router.callback_query(F.data.startswith("profile:ratings:page:"))
async def user_profile_ratings_handler(callback: CallbackQuery):
    if not callback.from_user:
        return
    await callback.answer()

    page = 1
    if callback.data and callback.data.startswith("profile:ratings:page:"):
        try:
            page = int(callback.data.split(":")[-1])
        except ValueError:
            page = 1

    user_id = callback.from_user.id
    async with async_session_maker() as session:
        profile_service = UserProfileService(session)
        ratings, total_pages = await profile_service.get_user_ratings_paginated(user_id, page=page, page_size=5)

    if not ratings:
        text = "⭐ **BAHOLARIM**\n\nSiz hali hech qanday dasturga baho bermagansiz."
        kb = build_user_ratings_keyboard([], current_page=1, total_pages=1)
        if callback.message:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
        return

    text = f"⭐ **BAHOLARIM** (Sahifa {page}/{total_pages}):"
    kb = build_user_ratings_keyboard(ratings, current_page=page, total_pages=total_pages)
    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("profile:rating:detail:"))
async def user_rating_detail_handler(callback: CallbackQuery):
    if not callback.from_user:
        return
    await callback.answer()
    try:
        rating_id = int(callback.data.split(":")[-1])
    except ValueError:
        return

    user_id = callback.from_user.id
    async with async_session_maker() as session:
        profile_service = UserProfileService(session)
        ratings, _ = await profile_service.get_user_ratings_paginated(user_id, page=1, page_size=100)
        target = next((r for r in ratings if r.id == rating_id), None)

    if not target or not target.program:
        await callback.answer("⚠️ Baho topilmadi.", show_alert=True)
        return

    stars = "⭐" * target.rating
    text = (
        f"💻 **{target.program.name.upper()}**\n\n"
        f"Siz bergan baho: **{stars} ({target.rating}/5)**\n"
        f"📅 Sana: **{target.created_at.strftime('%d.%m.%Y')}**"
    )
    kb = build_user_rating_detail_keyboard(rating_id, target.program_id)
    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("profile:rating:delete:"))
async def user_rating_delete_handler(callback: CallbackQuery):
    if not callback.from_user:
        return
    try:
        rating_id = int(callback.data.split(":")[-1])
    except ValueError:
        return

    user_id = callback.from_user.id
    async with async_session_maker() as session:
        profile_service = UserProfileService(session)
        deleted = await profile_service.delete_user_rating(user_id, rating_id)

    if deleted:
        await callback.answer("🗑 Bahoyingiz o'chirildi!", show_alert=True)
        await user_profile_ratings_handler(callback)
    else:
        await callback.answer("⚠️ Bahoni o'chirishda xatolik yuz berdi.", show_alert=True)


# -----------------------------------------------------------------------------
# Reviews History & Moderation Status
# -----------------------------------------------------------------------------
@router.callback_query(F.data == "profile:reviews")
@router.callback_query(F.data.startswith("profile:reviews:page:"))
async def user_profile_reviews_handler(callback: CallbackQuery):
    if not callback.from_user:
        return
    await callback.answer()

    page = 1
    if callback.data and callback.data.startswith("profile:reviews:page:"):
        try:
            page = int(callback.data.split(":")[-1])
        except ValueError:
            page = 1

    user_id = callback.from_user.id
    async with async_session_maker() as session:
        profile_service = UserProfileService(session)
        reviews, total_pages = await profile_service.get_user_reviews_paginated(user_id, page=page, page_size=5)

    if not reviews:
        text = "💬 **SHARHLARIM**\n\nSiz hali sharh qoldirmagansiz."
        kb = build_user_reviews_keyboard([], current_page=1, total_pages=1)
        if callback.message:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
        return

    text = f"💬 **SHARHLARIM** (Sahifa {page}/{total_pages}):"
    kb = build_user_reviews_keyboard(reviews, current_page=page, total_pages=total_pages)
    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("profile:review:detail:"))
async def user_review_detail_handler(callback: CallbackQuery):
    if not callback.from_user:
        return
    await callback.answer()
    try:
        review_id = int(callback.data.split(":")[-1])
    except ValueError:
        return

    user_id = callback.from_user.id
    async with async_session_maker() as session:
        profile_service = UserProfileService(session)
        reviews, _ = await profile_service.get_user_reviews_paginated(user_id, page=1, page_size=100)
        target = next((r for r in reviews if r.id == review_id), None)

    if not target or not target.program:
        await callback.answer("⚠️ Sharh topilmadi.", show_alert=True)
        return

    status_str = "🟢 Tasdiqlangan" if target.status == "APPROVED" else ("🔴 Rad etilgan" if target.status == "REJECTED" else "🕐 Moderatsiya kutilmoqda")

    text = (
        f"💻 **{target.program.name.upper()}**\n\n"
        f"💬 **Sharhingiz:**\n“{target.text}”\n\n"
        f"Status: **{status_str}**\n"
        f"📅 Sana: **{target.created_at.strftime('%d.%m.%Y')}**"
    )
    kb = build_user_review_detail_keyboard(review_id, target.program_id)
    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("profile:review:delete:"))
async def user_review_delete_handler(callback: CallbackQuery):
    if not callback.from_user:
        return
    try:
        review_id = int(callback.data.split(":")[-1])
    except ValueError:
        return

    user_id = callback.from_user.id
    async with async_session_maker() as session:
        profile_service = UserProfileService(session)
        deleted = await profile_service.delete_user_review(user_id, review_id)

    if deleted:
        await callback.answer("🗑 Sharhingiz o'chirildi!", show_alert=True)
        await user_profile_reviews_handler(callback)
    else:
        await callback.answer("⚠️ Sharhni o'chirishda xatolik yuz berdi.", show_alert=True)


# -----------------------------------------------------------------------------
# Recently Viewed History Clear Confirm
# -----------------------------------------------------------------------------
@router.callback_query(F.data == "profile:recent:clear_confirm_ask")
async def recent_clear_ask_handler(callback: CallbackQuery):
    await callback.answer()
    text = "⚠️ **Yaqinda ko'rilganlar tarixini tozalashni tasdiqlaysizmi?**"
    kb = build_recent_clear_confirm_keyboard()
    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data == "profile:recent:clear_confirm")
async def recent_clear_confirm_handler(callback: CallbackQuery):
    if not callback.from_user:
        return
    user_id = callback.from_user.id
    async with async_session_maker() as session:
        recent_service = RecentService(session)
        await recent_service.clear_recently_viewed(user_id)

    await callback.answer("🗑 Tarix muvaffaqiyatli tozalandi!", show_alert=True)
    await user_profile_main_handler(callback)


# -----------------------------------------------------------------------------
# Personal Recommendations View
# -----------------------------------------------------------------------------
@router.callback_query(F.data == "profile:recommendations")
async def personal_recommendations_handler(callback: CallbackQuery):
    if not callback.from_user:
        return
    await callback.answer()
    user_id = callback.from_user.id

    async with async_session_maker() as session:
        rec_service = RecommendationService(session)
        progs = await rec_service.get_user_recommendations(user_id, limit=5)

    if not progs:
        text = "🎯 **SIZ UCHUN TAVSIYALAR**\n\nHozircha sizga tavsiya qilish uchun yetarli ma'lumot yo'q."
    else:
        text = "🎯 **SIZ UCHUN TAVSIYA ETILADIGAN DASTURLAR:**"

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    for p in progs:
        builder.row(
            InlineKeyboardButton(text=f"🎯 {p.name} ({p.version or 'v1.0'})", callback_data=f"program:view:{p.id}")
        )
    builder.row(InlineKeyboardButton(text="🔙 Profilga qaytish", callback_data="profile:main"))

    if callback.message:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")


# -----------------------------------------------------------------------------
# User Settings & Preferences
# -----------------------------------------------------------------------------
@router.callback_query(F.data == "profile:settings")
async def user_settings_handler(callback: CallbackQuery):
    if not callback.from_user:
        return
    await callback.answer()
    user_id = callback.from_user.id

    async with async_session_maker() as session:
        settings_service = UserSettingsService(session)
        setting = await settings_service.get_or_create_settings(user_id)

    text = "⚙️ **SHAXSIY SOZLAMALAR**\n\nBildirishnoma va maxfiylik sozlamalarini boshqaring:"
    kb = build_user_settings_keyboard(setting)
    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("profile:setting:toggle:"))
async def user_setting_toggle_handler(callback: CallbackQuery):
    if not callback.from_user:
        return
    field_name = callback.data.split(":")[-1]
    user_id = callback.from_user.id

    async with async_session_maker() as session:
        settings_service = UserSettingsService(session)
        new_val = await settings_service.toggle_setting(user_id, field_name)
        setting = await settings_service.get_or_create_settings(user_id)

    await callback.answer(f"⚙️ Sozlama {'yoqildi' if new_val else 'o\'chirildi'}")
    kb = build_user_settings_keyboard(setting)
    if callback.message:
        try:
            await callback.message.edit_reply_markup(reply_markup=kb)
        except Exception:
            pass


@router.callback_query(F.data == "profile:setting:language")
async def user_setting_language_handler(callback: CallbackQuery):
    await callback.answer("🌐 Hozircha faqat 🇺🇿 O'zbekcha tili qo'llab-quvvatlanadi.", show_alert=True)


@router.callback_query(F.data == "profile:setting:privacy")
async def user_setting_privacy_handler(callback: CallbackQuery):
    await callback.answer("🔒 Maxfiylik sozlamalari: Sharhlarda username ko'rinishi faol.", show_alert=True)
