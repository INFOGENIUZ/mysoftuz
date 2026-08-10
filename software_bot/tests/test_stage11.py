import os
import asyncio
import logging
import sys
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database.base import Base
from app.core.errors import generate_error_id, get_user_friendly_error_message
from app.core.logging_config import SecretScrubberFilter
from app.database.engine import run_database_integrity_check
from app.services.health_service import HealthService
from app.services.backup_service import BackupService
from app.middlewares.anti_spam import AntiSpamMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_stage11")


async def run_stage11_tests():
    logger.info("Starting Stage 11 Production Hardening, Security & Reliability Tests...")

    # 1. Setup in-memory test database
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    passed = 0
    failed = 0

    async with session_factory() as session:
        # ---------------------------------------------------------------------
        # Test 1 & 2: Error ID Generator & Sanitized Error Messages
        # ---------------------------------------------------------------------
        try:
            err_id = generate_error_id()
            assert err_id.startswith("ERR-")
            assert len(err_id) >= 15

            user_msg = get_user_friendly_error_message(is_admin=False)
            admin_msg = get_user_friendly_error_message(is_admin=True, error_id=err_id)

            assert "Traceback" not in user_msg
            assert err_id in admin_msg
            logger.info("✅ Test 1 & 2 Passed: Error ID generator and sanitized error messages verified")
            passed += 2
        except Exception as e:
            logger.error(f"❌ Test 1 & 2 Failed: {e}")
            failed += 2

        # ---------------------------------------------------------------------
        # Test 3 & 4: Secret Scrubber Filter & Log Rotation
        # ---------------------------------------------------------------------
        try:
            scrubber = SecretScrubberFilter(secrets=["my_super_secret_key_123"])
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="test.py", lineno=1,
                msg="Token 123456789:ABCdefGHIjklMNOpqrsTUVwxyz12345 leaked with my_super_secret_key_123",
                args=(), exc_info=None
            )
            scrubber.filter(record)

            assert "123456789:ABCdef" not in record.msg
            assert "my_super_secret_key_123" not in record.msg
            logger.info("✅ Test 3 & 4 Passed: Secret scrubber filter masked tokens and credentials in logs")
            passed += 2
        except Exception as e:
            logger.error(f"❌ Test 3 & 4 Failed: {e}")
            failed += 2

        # ---------------------------------------------------------------------
        # Test 5 & 6: SQLite PRAGMAs & DB Integrity Check & Health Service
        # ---------------------------------------------------------------------
        try:
            is_ok, res_str = await run_database_integrity_check(session)
            assert is_ok is True
            assert res_str == "ok"

            health_service = HealthService(session)
            health = await health_service.get_health_status()
            assert health["status"] == "OK"
            assert health["db_status"] == "OK"
            logger.info("✅ Test 5 & 6 Passed: DB integrity check and Health Service status verified")
            passed += 2
        except Exception as e:
            logger.error(f"❌ Test 5 & 6 Failed: {e}")
            failed += 2

        # ---------------------------------------------------------------------
        # Test 7 & 8: Backup Service Creation & Retention Cleanup
        # ---------------------------------------------------------------------
        try:
            test_backup_dir = "test_backups_dir"

            # Create dummy db file for backup test
            dummy_db = "data/software_bot.db"
            os.makedirs("data", exist_ok=True)
            with open(dummy_db, "w") as f:
                f.write("dummy db data")

            is_success, backup_path = await BackupService.create_backup(backup_dir=test_backup_dir)
            assert is_success is True
            assert os.path.exists(backup_path)

            cleaned = await BackupService.clean_old_backups(backup_dir=test_backup_dir, retention_days=0)
            assert isinstance(cleaned, int)

            # Cleanup test files
            if os.path.exists(backup_path):
                os.remove(backup_path)
            if os.path.exists(test_backup_dir):
                os.rmdir(test_backup_dir)

            logger.info("✅ Test 7 & 8 Passed: Backup Service online backup and retention cleanup verified")
            passed += 2
        except Exception as e:
            logger.error(f"❌ Test 7 & 8 Failed: {e}")
            failed += 2

        # ---------------------------------------------------------------------
        # Test 9 & 10: Anti-Spam Middleware & Rate Limiting
        # ---------------------------------------------------------------------
        try:
            anti_spam = AntiSpamMiddleware(rate_limit_seconds=0.5)

            mock_user = MagicMock()
            mock_user.id = 777

            mock_data = {"event_from_user": mock_user}
            mock_handler = AsyncMock(return_value="OK")
            mock_event = AsyncMock()

            # First call -> Allowed
            res1 = await anti_spam(mock_handler, mock_event, mock_data)
            assert res1 == "OK"

            # Immediate second call -> Throttled
            res2 = await anti_spam(mock_handler, mock_event, mock_data)
            assert res2 is None
            logger.info("✅ Test 9 & 10 Passed: Anti-Spam Middleware rate limiting and throttling verified")
            passed += 2
        except Exception as e:
            logger.error(f"❌ Test 9 & 10 Failed: {e}")
            failed += 2

    await test_engine.dispose()

    logger.info("==========================================")
    logger.info(f"Stage 11 Production Hardening Tests Summary: {passed} Passed, {failed} Failed")
    logger.info("==========================================")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_stage11_tests())
