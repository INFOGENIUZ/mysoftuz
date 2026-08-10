import os
import asyncio
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock

from app.config import settings
settings.DATABASE_URL = "sqlite+aiosqlite:///data/test_temp.db"

from app.core.permissions import (

    Role,
    Permission,
    get_role_permissions,
    has_permission,
)
from app.services.admin_service import AdminService
from app.middlewares.admin import AdminMiddleware
from app.filters.admin import AdminFilter
from app.keyboards.admin.reply import get_admin_main_keyboard
from app.keyboards.user.reply import get_user_main_keyboard
from app.handlers.admin import setup_admin_routers
from app.handlers.user.start import non_admin_command_rejection, non_admin_callback_rejection


class TestRBACAccessControl(unittest.TestCase):

    def test_rbac_roles_and_permissions_registry(self):
        """Verify standard roles exist and map to appropriate permissions."""
        roles = [r.value for r in Role]
        self.assertIn("user", roles)
        self.assertIn("admin", roles)
        self.assertIn("super_admin", roles)
        self.assertIn("moderator", roles)
        self.assertIn("team_owner", roles)
        self.assertIn("team_member", roles)
        self.assertIn("pro_user", roles)

        user_perms = get_role_permissions(Role.USER.value)
        self.assertIn(Permission.CATEGORIES_READ.value, user_perms)
        self.assertIn(Permission.PROGRAMS_READ.value, user_perms)
        self.assertNotIn(Permission.CATEGORIES_MANAGE.value, user_perms)

        admin_perms = get_role_permissions(Role.ADMIN.value)
        self.assertIn(Permission.CATEGORIES_MANAGE.value, admin_perms)
        self.assertIn(Permission.USERS_READ.value, admin_perms)

        super_admin_perms = get_role_permissions(Role.SUPER_ADMIN.value)
        self.assertIn(Permission.BROADCAST_SEND.value, super_admin_perms)

        self.assertTrue(has_permission(Role.SUPER_ADMIN.value, Permission.BROADCAST_SEND.value))
        self.assertFalse(has_permission(Role.ADMIN.value, Permission.BROADCAST_SEND.value))
        self.assertFalse(has_permission(Role.USER.value, Permission.CATEGORIES_MANAGE.value))
        print("[PASS] Test 1: RBAC Roles and Permissions Registry")

    def test_admin_service_role_resolution(self):
        """Verify backend role resolution logic in AdminService."""
        async def run():
            admin_service = AdminService(session=None)
            role = await admin_service.get_admin_role(8887751785)
            self.assertEqual(role, Role.SUPER_ADMIN.value)
            self.assertTrue(await admin_service.is_admin(8887751785))

            non_admin_id = 999999999
            role = await admin_service.get_admin_role(non_admin_id)
            self.assertIsNone(role)
            self.assertFalse(await admin_service.is_admin(non_admin_id))
            self.assertEqual(await admin_service.get_user_role(non_admin_id), Role.USER.value)

        asyncio.run(run())
        print("[PASS] Test 2: AdminService backend role resolution")

    def test_admin_middleware_auth_context_attachment(self):
        """Verify AdminMiddleware populates full auth_context data."""
        async def run():
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
            self.assertIn("auth_context", result)
            self.assertEqual(result["user_role"], Role.SUPER_ADMIN.value)
            self.assertTrue(result["is_admin"])
            self.assertEqual(result["auth_context"]["user_id"], 8887751785)
            self.assertIn(Permission.BROADCAST_SEND.value, result["permissions"])

        asyncio.run(run())
        print("[PASS] Test 3: AdminMiddleware auth_context population")

    def test_non_admin_403_access_rejection(self):
        """Verify non-admin users attempting admin command or callbacks receive 403 response."""
        async def run():
            mock_msg = AsyncMock()
            await non_admin_command_rejection(mock_msg)
            mock_msg.answer.assert_called_once_with("⛔ Sizda ushbu bo'limga kirish huquqi yo'q.")

            mock_cb = AsyncMock()
            await non_admin_callback_rejection(mock_cb)
            mock_cb.answer.assert_called_once_with("⛔ Sizda ushbu bo'limga kirish huquqi yo'q.", show_alert=True)

        asyncio.run(run())
        print("[PASS] Test 4: Non-admin 403 Access Rejection")

    def test_role_aware_keyboards(self):
        """Verify user and admin keyboards are generated cleanly with appropriate options."""
        user_kb = get_user_main_keyboard()
        button_texts = [b.text for row in user_kb.keyboard for b in row]
        self.assertIn("📂 Kategoriyalar", button_texts)
        self.assertIn("🔎 Qidirish", button_texts)
        self.assertNotIn("📢 Reklama", button_texts)

        mod_kb = get_admin_main_keyboard(role=Role.MODERATOR.value)
        mod_buttons = [b.text for row in mod_kb.keyboard for b in row]
        self.assertIn("📂 Kategoriyalar", mod_buttons)
        self.assertIn("💻 Dasturlar", mod_buttons)
        self.assertNotIn("📢 Reklama", mod_buttons)

        super_kb = get_admin_main_keyboard(role=Role.SUPER_ADMIN.value)
        super_buttons = [b.text for row in super_kb.keyboard for b in row]
        self.assertIn("📂 Kategoriyalar", super_buttons)
        self.assertIn("💻 Dasturlar", super_buttons)
        self.assertIn("📢 Reklama", super_buttons)
        self.assertIn("⚙️ Sozlamalar", super_buttons)
        print("[PASS] Test 5: Role-aware keyboard generation")

    def test_admin_router_guard_filters(self):
        """Verify admin_root_router rejects non-admins and accepts admins at top router level."""
        async def run():
            admin_router = setup_admin_routers()

            # Non-admin event check
            non_admin_event = MagicMock()
            non_admin_event.from_user = MagicMock()
            non_admin_event.from_user.id = 999999999
            allowed_user, _ = await admin_router.message.check_root_filters(non_admin_event)
            self.assertFalse(allowed_user)

            # Admin event check
            admin_event = MagicMock()
            admin_event.from_user = MagicMock()
            admin_event.from_user.id = 8887751785
            allowed_admin, _ = await admin_router.message.check_root_filters(admin_event)
            self.assertTrue(allowed_admin)

        asyncio.run(run())
        print("[PASS] Test 6: Admin router level guard filter")




if __name__ == "__main__":
    unittest.main()
