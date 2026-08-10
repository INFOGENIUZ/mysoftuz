import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User, Program, Subscription, ProgramEntitlement

logger = logging.getLogger(__name__)


class EntitlementService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def has_active_premium(self, user_id: int) -> bool:
        """Checks if user has active premium subscription."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(Subscription)
            .where(
                Subscription.user_id == user_id,
                Subscription.status == "ACTIVE",
                Subscription.expires_at > now
            )
            .order_by(Subscription.expires_at.desc())
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none() is not None

    async def has_program_entitlement(self, user_id: int, program_id: int) -> bool:
        """Checks if user purchased paid program entitlement."""
        stmt = (
            select(ProgramEntitlement)
            .where(
                ProgramEntitlement.user_id == user_id,
                ProgramEntitlement.program_id == program_id,
                ProgramEntitlement.status == "ACTIVE"
            )
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none() is not None

    async def can_download_program(self, user_id: int, program_id: int) -> bool:
        """
        Evaluates download entitlement:
        - FREE: Allowed for all
        - PREMIUM: Allowed if active premium
        - PAID: Allowed if purchased entitlement
        """
        p_stmt = select(Program).where(Program.id == program_id)
        prog = (await self.session.execute(p_stmt)).scalar_one_or_none()
        if not prog:
            return False

        access_type = getattr(prog, "access_type", "FREE")

        if access_type == "FREE":
            return True
        elif access_type == "PREMIUM":
            return await self.has_active_premium(user_id)
        elif access_type == "PAID":
            return await self.has_program_entitlement(user_id, program_id)
        return True
