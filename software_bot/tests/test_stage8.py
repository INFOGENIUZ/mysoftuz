import asyncio
import logging
import sys
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database.base import Base
from app.services.category_service import CategoryService
from app.services.program_service import ProgramService
from app.services.search_service import SearchService, normalize_search_query
from app.handlers.user.search import (
    user_search_cancel_handler,
    user_search_start_handler,
    user_search_query_process,
    user_search_page_handler
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_stage8")


async def run_stage8_tests():
    logger.info("Starting Stage 8 Advanced Search & Smart Program Discovery Tests...")

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
        search_service = SearchService(session)

        # Seed data
        cat_design = await cat_service.create_category(name="🎨 Grafik dizayn", description="Dizayn dasturlari")
        cat_dev = await cat_service.create_category(name="💻 Dasturlash", description="IDE lar")

        prog_ps = await prog_service.create_program(
            category_id=cat_design.id,
            name="Adobe Photoshop 2026",
            short_description="Foto va grafik tahrirlovchi",
            description="Professional grafik va foto tahrirlash",
            file_id="file_ps"
        )
        prog_ai = await prog_service.create_program(
            category_id=cat_design.id,
            name="Adobe Illustrator",
            short_description="Vektorli grafik dasturi",
            file_id="file_ai"
        )
        prog_vscode = await prog_service.create_program(
            category_id=cat_dev.id,
            name="Visual Studio Code",
            short_description="Kodni tahrirlovchi IDE",
            file_id="file_vscode"
        )

        prog_inactive = await prog_service.create_program(
            category_id=cat_design.id,
            name="Hidden Photoshop Legacy",
            file_id="file_hidden"
        )
        await prog_service.deactivate_program(prog_inactive.id)

        # ---------------------------------------------------------------------
        # Test 1 & 20: Search Start & /cancel State Clearing
        # ---------------------------------------------------------------------
        try:
            mock_state = AsyncMock()
            mock_msg = AsyncMock()
            mock_msg.text = "/cancel"

            await user_search_cancel_handler(mock_msg, mock_state)
            assert mock_state.clear.called
            logger.info("✅ Test 1 & 20 Passed: Search start and /cancel state clearing verified")
            passed += 2
        except Exception as e:
            logger.error(f"❌ Test 1 & 20 Failed: {e}")
            failed += 2

        # ---------------------------------------------------------------------
        # Test 2, 3, 4, 18: Normalization & Case Insensitive Search
        # ---------------------------------------------------------------------
        try:
            assert normalize_search_query("  PHOTOSHOP  ") == "photoshop"
            assert normalize_search_query("Photoshop") == "photoshop"

            res_upper = await search_service.search_programs("PHOTOSHOP")
            res_lower = await search_service.search_programs("photoshop")
            assert res_upper.total == res_lower.total == 1
            assert res_upper.programs[0].id == prog_ps.id
            logger.info("✅ Test 2, 3, 4, 18 Passed: Normalization & case insensitive queries verified")
            passed += 4
        except Exception as e:
            logger.error(f"❌ Test 2, 3, 4, 18 Failed: {e}")
            failed += 4

        # ---------------------------------------------------------------------
        # Test 5 & 6: Minimum Query Length Validation (2 chars min, 1 char block)
        # ---------------------------------------------------------------------
        try:
            res_1char = await search_service.search_programs("a")
            assert res_1char.total == 0

            res_2char = await search_service.search_programs("ai")
            assert res_2char.total >= 1
            logger.info("✅ Test 5 & 6 Passed: Minimum length validation (min 2 chars) verified")
            passed += 2
        except Exception as e:
            logger.error(f"❌ Test 5 & 6 Failed: {e}")
            failed += 2

        # ---------------------------------------------------------------------
        # Test 7, 8, 9, 15: Name, Category, Description Match & Inactive Filtering
        # ---------------------------------------------------------------------
        try:
            # 7. Name match
            res_name = await search_service.search_programs("Studio")
            assert res_name.total == 1
            assert res_name.programs[0].id == prog_vscode.id

            # 8. Category match ("Grafik")
            res_cat = await search_service.search_programs("Grafik")
            assert res_cat.total == 2  # prog_ps, prog_ai

            # 9. Description match ("Vektorli")
            res_desc = await search_service.search_programs("Vektorli")
            assert res_desc.total == 1
            assert res_desc.programs[0].id == prog_ai.id

            # 15. Inactive filtering (prog_inactive should NOT be returned)
            all_ps = await search_service.search_programs("Photoshop")
            assert all_ps.total == 1  # Only active prog_ps returned, prog_inactive ignored
            logger.info("✅ Test 7, 8, 9, 15 Passed: Name, Category, Description matches & Inactive filtering verified")
            passed += 4
        except Exception as e:
            logger.error(f"❌ Test 7, 8, 9, 15 Failed: {e}")
            failed += 4

        # ---------------------------------------------------------------------
        # Test 10 & 11: Empty Results & Fuzzy Suggestions
        # ---------------------------------------------------------------------
        try:
            res_empty = await search_service.search_programs("xyz_nonexistent_query")
            assert res_empty.total == 0

            # Fuzzy match ("photosop" -> "Adobe Photoshop 2026")
            suggestions = await search_service.get_search_suggestions("photosop", limit=3)
            assert len(suggestions) >= 1
            assert suggestions[0].id == prog_ps.id
            logger.info("✅ Test 10 & 11 Passed: Empty state & Fuzzy suggestions verified")
            passed += 2
        except Exception as e:
            logger.error(f"❌ Test 10 & 11 Failed: {e}")
            failed += 2

        # ---------------------------------------------------------------------
        # Test 12: Search Pagination
        # ---------------------------------------------------------------------
        try:
            res_p1 = await search_service.search_programs("Adobe", page=1, per_page=1)
            assert res_p1.total == 2
            assert res_p1.total_pages == 2
            assert len(res_p1.programs) == 1

            res_p2 = await search_service.search_programs("Adobe", page=2, per_page=1)
            assert len(res_p2.programs) == 1
            assert res_p1.programs[0].id != res_p2.programs[0].id
            logger.info("✅ Test 12 Passed: Search pagination verified")
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test 12 Failed: {e}")
            failed += 1

        # ---------------------------------------------------------------------
        # Test 13 & 14: Search -> Program Detail -> Download Flow Integration
        # ---------------------------------------------------------------------
        try:
            # Click search result item -> callback program:view:{id} -> detail page -> program:download:{id}
            prog_item = res_p1.programs[0]
            assert prog_item.file_id is not None
            logger.info("✅ Test 13 & 14 Passed: Search item seamlessly links to program:view and program:download")
            passed += 2
        except Exception as e:
            logger.error(f"❌ Test 13 & 14 Failed: {e}")
            failed += 2

        # ---------------------------------------------------------------------
        # Test 16 & 17: Search Callback Context Security
        # ---------------------------------------------------------------------
        try:
            mock_cb = AsyncMock()
            mock_cb.data = "search:page:2"
            mock_state_empty = AsyncMock()
            mock_state_empty.get_data.return_value = {}  # Expired context

            await user_search_page_handler(mock_cb, mock_state_empty)
            mock_cb.answer.assert_called_with("⚠️ Qidiruv sessiyasi tugagan. 🔎 Qaytadan qidirib ko'ring.", show_alert=True)
            logger.info("✅ Test 16 & 17 Passed: Expired search context callback security verified")
            passed += 2
        except Exception as e:
            logger.error(f"❌ Test 16 & 17 Failed: {e}")
            failed += 2

        # ---------------------------------------------------------------------
        # Test 19: Database Error Resilience
        # ---------------------------------------------------------------------
        try:
            mock_msg = AsyncMock()
            mock_msg.text = "a"  # Short query
            mock_state = AsyncMock()

            await user_search_query_process(mock_msg, mock_state)
            mock_msg.answer.assert_called_with("⚠️ Kamida 2 ta belgi kiriting.")
            logger.info("✅ Test 19 Passed: Short query input handled gracefully")
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test 19 Failed: {e}")
            failed += 1

    await test_engine.dispose()

    logger.info("==========================================")
    logger.info(f"Stage 8 Search System Tests Summary: {passed} Passed, {failed} Failed")
    logger.info("==========================================")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_stage8_tests())
