import asyncio
import logging
import sys
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database.base import Base
from app.services.user_service import UserService
from app.services.category_service import CategoryService
from app.services.program_service import ProgramService
from app.handlers.admin.categories import (
    admin_categories_list_handler,
    admin_category_delete_prompt,
    admin_category_cancel_handler
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_stage5")


async def run_stage5_tests():
    logger.info("Starting Stage 5 Category Management Admin CRUD Tests...")

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

        # ---------------------------------------------------------------------
        # Test 1: Admin Category List View
        # ---------------------------------------------------------------------
        try:
            cat1 = await cat_service.create_category(name="💻 Dasturlash", description="IDE lar")
            categories, total_pages = await cat_service.get_admin_categories_paginated(page=1, page_size=10)
            assert len(categories) >= 1
            logger.info("✅ Test 1 Passed: Admin category list view returned categories")
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test 1 Failed: {e}")
            failed += 1

        # ---------------------------------------------------------------------
        # Test 2: Admin Creates New Category
        # ---------------------------------------------------------------------
        try:
            cat2 = await cat_service.create_category(name="📄 Office", description="Hujjatlar", sort_order=2)
            assert cat2.id is not None
            assert cat2.slug == "office"
            logger.info("✅ Test 2 Passed: New category created successfully")
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test 2 Failed: {e}")
            failed += 1

        # ---------------------------------------------------------------------
        # Test 3: Duplicate Category Prevention
        # ---------------------------------------------------------------------
        try:
            await cat_service.create_category(name="📄 Office")
            logger.error("❌ Test 3 Failed: Duplicate category was allowed!")
            failed += 1
        except ValueError:
            logger.info("✅ Test 3 Passed: Duplicate category name prevented")
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test 3 Failed: {e}")
            failed += 1

        # ---------------------------------------------------------------------
        # Test 4: Edit Category
        # ---------------------------------------------------------------------
        try:
            updated_cat = await cat_service.update_category(cat2.id, name="📄 Office Suite", sort_order=5)
            assert updated_cat.name == "📄 Office Suite"
            assert updated_cat.slug == "office-suite"
            assert updated_cat.sort_order == 5
            logger.info("✅ Test 4 Passed: Category edit and slug update successful")
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test 4 Failed: {e}")
            failed += 1

        # ---------------------------------------------------------------------
        # Test 5 & 6: Deactivate & Activate Category
        # ---------------------------------------------------------------------
        try:
            deactivated = await cat_service.deactivate_category(cat2.id)
            assert deactivated is True
            check_deact = await cat_service.get_category_by_id(cat2.id)
            assert check_deact.is_active is False

            activated = await cat_service.activate_category(cat2.id)
            assert activated is True
            check_act = await cat_service.get_category_by_id(cat2.id)
            assert check_act.is_active is True
            logger.info("✅ Test 5 & 6 Passed: Deactivate and Activate category successful")
            passed += 2
        except Exception as e:
            logger.error(f"❌ Test 5 & 6 Failed: {e}")
            failed += 2

        # ---------------------------------------------------------------------
        # Test 7: Delete Empty Category
        # ---------------------------------------------------------------------
        try:
            empty_cat = await cat_service.create_category(name="🔧 Temp Category")
            deleted = await cat_service.delete_category(empty_cat.id)
            assert deleted is True
            check_del = await cat_service.get_category_by_id(empty_cat.id)
            assert check_del is None
            logger.info("✅ Test 7 Passed: Empty category deleted successfully")
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test 7 Failed: {e}")
            failed += 1

        # ---------------------------------------------------------------------
        # Test 8: Prevent Deleting Category with Associated Programs (Delete Protection)
        # ---------------------------------------------------------------------
        try:
            prog = await prog_service.create_program(
                category_id=cat1.id,
                name="VS Code",
                file_id="BQACAgQ_test_id"
            )
            await cat_service.delete_category(cat1.id)
            logger.error("❌ Test 8 Failed: Category with programs was deleted!")
            failed += 1
        except ValueError as ve:
            assert "Cannot delete category" in str(ve)
            logger.info("✅ Test 8 Passed: Delete protection prevented deleting category with programs")
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test 8 Failed: {e}")
            failed += 1

        # ---------------------------------------------------------------------
        # Test 9 & 10: Category Pagination & Program Count
        # ---------------------------------------------------------------------
        try:
            categories_list, total_pages = await cat_service.get_admin_categories_paginated(page=1, page_size=10)
            found_cat1 = False
            for cat, count in categories_list:
                if cat.id == cat1.id:
                    assert count == 1
                    found_cat1 = True
            assert found_cat1 is True
            logger.info("✅ Test 9 & 10 Passed: Category pagination & Program count accuracy verified")
            passed += 2
        except Exception as e:
            logger.error(f"❌ Test 9 & 10 Failed: {e}")
            failed += 2

        # ---------------------------------------------------------------------
        # Test 11 & 12: Moderator Category View & Delete Protection
        # ---------------------------------------------------------------------
        try:
            mock_cb = AsyncMock()
            mock_cb.data = f"admin:category:delete:{cat1.id}"
            await admin_category_delete_prompt(mock_cb, admin_role="moderator")
            mock_cb.answer.assert_called_with("⛔ Moderatorlarda o'chirish huquqi yo'q.", show_alert=True)
            logger.info("✅ Test 11 & 12 Passed: Moderator role permission checks verified")
            passed += 2
        except Exception as e:
            logger.error(f"❌ Test 11 & 12 Failed: {e}")
            failed += 2

        # ---------------------------------------------------------------------
        # Test 13: Regular User Blocked from Admin Handler
        # ---------------------------------------------------------------------
        try:
            mock_msg = AsyncMock()
            await admin_categories_list_handler(mock_msg, is_admin=False)
            mock_msg.answer.assert_called_with("⛔ Sizda ushbu bo'limga kirish huquqi yo'q.")
            logger.info("✅ Test 13 Passed: Regular user blocked from admin category list handler")
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test 13 Failed: {e}")
            failed += 1

        # ---------------------------------------------------------------------
        # Test 14: FSM /cancel Flow
        # ---------------------------------------------------------------------
        try:
            mock_msg = AsyncMock()
            mock_msg.text = "/cancel"
            mock_state = AsyncMock()
            await admin_category_cancel_handler(mock_msg, mock_state)
            assert mock_state.clear.called
            logger.info("✅ Test 14 Passed: FSM cancel flow cleared state successfully")
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test 14 Failed: {e}")
            failed += 1

        # ---------------------------------------------------------------------
        # Test 15: User Panel Ignores Inactive Categories
        # ---------------------------------------------------------------------
        try:
            temp_cat = await cat_service.create_category(name="🔴 Hidden Category")
            await cat_service.deactivate_category(temp_cat.id)

            user_cats, _ = await cat_service.get_categories_paginated(page=1, page_size=100)
            user_cat_ids = [c.id for c in user_cats]
            assert temp_cat.id not in user_cat_ids
            logger.info("✅ Test 15 Passed: User panel correctly ignores inactive categories")
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test 15 Failed: {e}")
            failed += 1

    await test_engine.dispose()

    logger.info("==========================================")
    logger.info(f"Stage 5 Category Admin CRUD Tests Summary: {passed} Passed, {failed} Failed")
    logger.info("==========================================")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_stage5_tests())
