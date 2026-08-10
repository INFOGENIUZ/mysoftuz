import logging
from typing import List, Tuple
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Favorite, Program, User
from app.utils.pagination import get_pagination, Pagination

logger = logging.getLogger(__name__)


class FavoriteService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _get_user_db_id(self, telegram_id: int) -> int:
        stmt = select(User.id).where(User.telegram_id == telegram_id)
        res = await self.session.execute(stmt)
        uid = res.scalar_one_or_none()
        if not uid:
            user = User(telegram_id=telegram_id)
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
            return user.id
        return uid

    async def add_favorite(self, user_telegram_id: int, program_id: int) -> bool:
        """Adds a program to user's favorites. Returns True if added, False if already favorited."""
        user_id = await self._get_user_db_id(user_telegram_id)
        stmt = select(Favorite).where(Favorite.user_id == user_id, Favorite.program_id == program_id)
        res = await self.session.execute(stmt)
        existing = res.scalar_one_or_none()

        if existing:
            return False

        fav = Favorite(user_id=user_id, program_id=program_id)
        self.session.add(fav)
        await self.session.commit()
        logger.info(f"Favorite added: user={user_telegram_id}, program={program_id}")
        return True

    async def remove_favorite(self, user_telegram_id: int, program_id: int) -> bool:
        """Removes a program from user's favorites."""
        user_id = await self._get_user_db_id(user_telegram_id)
        stmt = delete(Favorite).where(Favorite.user_id == user_id, Favorite.program_id == program_id)
        res = await self.session.execute(stmt)
        await self.session.commit()
        return res.rowcount > 0

    async def is_favorite(self, user_telegram_id: int, program_id: int) -> bool:
        """Checks if a program is in user's favorites."""
        user_id = await self._get_user_db_id(user_telegram_id)
        stmt = select(func.count(Favorite.id)).where(Favorite.user_id == user_id, Favorite.program_id == program_id)
        res = await self.session.execute(stmt)
        return (res.scalar_one() or 0) > 0

    async def get_user_favorites_paginated(
        self, user_telegram_id: int, page: int = 1, page_size: int = 10
    ) -> Tuple[List[Program], int]:
        """Fetch user's active favorited programs paginated."""
        user_id = await self._get_user_db_id(user_telegram_id)

        count_stmt = (
            select(func.count(Favorite.id))
            .join(Program, Favorite.program_id == Program.id)
            .where(Favorite.user_id == user_id, Program.is_active == True)
        )
        total_items = (await self.session.execute(count_stmt)).scalar_one() or 0

        pagination = get_pagination(total_items=total_items, page=page, per_page=page_size)

        stmt = (
            select(Program)
            .join(Favorite, Program.id == Favorite.program_id)
            .where(Favorite.user_id == user_id, Program.is_active == True)
            .order_by(Favorite.created_at.desc())
            .limit(page_size)
            .offset(pagination.offset)
        )
        res = await self.session.execute(stmt)
        programs = list(res.scalars().all())
        return programs, pagination.total_pages
