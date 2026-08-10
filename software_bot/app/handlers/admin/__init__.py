from aiogram import Router
from app.filters.admin import AdminFilter
from app.handlers.admin.start import router as admin_start_router
from app.handlers.admin.categories import router as admin_categories_router
from app.handlers.admin.programs import router as admin_programs_router
from app.handlers.admin.users import router as admin_users_router
from app.handlers.admin.statistics import router as admin_statistics_router
from app.handlers.admin.settings import router as admin_settings_router
from app.handlers.admin.broadcast import router as admin_broadcast_router
from app.handlers.admin.reviews import router as admin_reviews_router
from app.handlers.admin.versions import router as admin_versions_router
from app.handlers.admin.analytics import router as admin_analytics_router


def setup_admin_routers() -> Router:
    admin_root_router = Router(name="admin_root_router")
    
    # Enforce backend AdminFilter guard at the router level
    admin_root_router.message.filter(AdminFilter())
    admin_root_router.callback_query.filter(AdminFilter())

    admin_root_router.include_router(admin_start_router)
    admin_root_router.include_router(admin_categories_router)
    admin_root_router.include_router(admin_programs_router)
    admin_root_router.include_router(admin_users_router)
    admin_root_router.include_router(admin_statistics_router)
    admin_root_router.include_router(admin_settings_router)
    admin_root_router.include_router(admin_broadcast_router)
    admin_root_router.include_router(admin_reviews_router)
    admin_root_router.include_router(admin_versions_router)
    admin_root_router.include_router(admin_analytics_router)
    return admin_root_router



__all__ = [
    "setup_admin_routers",
    "admin_start_router",
    "admin_categories_router",
    "admin_programs_router",
    "admin_users_router",
    "admin_statistics_router",
    "admin_settings_router",
    "admin_broadcast_router",
    "admin_reviews_router",
    "admin_versions_router",
    "admin_analytics_router",
]
