import logging
from datetime import datetime, timezone
from typing import List, Tuple
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import RecentlyViewed, Program, User
from app.utils.pagination import get_pagination

logger = logging.getLogger(__name__)
RECENTLY_VIEWED_LIMIT = 20


class RecentService:
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

    async def record_view(self, user_telegram_id: int, program_id: int) -> None:
        """
        Records a program view in history. Updates timestamp if already viewed.
        Enforces MAX 20 items per user by pruning the oldest.
        """
        user_id = await self._get_user_db_id(user_telegram_id)

        stmt = select(RecentlyViewed).where(RecentlyViewed.user_id == user_id, RecentlyViewed.program_id == program_id)
        res = await self.session.execute(stmt)
        existing = res.scalar_one_or_none()

        if existing:
            existing.viewed_at = datetime.now(timezone.utc)
        else:
            recent = RecentlyViewed(user_id=user_id, program_id=program_id)
            self.session.add(recent)

        await self.session.commit()

        # Enforce max limit by trimming oldest entries if count > 20
        count_stmt = select(func.count(RecentlyViewed.id)).where(RecentlyViewed.user_id == user_id)
        total = (await self.session.execute(count_stmt)).scalar_one() or 0

        if total > RECENTLY_VIEWED_LIMIT:
            excess = total - RECENTLY_VIEWED_LIMIT
            subq = (
                select(RecentlyViewed.id)
                .where(RecentlyViewed.user_id == user_id)
                .order_by(RecentlyViewed.viewed_at.asc())
                .limit(excess)
            )
            old_ids = list((await self.session.execute(subq)).scalars().all())
            if old_ids:
                del_stmt = delete(RecentlyViewed).where(RecentlyViewed.id.in_(old_ids))
                await self.session.execute(del_stmt)
                await self.session.commit()

    async def get_recently_viewed_paginated(
        self, user_telegram_id: int, page: int = 1, page_size: int = 10
    ) -> Tuple[List[Program], int]:
        """Fetch user's active recently viewed programs sorted by viewed_at DESC."""
        user_id = await self._get_user_db_id(user_telegram_id)

        count_stmt = (
            select(func.count(RecentlyViewed.id))
            .join(Program, RecentlyViewed.program_id == Program.id)
            .where(RecentlyViewed.user_id == user_id, Program.is_active == True)
        )
        total_items = (await self.session.execute(count_stmt)).scalar_one() or 0

        pagination = get_pagination(total_items=total_items, page=page, per_page=page_size)

        stmt = (
            select(Program)
            .join(RecentlyViewed, Program.id == RecentlyViewed.program_id)
            .where(RecentlyViewed.user_id == user_id, Program.is_active == True)
            .order_by(RecentlyViewed.viewed_at.desc())
            .limit(page_size)
            .offset(pagination.offset)
        )
        res = await self.session.execute(stmt)
        programs = list(res.scalars().all())
        return programs, pagination.total_pages
