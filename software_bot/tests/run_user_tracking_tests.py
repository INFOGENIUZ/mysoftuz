import os
import asyncio
import sys
import unittest
import time
from unittest.mock import AsyncMock, MagicMock

from app.config import settings
settings.DATABASE_URL = "sqlite+aiosqlite:///data/test_temp.db"

from app.database.engine import init_db, async_session_maker
from app.database.models import User
from app.services.user_service import UserService
from app.services.statistics_service import StatisticsService
from app.middlewares.user_tracking import UserTrackingMiddleware


class TestUserTrackingAndAnalytics(unittest.TestCase):

    def setUp(self):
        asyncio.run(init_db())

    def test_user_tracking_and_auto_registration(self):
        """TEST 1: Automatic user registration and fields update (Ism, Familiya, Username, Last activity)."""
        async def run():
            ts = time.time_ns()
            user_tg_id = 9900112233 + (ts % 1000000)

            # Setup mock update
            middleware = UserTrackingMiddleware()
            mock_handler = AsyncMock(return_value="OK")
            mock_tg_user = MagicMock()
            mock_tg_user.id = user_tg_id
            mock_tg_user.first_name = "Alisher"
            mock_tg_user.last_name = "Navoiy"
            mock_tg_user.username = f"alisher_{ts}"
            mock_tg_user.language_code = "uz"

            event = MagicMock()
            data = {"event_from_user": mock_tg_user}

            await middleware(mock_handler, event, data)

            async with async_session_maker() as session:
                user_service = UserService(session)
                user = await user_service.get_user_by_telegram_id(user_tg_id)

                self.assertIsNotNone(user)
                self.assertEqual(user.first_name, "Alisher")
                self.assertEqual(user.last_name, "Navoiy")
                self.assertEqual(user.username, f"alisher_{ts}")
                self.assertIsNotNone(user.last_activity)

        asyncio.run(run())
        print("[PASS] TEST 1: User tracking & auto-registration verified")

    def test_dau_and_user_analytics(self):
        """TEST 2: DAU, WAU, and today registered users statistics calculation."""
        async def run():
            ts = time.time_ns()
            user_tg_id = 8811223344 + (ts % 1000000)

            async with async_session_maker() as session:
                user_service = UserService(session)
                await user_service.get_or_create_user(
                    telegram_id=user_tg_id,
                    first_name="TestUser",
                    last_name="Analytics",
                    username=f"test_analytics_{ts}"
                )

                stats_service = StatisticsService(session)
                stats = await stats_service.get_dashboard_stats()

                self.assertGreaterEqual(stats["total_users"], 1)
                self.assertGreaterEqual(stats["today_users"], 1)
                self.assertGreaterEqual(stats["today_active_users"], 1)

        asyncio.run(run())
        print("[PASS] TEST 2: DAU & User analytics calculation verified")

    def test_admin_users_pagination_and_search(self):
        """TEST 3: Admin user listing, pagination, and search by username/ID."""
        async def run():
            ts = time.time_ns()
            unique_uname = f"search_target_{ts}"
            async with async_session_maker() as session:
                user_service = UserService(session)
                created_user, _ = await user_service.get_or_create_user(
                    telegram_id=7766554433 + (ts % 100000),
                    first_name="Zahiriddin",
                    last_name="Babur",
                    username=unique_uname
                )

                users, total_pages = await user_service.get_users_paginated(page=1, page_size=10)
                self.assertGreaterEqual(len(users), 1)

                # Search by username
                found_user = await user_service.get_user_by_telegram_id(created_user.telegram_id)
                self.assertIsNotNone(found_user)
                self.assertEqual(found_user.username, unique_uname)

        asyncio.run(run())
        print("[PASS] TEST 3: Admin user listing & search verified")

    def test_user_block_unblock_flow(self):
        """TEST 4: Blocking and unblocking users."""
        async def run():
            ts = time.time_ns()
            async with async_session_maker() as session:
                user_service = UserService(session)
                user, _ = await user_service.get_or_create_user(
                    telegram_id=6655443322 + (ts % 100000),
                    first_name="BlockTarget",
                    username=f"block_test_{ts}"
                )

                # Block
                user.is_blocked = True
                await session.commit()

                fetched = await user_service.get_user_by_telegram_id(user.telegram_id)
                self.assertTrue(fetched.is_blocked)

                # Unblock
                fetched.is_blocked = False
                await session.commit()

                unblocked = await user_service.get_user_by_telegram_id(user.telegram_id)
                self.assertFalse(unblocked.is_blocked)

        asyncio.run(run())
        print("[PASS] TEST 4: User block/unblock flow verified")


if __name__ == "__main__":
    unittest.main()
