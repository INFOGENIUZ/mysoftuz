import logging
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from app.config import settings
from app.database.engine import async_session_maker
from app.services.version_service import VersionService
from app.services.program_service import ProgramService
from app.services.download_service import DownloadService
from app.keyboards.user.inline import build_versions_history_keyboard
from app.utils.callback_factory import safe_answer_callback
from app.utils.exceptions import DownloadError

logger = logging.getLogger(__name__)
router = Router(name="user_versions_router")


def format_size(size_bytes: int) -> str:
    if not size_bytes or size_bytes <= 0:
        return "Nol/Noma'lum"
    if size_bytes >= 1073741824:
        return f"{size_bytes / 1073741824:.1f} GB"
    elif size_bytes >= 1048576:
        return f"{size_bytes / 1048576:.1f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes} Bytes"


@router.callback_query(F.data.startswith("version:list:"))
async def user_version_list_handler(callback: CallbackQuery):
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
    if not versions:
        await safe_answer_callback(callback, "📦 Bu dastur uchun versiyalar tarixi mavjud emas.")
        return

    text = f"📦 **{prog_name.upper()} VERSIYALAR TARIXI** (Sahifa 1/{total_pages}):"
    kb = build_versions_history_keyboard(program_id, versions, current_page=1, total_pages=total_pages)

    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("version:page:"))
async def user_version_page_handler(callback: CallbackQuery):
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
        version_service = VersionService(session)
        prog_service = ProgramService(session)

        program = await prog_service.get_program_by_id(program_id)
        versions, total_pages = await version_service.get_version_history_paginated(program_id, page=page, page_size=10)

    prog_name = program.name if program else "Dastur"
    text = f"📦 **{prog_name.upper()} VERSIYALAR TARIXI** (Sahifa {page}/{total_pages}):"
    kb = build_versions_history_keyboard(program_id, versions, current_page=page, total_pages=total_pages)

    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("version:view:"))
async def user_version_detail_handler(callback: CallbackQuery):
    await callback.answer()
    try:
        version_id = int(callback.data.split(":")[-1])
    except ValueError:
        return

    async with async_session_maker() as session:
        version_service = VersionService(session)
        version = await version_service.get_version_by_id(version_id)

    if not version:
        await safe_answer_callback(callback, "⚠️ Versiya topilmadi")
        return

    badge = "🟢 Joriy (Current) Versiya" if version.is_current else "⚪ Eski Versiya"
    created_str = version.created_at.strftime("%d.%m.%Y") if version.created_at else "Noma'lum"

    detail_text = (
        f"📦 **{version.program.name.upper()}**\n\n"
        f"🔢 Versiya: **{version.version}** ({badge})\n"
        f"📅 Reliz sanasi: **{created_str}**\n"
        f"💾 Hajm: **{format_size(version.file_size)}**\n\n"
        f"📝 **Yangiliklar & Reliz eslatmalari:**\n"
        f"{version.release_notes or 'Kichik tuzatishlar va optimallashtirish.'}"
    )

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📥 Ushbu versiyani yuklab olish", callback_data=f"version:download:{version.id}")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Versiyalar tarixi", callback_data=f"version:list:{version.program_id}")
    )

    if callback.message:
        await callback.message.edit_text(detail_text, reply_markup=builder.as_markup(), parse_mode="Markdown")


@router.callback_query(F.data.startswith("version:download:"))
async def user_version_download_handler(callback: CallbackQuery, bot: Bot):
    if not callback.from_user:
        return
    user_id = callback.from_user.id

    try:
        version_id = int(callback.data.split(":")[-1])
    except ValueError:
        return

    await callback.answer("⏳ Versiya fayli tayyorlanmoqda...")

    async with async_session_maker() as session:
        version_service = VersionService(session)
        dl_service = DownloadService(session)

        version = await version_service.get_version_by_id(version_id)
        if not version or not version.program:
            await callback.answer("⚠️ Versiya topilmadi", show_alert=True)
            return

        try:
            _, program = await dl_service.validate_downloadable_program(user_id, version.program_id)
        except DownloadError as de:
            await callback.answer(str(de), show_alert=True)
            return

        caption = (
            f"💻 **{program.name}**\n\n"
            f"🔢 Versiya: **{version.version}**\n"
            f"📦 Hajmi: **{format_size(version.file_size)}**"
        )

        try:
            await bot.send_document(
                chat_id=user_id,
                document=version.file_id,
                caption=caption,
                parse_mode="Markdown"
            )
            # Record download transaction
            await dl_service.record_download(user_id, program.id, version_id=version.id)
            if callback.message:
                try:
                    await callback.message.delete()
                except Exception as del_err:
                    logger.warning(f"Could not delete version message: {del_err}")
        except Exception as tg_err:
            logger.error(f"Failed to send version document: {tg_err}")
            if callback.message:
                await callback.message.answer("⚠️ Faylni yuborishda xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring.")

