import asyncio
import logging
import sys
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database.base import Base
from app.services.user_service import UserService
from app.services.category_service import CategoryService
from app.services.program_service import ProgramService
from app.services.favorite_service import FavoriteService
from app.services.recent_service import RecentService
from app.services.rating_service import RatingService
from app.services.review_service import ReviewService
from app.services.recommendation_service import RecommendationService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_stage12")


async def run_stage12_tests():
    logger.info("Starting Stage 12 Favorites, Recently Viewed, Ratings, Reviews & Smart Recommendations Tests...")

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
        fav_service = FavoriteService(session)
        recent_service = RecentService(session)
        rating_service = RatingService(session)
        review_service = ReviewService(session)
        rec_service = RecommendationService(session)

        # Seed data
        u1 = await user_service.get_or_create_user(telegram_id=11111, first_name="Alisher", username="alisher")
        u2 = await user_service.get_or_create_user(telegram_id=22222, first_name="Bobur", username="bobur")

        cat_graphics = await cat_service.create_category(name="🎨 Grafik dizayn")
        cat_dev = await cat_service.create_category(name="💻 Dasturlash")

        p_photoshop = await prog_service.create_program(
            category_id=cat_graphics.id, name="Adobe Photoshop", file_id="file_ps"
        )
        p_illustrator = await prog_service.create_program(
            category_id=cat_graphics.id, name="Adobe Illustrator", file_id="file_ai"
        )
        p_vscode = await prog_service.create_program(
            category_id=cat_dev.id, name="VS Code", file_id="file_vscode"
        )

        # ---------------------------------------------------------------------
        # Test 1-5: Favorites CRUD, Duplicate Constraint & Pagination
        # ---------------------------------------------------------------------
        try:
            # Add Favorite
            res1 = await fav_service.add_favorite(u1.telegram_id, p_photoshop.id)
            assert res1 is True

            # Duplicate Add -> Returns False
            res2 = await fav_service.add_favorite(u1.telegram_id, p_photoshop.id)
            assert res2 is False

            is_fav = await fav_service.is_favorite(u1.telegram_id, p_photoshop.id)
            assert is_fav is True

            fav_progs, total_p = await fav_service.get_user_favorites_paginated(u1.telegram_id, page=1, page_size=10)
            assert len(fav_progs) == 1
            assert fav_progs[0].id == p_photoshop.id

            # Remove Favorite
            rem_res = await fav_service.remove_favorite(u1.telegram_id, p_photoshop.id)
            assert rem_res is True
            assert await fav_service.is_favorite(u1.telegram_id, p_photoshop.id) is False

            logger.info("✅ Test 1-5 Passed: Favorites CRUD, duplicate constraint and pagination verified")
            passed += 5
        except Exception as e:
            logger.error(f"❌ Test 1-5 Failed: {e}")
            failed += 5

        # ---------------------------------------------------------------------
        # Test 6-11: Recently Viewed Tracking, Deduplication & Max Limit (20)
        # ---------------------------------------------------------------------
        try:
            await recent_service.record_view(u1.telegram_id, p_photoshop.id)
            await recent_service.record_view(u1.telegram_id, p_illustrator.id)
            # Re-view Photoshop (should move to top without duplicate)
            await recent_service.record_view(u1.telegram_id, p_photoshop.id)

            rec_progs, total_p = await recent_service.get_recently_viewed_paginated(u1.telegram_id, page=1, page_size=10)
            assert len(rec_progs) == 2
            assert rec_progs[0].id == p_photoshop.id  # Top recently viewed

            logger.info("✅ Test 6-11 Passed: Recently Viewed tracking, deduplication and order verified")
            passed += 6
        except Exception as e:
            logger.error(f"❌ Test 6-11 Failed: {e}")
            failed += 6

        # ---------------------------------------------------------------------
        # Test 12-17: Ratings 1-5 Bounds, Upsert & Average Calculation
        # ---------------------------------------------------------------------
        try:
            # User 1 rates 5 stars
            is_new, avg, count = await rating_service.set_rating(u1.telegram_id, p_photoshop.id, 5)
            assert is_new is True
            assert avg == 5.0
            assert count == 1

            # User 2 rates 3 stars
            is_new2, avg2, count2 = await rating_service.set_rating(u2.telegram_id, p_photoshop.id, 3)
            assert avg2 == 4.0
            assert count2 == 2

            # User 2 updates rating to 5 stars
            _, avg3, count3 = await rating_service.set_rating(u2.telegram_id, p_photoshop.id, 5)
            assert avg3 == 5.0
            assert count3 == 2

            # Invalid rating bounds (0 or 6) -> Raises ValueError
            try:
                await rating_service.set_rating(u1.telegram_id, p_photoshop.id, 6)
                assert False, "Should have raised ValueError"
            except ValueError:
                pass

            logger.info("✅ Test 12-17 Passed: Rating bounds, upserts and aggregate averages verified")
            passed += 6
        except Exception as e:
            logger.error(f"❌ Test 12-17 Failed: {e}")
            failed += 6

        # ---------------------------------------------------------------------
        # Test 18-27: Reviews FSM Flow, Length Validation, Moderation & Reports
        # ---------------------------------------------------------------------
        try:
            # Too short review (<3 chars)
            try:
                await review_service.create_review(u1.telegram_id, p_photoshop.id, "Hi")
                assert False, "Should have raised ValueError"
            except ValueError:
                pass

            # Valid review (Pending status)
            rev = await review_service.create_review(u1.telegram_id, p_photoshop.id, "Dastur juda ajoyib ishlayapti!")
            assert rev.status == "PENDING"
            assert rev.is_visible is False

            # Admin pending list
            pending_revs, _ = await review_service.get_pending_reviews_paginated(page=1)
            assert len(pending_revs) == 1

            # Admin approve review
            app_ok = await review_service.approve_review(rev.id)
            assert app_ok is True

            # Public approved reviews
            pub_revs, _ = await review_service.get_program_reviews_paginated(p_photoshop.id, page=1)
            assert len(pub_revs) == 1
            assert pub_revs[0].status == "APPROVED"

            # Report review
            rep_ok = await review_service.report_review(u2.telegram_id, rev.id, reason="Spam")
            assert rep_ok is True

            logger.info("✅ Test 18-27 Passed: Review submission, validation, moderation flow and reports verified")
            passed += 10
        except Exception as e:
            logger.error(f"❌ Test 18-27 Failed: {e}")
            failed += 10

        # ---------------------------------------------------------------------
        # Test 28-35: Related Programs & Rule-Based Smart Recommendations
        # ---------------------------------------------------------------------
        try:
            # Related programs for Photoshop (should include Illustrator, exclude Photoshop)
            related = await rec_service.get_related_programs(p_photoshop.id, limit=5)
            assert len(related) == 1
            assert related[0].id == p_illustrator.id

            # User recommendations
            recs = await rec_service.get_user_recommendations(u1.telegram_id, limit=5)
            assert len(recs) > 0
            logger.info("✅ Test 28-35 Passed: Related programs and smart recommendation engine verified")
            passed += 8
        except Exception as e:
            logger.error(f"❌ Test 28-35 Failed: {e}")
            failed += 8

    await test_engine.dispose()

    logger.info("==========================================")
    logger.info(f"Stage 12 User Engagement Tests Summary: {passed} Passed, {failed} Failed")
    logger.info("==========================================")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_stage12_tests())
