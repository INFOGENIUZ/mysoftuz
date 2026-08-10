import logging
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.database.engine import async_session_maker
from app.services.settings_service import SettingsService
from app.services.admin_log_service import AdminLogService
from app.states.admin_panel import AdminSettingsEditState
from app.keyboards.admin.reply import get_admin_main_keyboard, get_admin_cancel_keyboard
from app.keyboards.admin.inline import build_admin_settings_keyboard

logger = logging.getLogger(__name__)
router = Router(name="admin_settings_router")


# -----------------------------------------------------------------------------
# Cancel FSM
# -----------------------------------------------------------------------------
@router.message(F.text == "❌ Bekor qilish", StateFilter(AdminSettingsEditState))
@router.message(F.text == "/cancel", StateFilter(AdminSettingsEditState))
async def admin_settings_cancel_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Sozlamalar amali bekor qilindi.", reply_markup=get_admin_main_keyboard())


# -----------------------------------------------------------------------------
# Settings List
# -----------------------------------------------------------------------------
@router.message(F.text == "⚙️ Sozlamalar")
@router.callback_query(F.data == "admin:settings:list")
async def admin_settings_list_handler(event: Message | CallbackQuery, is_admin: bool = False, admin_role: str = "admin"):
    if not is_admin:
        if isinstance(event, Message):
            await event.answer("⛔ Sizda ushbu bo'limga kirish huquqi yo'q.")
        elif isinstance(event, CallbackQuery):
            await event.answer("⛔ Sizda ushbu bo'limga kirish huquqi yo'q.", show_alert=True)
        return

    if isinstance(event, CallbackQuery):
        await event.answer()

    async with async_session_maker() as session:
        settings_service = SettingsService(session)
        maintenance = await settings_service.get_bool_setting("MAINTENANCE_MODE", default=False)
        welcome = await settings_service.get_setting("WELCOME_TEXT", default="Assalomu alaykum!")
        support = await settings_service.get_setting("SUPPORT_USERNAME", default="@support")

    status_str = "🔴 FAOL" if maintenance else "🟢 ISHLAYAPTI"

    text = (
        "⚙️ **BOT SOZLAMALARI**\n\n"
        f"🚧 Maintenance Holati: **{status_str}**\n"
        f"💬 Support Username: **{support}**\n\n"
        "Bajarmoqchi bo'lgan amalingizni tanlang:"
    )

    kb = build_admin_settings_keyboard(maintenance_mode=maintenance)

    if isinstance(event, Message):
        await event.answer(text=text, reply_markup=kb, parse_mode="Markdown")
    elif isinstance(event, CallbackQuery) and event.message:
        await event.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")


# -----------------------------------------------------------------------------
# Toggle Maintenance Mode
# -----------------------------------------------------------------------------
@router.callback_query(F.data == "admin:settings:toggle_maintenance")
async def admin_settings_toggle_maintenance(callback: CallbackQuery, is_admin: bool = False, admin_role: str = "admin"):
    if admin_role == "moderator":
        await callback.answer("⛔ Moderatorlarda ruxsat yo'q.", show_alert=True)
        return

    async with async_session_maker() as session:
        settings_service = SettingsService(session)
        log_service = AdminLogService(session)

        current = await settings_service.get_bool_setting("MAINTENANCE_MODE", default=False)
        new_val = not current
        await settings_service.set_setting("MAINTENANCE_MODE", str(new_val).lower())

        await log_service.log_action(
            admin_id=callback.from_user.id,
            action="SETTING_UPDATED",
            entity_type="Setting",
            details=f"Toggled MAINTENANCE_MODE to {new_val}"
        )

    action_str = "yoqildi" if new_val else "o'chirildi"
    await callback.answer(f"🚧 Maintenance mode {action_str}!", show_alert=True)
    await admin_settings_list_handler(callback, is_admin=True, admin_role=admin_role)


# -----------------------------------------------------------------------------
# Edit Setting Value
# -----------------------------------------------------------------------------
@router.callback_query(F.data.startswith("admin:settings:edit:"))
async def admin_settings_edit_prompt(callback: CallbackQuery, state: FSMContext, admin_role: str = "admin"):
    if admin_role == "moderator":
        await callback.answer("⛔ Moderatorlarda ruxsat yo'q.", show_alert=True)
        return
    await callback.answer()

    key = callback.data.split(":")[-1]
    await state.set_state(AdminSettingsEditState.waiting_for_value)
    await state.update_data(setting_key=key)

    prompts = {
        "welcome_text": "📝 **Yangi Welcome matnini kiriting:**",
        "about_text": "ℹ️ **Yangi About matnini kiriting:**",
        "support_username": "💬 **Yangi Support Username kiriting (masalan @support):**",
        "channel_username": "📢 **Yangi Kanal Username kiriting (masalan @channel):**"
    }

    prompt_text = prompts.get(key, f"📝 **Yangi {key} qiymatini kiriting:**")
    if callback.message:
        await callback.message.answer(prompt_text, reply_markup=get_admin_cancel_keyboard(), parse_mode="Markdown")


@router.message(AdminSettingsEditState.waiting_for_value)
async def admin_settings_edit_save(message: Message, state: FSMContext):
    data = await state.get_data()
    key = data.get("setting_key")
    val = message.text.strip() if message.text else ""

    if not val:
        await message.answer("⚠️ Qushimcha qiymat kiriting:")
        return

    if key == "support_username" and not val.startswith("@"):
        val = f"@{val}"

    async with async_session_maker() as session:
        settings_service = SettingsService(session)
        log_service = AdminLogService(session)

        await settings_service.set_setting(key, val)
        await log_service.log_action(
            admin_id=message.from_user.id,
            action="SETTING_UPDATED",
            entity_type="Setting",
            details=f"Updated {key} = '{val}'"
        )

    await state.clear()
    await message.answer("✅ **Sozlama muvaffaqiyatli saqlandi!**", reply_markup=get_admin_main_keyboard(), parse_mode="Markdown")
