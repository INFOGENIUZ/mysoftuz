import logging
from typing import Dict, Any, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Order, Subscription, ProgramEntitlement, Program

logger = logging.getLogger(__name__)


class RevenueService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_revenue_summary(self) -> Dict[str, Any]:
        """Calculates Gross Revenue, Net Revenue, Orders count, Paid Orders, and Average Order Value."""
        total_orders = (await self.session.execute(select(func.count(Order.id)))).scalar_one() or 0
        paid_orders = (await self.session.execute(select(func.count(Order.id)).where(Order.status == "PAID"))).scalar_one() or 0
        refunded_orders = (await self.session.execute(select(func.count(Order.id)).where(Order.status == "REFUNDED"))).scalar_one() or 0

        gross_revenue = (await self.session.execute(
            select(func.sum(Order.amount)).where(Order.status.in_(["PAID", "REFUNDED"]))
        )).scalar() or 0

        refund_amount = (await self.session.execute(
            select(func.sum(Order.amount)).where(Order.status == "REFUNDED")
        )).scalar() or 0

        net_revenue = gross_revenue - refund_amount
        aov = round(net_revenue / paid_orders) if paid_orders > 0 else 0

        # Active subscriptions count
        active_subs = (await self.session.execute(
            select(func.count(Subscription.id)).where(Subscription.status == "ACTIVE")
        )).scalar_one() or 0

        return {
            "total_orders": total_orders,
            "paid_orders": paid_orders,
            "refunded_orders": refunded_orders,
            "gross_revenue": gross_revenue,
            "refund_amount": refund_amount,
            "net_revenue": net_revenue,
            "aov": aov,
            "active_subscriptions": active_subs,
        }
