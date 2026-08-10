from typing import Optional, Dict, List, Set
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database.models.admin import Admin
from app.core.permissions import get_role_permissions, has_permission as check_permission, Role


# Legacy alias mapping for backward compatibility
ROLE_PERMISSIONS: Dict[str, List[str]] = {
    "super_admin": ["categories", "programs", "users", "admins", "statistics", "settings", "broadcast"],
    "admin": ["categories", "programs", "statistics", "users"],
    "moderator": ["categories", "programs"],
}


class AdminService:
    def __init__(self, session: Optional[AsyncSession] = None):
        self.session = session

    async def get_admin_role(self, telegram_id: int) -> Optional[str]:
        """
        Determines user role from backend storage.
        Priority:
        1. Database `admins` table record if present and is_active=True.
        2. Environment `settings.ADMIN_IDS` (defaults to 'super_admin').
        3. Returns None for standard non-admin users.
        """
        if self.session:
            stmt = select(Admin).where(Admin.telegram_id == telegram_id, Admin.is_active == True)
            res = await self.session.execute(stmt)
            admin = res.scalar_one_or_none()
            if admin:
                return admin.role

        if telegram_id in settings.ADMIN_IDS:
            return Role.SUPER_ADMIN.value

        return None

    async def get_user_role(self, telegram_id: int) -> str:
        """Returns effective user role (defaulting to 'user' if not admin)."""
        role = await self.get_admin_role(telegram_id)
        return role if role else Role.USER.value

    async def is_admin(self, telegram_id: int) -> bool:
        """Checks if Telegram user is any type of admin (super_admin, admin, moderator)."""
        role = await self.get_admin_role(telegram_id)
        return role is not None and role in (Role.SUPER_ADMIN.value, Role.ADMIN.value, Role.MODERATOR.value)

    async def is_super_admin(self, telegram_id: int) -> bool:
        """Checks if Telegram user is super_admin."""
        role = await self.get_admin_role(telegram_id)
        return role == Role.SUPER_ADMIN.value

    async def is_moderator(self, telegram_id: int) -> bool:
        """Checks if Telegram user is moderator or higher."""
        role = await self.get_admin_role(telegram_id)
        return role in (Role.SUPER_ADMIN.value, Role.ADMIN.value, Role.MODERATOR.value)

    async def has_permission(self, telegram_id: int, permission: str) -> bool:
        """Checks if admin has specific feature permission (supports fine-grained and legacy permission strings)."""
        role = await self.get_admin_role(telegram_id)
        if not role:
            return False
        
        # Check fine-grained RBAC permission
        if check_permission(role, permission):
            return True

        # Fallback for legacy permission tokens
        allowed_legacy = ROLE_PERMISSIONS.get(role, [])
        return permission in allowed_legacy

    async def get_permissions_set(self, telegram_id: int) -> Set[str]:
        """Returns set of all granted permissions for user's role."""
        role = await self.get_user_role(telegram_id)
        return get_role_permissions(role)

