import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User, Order, Subscription, PremiumPlan, ProgramEntitlement, RevenueEvent

logger = logging.getLogger(__name__)


class PaymentService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_order(
        self,
        user_id: int,
        product_type: str,  # PREMIUM or PROGRAM
        product_id: int,
        amount: int,
        currency: str = "UZS"
    ) -> Order:
        """
        Creates an order with idempotency check (reusing pending order if active).
        """
        # Idempotency check: look for active pending order for user and product
        idempotency_key = f"{user_id}:{product_type}:{product_id}"
        stmt = (
            select(Order)
            .where(
                Order.user_id == user_id,
                Order.idempotency_key == idempotency_key,
                Order.status == "PENDING"
            )
            .limit(1)
        )
        existing_order = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing_order:
            return existing_order

        order = Order(
            user_id=user_id,
            product_type=product_type,
            product_id=product_id,
            amount=amount,
            currency=currency,
            status="PENDING",
            provider="SANDBOX",
            idempotency_key=idempotency_key
        )
        self.session.add(order)
        await self.session.commit()
        await self.session.refresh(order)

        # Revenue Event
        rev_evt = RevenueEvent(
            event_type="ORDER_CREATED",
            user_id=user_id,
            order_id=order.id,
            amount=amount,
            currency=currency
        )
        self.session.add(rev_evt)
        await self.session.commit()

        return order

    async def process_payment(
        self,
        order_id: int,
        provider_payment_id: str,
        paid_amount: int,
        paid_currency: str = "UZS"
    ) -> Tuple[bool, str]:
        """
        Verifies payment provider response and grants entitlement inside an atomic transaction.
        Never trusts client-side inputs.
        """
        stmt = select(Order).where(Order.id == order_id)
        order = (await self.session.execute(stmt)).scalar_one_or_none()

        if not order:
            return False, "Order topilmadi."

        if order.status == "PAID":
            return True, "Order allaqachon to'langan."

        if paid_amount < order.amount:
            order.status = "FAILED"
            await self.session.commit()
            return False, f"Summa yetarli emas ({paid_amount} < {order.amount})."

        # Unique provider payment check
        dup_stmt = select(Order).where(Order.provider_payment_id == provider_payment_id)
        dup_order = (await self.session.execute(dup_stmt)).scalar_one_or_none()
        if dup_order and dup_order.id != order.id:
            return False, "Ushbu to'lov ID allaqachon ishlatilgan."

        now = datetime.now(timezone.utc)
        order.status = "PAID"
        order.provider_payment_id = provider_payment_id
        order.paid_at = now

        # Grant Entitlement based on product type
        if order.product_type == "PREMIUM":
            plan_stmt = select(PremiumPlan).where(PremiumPlan.id == order.product_id)
            plan = (await self.session.execute(plan_stmt)).scalar_one_or_none()
            duration_days = plan.duration_days if plan else 30

            sub = Subscription(
                user_id=order.user_id,
                plan_id=order.product_id,
                status="ACTIVE",
                started_at=now,
                expires_at=now + timedelta(days=duration_days),
                payment_id=provider_payment_id
            )
            self.session.add(sub)

        elif order.product_type == "PROGRAM":
            entitlement = ProgramEntitlement(
                user_id=order.user_id,
                program_id=order.product_id,
                order_id=order.id,
                status="ACTIVE",
                granted_at=now,
                expires_at=None  # Lifetime access
            )
            self.session.add(entitlement)

        rev_evt = RevenueEvent(
            event_type="PAYMENT_PAID",
            user_id=order.user_id,
            order_id=order.id,
            amount=paid_amount,
            currency=paid_currency
        )
        self.session.add(rev_evt)

        await self.session.commit()
        return True, "To'lov muvaffaqiyatli amalga oshirildi!"

    async def refund_order(self, order_id: int, is_super_admin: bool = False) -> Tuple[bool, str]:
        """Revokes entitlement and processes refund for Super Admin."""
        if not is_super_admin:
            return False, "⛔ Refund faqat Super Admin uchun ruxsat etilgan."

        stmt = select(Order).where(Order.id == order_id)
        order = (await self.session.execute(stmt)).scalar_one_or_none()

        if not order or order.status != "PAID":
            return False, "Order topilmadi yoki to'lanmagan."

        order.status = "REFUNDED"

        # Revoke program entitlement if applicable
        if order.product_type == "PROGRAM":
            e_stmt = select(ProgramEntitlement).where(ProgramEntitlement.order_id == order.id)
            ent = (await self.session.execute(e_stmt)).scalar_one_or_none()
            if ent:
                ent.status = "REVOKED"

        rev_evt = RevenueEvent(
            event_type="REFUND_COMPLETED",
            user_id=order.user_id,
            order_id=order.id,
            amount=-order.amount,
            currency=order.currency
        )
        self.session.add(rev_evt)

        await self.session.commit()
        return True, "To'lov muvaffaqiyatli bekor qilindi (Refunded)."
