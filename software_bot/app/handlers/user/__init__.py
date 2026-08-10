from aiogram import Router
from app.handlers.user.start import router as user_start_router
from app.handlers.user.categories import router as user_categories_router
from app.handlers.user.programs import router as user_programs_router
from app.handlers.user.popular import router as user_popular_router
from app.handlers.user.new_programs import router as user_new_programs_router
from app.handlers.user.downloads import router as user_downloads_router
from app.handlers.user.favorites import router as user_favorites_router
from app.handlers.user.recent import router as user_recent_router
from app.handlers.user.reviews import router as user_reviews_router
from app.handlers.user.versions import router as user_versions_router
from app.handlers.user.notifications import router as user_notifications_router
from app.handlers.user.profile import router as user_profile_router
from app.handlers.user.search import router as user_search_router
from app.handlers.user.about import router as user_about_router
from app.handlers.user.navigation import router as user_navigation_router
from app.handlers.user.monetization import router as user_monetization_router


def setup_user_routers() -> Router:
    user_root_router = Router(name="user_root_router")
    user_root_router.include_router(user_start_router)
    user_root_router.include_router(user_categories_router)
    user_root_router.include_router(user_programs_router)
    user_root_router.include_router(user_popular_router)
    user_root_router.include_router(user_new_programs_router)
    user_root_router.include_router(user_downloads_router)
    user_root_router.include_router(user_favorites_router)
    user_root_router.include_router(user_recent_router)
    user_root_router.include_router(user_reviews_router)
    user_root_router.include_router(user_versions_router)
    user_root_router.include_router(user_notifications_router)
    user_root_router.include_router(user_profile_router)
    user_root_router.include_router(user_search_router)
    user_root_router.include_router(user_about_router)
    user_root_router.include_router(user_navigation_router)
    user_root_router.include_router(user_monetization_router)
    return user_root_router


__all__ = [
    "setup_user_routers",
    "user_start_router",
    "user_categories_router",
    "user_programs_router",
    "user_popular_router",
    "user_new_programs_router",
    "user_downloads_router",
    "user_favorites_router",
    "user_recent_router",
    "user_reviews_router",
    "user_versions_router",
    "user_notifications_router",
    "user_profile_router",
    "user_search_router",
    "user_about_router",
    "user_navigation_router",
    "user_monetization_router",
]
