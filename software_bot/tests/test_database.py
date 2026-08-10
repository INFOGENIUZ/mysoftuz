import asyncio
import logging
import sys
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database.base import Base
from app.services.user_service import UserService
from app.services.category_service import CategoryService
from app.services.program_service import ProgramService
from app.services.download_service import DownloadService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_database")


async def run_all_tests():
    logger.info("Starting Database Architecture Tests (Phase 2)...")
    
    # 1. Setup in-memory test database
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    passed_count = 0
    failed_count = 0

    async with session_factory() as session:
        user_service = UserService(session)
        category_service = CategoryService(session)
        program_service = ProgramService(session)
        download_service = DownloadService(session)

        # ---------------------------------------------------------------------
        # Test 1: User Creation
        # ---------------------------------------------------------------------
        try:
            user1 = await user_service.create_user(
                telegram_id=111222333,
                first_name="Alisher",
                last_name="Navoiy",
                username="alisher_navoiy"
            )
            assert user1.id is not None
            assert user1.telegram_id == 111222333
            logger.info("✅ Test 1 Passed: User creation successful")
            passed_count += 1
        except Exception as e:
            logger.error(f"❌ Test 1 Failed: {e}")
            failed_count += 1

        # ---------------------------------------------------------------------
        # Test 2: Prevent Duplicate Telegram ID
        # ---------------------------------------------------------------------
        try:
            await user_service.create_user(
                telegram_id=111222333,  # Duplicate ID
                first_name="Duplicate User"
            )
            logger.error("❌ Test 2 Failed: Duplicate Telegram ID was allowed!")
            failed_count += 1
        except IntegrityError:
            await session.rollback()
            logger.info("✅ Test 2 Passed: Duplicate Telegram ID prevented")
            passed_count += 1
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Test 2 Failed: Unexpected exception {e}")
            failed_count += 1

        # ---------------------------------------------------------------------
        # Test 3: Category Creation
        # ---------------------------------------------------------------------
        try:
            category = await category_service.create_category(
                name="🎨 Grafik dizayn",
                description="Grafik tahrirlash dasturlari"
            )
            assert category.id is not None
            assert category.slug == "grafik-dizayn"
            logger.info(f"✅ Test 3 Passed: Category created with slug '{category.slug}'")
            passed_count += 1
        except Exception as e:
            logger.error(f"❌ Test 3 Failed: {e}")
            failed_count += 1

        # ---------------------------------------------------------------------
        # Test 4 & 5: Program Creation & Category Link
        # ---------------------------------------------------------------------
        try:
            program = await program_service.create_program(
                category_id=category.id,
                name="Adobe Photoshop 2026",
                file_id="BQACAgQAAxkBAAIB_test_file_id",
                file_name="Photoshop2026Setup.exe",
                file_size=2147483648,
                architecture="x64",
                version="2026.1"
            )
            assert program.id is not None
            assert program.category_id == category.id
            assert program.slug == "adobe-photoshop-2026"
            logger.info("✅ Test 4 & 5 Passed: Program created and correctly linked to Category")
            passed_count += 2
        except Exception as e:
            logger.error(f"❌ Test 4 & 5 Failed: {e}")
            failed_count += 2

        # ---------------------------------------------------------------------
        # Test 6 & 7: Download Record Creation & Download Count Increment
        # ---------------------------------------------------------------------
        try:
            initial_count = program.downloads_count
            download, updated_program = await download_service.record_download(
                user_telegram_id=111222333,
                program_id=program.id
            )
            assert download.id is not None
            assert updated_program.downloads_count == initial_count + 1
            logger.info(f"✅ Test 6 & 7 Passed: Download log recorded and downloads_count incremented to {updated_program.downloads_count}")
            passed_count += 2
        except Exception as e:
            import traceback
            logger.error(f"❌ Test 6 & 7 Failed: {e}\n{traceback.format_exc()}")
            failed_count += 2

        # ---------------------------------------------------------------------
        # Test 8: Soft Delete Category
        # ---------------------------------------------------------------------
        try:
            soft_deleted = await category_service.soft_delete_category(category.id)
            assert soft_deleted is True
            cat_check = await category_service.get_category_by_id(category.id)
            assert cat_check.is_active is False
            # Program under category must remain untouched physically
            prog_check = await program_service.get_program_by_id(program.id)
            assert prog_check is not None
            logger.info("✅ Test 8 Passed: Category soft deleted without losing associated program")
            passed_count += 1
        except Exception as e:
            logger.error(f"❌ Test 8 Failed: {e}")
            failed_count += 1

    await engine.dispose()

    logger.info("==========================================")
    logger.info(f"Database Tests Summary: {passed_count} Passed, {failed_count} Failed")
    logger.info("==========================================")
    if failed_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
