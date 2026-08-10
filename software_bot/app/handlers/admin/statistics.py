import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from app.database.engine import async_session_maker
from app.services.statistics_service import StatisticsService
from app.keyboards.admin.inline import build_admin_dashboard_keyboard

logger = logging.getLogger(__name__)
router = Router(name="admin_statistics_router")


@router.message(F.text == "📊 Statistika")
@router.callback_query(F.data == "admin:stats:overview")
async def admin_statistics_overview_handler(event: Message | CallbackQuery, is_admin: bool = False):
    if not is_admin:
        if isinstance(event, Message):
            await event.answer("⛔ Sizda ushbu bo'limga kirish huquqi yo'q.")
        elif isinstance(event, CallbackQuery):
            await event.answer("⛔ Sizda ushbu bo'limga kirish huquqi yo'q.", show_alert=True)
        return

    if isinstance(event, CallbackQuery):
        await event.answer()

    async with async_session_maker() as session:
        stats_service = StatisticsService(session)
        stats = await stats_service.get_dashboard_stats()

    stats_text = (
        "📊 **BOT STATISTIKASI**\n\n"
        "👥 **FOYDALANUVCHILAR:**\n"
        f"• Jami: **{stats['total_users']:,} ta**\n"
        f"• Bugun faol (DAU): **{stats.get('today_active_users', 0):,} ta**\n"
        f"• Hafta faol (WAU): **{stats.get('week_active_users', 0):,} ta**\n"
        f"• Bugun yangi qo'shilgan: **{stats['today_users']:,} ta**\n"
        f"• Bloklanganlar: **{stats['blocked_users']:,} ta**\n\n"
        "💻 **DASTURLAR:**\n"
        f"• Jami: **{stats['total_programs']:,} ta**\n"
        f"• Faol: **{stats['active_programs']:,} ta**\n"
        f"• Nofaol: **{stats['inactive_programs']:,} ta**\n\n"
        "📂 **KATEGORIYALAR:**\n"
        f"• Jami: **{stats['total_categories']:,} ta**\n"
        f"• Faol: **{stats['active_categories']:,} ta**\n\n"
        "📥 **YUKLAB OLISHLAR:**\n"
        f"• Bugun: **{stats['today_downloads']:,} ta**\n"
        f"• Hafta: **{stats['week_downloads']:,} ta**\n"
        f"• Oy: **{stats['month_downloads']:,} ta**\n"
        f"• Jami: **{stats['total_downloads']:,} ta**"
    )


    kb = build_admin_dashboard_keyboard()

    if isinstance(event, Message):
        await event.answer(text=stats_text, reply_markup=kb, parse_mode="Markdown")
    elif isinstance(event, CallbackQuery) and event.message:
        await event.message.edit_text(text=stats_text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data == "admin:dashboard:refresh")
async def admin_dashboard_refresh_handler(callback: CallbackQuery, is_admin: bool = False):
    if not is_admin:
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return

    await callback.answer("🔄 Statistikalar yangilandi!")
    await admin_statistics_overview_handler(callback, is_admin=True)
