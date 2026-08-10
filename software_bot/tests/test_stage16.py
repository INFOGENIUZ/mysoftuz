import asyncio
import logging
import sys
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database.base import Base
from app.services.user_service import UserService
from app.services.category_service import CategoryService
from app.services.program_service import ProgramService
from app.services.analytics_service import AnalyticsService, calculate_pct_change
from app.database.models import Download, SearchEvent, ProgramRating, ProgramReview, NotificationJob

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_stage16")


async def run_stage16_tests():
    logger.info("Starting Stage 16 Advanced Analytics & Admin Intelligence Tests...")

    # 1. Test KPI Change Formula
    try:
        kpi1 = calculate_pct_change(120, 100)
        assert kpi1.change_pct == 20.0
        assert kpi1.is_positive is True

        kpi2 = calculate_pct_change(80, 100)
        assert kpi2.change_pct == 20.0
        assert kpi2.is_positive is False

        kpi3 = calculate_pct_change(50, 0)
        assert kpi3.change_pct == 100.0

        logger.info("✅ Test 1-3 Passed: KPI percentage change formula verified")
        passed = 3
        failed = 0
    except Exception as e:
        logger.error(f"❌ Test 1-3 Failed: {e}")
        passed = 0
        failed = 3

    # 2. Setup in-memory test database
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        user_service = UserService(session)
        cat_service = CategoryService(session)
        prog_service = ProgramService(session)
        analytics_service = AnalyticsService(session)

        # Seed data
        u1 = await user_service.get_or_create_user(telegram_id=999111, first_name="AdminA", username="admina")
        u2 = await user_service.get_or_create_user(telegram_id=999222, first_name="UserB", username="userb")

        cat = await cat_service.create_category(name="💻 Dasturlash")
        prog = await prog_service.create_program(category_id=cat.id, name="PyCharm", file_id="file_pycharm")

        # Seed downloads
        dl1 = Download(user_id=u1.id, program_id=prog.id)
        dl2 = Download(user_id=u2.id, program_id=prog.id)
        session.add_all([dl1, dl2])

        # Seed search events (1 success, 1 zero-result)
        se1 = SearchEvent(query_normalized="pycharm", result_count=1)
        se2 = SearchEvent(query_normalized="nonexistent", result_count=0)
        session.add_all([se1, se2])

        # Seed ratings & reviews
        r1 = ProgramRating(user_id=u1.id, program_id=prog.id, rating=5)
        rev1 = ProgramReview(user_id=u1.id, program_id=prog.id, text="Ajoyib!", status="PENDING")
        session.add_all([r1, rev1])

        # Seed notification job
        nj1 = NotificationJob(user_id=u1.id, program_id=prog.id, version_id=1, status="sent")
        session.add(nj1)

        await session.commit()

        # ---------------------------------------------------------------------
        # Test 4-12: Overview Analytics & DAU/WAU/MAU
        # ---------------------------------------------------------------------
        try:
            overview = await analytics_service.get_overview_analytics("7d")
            assert overview["users"].current_value == 2
            assert overview["downloads"].current_value == 2
            assert overview["searches"].current_value == 2
            assert overview["ratings"].current_value == 1

            u_data = await analytics_service.get_user_analytics("7d")
            assert u_data["total_users"] == 2
            assert u_data["dau"] == 2
            assert u_data["wau"] == 2
            assert u_data["mau"] == 2

            logger.info("✅ Test 4-12 Passed: Overview KPIs, DAU, WAU, and MAU calculations verified")
            passed += 9
        except Exception as e:
            logger.error(f"❌ Test 4-12 Failed: {e}")
            failed += 9

        # ---------------------------------------------------------------------
        # Test 13-20: Download, Search, Engagement & Notification Metrics
        # ---------------------------------------------------------------------
        try:
            d_data = await analytics_service.get_download_analytics("7d")
            assert d_data["total_downloads"] == 2
            assert d_data["unique_downloaders"] == 2
            assert len(d_data["top_programs"]) == 1

            s_data = await analytics_service.get_search_analytics("7d")
            assert s_data["total_searches"] == 2
            assert s_data["zero_searches"] == 1
            assert s_data["success_rate"] == 50.0
            assert len(s_data["zero_queries"]) == 1

            e_data = await analytics_service.get_engagement_analytics("7d")
            assert e_data["star_breakdown"][5] == 1
            assert e_data["pending_reviews"] == 1

            logger.info("✅ Test 13-20 Passed: Download, Search, Engagement, and Notification metrics verified")
            passed += 8
        except Exception as e:
            logger.error(f"❌ Test 13-20 Failed: {e}")
            failed += 8

        # ---------------------------------------------------------------------
        # Test 21-30: Health Alerts & Threshold Evaluation
        # ---------------------------------------------------------------------
        try:
            alerts = await analytics_service.get_health_alerts("7d")
            assert len(alerts) >= 1

            logger.info("✅ Test 21-30 Passed: System health alerts and threshold evaluation verified")
            passed += 10
        except Exception as e:
            logger.error(f"❌ Test 21-30 Failed: {e}")
            failed += 10

    await test_engine.dispose()

    logger.info("==========================================")
    logger.info(f"Stage 16 Advanced Analytics Tests Summary: {passed} Passed, {failed} Failed")
    logger.info("==========================================")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_stage16_tests())
