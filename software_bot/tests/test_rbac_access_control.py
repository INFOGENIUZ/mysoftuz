"""
Comprehensive Automated Test Suite for Role-Based Access Control (RBAC),
Role-Aware Navigation, Backend Authorization, and Route Protection.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.permissions import (
    Role,
    Permission,
    ROLE_PERMISSIONS_MAP,
    get_role_permissions,
    has_permission,
)
from app.services.admin_service import AdminService
from app.middlewares.admin import AdminMiddleware
from app.filters.admin import AdminFilter, SuperAdminFilter, ModeratorFilter, PermissionFilter
from app.keyboards.admin.reply import get_admin_main_keyboard
from app.keyboards.user.reply import get_user_main_keyboard
from app.handlers.admin import setup_admin_routers
from app.handlers.user.start import non_admin_command_rejection, non_admin_callback_rejection


@pytest.mark.asyncio
async def test_rbac_roles_and_permissions_registry():
    """Verify standard roles exist and map to appropriate permissions."""
    # Verify supported roles
    roles = [r.value for r in Role]
    assert "user" in roles
    assert "admin" in roles
    assert "super_admin" in roles
    assert "moderator" in roles
    assert "team_owner" in roles
    assert "team_member" in roles
    assert "pro_user" in roles

    # Verify user role permissions
    user_perms = get_role_permissions(Role.USER.value)
    assert Permission.CATEGORIES_READ.value in user_perms
    assert Permission.PROGRAMS_READ.value in user_perms
    assert Permission.CATEGORIES_MANAGE.value not in user_perms
    assert Permission.BROADCAST_SEND.value not in user_perms

    # Verify admin role permissions
    admin_perms = get_role_permissions(Role.ADMIN.value)
    assert Permission.CATEGORIES_MANAGE.value in admin_perms
    assert Permission.USERS_READ.value in admin_perms
    assert Permission.BROADCAST_SEND.value not in admin_perms

    # Verify super_admin role permissions
    super_admin_perms = get_role_permissions(Role.SUPER_ADMIN.value)
    assert Permission.BROADCAST_SEND.value in super_admin_perms
    assert Permission.SETTINGS_MANAGE.value in super_admin_perms

    # Verify helper function has_permission
    assert has_permission(Role.SUPER_ADMIN.value, Permission.BROADCAST_SEND.value) is True
    assert has_permission(Role.ADMIN.value, Permission.BROADCAST_SEND.value) is False
    assert has_permission(Role.USER.value, Permission.CATEGORIES_MANAGE.value) is False


@pytest.mark.asyncio
async def test_admin_service_role_resolution():
    """Verify backend role resolution logic in AdminService."""
    admin_service = AdminService(session=None)
    
    # Test configured env admin
    role = await admin_service.get_admin_role(8887751785)
    assert role == Role.SUPER_ADMIN.value
    assert await admin_service.is_admin(8887751785) is True
    assert await admin_service.is_super_admin(8887751785) is True

    # Test non-admin user
    non_admin_id = 999999999
    role = await admin_service.get_admin_role(non_admin_id)
    assert role is None
    assert await admin_service.is_admin(non_admin_id) is False
    assert await admin_service.get_user_role(non_admin_id) == Role.USER.value


@pytest.mark.asyncio
async def test_admin_middleware_auth_context_attachment():
    """Verify AdminMiddleware populates full auth_context data."""
    middleware = AdminMiddleware()

    mock_event = MagicMock()
    mock_user = MagicMock()
    mock_user.id = 8887751785
    mock_user.full_name = "Test Admin"
    mock_user.username = "testadmin"

    data = {"event_from_user": mock_user}

    async def dummy_handler(event, data):
        return data

    result = await middleware(dummy_handler, mock_event, data)
    assert "auth_context" in result
    assert result["user_role"] == Role.SUPER_ADMIN.value
    assert result["is_admin"] is True
    assert result["auth_context"]["user_id"] == 8887751785
    assert Permission.BROADCAST_SEND.value in result["permissions"]


@pytest.mark.asyncio
async def test_non_admin_403_access_rejection():
    """Verify non-admin users attempting admin command or callbacks receive 403 response."""
    mock_msg = AsyncMock()
    await non_admin_command_rejection(mock_msg)
    mock_msg.answer.assert_called_once_with("⛔ Sizda ushbu bo'limga kirish huquqi yo'q.")

    mock_cb = AsyncMock()
    await non_admin_callback_rejection(mock_cb)
    mock_cb.answer.assert_called_once_with("⛔ Sizda ushbu bo'limga kirish huquqi yo'q.", show_alert=True)


@pytest.mark.asyncio
async def test_role_aware_keyboards():
    """Verify user and admin keyboards are generated cleanly with appropriate options."""
    # User menu
    user_kb = get_user_main_keyboard()
    button_texts = [b.text for row in user_kb.keyboard for b in row]
    assert "📂 Kategoriyalar" in button_texts
    assert "🔎 Qidirish" in button_texts
    assert "💻 Dasturlar" not in button_texts
    assert "📢 Reklama" not in button_texts

    # Moderator admin menu
    mod_kb = get_admin_main_keyboard(role=Role.MODERATOR.value)
    mod_buttons = [b.text for row in mod_kb.keyboard for b in row]
    assert "📂 Kategoriyalar" in mod_buttons
    assert "💻 Dasturlar" in mod_buttons
    assert "📢 Reklama" not in mod_buttons

    # Super admin menu
    super_kb = get_admin_main_keyboard(role=Role.SUPER_ADMIN.value)
    super_buttons = [b.text for row in super_kb.keyboard for b in row]
    assert "📂 Kategoriyalar" in super_buttons
    assert "💻 Dasturlar" in super_buttons
    assert "📢 Reklama" in super_buttons
    assert "⚙️ Sozlamalar" in super_buttons


@pytest.mark.asyncio
async def test_admin_router_guard_filters():
    """Verify admin_root_router has AdminFilter attached at top level."""
    admin_router = setup_admin_routers()
    assert len(admin_router.message.filters) > 0
    assert any(isinstance(f.callback, AdminFilter) for f in admin_router.message.filters)
