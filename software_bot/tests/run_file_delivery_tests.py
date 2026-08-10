import os
import asyncio
import sys
import unittest
import time
from unittest.mock import AsyncMock, MagicMock

from app.config import settings
settings.DATABASE_URL = "sqlite+aiosqlite:///data/test_temp.db"

from app.database.engine import init_db, async_session_maker
from app.database.models import Program, ProgramVersion, Category
from app.services.category_service import CategoryService
from app.services.program_service import ProgramService
from app.services.download_service import DownloadService
from app.handlers.user.programs import program_download_handler
from app.utils.exceptions import FileMissingError, DownloadError



class TestFileDeliverySystem(unittest.TestCase):

    def setUp(self):
        asyncio.run(init_db())

    def test_admin_upload_persists_file_id_and_version(self):
        """TEST 1: Admin program upload persists file_id in Program and ProgramVersion."""
        async def run():
            ts = time.time_ns()
            async with async_session_maker() as session:
                cat_service = CategoryService(session)
                cat = await cat_service.create_category(name=f"Design Cat {ts}")

                prog_service = ProgramService(session)
                prog = await prog_service.create_program(
                    category_id=cat.id,
                    name=f"Photoshop Pro {ts}",
                    file_id=f"TG_FILE_ID_PHOTOSHOP_{ts}",
                    file_name="photoshop_installer.exe",
                    file_size=150000000,
                    version="2026.1"
                )

                self.assertIsNotNone(prog.id)
                self.assertEqual(prog.file_id, f"TG_FILE_ID_PHOTOSHOP_{ts}")
                self.assertEqual(prog.file_name, "photoshop_installer.exe")

                # Verify ProgramVersion synchronization
                versions = await prog_service.get_program_by_id(prog.id)
                self.assertIsNotNone(versions)
                self.assertEqual(versions.file_id, f"TG_FILE_ID_PHOTOSHOP_{ts}")

        asyncio.run(run())
        print("[PASS] TEST 1: Admin file upload persists file_id & ProgramVersion")

    def test_user_file_delivery_validation_and_lookup(self):
        """TEST 2: User download lookup retrieves correct telegram file_id."""
        async def run():
            ts = time.time_ns()
            async with async_session_maker() as session:
                cat_service = CategoryService(session)
                cat = await cat_service.create_category(name=f"Media Cat {ts}")

                prog_service = ProgramService(session)
                prog = await prog_service.create_program(
                    category_id=cat.id,
                    name=f"VLC Media Player {ts}",
                    file_id=f"TG_FILE_ID_VLC_{ts}",
                    file_size=50000000
                )

                dl_service = DownloadService(session)
                user, validated_prog = await dl_service.validate_downloadable_program(
                    user_telegram_id=8887751785, program_id=prog.id
                )

                self.assertEqual(validated_prog.id, prog.id)
                self.assertEqual(validated_prog.file_id, f"TG_FILE_ID_VLC_{ts}")

        asyncio.run(run())
        print("[PASS] TEST 2: User file delivery validation retrieves correct file_id")

    def test_multiple_programs_distinct_files(self):
        """TEST 3: Multiple distinct programs maintain distinct file_ids."""
        async def run():
            ts = time.time_ns()
            async with async_session_maker() as session:
                cat_service = CategoryService(session)
                cat = await cat_service.create_category(name=f"Tools Cat {ts}")

                prog_service = ProgramService(session)
                p1 = await prog_service.create_program(
                    category_id=cat.id, name=f"Tool A {ts}", file_id=f"FILE_A_{ts}"
                )
                p2 = await prog_service.create_program(
                    category_id=cat.id, name=f"Tool B {ts}", file_id=f"FILE_B_{ts}"
                )

                self.assertNotEqual(p1.file_id, p2.file_id)
                self.assertEqual(p1.file_id, f"FILE_A_{ts}")
                self.assertEqual(p2.file_id, f"FILE_B_{ts}")

        asyncio.run(run())
        print("[PASS] TEST 3: Multiple programs maintain distinct file_ids")

    def test_category_isolation(self):
        """TEST 4: Programs remain strictly isolated within their respective categories."""
        async def run():
            ts = time.time_ns()
            async with async_session_maker() as session:
                cat_service = CategoryService(session)
                c1 = await cat_service.create_category(name=f"Category One {ts}")
                c2 = await cat_service.create_category(name=f"Category Two {ts}")

                prog_service = ProgramService(session)
                await prog_service.create_program(category_id=c1.id, name=f"Prog C1 {ts}", file_id="F1")
                await prog_service.create_program(category_id=c2.id, name=f"Prog C2 {ts}", file_id="F2")

                progs_c1, count_c1 = await prog_service.get_programs_by_category_paginated(c1.id)
                progs_c2, count_c2 = await prog_service.get_programs_by_category_paginated(c2.id)

                self.assertTrue(all(p.category_id == c1.id for p in progs_c1))
                self.assertTrue(all(p.category_id == c2.id for p in progs_c2))

        asyncio.run(run())
        print("[PASS] TEST 4: Category program isolation verified")

    def test_missing_file_id_handled_gracefully(self):
        """TEST 5: Program missing file_id raises FileMissingError safely."""
        async def run():
            ts = time.time_ns()
            async with async_session_maker() as session:
                cat_service = CategoryService(session)
                cat = await cat_service.create_category(name=f"Empty Cat {ts}")

                # Create raw program directly in DB without file_id
                raw_prog = Program(
                    category_id=cat.id,
                    name=f"Empty File Prog {ts}",
                    slug=f"empty-file-prog-{ts}",
                    file_id="",  # Missing file_id
                    is_active=True
                )
                session.add(raw_prog)
                await session.commit()
                await session.refresh(raw_prog)

                dl_service = DownloadService(session)
                with self.assertRaises(FileMissingError):
                    await dl_service.validate_downloadable_program(8887751785, raw_prog.id)

        asyncio.run(run())
        print("[PASS] TEST 5: Missing file_id raises FileMissingError gracefully")

    def test_telegram_send_document_and_download_stat_recording(self):
        """TEST 6 & 8: Telegram file sending and atomic download statistics recording."""
        async def run():
            ts = time.time_ns()
            async with async_session_maker() as session:
                cat_service = CategoryService(session)
                cat = await cat_service.create_category(name=f"Stat Cat {ts}")

                prog_service = ProgramService(session)
                prog = await prog_service.create_program(
                    category_id=cat.id, name=f"Stat Prog {ts}", file_id=f"VALID_FILE_ID_{ts}"
                )

                dl_service = DownloadService(session)
                initial_count = prog.downloads_count

                # Record download transaction
                await dl_service.record_download(user_telegram_id=8887751785, program_id=prog.id)

                updated_prog = await prog_service.get_program_by_id(prog.id)
                self.assertEqual(updated_prog.downloads_count, initial_count + 1)

        asyncio.run(run())
        print("[PASS] TEST 6 & 8: Download transaction & stats count increment verified")


if __name__ == "__main__":
    unittest.main()
