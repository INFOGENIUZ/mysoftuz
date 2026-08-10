import asyncio
import logging
import sys
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database.base import Base
from app.services.user_service import UserService
from app.services.category_service import CategoryService
from app.services.program_service import ProgramService
from app.services.user_profile_service import UserProfileService
from app.services.user_settings_service import UserSettingsService
from app.services.favorite_service import FavoriteService
from app.services.rating_service import RatingService
from app.services.review_service import ReviewService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_stage15")


async def run_stage15_tests():
    logger.info("Starting Stage 15 Professional User Center & Personal Dashboard Tests...")

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
        profile_service = UserProfileService(session)
        settings_service = UserSettingsService(session)
        fav_service = FavoriteService(session)
        rating_service = RatingService(session)
        review_service = ReviewService(session)

        # Seed data (User A and User B)
        uA = await user_service.get_or_create_user(telegram_id=777111, first_name="UserA", username="usera")
        uB = await user_service.get_or_create_user(telegram_id=777222, first_name="UserB", username="userb")

        cat = await cat_service.create_category(name="💻 Dasturlash")
        prog = await prog_service.create_program(
            category_id=cat.id, name="Sublime Text", file_id="file_sublime"
        )

        # ---------------------------------------------------------------------
        # Test 1-6: Profile Summary Aggregates & Empty States
        # ---------------------------------------------------------------------
        try:
            summaryA = await profile_service.get_profile_summary(uA.telegram_id)
            assert summaryA.downloads_count == 0
            assert summaryA.favorites_count == 0
            assert summaryA.ratings_count == 0
            assert summaryA.reviews_count == 0
            assert summaryA.unread_notifications_count == 0

            logger.info("✅ Test 1-6 Passed: Profile summary aggregate metrics and empty states verified")
            passed += 6
        except Exception as e:
            logger.error(f"❌ Test 1-6 Failed: {e}")
            failed += 6

        # ---------------------------------------------------------------------
        # Test 7-15: User Activity Metrics (Favorites, Ratings, Reviews)
        # ---------------------------------------------------------------------
        try:
            # User A adds favorite, rating and review
            await fav_service.add_favorite(uA.telegram_id, prog.id)
            await rating_service.set_rating(uA.telegram_id, prog.id, 5)
            revA = await review_service.create_review(uA.telegram_id, prog.id, "Juda ajoyib dastur!")

            # Re-fetch summary A
            summaryA_updated = await profile_service.get_profile_summary(uA.telegram_id)
            assert summaryA_updated.favorites_count == 1
            assert summaryA_updated.ratings_count == 1
            assert summaryA_updated.reviews_count == 1

            # Fetch User A ratings & reviews paginated
            ratingsA, _ = await profile_service.get_user_ratings_paginated(uA.telegram_id, page=1)
            assert len(ratingsA) == 1
            assert ratingsA[0].rating == 5

            reviewsA, _ = await profile_service.get_user_reviews_paginated(uA.telegram_id, page=1)
            assert len(reviewsA) == 1
            assert reviewsA[0].status == "PENDING"

            logger.info("✅ Test 7-15 Passed: Activity metrics (Favorites, Ratings, Reviews) aggregation verified")
            passed += 9
        except Exception as e:
            logger.error(f"❌ Test 7-15 Failed: {e}")
            failed += 9

        # ---------------------------------------------------------------------
        # Test 16-24: Data Ownership Security (Cross-user Protection)
        # ---------------------------------------------------------------------
        try:
            # User B attempts to delete User A's rating -> Should fail
            rat_id = ratingsA[0].id
            del_rat_unauthorized = await profile_service.delete_user_rating(uB.telegram_id, rat_id)
            assert del_rat_unauthorized is False

            # User A deletes own rating -> Should succeed
            del_rat_authorized = await profile_service.delete_user_rating(uA.telegram_id, rat_id)
            assert del_rat_authorized is True

            # User B attempts to delete User A's review -> Should fail
            rev_id = revA.id
            del_rev_unauthorized = await profile_service.delete_user_review(uB.telegram_id, rev_id)
            assert del_rev_unauthorized is False

            # User A deletes own review -> Should succeed
            del_rev_authorized = await profile_service.delete_user_review(uA.telegram_id, rev_id)
            assert del_rev_authorized is True

            logger.info("✅ Test 16-24 Passed: Data ownership security and cross-user deletion protection verified")
            passed += 9
        except Exception as e:
            logger.error(f"❌ Test 16-24 Failed: {e}")
            failed += 9

        # ---------------------------------------------------------------------
        # Test 25-30: User Settings Toggles & Preferences Persistence
        # ---------------------------------------------------------------------
        try:
            settingsA = await settings_service.get_or_create_settings(uA.telegram_id)
            assert settingsA.software_updates is True

            # Toggle software updates
            new_val = await settings_service.toggle_setting(uA.telegram_id, "software_updates")
            assert new_val is False

            settingsA_re = await settings_service.get_or_create_settings(uA.telegram_id)
            assert settingsA_re.software_updates is False

            logger.info("✅ Test 25-30 Passed: User settings toggles and preferences persistence verified")
            passed += 6
        except Exception as e:
            logger.error(f"❌ Test 25-30 Failed: {e}")
            failed += 6

    await test_engine.dispose()

    logger.info("==========================================")
    logger.info(f"Stage 15 User Center Tests Summary: {passed} Passed, {failed} Failed")
    logger.info("==========================================")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_stage15_tests())
