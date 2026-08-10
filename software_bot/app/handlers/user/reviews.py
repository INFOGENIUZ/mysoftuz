import logging
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.database.engine import async_session_maker
from app.services.rating_service import RatingService
from app.services.review_service import ReviewService
from app.services.recommendation_service import RecommendationService
from app.services.program_service import ProgramService
from app.states.user import ReviewStates
from app.keyboards.user.reply import get_user_main_keyboard, get_search_cancel_keyboard
from app.keyboards.user.inline import (
    build_rating_selection_keyboard,
    build_reviews_keyboard,
    build_related_programs_keyboard,
    build_program_detail_keyboard
)
from app.utils.callback_factory import safe_answer_callback

logger = logging.getLogger(__name__)
router = Router(name="user_reviews_router")


# -----------------------------------------------------------------------------
# Ratings Handlers
# -----------------------------------------------------------------------------
@router.callback_query(F.data.startswith("rating:select:"))
async def rating_select_prompt(callback: CallbackQuery):
    await callback.answer()
    try:
        program_id = int(callback.data.split(":")[-1])
    except ValueError:
        return

    text = "⭐ **DASTURGA BAHO BERING**\n\nQuyida 1 dan 5 gacha yulduz tanlang:"
    kb = build_rating_selection_keyboard(program_id)
    if callback.message:
        await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("rating:set:"))
async def rating_set_process(callback: CallbackQuery):
    parts = callback.data.split(":")
    if len(parts) < 4:
        return
    try:
        program_id = int(parts[2])
        rating_val = int(parts[3])
    except ValueError:
        return

    if not callback.from_user:
        return

    user_id = callback.from_user.id
    async with async_session_maker() as session:
        rating_service = RatingService(session)
        is_new, new_avg, new_count = await rating_service.set_rating(user_id, program_id, rating_val)

        prog_service = ProgramService(session)
        program = await prog_service.get_program_by_id(program_id)

    msg = f"⭐ Bahoyingiz {rating_val} ta yulduzga saqlandi! Rahmat!" if is_new else f"⭐ Bahoyingiz {rating_val} ga o'zgartirildi!"
    await callback.answer(msg, show_alert=True)

    if callback.message and program:
        kb = build_program_detail_keyboard(program)
        detail_text = (
            f"💻 **{program.name.upper()}**\n\n"
            f"⭐ Reyting: **{program.rating_average:.1f} / 5** ({program.rating_count:,} ta baho)\n"
            f"⭐ Sizning bahoyingiz: **{rating_val} / 5**\n\n"
            f"📝 {program.description or program.short_description or ''}"
        )
        try:
            await callback.message.edit_text(text=detail_text, reply_markup=kb, parse_mode="Markdown")
        except Exception:
            pass


# -----------------------------------------------------------------------------
# Reviews Handlers
# -----------------------------------------------------------------------------
@router.callback_query(F.data.startswith("reviews:list:"))
async def reviews_list_handler(callback: CallbackQuery):
    await callback.answer()
    try:
        program_id = int(callback.data.split(":")[-1])
    except ValueError:
        return

    async with async_session_maker() as session:
        review_service = ReviewService(session)
        prog_service = ProgramService(session)

        program = await prog_service.get_program_by_id(program_id)
        reviews, total_pages = await review_service.get_program_reviews_paginated(program_id, page=1, page_size=5)

    prog_name = program.name if program else "Dastur"
    if not reviews:
        empty_text = f"💬 **{prog_name.upper()} SHARHLARI**\n\nHozircha bu dasturga tasdiqlangan sharhlar yo'q. Birinchi bo'lib sharh qoldiring!"
        kb = build_reviews_keyboard(program_id, [], current_page=1, total_pages=1)
        if callback.message:
            await callback.message.edit_text(empty_text, reply_markup=kb, parse_mode="Markdown")
        return

    text = f"💬 **{prog_name.upper()} SHARHLARI** (Sahifa 1/{total_pages}):"
    kb = build_reviews_keyboard(program_id, reviews, current_page=1, total_pages=total_pages)
    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("reviews:page:"))
async def reviews_page_handler(callback: CallbackQuery):
    await callback.answer()
    parts = callback.data.split(":")
    if len(parts) < 4:
        return
    try:
        program_id = int(parts[2])
        page = int(parts[3])
    except ValueError:
        return

    async with async_session_maker() as session:
        review_service = ReviewService(session)
        prog_service = ProgramService(session)

        program = await prog_service.get_program_by_id(program_id)
        reviews, total_pages = await review_service.get_program_reviews_paginated(program_id, page=page, page_size=5)

    prog_name = program.name if program else "Dastur"
    text = f"💬 **{prog_name.upper()} SHARHLARI** (Sahifa {page}/{total_pages}):"
    kb = build_reviews_keyboard(program_id, reviews, current_page=page, total_pages=total_pages)
    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("review:view:"))
async def review_view_detail_handler(callback: CallbackQuery):
    await callback.answer()
    try:
        review_id = int(callback.data.split(":")[-1])
    except ValueError:
        return

    async with async_session_maker() as session:
        review_service = ReviewService(session)
        review = await review_service.get_review_by_id(review_id)
        prog_service = ProgramService(session)
        program = await prog_service.get_program_by_id(review.program_id) if review else None

    if not review or not program:
        await callback.answer("⚠️ Sharh topilmadi.", show_alert=True)
        return

    author = f"@{review.user.username}" if (review.user and review.user.username) else "Anonim foydalanuvchi"
    created_str = review.created_at.strftime("%d.%m.%Y") if review.created_at else ""

    text = (
        f"💬 **{program.name.upper()} SHARHI**\n"
        f"👤 Muallif: **{author}**\n"
        f"📅 Sana: **{created_str}**\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"“{review.text}”"
    )

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💬 Sharhlar ro'yxati", callback_data=f"reviews:list:{program.id}"))
    builder.row(InlineKeyboardButton(text="💻 Dastur sahifasi", callback_data=f"program:view:{program.id}"))

    if callback.message:
        await callback.message.edit_text(text=text, reply_markup=builder.as_markup(), parse_mode="Markdown")


@router.callback_query(F.data.startswith("review:add:"))
async def review_add_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        program_id = int(callback.data.split(":")[-1])
    except ValueError:
        return

    await state.set_state(ReviewStates.waiting_for_text)
    await state.update_data(review_program_id=program_id)

    prompt = (
        "✍️ **SHARH YOZISH**\n\n"
        "Dastur haqida o'z fikringiz va sharhingizni yozib yuboring (3-1000 belgi).\n\n"
        "Masalan:\n`Dastur juda yaxshi ishlaydi, o'rnatish ham juda oson bo'ldi.`"
    )
    if callback.message:
        await callback.message.answer(prompt, reply_markup=get_search_cancel_keyboard(), parse_mode="Markdown")


@router.message(F.text == "🔙 Bekor qilish", StateFilter(ReviewStates))
async def review_cancel_process(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Sharh yozish bekor qilindi.", reply_markup=get_user_main_keyboard())


@router.message(ReviewStates.waiting_for_text)
async def review_save_process(message: Message, state: FSMContext):
    text_raw = message.text.strip() if message.text else ""
    if len(text_raw) < 3 or len(text_raw) > 1000:
        await message.answer("⚠️ Sharh matni 3 ta va 1000 ta belgi orasida bo'lishi kerak. Qayta yozing:")
        return

    data = await state.get_data()
    program_id = data.get("review_program_id")
    if not program_id or not message.from_user:
        await state.clear()
        return

    async with async_session_maker() as session:
        review_service = ReviewService(session)
        await review_service.create_review(
            user_telegram_id=message.from_user.id,
            program_id=program_id,
            text=text_raw
        )

    await state.clear()
    confirm_text = (
        "✅ **Sharhingiz qabul qilindi!**\n\n"
        "🕐 Administrator tekshiruvidan so'ng barchaga ko'rinadi."
    )
    await message.answer(confirm_text, reply_markup=get_user_main_keyboard(), parse_mode="Markdown")


# -----------------------------------------------------------------------------
# Related Programs Handler
# -----------------------------------------------------------------------------
@router.callback_query(F.data.startswith("related:view:"))
async def related_programs_view_handler(callback: CallbackQuery):
    await callback.answer()
    try:
        program_id = int(callback.data.split(":")[-1])
    except ValueError:
        return

    async with async_session_maker() as session:
        rec_service = RecommendationService(session)
        prog_service = ProgramService(session)

        program = await prog_service.get_program_by_id(program_id)
        related = await rec_service.get_related_programs(program_id, limit=5)

    prog_name = program.name if program else "Dastur"

    if not related:
        await safe_answer_callback(callback, "🔗 Ushbu dasturga o'xshash boshqa dasturlar topilmadi.")
        return

    text = f"🔗 **{prog_name.upper()} UCHUN O'XSHASH DASTURLAR:**\n\nQuyidagi dasturlarni ham ko'rishingiz mumkin:"
    kb = build_related_programs_keyboard(related, current_program_id=program_id)

    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
