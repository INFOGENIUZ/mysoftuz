import logging
from dataclasses import dataclass
from typing import List, Tuple, Optional
from sqlalchemy import select, func, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    User,
    Download,
    Favorite,
    ProgramRating,
    ProgramReview,
    UserNotification,
    Program,
)
from app.utils.pagination import get_pagination

logger = logging.getLogger(__name__)


@dataclass
class UserProfileSummary:
    user: User
    downloads_count: int
    favorites_count: int
    ratings_count: int
    reviews_count: int
    unread_notifications_count: int


class UserProfileService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _get_user_db_id(self, telegram_id: int) -> int:
        stmt = select(User.id).where(User.telegram_id == telegram_id)
        res = await self.session.execute(stmt)
        uid = res.scalar_one_or_none()
        if not uid:
            user = User(telegram_id=telegram_id, first_name="Foydalanuvchi")
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
            return user.id
        return uid

    async def get_profile_summary(self, telegram_id: int) -> UserProfileSummary:
        """
        Fetches user details and aggregated activity counts in optimized queries.
        """
        user_id = await self._get_user_db_id(telegram_id)
        user = (await self.session.execute(select(User).where(User.id == user_id))).scalar_one()

        dl_cnt = (await self.session.execute(
            select(func.count(Download.id)).where(Download.user_id == user_id)
        )).scalar_one() or 0

        fav_cnt = (await self.session.execute(
            select(func.count(Favorite.id)).where(Favorite.user_id == user_id)
        )).scalar_one() or 0

        rat_cnt = (await self.session.execute(
            select(func.count(ProgramRating.id)).where(ProgramRating.user_id == user_id)
        )).scalar_one() or 0

        rev_cnt = (await self.session.execute(
            select(func.count(ProgramReview.id)).where(ProgramReview.user_id == user_id)
        )).scalar_one() or 0

        notif_cnt = (await self.session.execute(
            select(func.count(UserNotification.id)).where(
                UserNotification.user_id == user_id, UserNotification.is_read == False
            )
        )).scalar_one() or 0

        return UserProfileSummary(
            user=user,
            downloads_count=dl_cnt,
            favorites_count=fav_cnt,
            ratings_count=rat_cnt,
            reviews_count=rev_cnt,
            unread_notifications_count=notif_cnt
        )

    async def get_user_ratings_paginated(
        self, telegram_id: int, page: int = 1, page_size: int = 5
    ) -> Tuple[List[ProgramRating], int]:
        """Fetch user's ratings history with associated programs."""
        user_id = await self._get_user_db_id(telegram_id)
        count_stmt = select(func.count(ProgramRating.id)).where(ProgramRating.user_id == user_id)
        total_items = (await self.session.execute(count_stmt)).scalar_one() or 0

        pagination = get_pagination(total_items=total_items, page=page, per_page=page_size)

        stmt = (
            select(ProgramRating)
            .where(ProgramRating.user_id == user_id)
            .order_by(ProgramRating.created_at.desc())
            .limit(page_size)
            .offset(pagination.offset)
        )
        res = await self.session.execute(stmt)
        ratings = list(res.scalars().all())
        return ratings, pagination.total_pages

    async def delete_user_rating(self, telegram_id: int, rating_id: int) -> bool:
        """Deletes a rating record enforcing strict user ownership."""
        user_id = await self._get_user_db_id(telegram_id)
        stmt = delete(ProgramRating).where(
            ProgramRating.id == rating_id,
            ProgramRating.user_id == user_id
        )
        res = await self.session.execute(stmt)
        await self.session.commit()
        return res.rowcount > 0

    async def get_user_reviews_paginated(
        self, telegram_id: int, page: int = 1, page_size: int = 5
    ) -> Tuple[List[ProgramReview], int]:
        """Fetch user's review submissions with status."""
        user_id = await self._get_user_db_id(telegram_id)
        count_stmt = select(func.count(ProgramReview.id)).where(ProgramReview.user_id == user_id)
        total_items = (await self.session.execute(count_stmt)).scalar_one() or 0

        pagination = get_pagination(total_items=total_items, page=page, per_page=page_size)

        stmt = (
            select(ProgramReview)
            .where(ProgramReview.user_id == user_id)
            .order_by(ProgramReview.created_at.desc())
            .limit(page_size)
            .offset(pagination.offset)
        )
        res = await self.session.execute(stmt)
        reviews = list(res.scalars().all())
        return reviews, pagination.total_pages

    async def delete_user_review(self, telegram_id: int, review_id: int) -> bool:
        """Deletes a review record enforcing strict user ownership."""
        user_id = await self._get_user_db_id(telegram_id)
        stmt = delete(ProgramReview).where(
            ProgramReview.id == review_id,
            ProgramReview.user_id == user_id
        )
        res = await self.session.execute(stmt)
        await self.session.commit()
        return res.rowcount > 0
