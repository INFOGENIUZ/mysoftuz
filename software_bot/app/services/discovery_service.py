import logging
from typing import List, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Program, SearchEvent

logger = logging.getLogger(__name__)


class DiscoveryService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_popular_programs(self, limit: int = 10) -> List[Program]:
        """Fetch top popular active programs ordered by downloads_count DESC."""
        stmt = (
            select(Program)
            .where(Program.is_active == True)
            .order_by(Program.downloads_count.desc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_new_programs(self, limit: int = 10) -> List[Program]:
        """Fetch newly added active programs ordered by created_at DESC."""
        stmt = (
            select(Program)
            .where(Program.is_active == True)
            .order_by(Program.created_at.desc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_zero_result_analytics(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Fetch zero-result queries aggregate analytics for Admin Panel."""
        stmt = (
            select(SearchEvent.query_normalized, func.count(SearchEvent.id))
            .where(SearchEvent.result_count == 0)
            .group_by(SearchEvent.query_normalized)
            .order_by(func.count(SearchEvent.id).desc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.all())
