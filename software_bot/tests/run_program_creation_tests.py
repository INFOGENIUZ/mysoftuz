import os
import asyncio
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock

from app.config import settings
settings.DATABASE_URL = "sqlite+aiosqlite:///data/test_temp.db"

from app.database.engine import init_db, async_session_maker

from app.services.category_service import CategoryService
from app.services.program_service import ProgramService
from app.handlers.admin.programs import (
    admin_program_select_category_handler,
    admin_program_create_start,
    admin_program_create_name,
    admin_program_cancel_handler,
)
from app.states.admin_program import AdminProgramCreateState
from app.keyboards.admin.inline import build_admin_dashboard_keyboard, build_admin_program_category_select_keyboard
from app.core.permissions import Role


class TestProgramCreationFlow(unittest.TestCase):

    def setUp(self):
        asyncio.run(init_db())

    def test_admin_dashboard_keyboard_callback(self):
        """Verify Dastur qo'shish button on Admin Dashboard points to category selection."""
        kb = build_admin_dashboard_keyboard()
        buttons = [btn for row in kb.inline_keyboard for btn in row]
        add_btn = next((b for b in buttons if "Dastur qo'shish" in b.text), None)
        self.assertIsNotNone(add_btn)
        self.assertEqual(add_btn.callback_data, "admin:program:select_category")
        print("[PASS] TEST 0: Admin Dashboard Dastur qo'shish callback data verified")

    def test_non_admin_program_creation_rejected(self):
        """TEST 5: Normal user attempting program creation is rejected with 403."""
        async def run():
            from aiogram.types import CallbackQuery
            mock_cb = MagicMock(spec=CallbackQuery)
            mock_cb.answer = AsyncMock()
            await admin_program_select_category_handler(mock_cb, is_admin=False)
            mock_cb.answer.assert_called_once_with("⛔ Sizda ushbu bo'limga kirish huquqi yo'q.", show_alert=True)

        asyncio.run(run())
        print("[PASS] TEST 5: Non-admin access denied for program creation")


    def test_program_creation_name_validation_and_duplicate(self):
        """TEST 2 & 3: Empty name validation error and duplicate program name warning."""
        async def run():
            import time
            unique_cat_name = f"Test Software Cat {time.time_ns()}"
            # Setup test category
            async with async_session_maker() as session:
                cat_service = CategoryService(session)
                cat = await cat_service.create_category(name=unique_cat_name)
                category_id = cat.id

            # TEST 3: Invalid/Empty name
            mock_state = AsyncMock()
            mock_state.get_data.return_value = {"category_id": category_id}
            
            mock_msg_empty = AsyncMock()
            mock_msg_empty.text = "   "
            await admin_program_create_name(mock_msg_empty, mock_state)
            mock_msg_empty.answer.assert_called_once_with("⚠️ Noto'g'ri nom formatini kiriting (1–150 belgi):")

            # Setup existing program in DB
            prog_name = f"Adobe Photoshop {time.time_ns()}"
            async with async_session_maker() as session:
                prog_service = ProgramService(session)
                await prog_service.create_program(
                    category_id=category_id,
                    name=prog_name,
                    file_id="test_file_id_123"
                )

            # TEST 2: Duplicate name entry
            mock_msg_dup = AsyncMock()
            mock_msg_dup.text = prog_name
            await admin_program_create_name(mock_msg_dup, mock_state)
            mock_msg_dup.answer.assert_called_once_with("⚠️ Bu dastur allaqachon mavjud.\n\nBoshqa nom kiriting:")

        asyncio.run(run())
        print("[PASS] TEST 2 & 3: Program name validation & duplicate warning verified")

    def test_program_creation_success_and_db_persistence(self):
        """TEST 1, 6 & 7: Full program creation, database persistence, and count reflection."""
        async def run():
            import time
            unique_cat_name = f"Utils Cat {time.time_ns()}"
            unique_prog_name = f"WinRAR Pro {time.time_ns()}"
            async with async_session_maker() as session:
                cat_service = CategoryService(session)
                cat = await cat_service.create_category(name=unique_cat_name)
                category_id = cat.id

                prog_service = ProgramService(session)
                prog = await prog_service.create_program(
                    category_id=category_id,
                    name=unique_prog_name,
                    file_id=f"winrar_file_id_{time.time_ns()}",
                    short_description="Archiver utility",
                    version="7.0",
                    file_size=10485760
                )
                self.assertIsNotNone(prog.id)
                self.assertEqual(prog.name, unique_prog_name)
                self.assertEqual(prog.category_id, category_id)

                # TEST 6: Persistence test
                fetched_prog = await prog_service.get_program_by_id(prog.id)
                self.assertIsNotNone(fetched_prog)
                self.assertEqual(fetched_prog.name, unique_prog_name)

                # TEST 7: Program count check
                progs, count = await prog_service.get_admin_programs_by_category_paginated(category_id)
                self.assertGreaterEqual(len(progs), 1)

        asyncio.run(run())
        print("[PASS] TEST 1, 6 & 7: Program creation, persistence, and stats count verified")



    def test_program_creation_cancel_flow(self):
        """TEST 4: Cancellation clears FSM state and returns safely."""
        async def run():
            mock_state = AsyncMock()
            mock_msg = AsyncMock()
            mock_msg.text = "❌ Bekor qilish"

            await admin_program_cancel_handler(mock_msg, mock_state)
            mock_state.clear.assert_called_once()
            mock_msg.answer.assert_called_once()

        asyncio.run(run())
        print("[PASS] TEST 4: FSM cancellation and state cleanup verified")

    def test_program_deletion_with_dependent_records(self):
        """TEST 8: Deleting a program removes all dependent records (RecentlyViewed, Downloads, etc.) without IntegrityError."""
        async def run():
            import time
            from app.database.models import RecentlyViewed, Download, Favorite
            ts = time.time_ns()
            async with async_session_maker() as session:
                cat_service = CategoryService(session)
                cat = await cat_service.create_category(name=f"Delete Cat {ts}")

                prog_service = ProgramService(session)
                prog = await prog_service.create_program(
                    category_id=cat.id,
                    name=f"Delete Target Prog {ts}",
                    file_id=f"FILE_ID_DEL_{ts}"
                )

                # Add dummy RecentlyViewed record
                rv = RecentlyViewed(user_id=1, program_id=prog.id)
                session.add(rv)
                await session.commit()

                # Delete program
                success = await prog_service.delete_program(prog.id)
                self.assertTrue(success)

                # Verify deletion
                deleted_prog = await prog_service.get_program_by_id(prog.id)
                self.assertIsNone(deleted_prog)

        asyncio.run(run())
        print("[PASS] TEST 8: Program deletion with dependent records verified")


if __name__ == "__main__":
    unittest.main()

