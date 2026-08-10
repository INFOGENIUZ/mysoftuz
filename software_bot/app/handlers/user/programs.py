import logging
import asyncio
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InputMediaPhoto
from app.database.engine import async_session_maker
from app.services.program_service import ProgramService
from app.services.download_service import DownloadService
from app.services.favorite_service import FavoriteService
from app.services.recent_service import RecentService
from app.services.rating_service import RatingService
from app.keyboards.user.inline import build_program_detail_keyboard
from app.utils.callback_factory import safe_answer_callback
from app.utils.exceptions import DownloadError

logger = logging.getLogger(__name__)
router = Router(name="user_programs_router")

# Simple in-memory lock set for rate limiting download button clicks
active_downloads_locks = set()


def format_size(size_bytes: int) -> str:
    """Helper to convert bytes to human readable format (KB, MB, GB)."""
    if not size_bytes or size_bytes <= 0:
        return "Nol/Noma'lum"
    if size_bytes >= 1073741824:
        return f"{size_bytes / 1073741824:.1f} GB"
    elif size_bytes >= 1048576:
        return f"{size_bytes / 1048576:.1f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes} Bytes"


@router.callback_query(F.data.startswith("program:view:"))
async def program_view_handler(callback: CallbackQuery):
    await callback.answer()
    try:
        program_id = int(callback.data.split(":")[-1])
    except ValueError:
        await safe_answer_callback(callback, "⚠️ Noto'g'ri dastur ID")
        return

    user_id = callback.from_user.id if callback.from_user else 0

    async with async_session_maker() as session:
        prog_service = ProgramService(session)
        fav_service = FavoriteService(session)
        recent_service = RecentService(session)
        rating_service = RatingService(session)

        program = await prog_service.get_program_by_id(program_id)
        if not program or not program.is_active:
            await safe_answer_callback(callback, "⚠️ Bu dastur hozircha mavjud emas.")
            return

        # 1. Record in Recently Viewed History
        await recent_service.record_view(user_id, program_id)

        # 2. Check if favorite
        is_fav = await fav_service.is_favorite(user_id, program_id)

        # 3. Check user's own rating
        user_rating = await rating_service.get_user_rating(user_id, program_id)

    rating_avg_str = f"⭐ **{program.rating_average:.1f} / 5** ({program.rating_count:,} ta baho)"
    my_rating_str = f"⭐ Sizning bahoyingiz: **{user_rating} / 5**" if user_rating else "⭐ Siz hali baho bermagansiz."

    detail_text = (
        f"💻 **{program.name.upper()}**\n\n"
        f"📂 Kategoriya: **{program.category.name if program.category else 'Noma\'lum'}**\n"
        f"{rating_avg_str}\n"
        f"{my_rating_str}\n"
        f"📥 Yuklab olishlar: **{program.downloads_count:,} ta**\n\n"
        f"⭐ Versiya: **{program.version or 'Noma\'lum'}**\n"
        f"💻 Arxitektura: **{program.architecture or 'x64'}**\n"
        f"🖥 Tizim: **{program.system_requirements or 'Windows 10 / 11'}**\n"
        f"💾 Hajmi: **{format_size(program.file_size)}**\n\n"
        f"📝 {program.description or program.short_description or 'Tavsif mavjud emas.'}"
    )

    kb = build_program_detail_keyboard(program, is_favorite=is_fav)

    if callback.message:
        if program.image_file_id:
            try:
                await callback.message.edit_media(
                    media=InputMediaPhoto(media=program.image_file_id, caption=detail_text, parse_mode="Markdown"),
                    reply_markup=kb
                )
            except Exception:
                await callback.message.answer_photo(
                    photo=program.image_file_id, caption=detail_text, reply_markup=kb, parse_mode="Markdown"
                )
        else:
            try:
                await callback.message.edit_text(text=detail_text, reply_markup=kb, parse_mode="Markdown")
            except Exception:
                await callback.message.answer(text=detail_text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("program:download:"))
async def program_download_handler(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    try:
        program_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("⚠️ Noto'g'ri dastur ID", show_alert=True)
        return

    lock_key = (user_id, program_id)
    if lock_key in active_downloads_locks:
        await callback.answer("⏳ Iltimos, biroz kuting...", show_alert=True)
        return

    active_downloads_locks.add(lock_key)
    try:
        await callback.answer("⏳ Fayl tayyorlanmoqda...")

        async with async_session_maker() as session:
            dl_service = DownloadService(session)

            try:
                user, program = await dl_service.validate_downloadable_program(user_id, program_id)
            except DownloadError as de:
                await callback.answer(str(de), show_alert=True)
                return

            caption = (
                f"💻 **{program.name}**\n\n"
                f"⭐ Versiya: **{program.version or 'Noma\'lum'}**\n"
                f"📦 Hajmi: **{format_size(program.file_size)}**"
            )

            try:
                await bot.send_document(
                    chat_id=user_id,
                    document=program.file_id,
                    caption=caption,
                    parse_mode="Markdown"
                )
            except Exception as tg_err:
                logger.error(f"Telegram send_document failed for program_id={program_id}: {tg_err}")
                if callback.message:
                    await callback.message.answer("⚠️ Faylni yuborishda xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring.")
                return

            try:
                await dl_service.record_download(user_id, program_id)
            except Exception as db_err:
                logger.error(f"Failed to record download in DB for program_id={program_id}: {db_err}")

            if callback.message:
                try:
                    await callback.message.delete()
                except Exception as del_err:
                    logger.warning(f"Could not delete program card message: {del_err}")


    finally:
        active_downloads_locks.discard(lock_key)
