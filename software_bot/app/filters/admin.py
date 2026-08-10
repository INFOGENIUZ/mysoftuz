from typing import Union, Optional, Dict, Any
from aiogram.filters import Filter
from aiogram.types import Message, CallbackQuery
from app.services.admin_service import AdminService
from app.database.engine import async_session_maker
from app.core.permissions import has_permission as check_permission


class AdminFilter(Filter):
    """Filter matching any admin user (super_admin, admin, moderator)."""

    async def __call__(self, event: Union[Message, CallbackQuery], **data: Dict[str, Any]) -> bool:
        if "is_admin" in data:
            return bool(data["is_admin"])

        if not event.from_user:
            return False
        async with async_session_maker() as session:
            admin_service = AdminService(session)
            return await admin_service.is_admin(event.from_user.id)


class SuperAdminFilter(Filter):
    """Filter matching only super_admin users."""

    async def __call__(self, event: Union[Message, CallbackQuery], **data: Dict[str, Any]) -> bool:
        if "is_super_admin" in data:
            return bool(data["is_super_admin"])

        if not event.from_user:
            return False
        async with async_session_maker() as session:
            admin_service = AdminService(session)
            return await admin_service.is_super_admin(event.from_user.id)


class ModeratorFilter(Filter):
    """Filter matching moderators or higher roles."""

    async def __call__(self, event: Union[Message, CallbackQuery], **data: Dict[str, Any]) -> bool:
        if "is_moderator" in data:
            return bool(data["is_moderator"])

        if not event.from_user:
            return False
        async with async_session_maker() as session:
            admin_service = AdminService(session)
            return await admin_service.is_moderator(event.from_user.id)


class PermissionFilter(Filter):
    """Filter matching users possessing a specific permission."""

    def __init__(self, permission: str):
        self.permission = permission

    async def __call__(self, event: Union[Message, CallbackQuery], **data: Dict[str, Any]) -> bool:
        if "permissions" in data:
            return self.permission in data["permissions"]

        if not event.from_user:
            return False
        async with async_session_maker() as session:
            admin_service = AdminService(session)
            return await admin_service.has_permission(event.from_user.id, self.permission)


# Backward compatibility alias
IsAdminFilter = AdminFilter

