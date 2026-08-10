import logging
from typing import Optional, Dict, Any, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import ProgramRating, Program, User

logger = logging.getLogger(__name__)


class RatingService:
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

    async def set_rating(self, user_telegram_id: int, program_id: int, rating_val: int) -> Tuple[bool, float, int]:
        """
        Sets or updates a user's rating (1 to 5 stars) for a program.
        Recalculates and updates Program.rating_average and Program.rating_count atomically.
        Returns (is_new_rating, new_average, new_count).
        """
        if not (1 <= rating_val <= 5):
            raise ValueError("Rating value must be between 1 and 5 stars.")

        user_id = await self._get_user_db_id(user_telegram_id)

        stmt = select(ProgramRating).where(ProgramRating.user_id == user_id, ProgramRating.program_id == program_id)
        res = await self.session.execute(stmt)
        rating_obj = res.scalar_one_or_none()

        is_new = False
        if rating_obj:
            rating_obj.rating = rating_val
        else:
            rating_obj = ProgramRating(user_id=user_id, program_id=program_id, rating=rating_val)
            self.session.add(rating_obj)
            is_new = True

        await self.session.commit()

        # Recalculate program aggregates
        avg_stmt = select(func.avg(ProgramRating.rating), func.count(ProgramRating.id)).where(ProgramRating.program_id == program_id)
        avg_res = await self.session.execute(avg_stmt)
        row = avg_res.one()

        new_avg = float(row[0]) if row[0] is not None else 0.0
        new_count = int(row[1]) if row[1] is not None else 0

        # Update Program
        prog_stmt = select(Program).where(Program.id == program_id)
        prog_res = await self.session.execute(prog_stmt)
        program = prog_res.scalar_one_or_none()

        if program:
            program.rating_average = round(new_avg, 2)
            program.rating_count = new_count
            await self.session.commit()

        logger.info(f"Rating set: user={user_telegram_id}, program={program_id}, rating={rating_val}, avg={new_avg:.2f}")
        return is_new, new_avg, new_count

    async def get_user_rating(self, user_telegram_id: int, program_id: int) -> Optional[int]:
        """Returns user's rating for a program if exists."""
        user_id = await self._get_user_db_id(user_telegram_id)
        stmt = select(ProgramRating.rating).where(ProgramRating.user_id == user_id, ProgramRating.program_id == program_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_program_rating_stats(self, program_id: int) -> Dict[str, Any]:
        """Returns detailed rating statistics (avg, count, star distribution)."""
        stmt = select(ProgramRating.rating, func.count(ProgramRating.id)).where(ProgramRating.program_id == program_id).group_by(ProgramRating.rating)
        res = await self.session.execute(stmt)
        dist = {r: 0 for r in range(1, 6)}
        total_count = 0
        total_sum = 0

        for rating_val, count in res.all():
            dist[rating_val] = count
            total_count += count
            total_sum += rating_val * count

        avg = (total_sum / total_count) if total_count > 0 else 0.0
        return {
            "average": round(avg, 2),
            "count": total_count,
            "distribution": dist
        }
