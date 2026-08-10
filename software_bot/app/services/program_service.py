from typing import List, Optional, Tuple
from sqlalchemy import select, func, or_, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import (
    Program,
    Category,
    ProgramVersion,
    Download,
    RecentlyViewed,
    Favorite,
    ProgramReview,
    ProgramRating,
    ProgramKeyword,
    ProgramSubscription,
)
from app.utils.slug import generate_unique_slug



class ProgramService:
    def __init__(self, session: AsyncSession):
        self.session = session


    async def create_program(
        self,
        category_id: int,
        name: str,
        file_id: str,
        short_description: Optional[str] = None,
        description: Optional[str] = None,
        version: Optional[str] = None,
        file_unique_id: Optional[str] = None,
        file_name: Optional[str] = None,
        file_size: Optional[int] = None,
        mime_type: Optional[str] = None,
        architecture: Optional[str] = None,
        system_requirements: Optional[str] = None,
        official_url: Optional[str] = None,
        image_file_id: Optional[str] = None,
        is_featured: bool = False
    ) -> Program:
        """Creates a new program after performing input validations."""
        if not name or not name.strip():
            raise ValueError("Program name cannot be empty")
        if not file_id or not file_id.strip():
            raise ValueError("Telegram file_id cannot be empty")
        if file_size is not None and file_size < 0:
            raise ValueError("file_size cannot be negative")

        clean_name = name.strip()

        # Verify Category
        stmt_cat = select(Category).where(Category.id == category_id)
        cat_res = await self.session.execute(stmt_cat)
        category = cat_res.scalar_one_or_none()
        if not category:
            raise ValueError(f"Category with id {category_id} does not exist")

        # Check duplicate name within category
        stmt_dup = select(Program).where(Program.category_id == category_id, Program.name == clean_name)
        res_dup = await self.session.execute(stmt_dup)
        if res_dup.scalar_one_or_none():
            raise ValueError(f"Program with name '{clean_name}' already exists in this category")

        slug = await generate_unique_slug(self.session, Program, clean_name)
        program = Program(
            category_id=category_id,
            name=clean_name,
            slug=slug,
            short_description=short_description.strip() if short_description else None,
            description=description.strip() if description else None,
            version=version.strip() if version else None,
            file_id=file_id.strip(),
            file_unique_id=file_unique_id.strip() if file_unique_id else None,
            file_name=file_name.strip() if file_name else None,
            file_size=file_size,
            mime_type=mime_type.strip() if mime_type else None,
            architecture=architecture.strip() if architecture else None,
            system_requirements=system_requirements.strip() if system_requirements else None,
            official_url=official_url.strip() if official_url else None,
            image_file_id=image_file_id.strip() if image_file_id else None,
            downloads_count=0,
            is_featured=is_featured,
            is_active=True
        )
        self.session.add(program)
        await self.session.flush()

        # Synchronize initial ProgramVersion
        pv = ProgramVersion(
            program_id=program.id,
            version=program.version or "1.0.0",
            file_id=program.file_id,
            file_unique_id=program.file_unique_id,
            file_size=program.file_size,
            release_notes="Dastlabki versiya",
            is_current=True
        )
        self.session.add(pv)

        await self.session.commit()
        await self.session.refresh(program)
        return program


    async def get_program_by_id(self, program_id: int) -> Optional[Program]:
        """Fetch program by ID regardless of is_active for Admin access."""
        stmt = select(Program).options(selectinload(Program.category)).where(Program.id == program_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


    async def get_program_by_slug(self, slug: str) -> Optional[Program]:
        """Fetch program by slug."""
        stmt = select(Program).where(Program.slug == slug)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_program_by_file_unique_id(self, file_unique_id: str) -> Optional[Program]:
        """Fetch program by Telegram file_unique_id to detect duplicates."""
        if not file_unique_id:
            return None
        stmt = select(Program).where(Program.file_unique_id == file_unique_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_programs_by_category_paginated(
        self, category_id: int, page: int = 1, page_size: int = 10
    ) -> Tuple[List[Program], int]:
        """Fetch active programs under a category using SQL LIMIT and OFFSET for user panel."""
        if page < 1:
            page = 1

        count_stmt = select(func.count(Program.id)).where(
            Program.category_id == category_id, Program.is_active == True
        )
        count_res = await self.session.execute(count_stmt)
        total_items = count_res.scalar_one() or 0

        total_pages = max(1, (total_items + page_size - 1) // page_size)
        if page > total_pages:
            page = total_pages

        offset = (page - 1) * page_size
        stmt = (
            select(Program)
            .where(Program.category_id == category_id, Program.is_active == True)
            .order_by(Program.name)
            .limit(page_size)
            .offset(offset)
        )
        res = await self.session.execute(stmt)
        programs = list(res.scalars().all())

        return programs, total_pages

    async def get_admin_programs_by_category_paginated(
        self, category_id: int, page: int = 1, page_size: int = 10
    ) -> Tuple[List[Program], int]:
        """Fetch all programs (active & inactive) under a category for Admin panel."""
        if page < 1:
            page = 1

        count_stmt = select(func.count(Program.id)).where(Program.category_id == category_id)
        count_res = await self.session.execute(count_stmt)
        total_items = count_res.scalar_one() or 0

        total_pages = max(1, (total_items + page_size - 1) // page_size)
        if page > total_pages:
            page = total_pages

        offset = (page - 1) * page_size
        stmt = (
            select(Program)
            .where(Program.category_id == category_id)
            .order_by(Program.sort_order, Program.name)
            .limit(page_size)
            .offset(offset)
        )
        res = await self.session.execute(stmt)
        programs = list(res.scalars().all())

        return programs, total_pages

    async def get_popular_programs_paginated(
        self, page: int = 1, page_size: int = 10
    ) -> Tuple[List[Program], int]:
        """Fetch popular programs sorted by downloads_count DESC using SQL LIMIT/OFFSET."""
        if page < 1:
            page = 1

        count_stmt = select(func.count(Program.id)).where(Program.is_active == True)
        count_res = await self.session.execute(count_stmt)
        total_items = count_res.scalar_one() or 0

        total_pages = max(1, (total_items + page_size - 1) // page_size)
        if page > total_pages:
            page = total_pages

        offset = (page - 1) * page_size
        stmt = (
            select(Program)
            .where(Program.is_active == True)
            .order_by(Program.downloads_count.desc(), Program.name)
            .limit(page_size)
            .offset(offset)
        )
        res = await self.session.execute(stmt)
        programs = list(res.scalars().all())

        return programs, total_pages

    async def get_new_programs_paginated(
        self, page: int = 1, page_size: int = 10
    ) -> Tuple[List[Program], int]:
        """Fetch newly added programs sorted by created_at DESC using SQL LIMIT/OFFSET."""
        if page < 1:
            page = 1

        count_stmt = select(func.count(Program.id)).where(Program.is_active == True)
        count_res = await self.session.execute(count_stmt)
        total_items = count_res.scalar_one() or 0

        total_pages = max(1, (total_items + page_size - 1) // page_size)
        if page > total_pages:
            page = total_pages

        offset = (page - 1) * page_size
        stmt = (
            select(Program)
            .where(Program.is_active == True)
            .order_by(Program.created_at.desc())
            .limit(page_size)
            .offset(offset)
        )
        res = await self.session.execute(stmt)
        programs = list(res.scalars().all())

        return programs, total_pages

    async def search_programs_paginated(
        self, query: str, page: int = 1, page_size: int = 10
    ) -> Tuple[List[Program], int]:
        """Search active programs by name or description using SQL ILIKE/LIKE and LIMIT/OFFSET."""
        if page < 1:
            page = 1
        clean_q = f"%{query.strip()}%"

        count_stmt = select(func.count(Program.id)).where(
            Program.is_active == True,
            or_(Program.name.ilike(clean_q), Program.description.ilike(clean_q))
        )
        count_res = await self.session.execute(count_stmt)
        total_items = count_res.scalar_one() or 0

        total_pages = max(1, (total_items + page_size - 1) // page_size)
        if page > total_pages:
            page = total_pages

        offset = (page - 1) * page_size
        stmt = (
            select(Program)
            .where(
                Program.is_active == True,
                or_(Program.name.ilike(clean_q), Program.description.ilike(clean_q))
            )
            .order_by(Program.name)
            .limit(page_size)
            .offset(offset)
        )
        res = await self.session.execute(stmt)
        programs = list(res.scalars().all())

        return programs, total_pages

    async def update_program(
        self,
        program_id: int,
        name: Optional[str] = None,
        short_description: Optional[str] = None,
        description: Optional[str] = None,
        version: Optional[str] = None,
        architecture: Optional[str] = None,
        system_requirements: Optional[str] = None,
        official_url: Optional[str] = None,
        image_file_id: Optional[str] = None,
        category_id: Optional[int] = None,
        file_id: Optional[str] = None,
        file_unique_id: Optional[str] = None,
        file_name: Optional[str] = None,
        file_size: Optional[int] = None,
        mime_type: Optional[str] = None,
        unset_image: bool = False,
        unset_url: bool = False
    ) -> Program:
        """Updates program fields, regenerates slug if name changed, and handles file replacement."""
        program = await self.get_program_by_id(program_id)
        if not program:
            raise ValueError(f"Program with id {program_id} not found")

        if category_id is not None and category_id != program.category_id:
            stmt_cat = select(Category).where(Category.id == category_id)
            res_cat = await self.session.execute(stmt_cat)
            if not res_cat.scalar_one_or_none():
                raise ValueError(f"Target Category with id {category_id} not found")
            program.category_id = category_id

        if name is not None and name.strip():
            clean_name = name.strip()
            if clean_name != program.name:
                stmt_dup = select(Program).where(
                    Program.category_id == program.category_id,
                    Program.name == clean_name,
                    Program.id != program_id
                )
                res_dup = await self.session.execute(stmt_dup)
                if res_dup.scalar_one_or_none():
                    raise ValueError(f"Program with name '{clean_name}' already exists in this category")

                program.name = clean_name
                program.slug = await generate_unique_slug(self.session, Program, clean_name)

        if short_description is not None:
            program.short_description = short_description.strip() if short_description.strip() else None
        if description is not None:
            program.description = description.strip() if description.strip() else None
        if version is not None:
            program.version = version.strip() if version.strip() else None
        if architecture is not None:
            program.architecture = architecture.strip() if architecture.strip() else None
        if system_requirements is not None:
            program.system_requirements = system_requirements.strip() if system_requirements.strip() else None

        if unset_url:
            program.official_url = None
        elif official_url is not None:
            program.official_url = official_url.strip() if official_url.strip() else None

        if unset_image:
            program.image_file_id = None
        elif image_file_id is not None:
            program.image_file_id = image_file_id.strip() if image_file_id.strip() else None

        if file_id is not None and file_id.strip():
            program.file_id = file_id.strip()
            if file_unique_id:
                program.file_unique_id = file_unique_id.strip()
            if file_name:
                program.file_name = file_name.strip()
            if file_size is not None:
                program.file_size = file_size
            if mime_type:
                program.mime_type = mime_type.strip()

        await self.session.commit()
        await self.session.refresh(program)
        return program

    async def activate_program(self, program_id: int) -> bool:
        """Activates a program (is_active = True)."""
        program = await self.get_program_by_id(program_id)
        if program:
            program.is_active = True
            await self.session.commit()
            return True
        return False

    async def deactivate_program(self, program_id: int) -> bool:
        """Deactivates a program (is_active = False)."""
        program = await self.get_program_by_id(program_id)
        if program:
            program.is_active = False
            await self.session.commit()
            return True
        return False

    async def delete_program(self, program_id: int) -> bool:
        """Deletes a program and all associated records from database atomically."""
        program = await self.get_program_by_id(program_id)
        if not program:
            raise ValueError(f"Program with id {program_id} not found")

        # Delete all dependent records across related tables to prevent FK constraint failures
        await self.session.execute(delete(Download).where(Download.program_id == program_id))
        await self.session.execute(delete(RecentlyViewed).where(RecentlyViewed.program_id == program_id))
        await self.session.execute(delete(Favorite).where(Favorite.program_id == program_id))
        await self.session.execute(delete(ProgramReview).where(ProgramReview.program_id == program_id))
        await self.session.execute(delete(ProgramRating).where(ProgramRating.program_id == program_id))
        await self.session.execute(delete(ProgramVersion).where(ProgramVersion.program_id == program_id))
        await self.session.execute(delete(ProgramKeyword).where(ProgramKeyword.program_id == program_id))
        await self.session.execute(delete(ProgramSubscription).where(ProgramSubscription.program_id == program_id))

        await self.session.delete(program)
        await self.session.commit()
        return True


    async def soft_delete_program(self, program_id: int) -> bool:
        """Soft deletes program by setting is_active=False."""
        return await self.deactivate_program(program_id)
