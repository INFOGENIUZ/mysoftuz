import asyncio
import logging
import sys
from unittest.mock import AsyncMock, MagicMock
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database.base import Base
from app.services.user_service import UserService
from app.services.category_service import CategoryService
from app.services.program_service import ProgramService
from app.services.download_service import DownloadService
from app.handlers.user.start import user_start_handler
from app.handlers.user.categories import categories_menu_handler, category_view_handler
from app.handlers.user.programs import program_view_handler
from app.handlers.user.popular import popular_menu_handler
from app.handlers.user.new_programs import new_programs_menu_handler
from app.handlers.user.downloads import user_downloads_menu_handler
from app.handlers.user.about import about_menu_handler
from app.handlers.user.search import search_menu_handler
from app.handlers.user.navigation import back_to_categories_handler, back_to_main_handler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_stage4")


async def run_stage4_tests():
    logger.info("Starting Stage 4 User Interface Tests...")

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

        # Seed test data
        test_user = await user_service.create_user(
            telegram_id=777888999, first_name="TestUser", username="testuser"
        )
        cat = await cat_service.create_category(name="🎨 Grafik dizayn", description="Grafik dasturlar")
        prog = await prog_service.create_program(
            category_id=cat.id,
            name="Photoshop 2026",
            file_id="BQACAgQAAxkBAAIB_file_id",
            short_description="Foto tahrirlash",
            version="2026",
            file_size=2500000000
        )
        await dl_service.record_download(user_telegram_id=test_user.telegram_id, program_id=prog.id)

        # ---------------------------------------------------------------------
        # Test 1: /start Command Response & ReplyKeyboard
        # ---------------------------------------------------------------------
        try:
            mock_msg = AsyncMock()
            mock_msg.from_user.id = 777888999
            mock_msg.from_user.first_name = "TestUser"
            mock_msg.from_user.last_name = None
            mock_msg.from_user.username = "testuser"
            mock_msg.from_user.language_code = "uz"

            await user_start_handler(mock_msg)

            assert mock_msg.answer.called
            call_kwargs = mock_msg.answer.call_args[1]
            assert "Software Store botiga xush kelibsiz" in call_kwargs["text"]
            assert call_kwargs["reply_markup"] is not None
            logger.info("✅ Test 1 Passed: /start welcome message & ReplyKeyboard sent")
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test 1 Failed: {e}")
            failed += 1

        # ---------------------------------------------------------------------
        # Test 2: 📂 Kategoriyalar Dynamic Category InlineKeyboard
        # ---------------------------------------------------------------------
        try:
            mock_msg = MagicMock(spec=Message)
            mock_msg.answer = AsyncMock()
            await categories_menu_handler(mock_msg)
            assert mock_msg.answer.called
            call_kwargs = mock_msg.answer.call_args[1]
            assert "DASTUR KATEGORIYALARI" in call_kwargs["text"]
            assert call_kwargs["reply_markup"] is not None
            logger.info("✅ Test 2 Passed: Dynamic categories menu rendered with InlineKeyboard")
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test 2 Failed: {e}")
            failed += 1

        # ---------------------------------------------------------------------
        # Test 3: Category Selection & Program List
        # ---------------------------------------------------------------------
        try:
            mock_cb = MagicMock(spec=CallbackQuery)
            mock_cb.from_user = MagicMock()
            mock_cb.from_user.id = 123
            mock_cb.answer = AsyncMock()
            mock_cb.data = f"category:view:{cat.id}"
            mock_cb.message = MagicMock(spec=Message)
            mock_cb.message.edit_text = AsyncMock()

            mock_state = AsyncMock()
            mock_state.get_data = AsyncMock(return_value={})
            await category_view_handler(mock_cb, state=mock_state)

            assert mock_cb.message.edit_text.called
            call_text = str(mock_cb.message.edit_text.call_args)
            assert cat.name.upper() in call_text
            logger.info("✅ Test 3 Passed: Category selection rendered program list")
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test 3 Failed: {e}")
            failed += 1

        # ---------------------------------------------------------------------
        # Test 4: Program Selection & Detail Page Layout
        # ---------------------------------------------------------------------
        try:
            mock_cb = MagicMock(spec=CallbackQuery)
            mock_cb.from_user = MagicMock()
            mock_cb.from_user.id = 123
            mock_cb.answer = AsyncMock()
            mock_cb.data = f"program:view:{prog.id}"
            mock_cb.message = MagicMock(spec=Message)
            mock_cb.message.edit_text = AsyncMock()

            mock_state = AsyncMock()
            mock_state.get_data = AsyncMock(return_value={})
            await program_view_handler(mock_cb, state=mock_state)

            assert mock_cb.message.edit_text.called
            call_text = str(mock_cb.message.edit_text.call_args)
            assert prog.name in call_text
            assert "YUKLAB OLISH" in str(mock_cb.message.edit_text.call_args)
            logger.info("✅ Test 4 Passed: Program detail page layout correct")
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test 4 Failed: {e}")
            failed += 1

        # ---------------------------------------------------------------------
        # Test 5: Back Navigation Callbacks
        # ---------------------------------------------------------------------
        try:
            mock_cb = MagicMock(spec=CallbackQuery)
            mock_cb.from_user = MagicMock()
            mock_cb.from_user.id = 123
            mock_cb.answer = AsyncMock()
            mock_cb.data = "back:categories"
            mock_cb.message = MagicMock(spec=Message)
            mock_cb.message.answer = AsyncMock()
            mock_cb.message.edit_text = AsyncMock()

            mock_state = AsyncMock()
            mock_state.get_data = AsyncMock(return_value={})
            await back_to_categories_handler(mock_cb, state=mock_state)

            mock_cb_main = MagicMock(spec=CallbackQuery)
            mock_cb_main.from_user = MagicMock()
            mock_cb_main.from_user.id = 123
            mock_cb_main.answer = AsyncMock()
            mock_cb_main.data = "back:main"
            mock_cb_main.message = MagicMock(spec=Message)
            mock_cb_main.message.answer = AsyncMock()
            mock_cb_main.message.edit_text = AsyncMock()

            await back_to_main_handler(mock_cb_main, state=AsyncMock())

            logger.info("✅ Test 5 Passed: Back navigation callbacks (back:categories, back:main) working")
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test 5 Failed: {e}")
            failed += 1

        # ---------------------------------------------------------------------
        # Test 6: 🔥 Mashhur dasturlar (downloads_count DESC)
        # ---------------------------------------------------------------------
        try:
            mock_msg = MagicMock(spec=Message)
            mock_msg.from_user = MagicMock()
            mock_msg.from_user.id = 123
            mock_msg.answer = AsyncMock()
            await popular_menu_handler(mock_msg, state=AsyncMock())
            assert mock_msg.answer.called
            call_text = str(mock_msg.answer.call_args)
            assert "ENG KO'P YUKLAB OLINGAN DASTURLAR" in call_text
            logger.info("✅ Test 6 Passed: Popular programs handler working")
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test 6 Failed: {e}")
            failed += 1

        # ---------------------------------------------------------------------
        # Test 7: 🆕 Yangi dasturlar (created_at DESC)
        # ---------------------------------------------------------------------
        try:
            mock_msg = MagicMock(spec=Message)
            mock_msg.from_user = MagicMock()
            mock_msg.from_user.id = 123
            mock_msg.answer = AsyncMock()
            await new_programs_menu_handler(mock_msg, state=AsyncMock())
            assert mock_msg.answer.called
            call_text = str(mock_msg.answer.call_args)
            assert "YANGI DASTURLAR" in call_text
            logger.info("✅ Test 7 Passed: New programs handler working")
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test 7 Failed: {e}")
            failed += 1

        # ---------------------------------------------------------------------
        # Test 8: 📥 Yuklab olishlarim History UI
        # ---------------------------------------------------------------------
        try:
            mock_msg = MagicMock(spec=Message)
            mock_msg.from_user = MagicMock()
            mock_msg.from_user.id = 777888999
            mock_msg.answer = AsyncMock()
            await user_downloads_menu_handler(mock_msg, state=AsyncMock())
            assert mock_msg.answer.called
            call_text = str(mock_msg.answer.call_args)
            assert "YUKLAB OLISHLARIM" in call_text
            logger.info("✅ Test 8 Passed: User download history rendered correctly")
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test 8 Failed: {e}")
            failed += 1

        # ---------------------------------------------------------------------
        # Test 9: ℹ️ Bot haqida Page
        # ---------------------------------------------------------------------
        try:
            mock_msg = MagicMock(spec=Message)
            mock_msg.answer = AsyncMock()
            await about_menu_handler(mock_msg)
            assert mock_msg.answer.called
            call_text = mock_msg.answer.call_args[0][0]
            assert "SOFTWARE STORE" in call_text
            logger.info("✅ Test 9 Passed: About page handler working")
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test 9 Failed: {e}")
            failed += 1

        # ---------------------------------------------------------------------
        # Test 10: 🔎 Qidirish State Activation
        # ---------------------------------------------------------------------
        try:
            mock_msg = MagicMock(spec=Message)
            mock_msg.answer = AsyncMock()
            mock_state = AsyncMock()
            await search_menu_handler(mock_msg, mock_state)
            assert mock_state.set_state.called
            assert mock_msg.answer.called
            logger.info("✅ Test 10 Passed: Search FSM state activated with cancel keyboard")
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test 10 Failed: {e}")
            failed += 1

    await test_engine.dispose()

    logger.info("==========================================")
    logger.info(f"Stage 4 UI Tests Summary: {passed} Passed, {failed} Failed")
    logger.info("==========================================")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_stage4_tests())
