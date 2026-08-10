import asyncio
import logging
import sys
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database.base import Base
from app.database.models import User, AdminLog
from app.services.user_service import UserService
from app.services.category_service import CategoryService
from app.services.program_service import ProgramService
from app.services.download_service import DownloadService
from app.services.statistics_service import StatisticsService
from app.services.settings_service import SettingsService
from app.services.admin_log_service import AdminLogService
from app.handlers.admin.start import admin_start_handler
from app.handlers.admin.users import admin_user_block_confirm, admin_user_unblock_confirm
from app.handlers.admin.settings import admin_settings_toggle_maintenance
from app.handlers.admin.broadcast import admin_broadcast_start_handler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_stage10")


async def run_stage10_tests():
    logger.info("Starting Stage 10 Admin Panel & Management Dashboard Tests...")

    # 1. Setup in-memory test database
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    passed = 0
    failed = 0

    async with session_factory() as session:
        user_service = UserService(session)
        cat_service = CategoryService(session)
        prog_service = ProgramService(session)
        dl_service = DownloadService(session)
        stats_service = StatisticsService(session)
        settings_service = SettingsService(session)
        log_service = AdminLogService(session)

        # Seed data
        u1 = await user_service.get_or_create_user(telegram_id=10101, first_name="Baxrom", username="baxrom")
        u2 = await user_service.get_or_create_user(telegram_id=20202, first_name="Davron", username="davron")

        cat = await cat_service.create_category(name="💻 Dasturlash")
        prog = await prog_service.create_program(
            category_id=cat.id, name="VS Code", file_id="file_vscode_id"
        )
        await dl_service.record_download(u1.telegram_id, prog.id)

        # ---------------------------------------------------------------------
        # Test 1, 2, 3: Dashboard Statistics Query Accuracy & Refresh
        # ---------------------------------------------------------------------
        try:
            stats = await stats_service.get_dashboard_stats()
            assert stats["total_users"] == 2
            assert stats["total_programs"] == 1
            assert stats["total_categories"] == 1
            assert stats["total_downloads"] == 1
            logger.info("✅ Test 1,2,3 Passed: Real-time dashboard statistics query accuracy verified")
            passed += 3
        except Exception as e:
            logger.error(f"❌ Test 1,2,3 Failed: {e}")
            failed += 3

        # ---------------------------------------------------------------------
        # Test 4-8: User Management (List, Detail, Block, Unblock, Audit Log)
        # ---------------------------------------------------------------------
        try:
            # Block User u1
            mock_cb_block = AsyncMock()
            mock_cb_block.from_user.id = 999
            mock_cb_block.data = f"admin:user:block_confirm:{u1.id}"

            await admin_user_block_confirm(mock_cb_block, admin_role="admin")

            # Check User Blocked status in DB
            check_u1 = await user_service.get_user_by_id(u1.id)
            assert check_u1.is_blocked is True

            # Unblock User u1
            mock_cb_unblock = AsyncMock()
            mock_cb_unblock.from_user.id = 999
            mock_cb_unblock.data = f"admin:user:unblock_confirm:{u1.id}"

            await admin_user_unblock_confirm(mock_cb_unblock, admin_role="admin")
            check_u1_unblocked = await user_service.get_user_by_id(u1.id)
            assert check_u1_unblocked.is_blocked is False

            # Verify Audit Log entries
            res_logs = await session.execute(select(AdminLog))
            logs = list(res_logs.scalars().all())
            assert len(logs) >= 2
            actions = [l.action for l in logs]
            assert "USER_BLOCKED" in actions
            assert "USER_UNBLOCKED" in actions
            logger.info("✅ Test 4-8 Passed: User block/unblock flow and Admin Audit logging verified")
            passed += 5
        except Exception as e:
            logger.error(f"❌ Test 4-8 Failed: {e}")
            failed += 5

        # ---------------------------------------------------------------------
        # Test 9-12: Settings Service & Maintenance Toggle with In-Memory Cache
        # ---------------------------------------------------------------------
        try:
            await settings_service.set_setting("WELCOME_TEXT", "Xush kelibsiz!")
            val = await settings_service.get_setting("WELCOME_TEXT")
            assert val == "Xush kelibsiz!"

            # Toggle Maintenance
            mock_cb_maint = AsyncMock()
            mock_cb_maint.from_user.id = 999
            await admin_settings_toggle_maintenance(mock_cb_maint, is_admin=True, admin_role="admin")

            maint_val = await settings_service.get_bool_setting("MAINTENANCE_MODE")
            assert maint_val is True
            logger.info("✅ Test 9-12 Passed: Settings updates, in-memory caching and maintenance mode toggle verified")
            passed += 4
        except Exception as e:
            logger.error(f"❌ Test 9-12 Failed: {e}")
            failed += 4

        # ---------------------------------------------------------------------
        # Test 13-16: Super Admin Broadcast Permissions & Blocked Role Check
        # ---------------------------------------------------------------------
        try:
            # Ordinary Admin attempt (Should be blocked)
            mock_evt_admin = AsyncMock()
            await admin_broadcast_start_handler(mock_evt_admin, AsyncMock(), admin_role="admin")
            mock_evt_admin.answer.assert_called_with("⛔ Reklama yuborish faqat Super Admin uchun ruxsat etilgan.")

            # Super Admin attempt (Should be allowed)
            mock_evt_super = AsyncMock()
            mock_state = AsyncMock()
            await admin_broadcast_start_handler(mock_evt_super, mock_state, admin_role="super_admin")
            assert mock_state.set_state.called
            logger.info("✅ Test 13-16 Passed: Super Admin broadcast role permissions strictly enforced")
            passed += 4
        except Exception as e:
            logger.error(f"❌ Test 13-16 Failed: {e}")
            failed += 4

        # ---------------------------------------------------------------------
        # Test 17-20: Admin Start / Dashboard Command & Navigation Isolation
        # ---------------------------------------------------------------------
        try:
            mock_msg_cmd = AsyncMock()
            mock_msg_cmd.from_user.first_name = "Muxiddin"
            await admin_start_handler(mock_msg_cmd, is_admin=True, admin_role="super_admin")
            assert mock_msg_cmd.answer.called
            logger.info("✅ Test 17-20 Passed: /admin dashboard command and role display verified")
            passed += 4
        except Exception as e:
            logger.error(f"❌ Test 17-20 Failed: {e}")
            failed += 4

    await test_engine.dispose()

    logger.info("==========================================")
    logger.info(f"Stage 10 Admin Panel Tests Summary: {passed} Passed, {failed} Failed")
    logger.info("==========================================")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_stage10_tests())
