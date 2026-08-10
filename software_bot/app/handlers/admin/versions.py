import logging
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.database.engine import async_session_maker
from app.services.version_service import VersionService
from app.services.program_service import ProgramService
from app.services.notification_service import NotificationService
from app.services.admin_log_service import AdminLogService
from app.states.admin_panel import AdminVersionStates
from app.keyboards.admin.reply import get_admin_main_keyboard, get_admin_cancel_keyboard
from app.keyboards.admin.inline import (
    build_admin_program_versions_keyboard,
    build_admin_version_publish_keyboard,
)

logger = logging.getLogger(__name__)
router = Router(name="admin_versions_router")


# -----------------------------------------------------------------------------
# Cancel FSM
# -----------------------------------------------------------------------------
@router.message(F.text == "❌ Bekor qilish", StateFilter(AdminVersionStates))
@router.message(F.text == "/cancel", StateFilter(AdminVersionStates))
async def admin_version_cancel_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Versiya amali bekor qilindi.", reply_markup=get_admin_main_keyboard())


# -----------------------------------------------------------------------------
# Admin Version History List
# -----------------------------------------------------------------------------
@router.callback_query(F.data.startswith("admin:version:list:"))
async def admin_version_list_handler(callback: CallbackQuery, is_admin: bool = False):
    if not is_admin:
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    await callback.answer()

    try:
        program_id = int(callback.data.split(":")[-1])
    except ValueError:
        return

    async with async_session_maker() as session:
        version_service = VersionService(session)
        prog_service = ProgramService(session)

        program = await prog_service.get_program_by_id(program_id)
        versions, total_pages = await version_service.get_version_history_paginated(program_id, page=1, page_size=10)

    prog_name = program.name if program else "Dastur"
    text = f"📦 **{prog_name.upper()} VERSIYALAR TARIXI**:"
    kb = build_admin_program_versions_keyboard(program_id, versions, current_page=1, total_pages=total_pages)

    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


# -----------------------------------------------------------------------------
# Add New Version FSM Flow
# -----------------------------------------------------------------------------
@router.callback_query(F.data.startswith("admin:version:create:"))
async def admin_version_create_start(callback: CallbackQuery, state: FSMContext, admin_role: str = "admin"):
    if admin_role == "moderator":
        await callback.answer("⛔ Moderatorlarda yangi versiya kiritish huquqi yo'q.", show_alert=True)
        return
    await callback.answer()

    try:
        program_id = int(callback.data.split(":")[-1])
    except ValueError:
        return

    await state.set_state(AdminVersionStates.waiting_for_version)
    await state.update_data(v_program_id=program_id)

    prompt = (
        "📦 **YANGI VERSIYA QO'SHISH**\n\n"
        "Yangi versiya raqamini yuboring.\n\n"
        "Masalan:\n`2026.2`"
    )
    if callback.message:
        await callback.message.answer(prompt, reply_markup=get_admin_cancel_keyboard(), parse_mode="Markdown")


@router.message(AdminVersionStates.waiting_for_version)
async def admin_version_receive_version(message: Message, state: FSMContext):
    ver_str = message.text.strip() if message.text else ""
    if not ver_str:
        await message.answer("⚠️ Versiya raqamini yozing:")
        return

    await state.update_data(v_version=ver_str)
    await state.set_state(AdminVersionStates.waiting_for_release_notes)

    prompt = (
        "📝 **YANGILIKLAR / RELIZ ESLATMALARI (Release Notes)**\n\n"
        "Ushbu versiyadagi yangiliklar va o'zgarishlarni kiriting:"
    )
    await message.answer(prompt, reply_markup=get_admin_cancel_keyboard(), parse_mode="Markdown")


@router.message(AdminVersionStates.waiting_for_release_notes)
async def admin_version_receive_notes(message: Message, state: FSMContext):
    notes = message.text.strip() if message.text else ""
    await state.update_data(v_release_notes=notes)
    await state.set_state(AdminVersionStates.waiting_for_official_url)

    prompt = (
        "🌐 **RASMIY RELIZ MANBASI URL (Ixtiyoriy)**\n\n"
        "Rasmiy vebsayt havolasini kiriting yoki o'tkazib yuborish uchun `/skip` bosing:"
    )
    await message.answer(prompt, reply_markup=get_admin_cancel_keyboard(), parse_mode="Markdown")


@router.message(AdminVersionStates.waiting_for_official_url)
async def admin_version_receive_url(message: Message, state: FSMContext):
    url_text = message.text.strip() if message.text else ""
    if url_text == "/skip":
        url_text = None

    await state.update_data(v_official_url=url_text)
    await state.set_state(AdminVersionStates.waiting_for_file)

    prompt = (
        "📁 **YANGI DASTUR FAYLINI YUBORING**\n\n"
        "Telegram orqali yangi dastur faylini (document) yuboring:"
    )
    await message.answer(prompt, reply_markup=get_admin_cancel_keyboard(), parse_mode="Markdown")


@router.message(AdminVersionStates.waiting_for_file, F.document)
async def admin_version_receive_file(message: Message, state: FSMContext):
    doc = message.document
    data = await state.get_data()
    program_id = data.get("v_program_id")
    ver_str = data.get("v_version")
    notes = data.get("v_release_notes")
    off_url = data.get("v_official_url")

    if not program_id or not doc:
        await state.clear()
        return

    async with async_session_maker() as session:
        version_service = VersionService(session)
        log_service = AdminLogService(session)

        # Create version (not current yet)
        version = await version_service.create_version(
            program_id=program_id,
            version_str=ver_str,
            file_id=doc.file_id,
            file_unique_id=doc.file_unique_id,
            file_size=doc.file_size,
            release_notes=notes,
            official_release_url=off_url,
            is_current=False
        )

        await log_service.log_action(
            admin_id=message.from_user.id,
            action="VERSION_CREATED",
            entity_type="ProgramVersion",
            entity_id=version.id,
            details=f"Created version {ver_str} for program {program_id}"
        )

    await state.clear()

    preview_text = (
        f"📦 **YANGI VERSIYA SAQLANDI (Hali nashr etilmadi)**\n\n"
        f"🔢 Versiya: **{version.version}**\n"
        f"💾 Hajmi: **{doc.file_size or 0} bytes**\n\n"
        f"📝 Release Notes:\n{notes or 'Yo\'q'}\n\n"
        "Kerakli nashr qilish turini tanlang:"
    )
    kb = build_admin_version_publish_keyboard(version.id, program_id)
    await message.answer(preview_text, reply_markup=kb, parse_mode="Markdown")


# -----------------------------------------------------------------------------
# Version Publish & Notification Enqueue
# -----------------------------------------------------------------------------
@router.callback_query(F.data.startswith("admin:version:publish:"))
async def admin_version_publish_silent(callback: CallbackQuery, is_admin: bool = False):
    if not is_admin:
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    try:
        version_id = int(callback.data.split(":")[-1])
    except ValueError:
        return

    async with async_session_maker() as session:
        version_service = VersionService(session)
        log_service = AdminLogService(session)

        pv = await version_service.publish_version(version_id)
        if pv:
            await log_service.log_action(
                admin_id=callback.from_user.id,
                action="VERSION_PUBLISHED",
                entity_type="ProgramVersion",
                entity_id=version_id,
                details=f"Published version {pv.version} as current without notify"
            )

    await callback.answer("🚀 Versiya joriy (Current) sifatida nashr qilindi!", show_alert=True)
    if pv and callback.message:
        await callback.message.edit_text(f"🚀 **Versiya {pv.version} nashr qilindi!**", parse_mode="Markdown")


@router.callback_query(F.data.startswith("admin:version:publish_notify:"))
async def admin_version_publish_notify(callback: CallbackQuery, is_admin: bool = False):
    if not is_admin:
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    try:
        version_id = int(callback.data.split(":")[-1])
    except ValueError:
        return

    async with async_session_maker() as session:
        version_service = VersionService(session)
        notif_service = NotificationService(session)
        log_service = AdminLogService(session)

        pv = await version_service.publish_version(version_id)
        queued_count = 0
        if pv:
            queued_count = await notif_service.enqueue_update_notifications(pv.program_id, pv.id)
            await log_service.log_action(
                admin_id=callback.from_user.id,
                action="VERSION_PUBLISHED",
                entity_type="ProgramVersion",
                entity_id=version_id,
                details=f"Published version {pv.version} and enqueued {queued_count} notifications"
            )

    await callback.answer(f"🚀 Nashr etildi! {queued_count} ta foydalanuvchiga bildirishnoma navbatga qo'yildi.", show_alert=True)
    if pv and callback.message:
        await callback.message.edit_text(
            f"🚀 **Versiya {pv.version} nashr etildi!**\n\n📢 **{queued_count} ta** bildirishnoma yetkazish navbatiga qo'shildi.",
            parse_mode="Markdown"
        )


@router.callback_query(F.data.startswith("admin:version:delete:"))
async def admin_version_delete_handler(callback: CallbackQuery, is_admin: bool = False):
    if not is_admin:
        await callback.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return
    try:
        version_id = int(callback.data.split(":")[-1])
    except ValueError:
        return

    async with async_session_maker() as session:
        version_service = VersionService(session)
        log_service = AdminLogService(session)

        deleted = await version_service.delete_version(version_id)
        if deleted:
            await log_service.log_action(
                admin_id=callback.from_user.id,
                action="VERSION_DELETED",
                entity_type="ProgramVersion",
                entity_id=version_id
            )

    if deleted:
        await callback.answer("🗑 Versiya o'chirildi!", show_alert=True)
        if callback.message:
            await callback.message.edit_text("🗑 Versiya o'chirildi.")
    else:
        await callback.answer("❌ Joriy (Current) versiyani o'chirib bo'lmaydi. Avval boshqa versiyani nashr qiling.", show_alert=True)
