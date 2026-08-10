from aiogram import Router
from software_bot.app.handlers.user import setup_user_routers
from software_bot.app.handlers.admin import setup_admin_routers
from handlers.common import router as common_router


def setup_routers() -> Router:
    """Sets up and combines all user and admin routers into main router."""
    main_router = Router(name="main_router")

    # Include Admin Routers first
    main_router.include_router(setup_admin_routers())

    # Include User Routers
    main_router.include_router(setup_user_routers())

    # Common router
    main_router.include_router(common_router)

    return main_router


__all__ = ["setup_routers"]
