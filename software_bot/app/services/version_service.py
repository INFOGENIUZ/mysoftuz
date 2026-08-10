import logging
from typing import List, Tuple, Optional
from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import ProgramVersion, Program
from app.utils.pagination import get_pagination

logger = logging.getLogger(__name__)


class VersionService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_version(
        self,
        program_id: int,
        version_str: str,
        file_id: str,
        file_unique_id: Optional[str] = None,
        file_size: Optional[int] = None,
        release_notes: Optional[str] = None,
        official_release_url: Optional[str] = None,
        is_current: bool = False
    ) -> ProgramVersion:
        """
        Creates a new version record for a program.
        If is_current=True, toggles all existing versions to is_current=False atomically.
        """
        if is_current:
            await self.session.execute(
                update(ProgramVersion)
                .where(ProgramVersion.program_id == program_id)
                .values(is_current=False)
            )

        pv = ProgramVersion(
            program_id=program_id,
            version=version_str,
            file_id=file_id,
            file_unique_id=file_unique_id,
            file_size=file_size,
            release_notes=release_notes,
            official_release_url=official_release_url,
            is_current=is_current
        )
        self.session.add(pv)
        await self.session.commit()
        await self.session.refresh(pv)

        # Sync Program cached version and file_id if current
        if is_current:
            prog_stmt = select(Program).where(Program.id == program_id)
            res = await self.session.execute(prog_stmt)
            program = res.scalar_one_or_none()
            if program:
                program.version = version_str
                program.file_id = file_id
                if file_size:
                    program.file_size = file_size
                await self.session.commit()

        logger.info(f"Version created: program_id={program_id}, version={version_str}, is_current={is_current}")
        return pv

    async def publish_version(self, version_id: int) -> Optional[ProgramVersion]:
        """
        Publishes a version, setting it as current (is_current=True)
        and demoting all other versions of the program to is_current=False.
        """
        stmt = select(ProgramVersion).where(ProgramVersion.id == version_id)
        res = await self.session.execute(stmt)
        pv = res.scalar_one_or_none()
        if not pv:
            return None

        # Demote existing current versions
        await self.session.execute(
            update(ProgramVersion)
            .where(ProgramVersion.program_id == pv.program_id)
            .values(is_current=False)
        )

        pv.is_current = True

        # Sync parent program object
        prog_stmt = select(Program).where(Program.id == pv.program_id)
        prog_res = await self.session.execute(prog_stmt)
        program = prog_res.scalar_one_or_none()
        if program:
            program.version = pv.version
            program.file_id = pv.file_id
            if pv.file_size:
                program.file_size = pv.file_size

        await self.session.commit()
        await self.session.refresh(pv)
        logger.info(f"Version published: version_id={version_id}, program_id={pv.program_id}, version={pv.version}")
        return pv

    async def get_current_version(self, program_id: int) -> Optional[ProgramVersion]:
        """Fetch current active version for a program."""
        stmt = (
            select(ProgramVersion)
            .where(ProgramVersion.program_id == program_id, ProgramVersion.is_current == True)
        )
        res = await self.session.execute(stmt)
        pv = res.scalar_one_or_none()
        if not pv:
            # Fallback to latest created version
            fallback_stmt = (
                select(ProgramVersion)
                .where(ProgramVersion.program_id == program_id)
                .order_by(ProgramVersion.created_at.desc())
            )
            pv = (await self.session.execute(fallback_stmt)).scalars().first()
        return pv

    async def get_version_by_id(self, version_id: int) -> Optional[ProgramVersion]:
        stmt = select(ProgramVersion).where(ProgramVersion.id == version_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_version_history_paginated(
        self, program_id: int, page: int = 1, page_size: int = 10
    ) -> Tuple[List[ProgramVersion], int]:
        """Fetch version release history for a program paginated."""
        count_stmt = select(func.count(ProgramVersion.id)).where(ProgramVersion.program_id == program_id)
        total_items = (await self.session.execute(count_stmt)).scalar_one() or 0

        pagination = get_pagination(total_items=total_items, page=page, per_page=page_size)

        stmt = (
            select(ProgramVersion)
            .where(ProgramVersion.program_id == program_id)
            .order_by(ProgramVersion.is_current.desc(), ProgramVersion.created_at.desc())
            .limit(page_size)
            .offset(pagination.offset)
        )
        res = await self.session.execute(stmt)
        versions = list(res.scalars().all())
        return versions, pagination.total_pages

    async def delete_version(self, version_id: int) -> bool:
        """Deletes a version. Prevents deletion if version is current."""
        pv = await self.get_version_by_id(version_id)
        if not pv or pv.is_current:
            return False

        await self.session.delete(pv)
        await self.session.commit()
        return True
