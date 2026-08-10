import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from app.database.engine import async_session_maker
from app.services.statistics_service import StatisticsService
from app.keyboards.admin import get_admin_main_keyboard, build_admin_dashboard_keyboard

logger = logging.getLogger(__name__)
router = Router(name="admin_start_router")


@router.message(Command("admin"))
@router.callback_query(F.data == "admin:menu")
async def admin_start_handler(event: Message | CallbackQuery, is_admin: bool = False, admin_role: str = "admin"):
    if not is_admin:
        if isinstance(event, Message):
            await event.answer("⛔ Sizda ushbu bo'limga kirish huquqi yo'q.")
        elif isinstance(event, CallbackQuery):
            await event.answer("⛔ Sizda ushbu bo'limga kirish huquqi yo'q.", show_alert=True)
        return

    if isinstance(event, CallbackQuery):
        await event.answer()

    admin_name = event.from_user.first_name if event.from_user else "Admin"
    role_display = "Super Admin" if admin_role == "super_admin" else admin_role.capitalize()

    async with async_session_maker() as session:
        stats_service = StatisticsService(session)
        stats = await stats_service.get_dashboard_stats()

    dashboard_text = (
        f"👨‍💻 **ADMIN PANEL**\n\n"
        f"Assalomu alaykum, **{admin_name}**!\n"
        f"🛡 Rol: **{role_display}**\n\n"
        "📊 **QISQA STATISTIKA:**\n\n"
        f"👥 Foydalanuvchilar: **{stats['total_users']:,} ta**\n"
        f"💻 Dasturlar: **{stats['total_programs']:,} ta**\n"
        f"📂 Kategoriyalar: **{stats['total_categories']:,} ta**\n\n"
        f"📥 Bugungi yuklab olishlar: **{stats['today_downloads']:,} ta**\n"
        f"📥 Jami yuklab olishlar: **{stats['total_downloads']:,} ta**\n\n"
        "🟢 Bot holati: **Ishlayapti**"
    )

    kb = build_admin_dashboard_keyboard()

    if isinstance(event, Message):
        await event.answer(text="👨‍💻 **Admin panelga xush kelibsiz.**", reply_markup=get_admin_main_keyboard(), parse_mode="Markdown")
        await event.answer(text=dashboard_text, reply_markup=kb, parse_mode="Markdown")
    elif isinstance(event, CallbackQuery) and event.message:
        await event.message.edit_text(text=dashboard_text, reply_markup=kb, parse_mode="Markdown")
