import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from sqlalchemy import select, func, update, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Download, Program, User
from app.utils.exceptions import (
    ProgramNotFoundError,
    ProgramInactiveError,
    FileMissingError,
    UserBlockedError,
)

logger = logging.getLogger(__name__)


class DownloadService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def validate_downloadable_program(self, user_telegram_id: int, program_id: int) -> Tuple[User, Program]:
        """
        Validates user eligibility and program status before initiating Telegram file delivery.
        Raises specific DownloadError exceptions if invalid.
        """
        # 1. Check/Get User
        stmt_user = select(User).where(User.telegram_id == user_telegram_id)
        user_res = await self.session.execute(stmt_user)
        user = user_res.scalar_one_or_none()

        if not user:
            # Auto-create user if missing
            user = User(
                telegram_id=user_telegram_id,
                first_name="User",
                is_active=True,
                is_blocked=False
            )
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)

        if user.is_blocked:
            raise UserBlockedError("⛔ Sizning akkauntingiz vaqtincha bloklangan.")

        # 2. Check Program
        stmt_prog = select(Program).where(Program.id == program_id)
        prog_res = await self.session.execute(stmt_prog)
        program = prog_res.scalar_one_or_none()

        if not program:
            raise ProgramNotFoundError("⚠️ Dastur topilmadi.")

        if not program.is_active:
            raise ProgramInactiveError("⚠️ Bu dastur hozircha mavjud emas.")

        if not program.file_id or len(program.file_id.strip()) < 5:
            raise FileMissingError("⚠️ Ushbu dastur fayli hozircha mavjud emas. Administratorga xabar berildi.")

        return user, program

    async def record_download(self, user_telegram_id: int, program_id: int, version_id: Optional[int] = None) -> Tuple[Download, Program]:
        """
        Records a successful download event into SQLite 'downloads' table AND
        atomically increments program's downloads_count by 1.
        MUST BE CALLED ONLY AFTER TELEGRAM bot.send_document SUCCESS!
        """

        stmt_user = select(User).where(User.telegram_id == user_telegram_id)
        user_res = await self.session.execute(stmt_user)
        user = user_res.scalar_one()

        stmt_prog = select(Program).where(Program.id == program_id)
        prog_res = await self.session.execute(stmt_prog)
        program = prog_res.scalar_one()

        # 1. Insert download record
        download = Download(
            user_id=user.id,
            program_id=program.id,
            created_at=datetime.now(timezone.utc)
        )
        self.session.add(download)

        # 2. Atomic increment of downloads_count using SQL update statement to prevent race conditions
        stmt_inc = (
            update(Program)
            .where(Program.id == program.id)
            .values(downloads_count=Program.downloads_count + 1)
        )
        await self.session.execute(stmt_inc)

        # 3. Commit transaction
        await self.session.commit()
        await self.session.refresh(program)

        return download, program

    async def get_user_downloads_unique_paginated(
        self, user_telegram_id: int, page: int = 1, page_size: int = 10
    ) -> Tuple[List[Tuple[Download, Program]], int]:
        """
        Fetches user's unique download history (unique programs, newest first) with SQL pagination.
        """
        if page < 1:
            page = 1

        stmt_user = select(User).where(User.telegram_id == user_telegram_id)
        user_res = await self.session.execute(stmt_user)
        user = user_res.scalar_one_or_none()

        if not user:
            return [], 1

        # Count total distinct downloaded programs
        count_stmt = (
            select(func.count(distinct(Download.program_id)))
            .where(Download.user_id == user.id)
        )
        count_res = await self.session.execute(count_stmt)
        total_items = count_res.scalar_one() or 0

        total_pages = max(1, (total_items + page_size - 1) // page_size)
        if page > total_pages:
            page = total_pages

        offset = (page - 1) * page_size

        # Select latest download record per program_id for user
        subq = (
            select(
                Download.program_id,
                func.max(Download.created_at).label("max_created")
            )
            .where(Download.user_id == user.id)
            .group_by(Download.program_id)
            .subquery()
        )

        stmt = (
            select(Download, Program)
            .join(subq, (Download.program_id == subq.c.program_id) & (Download.created_at == subq.c.max_created))
            .join(Program, Download.program_id == Program.id)
            .order_by(Download.created_at.desc())
            .limit(page_size)
            .offset(offset)
        )

        res = await self.session.execute(stmt)
        results = res.all()  # Returns list of tuples (Download, Program)

        return [(row[0], row[1]) for row in results], total_pages

    # -------------------------------------------------------------------------
    # Download Analytics Methods
    # -------------------------------------------------------------------------
    async def get_total_downloads(self) -> int:
        """Fetch total download events count across system."""
        stmt = select(func.count(Download.id))
        res = await self.session.execute(stmt)
        return res.scalar_one() or 0

    async def get_program_download_count(self, program_id: int) -> int:
        """Fetch download count for a specific program."""
        stmt = select(func.count(Download.id)).where(Download.program_id == program_id)
        res = await self.session.execute(stmt)
        return res.scalar_one() or 0

    async def get_user_download_count(self, user_telegram_id: int) -> int:
        """Fetch total download count for a specific user."""
        stmt_user = select(User).where(User.telegram_id == user_telegram_id)
        user_res = await self.session.execute(stmt_user)
        user = user_res.scalar_one_or_none()
        if not user:
            return 0

        stmt = select(func.count(Download.id)).where(Download.user_id == user.id)
        res = await self.session.execute(stmt)
        return res.scalar_one() or 0

    async def get_downloads_today(self) -> int:
        """Fetch download events count created today (UTC)."""
        now = datetime.now(timezone.utc)
        start_of_day = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        stmt = select(func.count(Download.id)).where(Download.created_at >= start_of_day)
        res = await self.session.execute(stmt)
        return res.scalar_one() or 0

    async def get_downloads_this_week(self) -> int:
        """Fetch download events count created in the last 7 days."""
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        stmt = select(func.count(Download.id)).where(Download.created_at >= seven_days_ago)
        res = await self.session.execute(stmt)
        return res.scalar_one() or 0

    async def get_downloads_this_month(self) -> int:
        """Fetch download events count created in the last 30 days."""
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        stmt = select(func.count(Download.id)).where(Download.created_at >= thirty_days_ago)
        res = await self.session.execute(stmt)
        return res.scalar_one() or 0

    async def get_top_downloaded_programs(self, limit: int = 10) -> List[Tuple[Program, int]]:
        """Fetch top downloaded active programs sorted by downloads_count DESC."""
        stmt = (
            select(Program, Program.downloads_count)
            .where(Program.is_active == True)
            .order_by(Program.downloads_count.desc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return [(row[0], row[1]) for row in res.all()]
