import html
import logging
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InputMediaPhoto
from app.database.engine import async_session_maker
from app.services.program_service import ProgramService
from app.services.favorite_service import FavoriteService
from app.services.recent_service import RecentService
from app.services.rating_service import RatingService
from app.services.download_service import DownloadService
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
async def program_view_handler(callback: CallbackQuery, state=None):
    await callback.answer()
    try:
        program_id = int(callback.data.split(":")[-1])
    except ValueError:
        await safe_answer_callback(callback, "Noto'g'ri dastur ID")
        return

    user_id = callback.from_user.id if callback.from_user else 0

    async with async_session_maker() as session:
        prog_service = ProgramService(session)
        fav_service = FavoriteService(session)
        recent_service = RecentService(session)
        rating_service = RatingService(session)

        program = await prog_service.get_program_by_id(program_id)
        if not program or not program.is_active:
            await safe_answer_callback(callback, "Bu dastur hozircha mavjud emas.")
            return

        # 1. Record in Recently Viewed History
        try:
            await recent_service.record_view(user_id, program_id)
        except Exception as e:
            logger.error(f"Failed to record view history: {e}")

        # 2. Check if favorite
        is_fav = await fav_service.is_favorite(user_id, program_id)

        # 3. Check user's own rating
        user_rating = await rating_service.get_user_rating(user_id, program_id)

        # Extract values inside session block to avoid DetachedInstanceError
        prog_name = program.name or "Dastur"
        cat_name = program.category.name if program.category else "Noma'lum"
        prog_version = program.version or "Noma'lum"
        prog_arch = program.architecture or "x64"
        prog_sys_req = program.system_requirements or "Windows 10 / 11"
        prog_size = format_size(program.file_size)
        prog_rating_avg = program.rating_average
        prog_rating_cnt = program.rating_count
        prog_downloads = program.downloads_count
        desc_text = program.description or program.short_description or "Tavsif mavjud emas."
        image_file_id = program.image_file_id

        # Build inline keyboard inside session block
        kb = build_program_detail_keyboard(program, is_favorite=is_fav)

    # Escape HTML to prevent Telegram parsing exceptions
    safe_name = html.escape(prog_name)
    safe_cat = html.escape(cat_name)
    safe_ver = html.escape(prog_version)
    safe_arch = html.escape(prog_arch)
    safe_sys = html.escape(prog_sys_req)
    safe_desc = html.escape(desc_text.strip())

    rating_avg_str = f"<b>{prog_rating_avg:.1f} / 5</b> <i>({prog_rating_cnt:,} ta baho)</i>"
    my_rating_str = f"<b>{user_rating} / 5</b>" if user_rating else "<i>Hali baholanmagan</i>"
    downloads_str = f"<b>{prog_downloads:,} marta</b>"

    detail_text = (
        f"<b>{safe_name.upper()}</b>\n"
        f"--------------------\n"
        f"<b>Kategoriya:</b> <code>{safe_cat}</code>\n"
        f"<b>Reyting:</b> {rating_avg_str}\n"
        f"<b>Sizning bahoyingiz:</b> {my_rating_str}\n"
        f"<b>Yuklab olishlar:</b> {downloads_str}\n\n"
        f"<b>TEXNIK XUSUSIYATLARI:</b>\n"
        f"<b>Versiya:</b> <code>{safe_ver}</code>\n"
        f"<b>Arxitektura:</b> <code>{safe_arch}</code>\n"
        f"<b>Tizim talabi:</b> <code>{safe_sys}</code>\n"
        f"<b>Fayl hajmi:</b> <code>{prog_size}</code>\n"
        f"--------------------\n\n"
        f"<b>TAVSIF:</b>\n{safe_desc}"
    )

    if callback.message:
        sent = False
        if image_file_id:
            try:
                await callback.message.edit_media(
                    media=InputMediaPhoto(media=image_file_id, caption=detail_text, parse_mode="HTML"),
                    reply_markup=kb
                )
                sent = True
            except Exception as e1:
                logger.debug(f"edit_media photo failed: {e1}")
                try:
                    await callback.message.answer_photo(
                        photo=image_file_id, caption=detail_text, reply_markup=kb, parse_mode="HTML"
                    )
                    sent = True
                except Exception as e2:
                    logger.debug(f"answer_photo failed: {e2}")

        if not sent:
            try:
                await callback.message.edit_text(text=detail_text, reply_markup=kb, parse_mode="HTML")
            except Exception as e3:
                logger.debug(f"edit_text HTML failed: {e3}")
                try:
                    await callback.message.edit_text(text=detail_text, reply_markup=kb)
                except Exception as e4:
                    logger.debug(f"edit_text plain failed: {e4}")
                    try:
                        await callback.message.answer(text=detail_text, reply_markup=kb)
                    except Exception as e5:
                        logger.error(f"All message sending attempts failed: {e5}")


@router.callback_query(F.data.startswith("program:download:"))
async def program_download_handler(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    try:
        program_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("Noto'g'ri dastur ID", show_alert=True)
        return

    lock_key = (user_id, program_id)
    if lock_key in active_downloads_locks:
        await callback.answer("Iltimos, biroz kuting...", show_alert=True)
        return

    active_downloads_locks.add(lock_key)
    try:
        await callback.answer("Fayl tayyorlanmoqda...")

        async with async_session_maker() as session:
            dl_service = DownloadService(session)

            try:
                user, program = await dl_service.validate_downloadable_program(user_id, program_id)
            except DownloadError as de:
                await callback.answer(str(de), show_alert=True)
                return

            safe_prog_name = html.escape(program.name or "Dastur")
            safe_prog_ver = html.escape(program.version or "Noma'lum")
            file_id = program.file_id
            prog_file_size = format_size(program.file_size)

            caption = (
                f"<b>{safe_prog_name}</b>\n\n"
                f"<i>Fayl yuklab olish uchun tayyor!</i>\n"
                f"<b>Versiya:</b> <code>{safe_prog_ver}</code>\n"
                f"<b>Fayl hajmi:</b> <code>{prog_file_size}</code>\n\n"
                f"<i>Bizning botimizdan foydalanganingiz uchun rahmat!</i>"
            )

            try:
                await bot.send_document(
                    chat_id=user_id,
                    document=file_id,
                    caption=caption,
                    parse_mode="HTML"
                )
            except Exception as tg_err:
                logger.error(f"Telegram send_document failed for program_id={program_id}: {tg_err}")
                plain_caption = (
                    f"{program.name}\n\n"
                    f"Fayl yuklab olish uchun tayyor!\n"
                    f"Versiya: {program.version or 'Noma\'lum'}\n"
                    f"Fayl hajmi: {prog_file_size}\n\n"
                    f"Bizning botimizdan foydalanganingiz uchun rahmat!"
                )
                try:
                    await bot.send_document(
                        chat_id=user_id,
                        document=file_id,
                        caption=plain_caption
                    )
                except Exception as tg_err2:
                    logger.error(f"Telegram send_document fallback failed for program_id={program_id}: {tg_err2}")
                    if callback.message:
                        await callback.message.answer(
                            "Faylni yuborishda xatolik yuz berdi.\n\n"
                            "Ehtimol, dastur fayli (file_id) yaroqsiz bo'lishi mumkin yoki fayl Telegram API cheklovidan katta."
                        )
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
