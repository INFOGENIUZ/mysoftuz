import asyncio
import logging
import sys
from unittest.mock import AsyncMock, MagicMock

from aiogram.types import Message, CallbackQuery
from app.config import settings
from app.services.admin_service import AdminService
from app.middlewares.admin import AdminMiddleware
from app.middlewares.maintenance import MaintenanceMiddleware
from app.utils.validators import validate_url, validate_file_size, is_extension_allowed
from app.utils.callback_factory import safe_answer_callback
from app.handlers.admin.start import admin_start_handler
from app.bot import global_error_handler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_stage3")


async def run_stage3_tests():
    logger.info("Starting Stage 3 Security & Global Middleware Tests...")

    from app.database.engine import init_db
    await init_db()

    passed = 0
    failed = 0

    # -------------------------------------------------------------------------
    # Test 1: Regular user sends /admin -> ⛔ Sizda ushbu bo'limga kirish huquqi yo'q.
    # -------------------------------------------------------------------------
    try:
        mock_user = MagicMock()
        mock_user.id = 999999
        mock_user.first_name = "User"
        mock_msg = MagicMock(spec=Message)
        mock_msg.from_user = mock_user
        mock_msg.answer = AsyncMock()

        await admin_start_handler(mock_msg, is_admin=False)

        assert mock_msg.answer.called
        call_arg = mock_msg.answer.call_args[0][0]
        assert "Sizda" in call_arg and "huquqi yo'q" in call_arg
        logger.info("✅ Test 1 Passed: Regular user denied /admin command")
        passed += 1
    except Exception as e:
        logger.error(f"❌ Test 1 Failed: {e}")
        failed += 1

    # -------------------------------------------------------------------------
    # Test 2: Admin sends /admin -> 👨‍💻 Admin panelga xush kelibsiz.
    # -------------------------------------------------------------------------
    try:
        mock_user = MagicMock()
        mock_user.id = 123456789
        mock_user.first_name = "Admin"
        mock_msg = MagicMock(spec=Message)
        mock_msg.from_user = mock_user
        mock_msg.answer = AsyncMock()

        await admin_start_handler(mock_msg, is_admin=True)

        assert mock_msg.answer.called
        call_kwargs = mock_msg.answer.call_args_list[0][1]
        assert "Admin panelga xush kelibsiz" in call_kwargs.get("text", "")
        logger.info("✅ Test 2 Passed: Admin granted access to /admin command")
        passed += 1
    except Exception as e:
        logger.error(f"❌ Test 2 Failed: {e}")
        failed += 1

    # -------------------------------------------------------------------------
    # Test 3: Maintenance mode ON -> Regular user blocked
    # -------------------------------------------------------------------------
    try:
        settings.MAINTENANCE_MODE = True
        middleware = MaintenanceMiddleware()
        mock_msg = MagicMock(spec=Message)
        mock_msg.answer = AsyncMock()
        mock_handler = AsyncMock()
        data = {"is_admin": False}

        result = await middleware(mock_handler, mock_msg, data)
        assert result is None
        mock_msg.answer.assert_called()
        call_text = mock_msg.answer.call_args[0][0]
        assert "texnik ishlar olib borilmoqda" in call_text
        logger.info("✅ Test 3 Passed: Maintenance mode blocked regular user")
        passed += 1
    except Exception as e:
        logger.error(f"❌ Test 3 Failed: {e}")
        failed += 1

    # -------------------------------------------------------------------------
    # Test 4: Maintenance mode ON -> Admin allowed through
    # -------------------------------------------------------------------------
    try:
        settings.MAINTENANCE_MODE = True
        middleware = MaintenanceMiddleware()
        mock_msg = AsyncMock()
        mock_handler = AsyncMock(return_value="OK")
        data = {"is_admin": True}

        result = await middleware(mock_handler, mock_msg, data)
        assert result == "OK"
        logger.info("✅ Test 4 Passed: Maintenance mode allowed Admin through")
        passed += 1
    except Exception as e:
        logger.error(f"❌ Test 4 Failed: {e}")
        failed += 1
    finally:
        settings.MAINTENANCE_MODE = False  # Reset

    # -------------------------------------------------------------------------
    # Test 5: Callback replay protection
    # -------------------------------------------------------------------------
    try:
        mock_cb = AsyncMock()
        answered = await safe_answer_callback(mock_cb, text="⚠️ Bu amal endi mavjud emas.")
        assert answered is True
        mock_cb.answer.assert_called_with(text="⚠️ Bu amal endi mavjud emas.", show_alert=True)
        logger.info("✅ Test 5 Passed: Callback replay protection answered safely")
        passed += 1
    except Exception as e:
        logger.error(f"❌ Test 5 Failed: {e}")
        failed += 1

    # -------------------------------------------------------------------------
    # Test 6: Invalid URL & File validation
    # -------------------------------------------------------------------------
    try:
        assert validate_url("https://example.com/file.exe") is True
        assert validate_url("invalid-url-string") is False
        assert validate_url("hello") is False
        assert validate_file_size(-100) is False
        assert is_extension_allowed("setup.exe") is True
        assert is_extension_allowed("malicious.bat") is False
        logger.info("✅ Test 6 Passed: URL and File validation functions accurate")
        passed += 1
    except Exception as e:
        logger.error(f"❌ Test 6 Failed: {e}")
        failed += 1

    # -------------------------------------------------------------------------
    # Test 7: Global Error Handler Exception Safety
    # -------------------------------------------------------------------------
    try:
        mock_event = MagicMock()
        mock_event.exception = RuntimeError("Test internal database error")
        mock_event.update.message = AsyncMock()
        mock_event.update.callback_query = None

        handled = await global_error_handler(mock_event)
        assert handled is True
        mock_event.update.message.answer.assert_called()
        err_msg = mock_event.update.message.answer.call_args[0][0]
        assert "Kutilmagan xatolik yuz berdi" in err_msg
        logger.info("✅ Test 7 Passed: Global error handler handled exception safely without leaking details")
        passed += 1
    except Exception as e:
        logger.error(f"❌ Test 7 Failed: {e}")
        failed += 1

    logger.info("==========================================")
    logger.info(f"Stage 3 Tests Summary: {passed} Passed, {failed} Failed")
    logger.info("==========================================")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_stage3_tests())
