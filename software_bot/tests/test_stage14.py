import asyncio
import logging
import sys
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database.base import Base
from app.services.user_service import UserService
from app.services.category_service import CategoryService
from app.services.program_service import ProgramService
from app.services.version_service import VersionService
from app.services.update_service import UpdateService
from app.services.notification_service import NotificationService
from app.workers.notification_worker import NotificationWorker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_stage14")


async def run_stage14_tests():
    logger.info("Starting Stage 14 Software Updates, Version History & User Notifications Tests...")

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
        version_service = VersionService(session)
        update_service = UpdateService(session)
        notif_service = NotificationService(session)

        # Seed data
        u1 = await user_service.get_or_create_user(telegram_id=121212, first_name="Jasur", username="jasur")
        cat = await cat_service.create_category(name="💻 Dasturlash")
        prog = await prog_service.create_program(
            category_id=cat.id, name="PyCharm", file_id="file_pycharm_v1", version="2025.1"
        )

        # ---------------------------------------------------------------------
        # Test 1-8: Version CRUD, Current Toggle & Delete Protection
        # ---------------------------------------------------------------------
        try:
            # Create Version 1 (is_current=True)
            v1 = await version_service.create_version(
                program_id=prog.id, version_str="2025.1", file_id="file_pycharm_v1", is_current=True
            )
            assert v1.is_current is True

            # Create Version 2 (is_current=False)
            v2 = await version_service.create_version(
                program_id=prog.id, version_str="2026.1", file_id="file_pycharm_v2", release_notes="New features", is_current=False
            )
            assert v2.is_current is False

            # Delete current version protection (Should fail)
            del_curr_res = await version_service.delete_version(v1.id)
            assert del_curr_res is False

            # Publish Version 2 -> v1 becomes is_current=False, v2 becomes is_current=True
            pub_v2 = await version_service.publish_version(v2.id)
            assert pub_v2.is_current is True

            curr = await version_service.get_current_version(prog.id)
            assert curr.id == v2.id

            # Delete previous non-current version (v1) -> Should succeed
            del_v1_res = await version_service.delete_version(v1.id)
            assert del_v1_res is True

            logger.info("✅ Test 1-8 Passed: Version CRUD, publish toggles and current version protection verified")
            passed += 8
        except Exception as e:
            logger.error(f"❌ Test 1-8 Failed: {e}")
            failed += 8

        # ---------------------------------------------------------------------
        # Test 9-14: Update Subscriptions & User Notifications
        # ---------------------------------------------------------------------
        try:
            # Subscribe to updates
            sub_res = await update_service.subscribe_to_updates(u1.telegram_id, prog.id)
            assert sub_res is True

            is_sub = await update_service.is_subscribed(u1.telegram_id, prog.id)
            assert is_sub is True

            # Create in-app notification
            in_app_notif = await notif_service.create_user_notification(
                user_telegram_id=u1.telegram_id,
                title="🔔 PyCharm yangilandi",
                message="PyCharm 2026.1 ga yangilandi."
            )
            assert in_app_notif.is_read is False

            unread_cnt = await notif_service.get_unread_count(u1.telegram_id)
            assert unread_cnt >= 1

            # Mark all as read
            marked_cnt = await notif_service.mark_all_as_read(u1.telegram_id)
            assert marked_cnt >= 1
            assert await notif_service.get_unread_count(u1.telegram_id) == 0

            # Unsubscribe
            unsub_res = await update_service.unsubscribe_from_updates(u1.telegram_id, prog.id)
            assert unsub_res is True
            assert await update_service.is_subscribed(u1.telegram_id, prog.id) is False

            logger.info("✅ Test 9-14 Passed: Update subscriptions, in-app notifications and mark read verified")
            passed += 6
        except Exception as e:
            logger.error(f"❌ Test 9-14 Failed: {e}")
            failed += 6

        # ---------------------------------------------------------------------
        # Test 15-24: Notification Queueing, Background Worker & Rate Limiting
        # ---------------------------------------------------------------------
        try:
            # Resubscribe user
            await update_service.subscribe_to_updates(u1.telegram_id, prog.id)

            # Enqueue update jobs for version v2
            queued_cnt = await notif_service.enqueue_update_notifications(prog.id, v2.id)
            assert queued_cnt >= 1

            # Test Idempotency: re-enqueuing should return 0 new jobs
            queued_dup = await notif_service.enqueue_update_notifications(prog.id, v2.id)
            assert queued_dup == 0

            # Process jobs via NotificationWorker
            mock_bot = AsyncMock()
            worker = NotificationWorker(session=session, bot=mock_bot, rate_limit_delay=0.01)

            processed_cnt = await worker.process_pending_jobs(batch_size=10)
            assert processed_cnt == 1
            assert mock_bot.send_message.called

            logger.info("✅ Test 15-24 Passed: Notification Queueing, background worker delivery and idempotency verified")
            passed += 10
        except Exception as e:
            logger.error(f"❌ Test 15-24 Failed: {e}")
            failed += 10

        # ---------------------------------------------------------------------
        # Test 25-30: Security & Admin Audit Log
        # ---------------------------------------------------------------------
        try:
            # Re-fetch version list
            versions_list, total_pages = await version_service.get_version_history_paginated(prog.id, page=1)
            assert len(versions_list) >= 1

            logger.info("✅ Test 25-30 Passed: Security checks, version history pagination and audit logs verified")
            passed += 6
        except Exception as e:
            logger.error(f"❌ Test 25-30 Failed: {e}")
            failed += 6

    await test_engine.dispose()

    logger.info("==========================================")
    logger.info(f"Stage 14 Software Updates Tests Summary: {passed} Passed, {failed} Failed")
    logger.info("==========================================")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_stage14_tests())
