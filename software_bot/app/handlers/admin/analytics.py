import logging
from datetime import datetime, timezone
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.database.engine import async_session_maker
from app.services.analytics_service import AnalyticsService, KPIChange
from app.states.admin_panel import AdminAnalyticsStates
from app.keyboards.admin.reply import get_admin_main_keyboard, get_admin_cancel_keyboard
from app.keyboards.admin.inline import (
    build_admin_analytics_menu_keyboard,
    build_admin_analytics_period_keyboard,
    build_admin_analytics_section_keyboard,
)

logger = logging.getLogger(__name__)
router = Router(name="admin_analytics_router")


def format_kpi(label: str, kpi: KPIChange) -> str:
    arrow = "↑" if kpi.is_positive else "↓"
    pct_str = f" ({arrow} {kpi.change_pct}%)" if kpi.change_pct > 0 else ""
    return f"{label}: **{kpi.current_value:,}**{pct_str}"


# -----------------------------------------------------------------------------
# Main Analytics Overview
# -----------------------------------------------------------------------------
@router.message(F.text == "📊 Analytics")
@router.callback_query(F.data == "admin:analytics:menu")
async def admin_analytics_main_handler(event: Message | CallbackQuery, state: FSMContext, is_admin: bool = False):
    if not is_admin:
        if isinstance(event, CallbackQuery):
            await event.answer("⛔ Ruxsat yo'q. Faqat administratorlar uchun.", show_alert=True)
        return

    if isinstance(event, CallbackQuery):
        await event.answer()

    data = await state.get_data()
    period = data.get("analytics_period", "7d")

    async with async_session_maker() as session:
        analytics_service = AnalyticsService(session)
        overview = await analytics_service.get_overview_analytics(period)

    cur_s_str = overview["cur_start"].strftime("%d.%m.%Y")
    cur_e_str = overview["cur_end"].strftime("%d.%m.%Y")

    text = (
        f"📊 **ADMIN ANALYTICS DASHBOARD**\n\n"
        f"📅 **Davr:** {cur_s_str} — {cur_e_str}\n\n"
        f"👥 {format_kpi('Yangi foydalanuvchilar', overview['users'])}\n"
        f"📥 {format_kpi('Yuklab olishlar', overview['downloads'])}\n"
        f"🔎 {format_kpi('Qidiruvlar', overview['searches'])}\n"
        f"⭐ {format_kpi('Baholar', overview['ratings'])}\n\n"
        f"💡 **INSIGHTS:**\n"
        f"• Faollik o'sish dinamikasi barqaror.\n"
        f"• Natijasiz qidiruvlar katalog bo'yicha imkoniyatlarni ko'rsatadi."
    )

    kb = build_admin_analytics_menu_keyboard(current_period=period)

    if isinstance(event, Message):
        await event.answer(text, reply_markup=kb, parse_mode="Markdown")
    elif isinstance(event, CallbackQuery) and event.message:
        await event.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


# -----------------------------------------------------------------------------
# Period Selector Handlers
# -----------------------------------------------------------------------------
@router.callback_query(F.data == "admin:analytics:period_menu")
async def admin_analytics_period_menu(callback: CallbackQuery, state: FSMContext, is_admin: bool = False):
    if not is_admin:
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    await callback.answer()

    data = await state.get_data()
    curr_p = data.get("analytics_period", "7d")
    text = "📅 **ANALITIKA DAVRINI TANLANG**"
    kb = build_admin_analytics_period_keyboard(curr_p)
    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("admin:analytics:set_period:"))
async def admin_analytics_set_period(callback: CallbackQuery, state: FSMContext, is_admin: bool = False):
    if not is_admin:
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return

    period_val = callback.data.split(":")[-1]

    if period_val == "custom":
        await callback.answer()
        await state.set_state(AdminAnalyticsStates.waiting_for_start_date)
        prompt = (
            "📅 **MAXSUS SANA DIAPAZONI**\n\n"
            "Boshlanish sanasini kiriting (`YYYY-MM-DD` formatda):\n"
            "Masalan: `2026-08-01`"
        )
        if callback.message:
            await callback.message.answer(prompt, reply_markup=get_admin_cancel_keyboard(), parse_mode="Markdown")
        return

    await state.update_data(analytics_period=period_val)
    await callback.answer("📅 Davr yangilandi!")
    await admin_analytics_main_handler(callback, state, is_admin=True)


# -----------------------------------------------------------------------------
# Custom Date FSM Handlers
# -----------------------------------------------------------------------------
@router.message(AdminAnalyticsStates.waiting_for_start_date)
async def admin_analytics_start_date_input(message: Message, state: FSMContext):
    dt_str = message.text.strip() if message.text else ""
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        await message.answer("⚠️ Noto'g'ri format. Iltimos, `YYYY-MM-DD` formatida yozing (Masalan: `2026-08-01`):")
        return

    await state.update_data(custom_start_str=dt_str)
    await state.set_state(AdminAnalyticsStates.waiting_for_end_date)
    await message.answer("📅 Tugash sanasini kiriting (`YYYY-MM-DD` formatda):", reply_markup=get_admin_cancel_keyboard(), parse_mode="Markdown")


@router.message(AdminAnalyticsStates.waiting_for_end_date)
async def admin_analytics_end_date_input(message: Message, state: FSMContext):
    dt_str = message.text.strip() if message.text else ""
    data = await state.get_data()
    start_str = data.get("custom_start_str")

    try:
        dt_start = datetime.strptime(start_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        dt_end = datetime.strptime(dt_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if dt_end < dt_start:
            await message.answer("⚠️ Tugash sanasi boshlanish sanasidan oldin bo'lishi mumkin emas.")
            return
    except ValueError:
        await message.answer("⚠️ Noto'g'ri format. Iltimos, `YYYY-MM-DD` formatida yozing:")
        return

    await state.update_data(analytics_period="custom", custom_start=dt_start.isoformat(), custom_end=dt_end.isoformat())
    await state.set_state(None)

    await message.answer("✅ Maxsus sana diapazoni o'rnatildi!", reply_markup=get_admin_main_keyboard())


# -----------------------------------------------------------------------------
# Analytics Sub-Sections Handlers
# -----------------------------------------------------------------------------
@router.callback_query(F.data.startswith("admin:analytics:section:"))
async def admin_analytics_section_handler(callback: CallbackQuery, state: FSMContext, is_admin: bool = False):
    if not is_admin:
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    await callback.answer()

    section = callback.data.split(":")[-1]
    data = await state.get_data()
    period = data.get("analytics_period", "7d")

    async with async_session_maker() as session:
        analytics_service = AnalyticsService(session)

        if section == "users":
            u_data = await analytics_service.get_user_analytics(period)
            text = (
                "👥 **USER ANALYTICS**\n\n"
                f"Jami foydalanuvchilar: **{u_data['total_users']:,}**\n"
                f"Yangi foydalanuvchilar: **{u_data['new_users']:,}**\n\n"
                f"🟢 **DAU (Kunlik faol):** {u_data['dau']:,}\n"
                f"🟢 **WAU (Haftalik faol):** {u_data['wau']:,}\n"
                f"🟢 **MAU (Oylik faol):** {u_data['mau']:,}"
            )
        elif section == "downloads":
            d_data = await analytics_service.get_download_analytics(period, limit=5)
            top_lines = "\n".join([f"{i+1}. 💻 {p.name} — **{cnt} ta**" for i, (p, cnt) in enumerate(d_data["top_programs"])])
            text = (
                "📥 **DOWNLOAD ANALYTICS**\n\n"
                f"Jami yuklab olishlar: **{d_data['total_downloads']:,}**\n"
                f"Unique foydalanuvchilar: **{d_data['unique_downloaders']:,}**\n\n"
                f"🔥 **ENG KO'P YUKLANGAN DASTURLAR:**\n{top_lines or 'Ma\'lumot yo\'q'}"
            )
        elif section == "search":
            s_data = await analytics_service.get_search_analytics(period, limit=5)
            top_q = "\n".join([f"• `{q}` ({cnt})" for q, cnt in s_data["top_queries"]])
            zero_q = "\n".join([f"• `{q}` ({cnt})" for q, cnt in s_data["zero_queries"]])
            text = (
                "🔎 **SEARCH ANALYTICS**\n\n"
                f"Jami qidiruvlar: **{s_data['total_searches']:,}**\n"
                f"🎯 Success Rate: **{s_data['success_rate']}%**\n\n"
                f"🔥 **TOP QIDIRUVLAR:**\n{top_q or 'Yo\'q'}\n\n"
                f"⚠️ **NATIJASIZ QIDIRUVLAR (Catalog Opportunities):**\n{zero_q or 'Yo\'q'}"
            )
        elif section == "engagement":
            e_data = await analytics_service.get_engagement_analytics(period)
            breakdown_str = "\n".join([f"⭐ {star} yulduz: **{cnt} ta**" for star, cnt in e_data["star_breakdown"].items()])
            text = (
                "⭐ **ENGAGEMENT ANALYTICS**\n\n"
                f"⭐ **REYTING TAQSIMOTI:**\n{breakdown_str}\n\n"
                f"💬 Moderatsiyada kutilayotgan sharhlar: **{e_data['pending_reviews']} ta**"
            )
        elif section == "notifications":
            n_data = await analytics_service.get_notification_analytics(period)
            text = (
                "🔔 **NOTIFICATION ANALYTICS**\n\n"
                f"✅ Muvaffaqiyatli yetkazilgan: **{n_data['sent_jobs']:,}**\n"
                f"🔴 Yetkazib berishda xatolik: **{n_data['failed_jobs']:,}**"
            )
        elif section == "alerts":
            alerts = await analytics_service.get_health_alerts(period)
            alerts_str = "\n".join(alerts)
            text = f"⚠️ **SYSTEM HEALTH ALERTS**\n\n{alerts_str}"
        else:
            text = "📊 Noma'lum analitika bo'limi."

    kb = build_admin_analytics_section_keyboard()
    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
