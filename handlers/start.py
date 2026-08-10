import logging
from aiogram import Router
from software_bot.app.handlers.user.start import router as user_start_router

logger = logging.getLogger(__name__)
router = Router(name="root_start_router")
router.include_router(user_start_router)
