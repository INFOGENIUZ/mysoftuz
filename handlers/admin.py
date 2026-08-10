import logging
from aiogram import Router
from software_bot.app.handlers.admin import setup_admin_routers

logger = logging.getLogger(__name__)
router = Router(name="root_admin_router")
router.include_router(setup_admin_routers())
