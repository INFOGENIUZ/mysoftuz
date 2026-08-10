import logging
from typing import List, Tuple, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import ProgramReview, ReviewReport, User, Program
from app.utils.pagination import get_pagination

logger = logging.getLogger(__name__)


class ReviewService:
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

    async def create_review(
        self, user_telegram_id: int, program_id: int, text: str, rating_id: Optional[int] = None
    ) -> ProgramReview:
        """Creates a new program review in PENDING status for moderation."""
        text_clean = text.strip()
        if len(text_clean) < 3:
            raise ValueError("Sharh matni kamida 3 ta belgidan iborat bo'lishi kerak.")
        if len(text_clean) > 1000:
            raise ValueError("Sharh matni maksimal 1000 ta belgidan oshmasligi kerak.")

        user_id = await self._get_user_db_id(user_telegram_id)

        # Check if user already has a pending/approved review
        stmt = select(ProgramReview).where(
            ProgramReview.user_id == user_id,
            ProgramReview.program_id == program_id
        )
        res = await self.session.execute(stmt)
        existing = res.scalar_one_or_none()

        if existing:
            existing.text = text_clean
            existing.status = "PENDING"
            existing.is_visible = False
            await self.session.commit()
            await self.session.refresh(existing)
            return existing

        review = ProgramReview(
            user_id=user_id,
            program_id=program_id,
            rating_id=rating_id,
            text=text_clean,
            status="PENDING",
            is_visible=False
        )
        self.session.add(review)
        await self.session.commit()
        await self.session.refresh(review)
        logger.info(f"Review submitted: user={user_telegram_id}, program={program_id}, review_id={review.id}")
        return review

    async def get_program_reviews_paginated(
        self, program_id: int, page: int = 1, page_size: int = 5
    ) -> Tuple[List[ProgramReview], int]:
        """Fetch approved public reviews for a program."""
        count_stmt = select(func.count(ProgramReview.id)).where(
            ProgramReview.program_id == program_id,
            ProgramReview.status == "APPROVED"
        )
        total_items = (await self.session.execute(count_stmt)).scalar_one() or 0

        pagination = get_pagination(total_items=total_items, page=page, per_page=page_size)

        stmt = (
            select(ProgramReview)
            .where(ProgramReview.program_id == program_id, ProgramReview.status == "APPROVED")
            .order_by(ProgramReview.created_at.desc())
            .limit(page_size)
            .offset(pagination.offset)
        )
        res = await self.session.execute(stmt)
        reviews = list(res.scalars().all())
        return reviews, pagination.total_pages

    async def get_pending_reviews_paginated(
        self, page: int = 1, page_size: int = 10
    ) -> Tuple[List[ProgramReview], int]:
        """Fetch pending reviews for admin moderation."""
        count_stmt = select(func.count(ProgramReview.id)).where(ProgramReview.status == "PENDING")
        total_items = (await self.session.execute(count_stmt)).scalar_one() or 0

        pagination = get_pagination(total_items=total_items, page=page, per_page=page_size)

        stmt = (
            select(ProgramReview)
            .where(ProgramReview.status == "PENDING")
            .order_by(ProgramReview.created_at.asc())
            .limit(page_size)
            .offset(pagination.offset)
        )
        res = await self.session.execute(stmt)
        reviews = list(res.scalars().all())
        return reviews, pagination.total_pages

    async def approve_review(self, review_id: int) -> bool:
        """Approves a review, setting status to APPROVED and is_visible to True."""
        stmt = select(ProgramReview).where(ProgramReview.id == review_id)
        res = await self.session.execute(stmt)
        review = res.scalar_one_or_none()
        if not review:
            return False

        review.status = "APPROVED"
        review.is_visible = True
        await self.session.commit()
        return True

    async def reject_review(self, review_id: int) -> bool:
        """Rejects a review, setting status to REJECTED."""
        stmt = select(ProgramReview).where(ProgramReview.id == review_id)
        res = await self.session.execute(stmt)
        review = res.scalar_one_or_none()
        if not review:
            return False

        review.status = "REJECTED"
        review.is_visible = False
        await self.session.commit()
        return True

    async def delete_review(self, review_id: int) -> bool:
        """Deletes a review from database."""
        stmt = select(ProgramReview).where(ProgramReview.id == review_id)
        res = await self.session.execute(stmt)
        review = res.scalar_one_or_none()
        if not review:
            return False

        await self.session.delete(review)
        await self.session.commit()
        return True

    async def report_review(self, user_telegram_id: int, review_id: int, reason: Optional[str] = None) -> bool:
        """Records a user report against a review."""
        user_id = await self._get_user_db_id(user_telegram_id)
        report = ReviewReport(user_id=user_id, review_id=review_id, reason=reason)
        self.session.add(report)
        await self.session.commit()
        return True

    async def get_review_by_id(self, review_id: int) -> Optional[ProgramReview]:
        """Fetch review by ID."""
        stmt = select(ProgramReview).where(ProgramReview.id == review_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()
