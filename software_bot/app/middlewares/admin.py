from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User, Message, CallbackQuery
from app.services.admin_service import AdminService
from app.database.engine import async_session_maker
from app.core.permissions import get_role_permissions, Role


class AdminMiddleware(BaseMiddleware):
    """
    Middleware populating authentication context, user role, and permissions in `data` dictionary.
    Rejects unauthorized access to admin handlers cleanly on the backend.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        telegram_user: User = data.get("event_from_user")
        if telegram_user:
            async with async_session_maker() as session:
                admin_service = AdminService(session)
                role = await admin_service.get_admin_role(telegram_user.id)
                effective_role = role if role else Role.USER.value
                permissions = get_role_permissions(effective_role)

                data["user_role"] = effective_role
                data["admin_role"] = role
                data["is_admin"] = role is not None and role in (Role.SUPER_ADMIN.value, Role.ADMIN.value, Role.MODERATOR.value)
                data["is_super_admin"] = role == Role.SUPER_ADMIN.value
                data["is_moderator"] = role in (Role.SUPER_ADMIN.value, Role.ADMIN.value, Role.MODERATOR.value)
                data["permissions"] = permissions
                data["auth_context"] = {
                    "user_id": telegram_user.id,
                    "name": telegram_user.full_name,
                    "username": telegram_user.username,
                    "role": effective_role,
                    "permissions": permissions,
                    "is_admin": data["is_admin"]
                }
        else:
            data["user_role"] = Role.USER.value
            data["admin_role"] = None
            data["is_admin"] = False
            data["is_super_admin"] = False
            data["is_moderator"] = False
            data["permissions"] = get_role_permissions(Role.USER.value)
            data["auth_context"] = {
                "user_id": None,
                "name": "Guest",
                "username": None,
                "role": Role.USER.value,
                "permissions": data["permissions"],
                "is_admin": False
            }

        return await handler(event, data)

