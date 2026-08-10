import logging
from typing import List, Dict
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Program, Favorite, RecentlyViewed, Download, User

logger = logging.getLogger(__name__)


class RecommendationService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_related_programs(self, program_id: int, limit: int = 5) -> List[Program]:
        """
        Fetches related programs belonging to the same category,
        excluding current program, ordered by downloads_count DESC.
        """
        # Fetch current program's category
        prog_stmt = select(Program.category_id).where(Program.id == program_id)
        res = await self.session.execute(prog_stmt)
        cat_id = res.scalar_one_or_none()

        if not cat_id:
            return []

        stmt = (
            select(Program)
            .where(
                Program.category_id == cat_id,
                Program.id != program_id,
                Program.is_active == True
            )
            .order_by(Program.downloads_count.desc())
            .limit(limit)
        )
        related = list((await self.session.execute(stmt)).scalars().all())
        return related

    async def get_user_recommendations(self, user_telegram_id: int, limit: int = 10) -> List[Program]:
        """
        Generates personalized smart recommendations for a user based on rule-based scoring:
        - Category preference score (+50 for favorite category, +30 for download category, +15 for recently viewed)
        - Excludes already downloaded and current active programs.
        - Fallbacks to top popular programs if user history is empty.
        """
        # Get user db_id
        u_stmt = select(User.id).where(User.telegram_id == user_telegram_id)
        user_id = (await self.session.execute(u_stmt)).scalar_one_or_none()

        if not user_id:
            # Fallback to popular active programs
            pop_stmt = (
                select(Program)
                .where(Program.is_active == True)
                .order_by(Program.downloads_count.desc())
                .limit(limit)
            )
            return list((await self.session.execute(pop_stmt)).scalars().all())

        # Gather interacted category weights
        category_scores: Dict[int, int] = {}

        # Favorites categories (+50)
        fav_stmt = (
            select(Program.category_id, func.count(Favorite.id))
            .join(Program, Favorite.program_id == Program.id)
            .where(Favorite.user_id == user_id)
            .group_by(Program.category_id)
        )
        for cat_id, cnt in (await self.session.execute(fav_stmt)).all():
            category_scores[cat_id] = category_scores.get(cat_id, 0) + (cnt * 50)

        # Downloads categories (+30)
        dl_stmt = (
            select(Program.category_id, func.count(Download.id))
            .join(Program, Download.program_id == Program.id)
            .where(Download.user_id == user_id)
            .group_by(Program.category_id)
        )
        for cat_id, cnt in (await self.session.execute(dl_stmt)).all():
            category_scores[cat_id] = category_scores.get(cat_id, 0) + (cnt * 30)

        # Recently viewed categories (+15)
        rv_stmt = (
            select(Program.category_id, func.count(RecentlyViewed.id))
            .join(Program, RecentlyViewed.program_id == Program.id)
            .where(RecentlyViewed.user_id == user_id)
            .group_by(Program.category_id)
        )
        for cat_id, cnt in (await self.session.execute(rv_stmt)).all():
            category_scores[cat_id] = category_scores.get(cat_id, 0) + (cnt * 15)

        # Get list of already downloaded program IDs to exclude
        dl_pids_stmt = select(Download.program_id).where(Download.user_id == user_id)
        excluded_pids = set((await self.session.execute(dl_pids_stmt)).scalars().all())

        # If user has favorite/download category preferences
        if category_scores:
            top_category_id = max(category_scores, key=category_scores.get)
            stmt = (
                select(Program)
                .where(
                    Program.category_id == top_category_id,
                    Program.is_active == True
                )
                .order_by(Program.downloads_count.desc())
                .limit(limit)
            )
            recs = [p for p in (await self.session.execute(stmt)).scalars().all() if p.id not in excluded_pids]
            if len(recs) >= limit:
                return recs[:limit]

        # Fallback to general top popular active programs
        pop_stmt = (
            select(Program)
            .where(Program.is_active == True)
            .order_by(Program.downloads_count.desc())
            .limit(limit)
        )
        popular_progs = list((await self.session.execute(pop_stmt)).scalars().all())
        return popular_progs[:limit]
