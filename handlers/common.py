import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from software_bot.app.keyboards.user.reply import get_user_main_keyboard

logger = logging.getLogger(__name__)
router = Router(name="root_common_router")


@router.callback_query(F.data == "back:main")
async def back_to_main_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    await callback.answer()
    text = "🏠 **BOSH MENYU**\n\nKerakli bo'limni tanlang:"
    if callback.message:
        await callback.message.answer(text, reply_markup=get_user_main_keyboard(), parse_mode="Markdown")
