import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import List, Tuple, Optional, Dict, Any
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    User,
    Download,
    SearchEvent,
    Program,
    Category,
    ProgramRating,
    ProgramReview,
    NotificationJob,
    ProgramVersion,
    RecentlyViewed,
)

logger = logging.getLogger(__name__)


@dataclass
class KPIChange:
    current_value: int
    previous_value: int
    change_pct: float
    is_positive: bool


def calculate_pct_change(current: int, previous: int) -> KPIChange:
    """Calculates percentage change between current and previous periods."""
    if previous == 0:
        pct = 100.0 if current > 0 else 0.0
    else:
        pct = round(((current - previous) / previous) * 100.0, 1)
    return KPIChange(
        current_value=current,
        previous_value=previous,
        change_pct=abs(pct),
        is_positive=pct >= 0
    )


class AnalyticsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def resolve_date_range(self, period: str = "7d", custom_start: Optional[datetime] = None, custom_end: Optional[datetime] = None) -> Tuple[datetime, datetime, datetime, datetime]:
        """
        Returns (current_start, current_end, previous_start, previous_end) in UTC.
        Supported periods: 'today', 'yesterday', '7d', '30d', '90d', '1y', 'custom'
        """
        now = datetime.now(timezone.utc)

        if period == "today":
            cur_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            cur_end = now
            delta = timedelta(days=1)
        elif period == "yesterday":
            cur_start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            cur_end = now.replace(hour=0, minute=0, second=0, microsecond=0)
            delta = timedelta(days=1)
        elif period == "30d":
            cur_start = now - timedelta(days=30)
            cur_end = now
            delta = timedelta(days=30)
        elif period == "90d":
            cur_start = now - timedelta(days=90)
            cur_end = now
            delta = timedelta(days=90)
        elif period == "1y":
            cur_start = now - timedelta(days=365)
            cur_end = now
            delta = timedelta(days=365)
        elif period == "custom" and custom_start and custom_end:
            cur_start = custom_start
            cur_end = custom_end
            delta = cur_end - cur_start
        else:  # default '7d'
            cur_start = now - timedelta(days=7)
            cur_end = now
            delta = timedelta(days=7)

        prev_end = cur_start
        prev_start = cur_start - delta
        return cur_start, cur_end, prev_start, prev_end

    async def get_overview_analytics(self, period: str = "7d") -> Dict[str, Any]:
        """Fetches aggregate KPI overview comparisons."""
        cur_start, cur_end, prev_start, prev_end = self.resolve_date_range(period)

        # Users
        u_cur = (await self.session.execute(
            select(func.count(User.id)).where(User.created_at >= cur_start, User.created_at <= cur_end)
        )).scalar_one() or 0
        u_prev = (await self.session.execute(
            select(func.count(User.id)).where(User.created_at >= prev_start, User.created_at < prev_end)
        )).scalar_one() or 0

        # Downloads
        d_cur = (await self.session.execute(
            select(func.count(Download.id)).where(Download.created_at >= cur_start, Download.created_at <= cur_end)
        )).scalar_one() or 0
        d_prev = (await self.session.execute(
            select(func.count(Download.id)).where(Download.created_at >= prev_start, Download.created_at < prev_end)
        )).scalar_one() or 0

        # Searches
        s_cur = (await self.session.execute(
            select(func.count(SearchEvent.id)).where(SearchEvent.created_at >= cur_start, SearchEvent.created_at <= cur_end)
        )).scalar_one() or 0
        s_prev = (await self.session.execute(
            select(func.count(SearchEvent.id)).where(SearchEvent.created_at >= prev_start, SearchEvent.created_at < prev_end)
        )).scalar_one() or 0

        # Ratings
        r_cur = (await self.session.execute(
            select(func.count(ProgramRating.id)).where(ProgramRating.created_at >= cur_start, ProgramRating.created_at <= cur_end)
        )).scalar_one() or 0
        r_prev = (await self.session.execute(
            select(func.count(ProgramRating.id)).where(ProgramRating.created_at >= prev_start, ProgramRating.created_at < prev_end)
        )).scalar_one() or 0

        return {
            "period": period,
            "cur_start": cur_start,
            "cur_end": cur_end,
            "users": calculate_pct_change(u_cur, u_prev),
            "downloads": calculate_pct_change(d_cur, d_prev),
            "searches": calculate_pct_change(s_cur, s_prev),
            "ratings": calculate_pct_change(r_cur, r_prev),
        }

    async def get_user_analytics(self, period: str = "7d") -> Dict[str, Any]:
        """Calculates DAU, WAU, MAU, and user growth for Admin Intelligence."""
        now = datetime.now(timezone.utc)
        cur_start, cur_end, _, _ = self.resolve_date_range(period)

        total_users = (await self.session.execute(select(func.count(User.id)))).scalar_one() or 0
        new_users = (await self.session.execute(
            select(func.count(User.id)).where(User.created_at >= cur_start, User.created_at <= cur_end)
        )).scalar_one() or 0

        # DAU (1 day)
        dau_start = now - timedelta(days=1)
        dau = (await self.session.execute(
            select(func.count(func.distinct(Download.user_id))).where(Download.created_at >= dau_start)
        )).scalar_one() or 0

        # WAU (7 days)
        wau_start = now - timedelta(days=7)
        wau = (await self.session.execute(
            select(func.count(func.distinct(Download.user_id))).where(Download.created_at >= wau_start)
        )).scalar_one() or 0

        # MAU (30 days)
        mau_start = now - timedelta(days=30)
        mau = (await self.session.execute(
            select(func.count(func.distinct(Download.user_id))).where(Download.created_at >= mau_start)
        )).scalar_one() or 0

        return {
            "total_users": total_users,
            "new_users": new_users,
            "dau": dau,
            "wau": wau,
            "mau": mau,
        }

    async def get_download_analytics(self, period: str = "7d", limit: int = 5) -> Dict[str, Any]:
        """Fetches top downloaded programs and version usage metrics."""
        cur_start, cur_end, _, _ = self.resolve_date_range(period)

        # Top downloaded programs in period
        stmt = (
            select(Program, func.count(Download.id).label("period_dl"))
            .join(Download, Download.program_id == Program.id)
            .where(Download.created_at >= cur_start, Download.created_at <= cur_end)
            .group_by(Program.id)
            .order_by(func.count(Download.id).desc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        top_programs = list(res.all())

        # Total downloads in period
        total_period_dl = (await self.session.execute(
            select(func.count(Download.id)).where(Download.created_at >= cur_start, Download.created_at <= cur_end)
        )).scalar_one() or 0

        # Unique downloaders
        unique_users = (await self.session.execute(
            select(func.count(func.distinct(Download.user_id))).where(Download.created_at >= cur_start, Download.created_at <= cur_end)
        )).scalar_one() or 0

        return {
            "top_programs": top_programs,
            "total_downloads": total_period_dl,
            "unique_downloaders": unique_users
        }

    async def get_search_analytics(self, period: str = "7d", limit: int = 5) -> Dict[str, Any]:
        """Fetches top search queries, zero-result queries, and search success rate."""
        cur_start, cur_end, _, _ = self.resolve_date_range(period)

        total_searches = (await self.session.execute(
            select(func.count(SearchEvent.id)).where(SearchEvent.created_at >= cur_start, SearchEvent.created_at <= cur_end)
        )).scalar_one() or 0

        zero_searches = (await self.session.execute(
            select(func.count(SearchEvent.id)).where(
                SearchEvent.created_at >= cur_start,
                SearchEvent.created_at <= cur_end,
                SearchEvent.result_count == 0
            )
        )).scalar_one() or 0

        success_rate = 100.0 if total_searches == 0 else round(((total_searches - zero_searches) / total_searches) * 100.0, 1)

        # Top search queries
        top_q_stmt = (
            select(SearchEvent.query_normalized, func.count(SearchEvent.id).label("q_cnt"))
            .where(SearchEvent.created_at >= cur_start, SearchEvent.created_at <= cur_end)
            .group_by(SearchEvent.query_normalized)
            .order_by(func.count(SearchEvent.id).desc())
            .limit(limit)
        )
        top_queries = list((await self.session.execute(top_q_stmt)).all())

        # Zero result queries
        zero_q_stmt = (
            select(SearchEvent.query_normalized, func.count(SearchEvent.id).label("q_cnt"))
            .where(SearchEvent.created_at >= cur_start, SearchEvent.created_at <= cur_end, SearchEvent.result_count == 0)
            .group_by(SearchEvent.query_normalized)
            .order_by(func.count(SearchEvent.id).desc())
            .limit(limit)
        )
        zero_queries = list((await self.session.execute(zero_q_stmt)).all())

        return {
            "total_searches": total_searches,
            "zero_searches": zero_searches,
            "success_rate": success_rate,
            "top_queries": top_queries,
            "zero_queries": zero_queries
        }

    async def get_engagement_analytics(self, period: str = "7d") -> Dict[str, Any]:
        """Fetches ratings breakdown and moderation queue count."""
        cur_start, cur_end, _, _ = self.resolve_date_range(period)

        # Star breakdown (1 to 5)
        breakdown = {}
        for star in range(1, 6):
            cnt = (await self.session.execute(
                select(func.count(ProgramRating.id)).where(
                    ProgramRating.created_at >= cur_start,
                    ProgramRating.created_at <= cur_end,
                    ProgramRating.rating == star
                )
            )).scalar_one() or 0
            breakdown[star] = cnt

        # Pending reviews
        pending_reviews = (await self.session.execute(
            select(func.count(ProgramReview.id)).where(ProgramReview.status == "PENDING")
        )).scalar_one() or 0

        return {
            "star_breakdown": breakdown,
            "pending_reviews": pending_reviews
        }

    async def get_notification_analytics(self, period: str = "7d") -> Dict[str, Any]:
        """Fetches notification jobs delivery status."""
        cur_start, cur_end, _, _ = self.resolve_date_range(period)

        sent_jobs = (await self.session.execute(
            select(func.count(NotificationJob.id)).where(
                NotificationJob.created_at >= cur_start,
                NotificationJob.created_at <= cur_end,
                NotificationJob.status == "sent"
            )
        )).scalar_one() or 0

        failed_jobs = (await self.session.execute(
            select(func.count(NotificationJob.id)).where(
                NotificationJob.created_at >= cur_start,
                NotificationJob.created_at <= cur_end,
                NotificationJob.status == "failed"
            )
        )).scalar_one() or 0

        return {
            "sent_jobs": sent_jobs,
            "failed_jobs": failed_jobs
        }

    async def get_health_alerts(self, period: str = "7d") -> List[str]:
        """Evaluates drop thresholds and generates system health alert signals."""
        alerts: List[str] = []

        overview = await self.get_overview_analytics(period)
        dl_kpi: KPIChange = overview["downloads"]
        if not dl_kpi.is_positive and dl_kpi.change_pct >= 20.0:
            alerts.append(f"⚠️ Yuklab olishlar faolligi {dl_kpi.change_pct}% ga pasaygan.")

        search_analytics = await self.get_search_analytics(period)
        if search_analytics["total_searches"] > 10 and search_analytics["success_rate"] < 80.0:
            alerts.append(f"⚠️ Natijasiz qidiruvlar ulushi yuqori (Success rate: {search_analytics['success_rate']}%).")

        notif_analytics = await self.get_notification_analytics(period)
        total_notifs = notif_analytics["sent_jobs"] + notif_analytics["failed_jobs"]
        if total_notifs > 0:
            fail_pct = round((notif_analytics["failed_jobs"] / total_notifs) * 100.0, 1)
            if fail_pct >= 10.0:
                alerts.append(f"🔴 Bildirishnoma yetkazib berish xatoligi yuqori ({fail_pct}% failed).")

        if not alerts:
            alerts.append("🟢 Tizim barqaror va hech qanday kritik ogohlantirishlar yo'q.")

        return alerts
