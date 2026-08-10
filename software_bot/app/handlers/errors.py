import logging
from aiogram import Router
from aiogram.types import ErrorEvent, Message, CallbackQuery
from app.core.errors import generate_error_id, get_user_friendly_error_message
from app.utils.callback_factory import safe_answer_callback

logger = logging.getLogger(__name__)
router = Router(name="global_errors_router")


@router.error()
async def global_error_handler(event: ErrorEvent, is_admin: bool = False):
    """
    Global unhandled exception handler.
    Generates a unique Error ID, logs full details securely,
    and returns a sanitized user/admin message.
    """
    error_id = generate_error_id()
    exc = event.exception
    update = event.update
    user_id = None
    if update.message and update.message.from_user:
        user_id = update.message.from_user.id
    elif update.callback_query and update.callback_query.from_user:
        user_id = update.callback_query.from_user.id

    logger.error(
        f"UnhandledException [{error_id}] | User: {user_id} | Exception: {type(exc).__name__}: {exc}",
        exc_info=exc
    )


    # Determine user/admin response
    safe_msg = get_user_friendly_error_message(is_admin=is_admin, error_id=error_id)

    if update.message:
        try:
            await update.message.answer(safe_msg, parse_mode="Markdown")
        except Exception:
            pass
    elif update.callback_query:
        try:
            await update.callback_query.answer("⚠️ Xatolik yuz berdi.", show_alert=True)
            if update.callback_query.message:
                await update.callback_query.message.answer(safe_msg, parse_mode="Markdown")
        except Exception:
            pass

    return True
