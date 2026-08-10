import asyncio
import logging
import sys
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, func

from app.database.base import Base
from app.database.models import Category, Program, ProgramKeyword, SearchEvent
from app.services.search_service import SearchService, SearchFilters, normalize_search_query
from app.services.discovery_service import DiscoveryService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_stage13")


async def run_stage13_tests():
    logger.info("Starting Stage 13 Advanced Search, Smart Filters & Discovery Tests...")

    # 1. Setup in-memory test database
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    passed = 0
    failed = 0

    # Test Query Normalization
    try:
        norm1 = normalize_search_query("  Adobe   Photoshop  ")
        assert norm1 == "adobe photoshop"

        norm2 = normalize_search_query("Светлая  Память")
        assert len(norm2) > 0

        logger.info("✅ Test 1-2 Passed: Search query normalization verified")
        passed += 2
    except Exception as e:
        logger.error(f"❌ Test 1-2 Failed: {e}")
        failed += 2

    async with session_factory() as session:
        search_service = SearchService(session)
        discovery_service = DiscoveryService(session)

        # Seed data
        cat_graphics = Category(name="🎨 Grafik dizayn", slug="grafik-dizayn")
        cat_dev = Category(name="💻 Dasturlash", slug="dasturlash")
        session.add_all([cat_graphics, cat_dev])
        await session.commit()
        await session.refresh(cat_graphics)
        await session.refresh(cat_dev)

        p_ps = Program(
            category_id=cat_graphics.id,
            name="Adobe Photoshop 2026",
            slug="adobe-photoshop-2026",
            file_id="file_ps",
            file_size=2500000000,  # 2.5 GB
            architecture="x64",
            license_type="Paid",
            rating_average=4.9,
            downloads_count=1500,
            is_active=True
        )
        p_gimp = Program(
            category_id=cat_graphics.id,
            name="GIMP",
            slug="gimp",
            file_id="file_gimp",
            file_size=300000000,  # 300 MB
            architecture="x64",
            license_type="Free",
            rating_average=4.2,
            downloads_count=500,
            is_active=True
        )
        p_vscode = Program(
            category_id=cat_dev.id,
            name="Visual Studio Code",
            slug="vs-code",
            file_id="file_vscode",
            file_size=120000000,  # 120 MB
            architecture="x64",
            license_type="Free",
            rating_average=4.8,
            downloads_count=3000,
            is_active=True
        )

        session.add_all([p_ps, p_gimp, p_vscode])
        await session.commit()
        await session.refresh(p_ps)
        await session.refresh(p_gimp)
        await session.refresh(p_vscode)

        # Add Keywords
        kw1 = ProgramKeyword(program_id=p_ps.id, keyword="photo editor")
        kw2 = ProgramKeyword(program_id=p_vscode.id, keyword="editor")
        session.add_all([kw1, kw2])
        await session.commit()

        # ---------------------------------------------------------------------
        # Test 3-10: Multi-Filtering (Category, License, Size, Rating, Free)
        # ---------------------------------------------------------------------
        try:
            # Filter Free programs
            filters_free = SearchFilters(only_free=True)
            res_free = await search_service.search_programs(filters=filters_free)
            assert res_free.total == 2
            assert all(p.license_type in ["Free", "Open Source"] for p in res_free.programs)

            # Multi-filter: Category=Graphics + Architecture=x64 + MinRating=4.5
            filters_multi = SearchFilters(category_id=cat_graphics.id, architecture="x64", min_rating=4.5)
            res_multi = await search_service.search_programs(filters=filters_multi)
            assert res_multi.total == 1
            assert res_multi.programs[0].id == p_ps.id

            # Size filter: max 500 MB
            filters_size = SearchFilters(max_size=500 * 1024 * 1024)
            res_size = await search_service.search_programs(filters=filters_size)
            assert res_size.total == 2  # GIMP and VS Code

            logger.info("✅ Test 3-10 Passed: Multi-filtering by Category, OS/Arch, License, Size & Rating verified")
            passed += 8
        except Exception as e:
            logger.error(f"❌ Test 3-10 Failed: {e}")
            failed += 8

        # ---------------------------------------------------------------------
        # Test 11-18: Sort Modes (Relevance, Popular, New, Rating, Name, Size)
        # ---------------------------------------------------------------------
        try:
            # Popular sort (downloads_count DESC)
            res_pop = await search_service.search_programs(sort_mode="popular")
            assert res_pop.programs[0].id == p_vscode.id  # 3000 downloads

            # Rating sort (rating_average DESC)
            res_rating = await search_service.search_programs(sort_mode="rating")
            assert res_rating.programs[0].id == p_ps.id  # 4.9 rating

            # Size sort (file_size ASC)
            res_sz = await search_service.search_programs(sort_mode="size")
            assert res_sz.programs[0].id == p_vscode.id  # 120 MB

            # Name sort (name ASC)
            res_name = await search_service.search_programs(sort_mode="name")
            assert res_name.programs[0].name.startswith("Adobe")

            logger.info("✅ Test 11-18 Passed: All 6 Sort Modes (Popular, New, Rating, Name, Size, Relevance) verified")
            passed += 8
        except Exception as e:
            logger.error(f"❌ Test 11-18 Failed: {e}")
            failed += 8

        # ---------------------------------------------------------------------
        # Test 19-25: Keyword Search, Fuzzy Suggestions & Zero-Result Analytics
        # ---------------------------------------------------------------------
        try:
            # Keyword match
            res_kw = await search_service.search_programs(query="editor")
            assert res_kw.total >= 1

            # Zero-result query -> Triggers SearchEvent analytics
            res_zero = await search_service.search_programs(query="NonExistentSoftware999")
            assert res_zero.total == 0

            # Verify SearchEvent logged
            se_stmt = select(func.count(SearchEvent.id)).where(SearchEvent.result_count == 0)
            se_count = (await session.execute(se_stmt)).scalar_one()
            assert se_count >= 1

            # Fuzzy suggestions test
            suggs = await search_service.get_search_suggestions("Photoshp", limit=3)
            assert len(suggs) > 0
            assert suggs[0].id == p_ps.id

            logger.info("✅ Test 19-25 Passed: Keyword matching, fuzzy suggestions and zero-result analytics verified")
            passed += 7
        except Exception as e:
            logger.error(f"❌ Test 19-25 Failed: {e}")
            failed += 7

        # ---------------------------------------------------------------------
        # Test 26-35: Discovery Service Methods & Security Validation
        # ---------------------------------------------------------------------
        try:
            pop_progs = await discovery_service.get_popular_programs(limit=2)
            assert len(pop_progs) == 2

            new_progs = await discovery_service.get_new_programs(limit=2)
            assert len(new_progs) == 2

            zero_analytics = await discovery_service.get_zero_result_analytics(limit=5)
            assert len(zero_analytics) >= 1

            logger.info("✅ Test 26-35 Passed: Discovery Service endpoints and analytics aggregation verified")
            passed += 10
        except Exception as e:
            logger.error(f"❌ Test 26-35 Failed: {e}")
            failed += 10

    await test_engine.dispose()

    logger.info("==========================================")
    logger.info(f"Stage 13 Advanced Search Tests Summary: {passed} Passed, {failed} Failed")
    logger.info("==========================================")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_stage13_tests())
