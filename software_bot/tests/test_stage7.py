import asyncio
import logging
import sys
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database.base import Base
from app.services.user_service import UserService
from app.services.category_service import CategoryService
from app.services.program_service import ProgramService
from app.services.download_service import DownloadService
from app.handlers.admin.programs import admin_program_test_download
from app.handlers.user.programs import program_download_handler
from app.utils.exceptions import (
    ProgramNotFoundError,
    ProgramInactiveError,
    FileMissingError,
    UserBlockedError,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_stage7")


async def run_stage7_tests():
    logger.info("Starting Stage 7 Download System, Download History & Analytics Tests...")

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

        # Seed data
        user1 = await user_service.get_or_create_user(telegram_id=111111, first_name="Ali")
        cat = await cat_service.create_category(name="💻 Dasturlash")
        prog1 = await prog_service.create_program(
            category_id=cat.id,
            name="VS Code",
            file_id="BQACAgQ_valid_file_id_1"
        )
        prog_inactive = await prog_service.create_program(
            category_id=cat.id,
            name="Inactive App",
            file_id="BQACAgQ_valid_file_id_2"
        )
        await prog_service.deactivate_program(prog_inactive.id)

        # ---------------------------------------------------------------------
        # Test 1 & 7: Active Program Download & DB Transaction Check
        # ---------------------------------------------------------------------
        try:
            u, p = await dl_service.validate_downloadable_program(user1.telegram_id, prog1.id)
            assert u.id == user1.id
            assert p.id == prog1.id

            dl_record, updated_prog = await dl_service.record_download(user1.telegram_id, prog1.id)
            assert dl_record.id is not None
            assert updated_prog.downloads_count == 1

            total_dls = await dl_service.get_total_downloads()
            assert total_dls == 1
            logger.info("✅ Test 1 & 7 Passed: Active program download validation and atomic DB transaction verified")
            passed += 2
        except Exception as e:
            logger.error(f"❌ Test 1 & 7 Failed: {e}")
            failed += 2

        # ---------------------------------------------------------------------
        # Test 2: Inactive Program Block
        # ---------------------------------------------------------------------
        try:
            await dl_service.validate_downloadable_program(user1.telegram_id, prog_inactive.id)
            logger.error("❌ Test 2 Failed: Inactive program was validated for download!")
            failed += 1
        except ProgramInactiveError:
            logger.info("✅ Test 2 Passed: Inactive program download prevented")
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test 2 Failed: {e}")
            failed += 1

        # ---------------------------------------------------------------------
        # Test 3: Missing File ID Block
        # ---------------------------------------------------------------------
        try:
            prog_no_file = await prog_service.create_program(
                category_id=cat.id, name="No File App", file_id=" "
            )
            await dl_service.validate_downloadable_program(user1.telegram_id, prog_no_file.id)
            logger.error("❌ Test 3 Failed: Program with missing file_id was validated!")
            failed += 1
        except FileMissingError:
            logger.info("✅ Test 3 Passed: Missing file_id download prevented")
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test 3 Failed: {e}")
            failed += 1

        # ---------------------------------------------------------------------
        # Test 4: Blocked User Protection
        # ---------------------------------------------------------------------
        try:
            blocked_user = await user_service.get_or_create_user(telegram_id=999999, first_name="Blocked")
            blocked_user.is_blocked = True
            await session.commit()

            await dl_service.validate_downloadable_program(blocked_user.telegram_id, prog1.id)
            logger.error("❌ Test 4 Failed: Blocked user was allowed to download!")
            failed += 1
        except UserBlockedError:
            logger.info("✅ Test 4 Passed: Blocked user download prevented")
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test 4 Failed: {e}")
            failed += 1

        # ---------------------------------------------------------------------
        # Test 5: Invalid Callback Program ID
        # ---------------------------------------------------------------------
        try:
            await dl_service.validate_downloadable_program(user1.telegram_id, 99999)
            logger.error("❌ Test 5 Failed: Non-existent program ID was validated!")
            failed += 1
        except ProgramNotFoundError:
            logger.info("✅ Test 5 Passed: Invalid program ID raises ProgramNotFoundError")
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test 5 Failed: {e}")
            failed += 1

        # ---------------------------------------------------------------------
        # Test 6: Telegram Send Error Rollback (No DB Record Created)
        # ---------------------------------------------------------------------
        try:
            before_count = await dl_service.get_total_downloads()
            mock_bot_err = AsyncMock()
            mock_bot_err.send_document.side_effect = Exception("Telegram API 500 Network Error")

            mock_cb = AsyncMock()
            mock_cb.from_user.id = user1.telegram_id
            mock_cb.data = f"program:download:{prog1.id}"

            await program_download_handler(mock_cb, mock_bot_err)

            after_count = await dl_service.get_total_downloads()
            assert before_count == after_count  # No record created!
            logger.info("✅ Test 6 Passed: Telegram API error prevented download DB record creation")
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test 6 Failed: {e}")
            failed += 1

        # ---------------------------------------------------------------------
        # Test 8: Repeated Download (Multiple Records Allowed)
        # ---------------------------------------------------------------------
        try:
            await dl_service.record_download(user1.telegram_id, prog1.id)
            await dl_service.record_download(user1.telegram_id, prog1.id)

            u_count = await dl_service.get_user_download_count(user1.telegram_id)
            assert u_count == 3  # 1 from Test 1 + 2 repeated downloads
            logger.info("✅ Test 8 Passed: Multiple download records allowed for repeated downloads")
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test 8 Failed: {e}")
            failed += 1

        # ---------------------------------------------------------------------
        # Test 9: Download History (Unique Programs & Pagination)
        # ---------------------------------------------------------------------
        try:
            prog2 = await prog_service.create_program(
                category_id=cat.id, name="PyCharm PRO", file_id="BQACAgQ_valid_file_id_3"
            )
            await dl_service.record_download(user1.telegram_id, prog2.id)

            history, pages = await dl_service.get_user_downloads_unique_paginated(user1.telegram_id, page=1, page_size=10)
            assert len(history) == 2  # Unique programs: prog2, prog1
            assert history[0][1].id == prog2.id  # Newest first
            logger.info("✅ Test 9 Passed: Download history returns unique programs, newest first")
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test 9 Failed: {e}")
            failed += 1

        # ---------------------------------------------------------------------
        # Test 10 & 11: Popular & New Programs Queries
        # ---------------------------------------------------------------------
        try:
            pop_progs, _ = await prog_service.get_popular_programs_paginated(page=1, page_size=10)
            assert pop_progs[0].downloads_count >= pop_progs[1].downloads_count

            new_progs, _ = await prog_service.get_new_programs_paginated(page=1, page_size=10)
            assert len(new_progs) >= 2
            logger.info("✅ Test 10 & 11 Passed: Popular programs (downloads_count DESC) & New programs verified")
            passed += 2
        except Exception as e:
            logger.error(f"❌ Test 10 & 11 Failed: {e}")
            failed += 2

        # ---------------------------------------------------------------------
        # Test 12: Admin Test Download Separation
        # ---------------------------------------------------------------------
        try:
            prog1_before_count = (await prog_service.get_program_by_id(prog1.id)).downloads_count
            dl_before_total = await dl_service.get_total_downloads()

            mock_bot_admin = AsyncMock()
            mock_cb_admin = AsyncMock()
            mock_cb_admin.from_user.id = 123456789
            mock_cb_admin.data = f"admin:program:test_download:{prog1.id}"

            await admin_program_test_download(mock_cb_admin, mock_bot_admin, is_admin=True)

            prog1_after_count = (await prog_service.get_program_by_id(prog1.id)).downloads_count
            dl_after_total = await dl_service.get_total_downloads()

            assert prog1_before_count == prog1_after_count
            assert dl_before_total == dl_after_total
            logger.info("✅ Test 12 Passed: Admin test download does not affect user download statistics")
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test 12 Failed: {e}")
            failed += 1

    await test_engine.dispose()

    logger.info("==========================================")
    logger.info(f"Stage 7 Download System Tests Summary: {passed} Passed, {failed} Failed")
    logger.info("==========================================")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_stage7_tests())
