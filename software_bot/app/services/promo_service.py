import logging
from datetime import datetime, timezone
from typing import Optional, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import PromoCode, PromoUsage

logger = logging.getLogger(__name__)


class PromoService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_promo(
        self,
        code: str,
        promo_type: str = "PERCENT",  # PERCENT, FIXED, FREE_DAYS
        value: int = 10,
        max_uses: int = 100
    ) -> PromoCode:
        """Creates a new promo code."""
        code_clean = code.strip().upper()
        promo = PromoCode(
            code=code_clean,
            type=promo_type,
            value=value,
            max_uses=max_uses,
            used_count=0,
            is_active=True
        )
        self.session.add(promo)
        await self.session.commit()
        await self.session.refresh(promo)
        return promo

    async def validate_and_apply_promo(self, code: str, user_id: int, original_amount: int) -> Tuple[bool, int, str]:
        """
        Validates promo code active status, max usage, user usage limit, and calculates final amount.
        Returns tuple: (is_valid, final_amount, message)
        """
        code_clean = code.strip().upper()
        stmt = select(PromoCode).where(PromoCode.code == code_clean, PromoCode.is_active == True)
        promo = (await self.session.execute(stmt)).scalar_one_or_none()

        if not promo:
            return False, original_amount, "Promokod topilmadi yoki faol emas."

        if promo.used_count >= promo.max_uses:
            return False, original_amount, "Promokod ishlatish limiti tugagan."

        # Check if user already used this promo
        u_stmt = select(PromoUsage).where(PromoUsage.promo_id == promo.id, PromoUsage.user_id == user_id)
        user_usage = (await self.session.execute(u_stmt)).scalar_one_or_none()
        if user_usage:
            return False, original_amount, "Siz ushbu promokoddan allaqachon foydalangansiz."

        # Calculate discount
        if promo.type == "PERCENT":
            discount = int(original_amount * (promo.value / 100.0))
            final_amount = max(0, original_amount - discount)
        elif promo.type == "FIXED":
            final_amount = max(0, original_amount - promo.value)
        else:
            final_amount = original_amount

        # Record promo usage
        promo.used_count += 1
        usage = PromoUsage(promo_id=promo.id, user_id=user_id)
        self.session.add(usage)
        await self.session.commit()

        return True, final_amount, f"Promokod muvaffaqiyatli qo'llanildi! Narx: {final_amount:,} UZS"
