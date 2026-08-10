from aiogram import Router
from app.handlers.admin import setup_admin_routers
from app.handlers.user import setup_user_routers


def setup_handlers() -> Router:
    """
    Assembles and returns the root router.
    Admin routers are registered first to prioritize admin filters,
    followed by user handlers.
    """
    root_router = Router(name="root_router")

    admin_router = setup_admin_routers()
    root_router.include_router(admin_router)

    user_router = setup_user_routers()
    root_router.include_router(user_router)

    return root_router


__all__ = ["setup_handlers"]
