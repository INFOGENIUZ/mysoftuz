import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import User, Program, Category, Download

logger = logging.getLogger(__name__)


class StatisticsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_dashboard_stats(self) -> Dict[str, Any]:
        """
        Calculates real-time dashboard statistics using efficient SQL aggregate queries.
        No hardcoded values!
        """
        now = datetime.now(timezone.utc)
        start_of_day = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        seven_days_ago = now - timedelta(days=7)
        thirty_days_ago = now - timedelta(days=30)

        # Users counts & activity
        total_users = (await self.session.execute(select(func.count(User.id)))).scalar_one() or 0
        active_users = (await self.session.execute(select(func.count(User.id)).where(User.is_blocked == False))).scalar_one() or 0
        blocked_users = (await self.session.execute(select(func.count(User.id)).where(User.is_blocked == True))).scalar_one() or 0
        today_users = (await self.session.execute(select(func.count(User.id)).where(User.created_at >= start_of_day))).scalar_one() or 0
        week_users = (await self.session.execute(select(func.count(User.id)).where(User.created_at >= seven_days_ago))).scalar_one() or 0
        month_users = (await self.session.execute(select(func.count(User.id)).where(User.created_at >= thirty_days_ago))).scalar_one() or 0

        # Activity metrics (DAU / WAU / MAU)
        today_active_users = (await self.session.execute(select(func.count(User.id)).where(User.last_activity >= start_of_day))).scalar_one() or 0
        week_active_users = (await self.session.execute(select(func.count(User.id)).where(User.last_activity >= seven_days_ago))).scalar_one() or 0
        month_active_users = (await self.session.execute(select(func.count(User.id)).where(User.last_activity >= thirty_days_ago))).scalar_one() or 0

        # Programs counts
        total_programs = (await self.session.execute(select(func.count(Program.id)))).scalar_one() or 0
        active_programs = (await self.session.execute(select(func.count(Program.id)).where(Program.is_active == True))).scalar_one() or 0
        inactive_programs = (await self.session.execute(select(func.count(Program.id)).where(Program.is_active == False))).scalar_one() or 0

        # Categories counts
        total_categories = (await self.session.execute(select(func.count(Category.id)))).scalar_one() or 0
        active_categories = (await self.session.execute(select(func.count(Category.id)).where(Category.is_active == True))).scalar_one() or 0

        # Downloads counts
        total_downloads = (await self.session.execute(select(func.count(Download.id)))).scalar_one() or 0
        today_downloads = (await self.session.execute(select(func.count(Download.id)).where(Download.created_at >= start_of_day))).scalar_one() or 0
        week_downloads = (await self.session.execute(select(func.count(Download.id)).where(Download.created_at >= seven_days_ago))).scalar_one() or 0
        month_downloads = (await self.session.execute(select(func.count(Download.id)).where(Download.created_at >= thirty_days_ago))).scalar_one() or 0

        return {
            "total_users": total_users,
            "active_users": active_users,
            "blocked_users": blocked_users,
            "today_users": today_users,
            "week_users": week_users,
            "month_users": month_users,
            "today_active_users": today_active_users,
            "week_active_users": week_active_users,
            "month_active_users": month_active_users,
            "total_programs": total_programs,
            "active_programs": active_programs,
            "inactive_programs": inactive_programs,
            "total_categories": total_categories,
            "active_categories": active_categories,
            "total_downloads": total_downloads,
            "today_downloads": today_downloads,
            "week_downloads": week_downloads,
            "month_downloads": month_downloads,
        }


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
