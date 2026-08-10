"""
Centralized Role-Based Access Control (RBAC) Permissions Registry.

Defines supported system roles, granular permission constants, and
role-to-permission mappings for server-side authorization.
"""
from enum import Enum
from typing import Set, Dict, Optional, List


class Role(str, Enum):
    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"
    MODERATOR = "moderator"
    TEAM_OWNER = "team_owner"
    TEAM_MEMBER = "team_member"
    PRO_USER = "pro_user"


class Permission(str, Enum):
    # User permissions
    CATEGORIES_READ = "categories.read"
    PROGRAMS_READ = "programs.read"
    PROFILE_MANAGE = "profile.manage"
    FAVORITES_MANAGE = "favorites.manage"
    DOWNLOADS_READ = "downloads.read"

    # Admin / Management permissions
    CATEGORIES_MANAGE = "categories.manage"
    PROGRAMS_MANAGE = "programs.manage"
    USERS_READ = "users.read"
    USERS_MANAGE = "users.manage"
    STATISTICS_READ = "statistics.read"
    ANALYTICS_READ = "analytics.read"
    LOGS_READ = "logs.read"
    SETTINGS_MANAGE = "settings.manage"
    BROADCAST_SEND = "broadcast.send"
    ADMINS_MANAGE = "admins.manage"


# Role to Permissions Mapping
ROLE_PERMISSIONS_MAP: Dict[str, Set[str]] = {
    Role.USER.value: {
        Permission.CATEGORIES_READ.value,
        Permission.PROGRAMS_READ.value,
        Permission.PROFILE_MANAGE.value,
        Permission.FAVORITES_MANAGE.value,
        Permission.DOWNLOADS_READ.value,
    },
    Role.PRO_USER.value: {
        Permission.CATEGORIES_READ.value,
        Permission.PROGRAMS_READ.value,
        Permission.PROFILE_MANAGE.value,
        Permission.FAVORITES_MANAGE.value,
        Permission.DOWNLOADS_READ.value,
    },
    Role.TEAM_MEMBER.value: {
        Permission.CATEGORIES_READ.value,
        Permission.PROGRAMS_READ.value,
        Permission.PROFILE_MANAGE.value,
        Permission.FAVORITES_MANAGE.value,
        Permission.DOWNLOADS_READ.value,
    },
    Role.TEAM_OWNER.value: {
        Permission.CATEGORIES_READ.value,
        Permission.PROGRAMS_READ.value,
        Permission.PROFILE_MANAGE.value,
        Permission.FAVORITES_MANAGE.value,
        Permission.DOWNLOADS_READ.value,
    },
    Role.MODERATOR.value: {
        Permission.CATEGORIES_READ.value,
        Permission.PROGRAMS_READ.value,
        Permission.PROFILE_MANAGE.value,
        Permission.FAVORITES_MANAGE.value,
        Permission.DOWNLOADS_READ.value,
        Permission.CATEGORIES_MANAGE.value,
        Permission.PROGRAMS_MANAGE.value,
        Permission.STATISTICS_READ.value,
    },
    Role.ADMIN.value: {
        Permission.CATEGORIES_READ.value,
        Permission.PROGRAMS_READ.value,
        Permission.PROFILE_MANAGE.value,
        Permission.FAVORITES_MANAGE.value,
        Permission.DOWNLOADS_READ.value,
        Permission.CATEGORIES_MANAGE.value,
        Permission.PROGRAMS_MANAGE.value,
        Permission.USERS_READ.value,
        Permission.USERS_MANAGE.value,
        Permission.STATISTICS_READ.value,
        Permission.ANALYTICS_READ.value,
        Permission.LOGS_READ.value,
    },
    Role.SUPER_ADMIN.value: {
        Permission.CATEGORIES_READ.value,
        Permission.PROGRAMS_READ.value,
        Permission.PROFILE_MANAGE.value,
        Permission.FAVORITES_MANAGE.value,
        Permission.DOWNLOADS_READ.value,
        Permission.CATEGORIES_MANAGE.value,
        Permission.PROGRAMS_MANAGE.value,
        Permission.USERS_READ.value,
        Permission.USERS_MANAGE.value,
        Permission.STATISTICS_READ.value,
        Permission.ANALYTICS_READ.value,
        Permission.LOGS_READ.value,
        Permission.SETTINGS_MANAGE.value,
        Permission.BROADCAST_SEND.value,
        Permission.ADMINS_MANAGE.value,
    },
}


def get_role_permissions(role: Optional[str]) -> Set[str]:
    """Returns the set of permission strings associated with a given role."""
    if not role:
        return set()
    role_key = str(role).lower()
    return ROLE_PERMISSIONS_MAP.get(role_key, set())


def has_permission(role: Optional[str], permission: str) -> bool:
    """Checks if a given role possesses a specific permission."""
    if not role or not permission:
        return False
    user_perms = get_role_permissions(role)
    return permission in user_perms
