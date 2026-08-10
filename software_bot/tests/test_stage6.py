import asyncio
import logging
import sys
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database.base import Base
from app.services.category_service import CategoryService
from app.services.program_service import ProgramService
from app.services.file_service import FileService
from app.handlers.admin.programs import (
    admin_programs_list_handler,
    admin_program_test_download,
    admin_program_delete_prompt,
    admin_program_cancel_handler
)
from app.utils.validators import is_extension_allowed, validate_file_size, validate_url

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_stage6")


async def run_stage6_tests():
    logger.info("Starting Stage 6 Program Management & Telegram File Upload Tests...")

    # 1. Setup in-memory test database
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    passed = 0
    failed = 0

    async with session_factory() as session:
        cat_service = CategoryService(session)
        prog_service = ProgramService(session)
        file_service = FileService(session)

        # Create Category Context
        cat = await cat_service.create_category(name="💻 Dasturlash", description="IDE lar")
        cat2 = await cat_service.create_category(name="🌐 Internet", description="Brauzerlar")

        # ---------------------------------------------------------------------
        # Test 1, 2, 8, 9, 10, 11, 13: Create Program with File Metadata
        # ---------------------------------------------------------------------
        try:
            prog1 = await prog_service.create_program(
                category_id=cat.id,
                name="Visual Studio Code 2026",
                file_id="BQACAgQAAxkBAAIB_test_file_id_123",
                file_unique_id="AgAD_unique_id_123",
                file_name="VSCodeSetup-x64-1.95.exe",
                file_size=95000000,
                mime_type="application/x-msdownload",
                version="1.95.0",
                architecture="x64",
                official_url="https://code.visualstudio.com"
            )

            assert prog1.id is not None
            assert prog1.file_id == "BQACAgQAAxkBAAIB_test_file_id_123"
            assert prog1.file_unique_id == "AgAD_unique_id_123"
            assert prog1.file_size == 95000000
            assert prog1.slug == "visual-studio-code-2026"
            logger.info("✅ Test 1,2,8,9,10,11,13 Passed: Program created with file metadata in SQLite")
            passed += 7
        except Exception as e:
            logger.error(f"❌ Test 1,2,8,9,10,11,13 Failed: {e}")
            failed += 7

        # ---------------------------------------------------------------------
        # Test 3: Prevent Duplicate Program Name in Category
        # ---------------------------------------------------------------------
        try:
            await prog_service.create_program(
                category_id=cat.id,
                name="Visual Studio Code 2026",
                file_id="BQACAgQ_dup"
            )
            logger.error("❌ Test 3 Failed: Duplicate program name was allowed in same category!")
            failed += 1
        except ValueError:
            logger.info("✅ Test 3 Passed: Duplicate program name prevented in same category")
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test 3 Failed: {e}")
            failed += 1

        # ---------------------------------------------------------------------
        # Test 4: Official URL Validation
        # ---------------------------------------------------------------------
        try:
            assert validate_url("https://code.visualstudio.com") is True
            assert validate_url("ftp://invalid-url") is False
            assert validate_url("hello_world") is False
            logger.info("✅ Test 4 Passed: Official URL validation verified")
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test 4 Failed: {e}")
            failed += 1

        # ---------------------------------------------------------------------
        # Test 6 & 7: Invalid Extension & File Size Limit Check
        # ---------------------------------------------------------------------
        try:
            assert is_extension_allowed("malicious_script.bat") is False
            assert is_extension_allowed("installer.exe") is True
            assert is_extension_allowed("archive.7z") is True
            assert validate_file_size(-500) is False
            logger.info("✅ Test 6 & 7 Passed: Extension and File Size validations working")
            passed += 2
        except Exception as e:
            logger.error(f"❌ Test 6 & 7 Failed: {e}")
            failed += 2

        # ---------------------------------------------------------------------
        # Test 14 & 15: Admin Program List & Admin Detail View
        # ---------------------------------------------------------------------
        try:
            progs, total_pages = await prog_service.get_admin_programs_by_category_paginated(cat.id, page=1, page_size=10)
            assert len(progs) == 1
            fetched_prog = await prog_service.get_program_by_id(prog1.id)
            assert fetched_prog.name == "Visual Studio Code 2026"
            logger.info("✅ Test 14 & 15 Passed: Admin program list and detail view fetched correctly")
            passed += 2
        except Exception as e:
            logger.error(f"❌ Test 14 & 15 Failed: {e}")
            failed += 2

        # ---------------------------------------------------------------------
        # Test 16: Program Edit
        # ---------------------------------------------------------------------
        try:
            updated_prog = await prog_service.update_program(
                prog1.id, name="VS Code 2026 PRO", version="1.96.0"
            )
            assert updated_prog.name == "VS Code 2026 PRO"
            assert updated_prog.version == "1.96.0"
            logger.info("✅ Test 16 Passed: Program edit successful")
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test 16 Failed: {e}")
            failed += 1

        # ---------------------------------------------------------------------
        # Test 17: File Replacement
        # ---------------------------------------------------------------------
        try:
            replaced_prog = await prog_service.update_program(
                prog1.id,
                file_id="BQACAgQ_new_replaced_file_id",
                file_unique_id="AgAD_new_unique_id",
                file_name="VSCode_New_Installer.exe",
                file_size=98000000
            )
            assert replaced_prog.file_id == "BQACAgQ_new_replaced_file_id"
            assert replaced_prog.file_size == 98000000
            logger.info("✅ Test 17 Passed: Program file replacement successful")
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test 17 Failed: {e}")
            failed += 1

        # ---------------------------------------------------------------------
        # Test 18: Category Change
        # ---------------------------------------------------------------------
        try:
            moved_prog = await prog_service.update_program(prog1.id, category_id=cat2.id)
            assert moved_prog.category_id == cat2.id
            logger.info("✅ Test 18 Passed: Program moved to new category successfully")
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test 18 Failed: {e}")
            failed += 1

        # ---------------------------------------------------------------------
        # Test 19 & 20: Deactivate & Activate Program
        # ---------------------------------------------------------------------
        try:
            await prog_service.deactivate_program(prog1.id)
            check_deact = await prog_service.get_program_by_id(prog1.id)
            assert check_deact.is_active is False

            await prog_service.activate_program(prog1.id)
            check_act = await prog_service.get_program_by_id(prog1.id)
            assert check_act.is_active is True
            logger.info("✅ Test 19 & 20 Passed: Program Deactivate & Activate working")
            passed += 2
        except Exception as e:
            logger.error(f"❌ Test 19 & 20 Failed: {e}")
            failed += 2

        # ---------------------------------------------------------------------
        # Test 21: Program Delete
        # ---------------------------------------------------------------------
        try:
            del_prog = await prog_service.create_program(
                category_id=cat2.id, name="Temp App", file_id="BQACAgQ_temp"
            )
            deleted = await prog_service.delete_program(del_prog.id)
            assert deleted is True
            check_del = await prog_service.get_program_by_id(del_prog.id)
            assert check_del is None
            logger.info("✅ Test 21 Passed: Program deleted successfully")
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test 21 Failed: {e}")
            failed += 1

        # ---------------------------------------------------------------------
        # Test 22: Admin Test Download via Telegram file_id
        # ---------------------------------------------------------------------
        try:
            mock_bot = AsyncMock()
            mock_cb = AsyncMock()
            mock_cb.data = f"admin:program:test_download:{prog1.id}"
            mock_cb.from_user.id = 123456789

            await admin_program_test_download(mock_cb, mock_bot, is_admin=True)

            assert mock_bot.send_document.called
            call_kwargs = mock_bot.send_document.call_args[1]
            assert call_kwargs["document"] == "BQACAgQ_new_replaced_file_id"
            logger.info("✅ Test 22 Passed: Admin test download sent document via file_id to chat")
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test 22 Failed: {e}")
            failed += 1

        # ---------------------------------------------------------------------
        # Test 23 & 24: Moderator Permission & Regular User Callback Block
        # ---------------------------------------------------------------------
        try:
            mock_cb_mod = AsyncMock()
            mock_cb_mod.data = f"admin:program:delete:{prog1.id}"
            await admin_program_delete_prompt(mock_cb_mod, admin_role="moderator")
            mock_cb_mod.answer.assert_called_with("⛔ Moderatorlarda o'chirish huquqi yo'q.", show_alert=True)

            mock_cb_user = AsyncMock()
            mock_cb_user.data = f"admin:programs:list:{cat2.id}"
            await admin_programs_list_handler(mock_cb_user, is_admin=False)
            mock_cb_user.answer.assert_called_with("⛔ Sizda ushbu bo'limga kirish huquqi yo'q.", show_alert=True)

            logger.info("✅ Test 23 & 24 Passed: Moderator and Regular User permission blocks verified")
            passed += 2
        except Exception as e:
            logger.error(f"❌ Test 23 & 24 Failed: {e}")
            failed += 2

        # ---------------------------------------------------------------------
        # Test 25: FSM /cancel Flow
        # ---------------------------------------------------------------------
        try:
            mock_msg = AsyncMock()
            mock_msg.text = "/cancel"
            mock_state = AsyncMock()
            await admin_program_cancel_handler(mock_msg, mock_state)
            assert mock_state.clear.called
            logger.info("✅ Test 25 Passed: FSM cancel flow cleared state successfully")
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test 25 Failed: {e}")
            failed += 1

    await test_engine.dispose()

    logger.info("==========================================")
    logger.info(f"Stage 6 Program Admin CRUD Tests Summary: {passed} Passed, {failed} Failed")
    logger.info("==========================================")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_stage6_tests())
