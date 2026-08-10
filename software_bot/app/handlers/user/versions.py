import html
import logging
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
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

    safe_prog_name = html.escape(prog_name)
    text = f"📦 <b>{safe_prog_name.upper()} VERSIYALAR TARIXI</b> (Sahifa 1/{total_pages}):"
    kb = build_versions_history_keyboard(program_id, versions, current_page=1, total_pages=total_pages)

    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


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

    safe_prog_name = html.escape(prog_name)
    text = f"📦 <b>{safe_prog_name.upper()} VERSIYALAR TARIXI</b> (Sahifa {page}/{total_pages}):"
    kb = build_versions_history_keyboard(program_id, versions, current_page=page, total_pages=total_pages)

    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


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

        prog_name = version.program.name if version.program else "Dastur"
        prog_id = version.program_id
        ver_str = version.version
        is_curr = version.is_current
        created_at_dt = version.created_at
        ver_file_size = version.file_size
        rel_notes = version.release_notes

    badge = "🟢 Joriy Versiya" if is_curr else "⚪ Eski Versiya"
    created_str = created_at_dt.strftime("%d.%m.%Y") if created_at_dt else "Noma'lum"

    notes = rel_notes or "Kichik tuzatishlar va optimallashtirish."

    safe_prog_name = html.escape(prog_name)
    safe_ver = html.escape(ver_str or "Noma'lum")
    safe_notes = html.escape(notes.strip())

    detail_text = (
        f"📦 <b>{safe_prog_name.upper()}</b>\n"
        f"--------------------\n"
        f"🔢 <b>Versiya:</b> <code>{safe_ver}</code> ({badge})\n"
        f"📅 <b>Reliz sanasi:</b> <code>{created_str}</code>\n"
        f"💾 <b>Fayl hajmi:</b> <code>{format_size(ver_file_size)}</code>\n"
        f"--------------------\n\n"
        f"📝 <b>YANGILIKLAR & ESLATMALAR:</b>\n"
        f"{safe_notes}"
    )

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📥 Ushbu versiyani yuklab olish", callback_data=f"version:download:{version_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Versiyalar tarixi", callback_data=f"version:list:{prog_id}")
    )

    if callback.message:
        await callback.message.edit_text(detail_text, reply_markup=builder.as_markup(), parse_mode="HTML")


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

        prog_id = version.program_id
        file_id = version.file_id
        ver_str = version.version
        ver_size = version.file_size

        try:
            _, program = await dl_service.validate_downloadable_program(user_id, prog_id)
            prog_name = program.name
        except DownloadError as de:
            await callback.answer(str(de), show_alert=True)
            return

    safe_prog_name = html.escape(prog_name or "Dastur")
    safe_ver = html.escape(ver_str or "Noma'lum")

    caption = (
        f"📥 <b>{safe_prog_name}</b> (v{safe_ver})\n\n"
        f"✅ <i>Fayl yuklab olish uchun tayyor!</i>\n"
        f"▫️ <b>Versiya:</b> <code>{safe_ver}</code>\n"
        f"▫️ <b>Fayl hajmi:</b> <code>{format_size(ver_size)}</code>\n\n"
        f"🚀 <i>Bizning botimizdan foydalanganingiz uchun rahmat!</i>"
    )

    plain_caption = (
        f"📥 {prog_name} (v{ver_str})\n\n"
        f"Fayl yuklab olish uchun tayyor!\n"
        f"Versiya: {ver_str}\n"
        f"Fayl hajmi: {format_size(ver_size)}\n\n"
        f"Bizning botimizdan foydalanganingiz uchun rahmat!"
    )

    try:
        await bot.send_document(
            chat_id=user_id,
            document=file_id,
            caption=caption,
            parse_mode="HTML"
        )
        async with async_session_maker() as session:
            dl_service = DownloadService(session)
            await dl_service.record_download(user_id, prog_id, version_id=version_id)

        if callback.message:
            try:
                await callback.message.delete()
            except Exception as del_err:
                logger.warning(f"Could not delete version message: {del_err}")
    except Exception as tg_err:
        logger.error(f"Failed to send version document: {tg_err}")
        try:
            await bot.send_document(
                chat_id=user_id,
                document=file_id,
                caption=plain_caption
            )
            async with async_session_maker() as session:
                dl_service = DownloadService(session)
                await dl_service.record_download(user_id, prog_id, version_id=version_id)

            if callback.message:
                try:
                    await callback.message.delete()
                except Exception as del_err:
                    logger.warning(f"Could not delete version message: {del_err}")
        except Exception as tg_err2:
            logger.error(f"Failed to send version document fallback: {tg_err2}")
            if callback.message:
                await callback.message.answer(
                    "⚠️ Faylni yuborishda xatolik yuz berdi. Versiya fayli (file_id) yaroqsiz bo'lishi mumkin."
                )
