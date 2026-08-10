import logging
from typing import Optional, List, Tuple
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    ProgramSubscription,
    UserNotificationSetting,
    Download,
    ProgramVersion,
    User,
)

logger = logging.getLogger(__name__)


class UpdateService:
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

    async def subscribe_to_updates(self, user_telegram_id: int, program_id: int) -> bool:
        """Subscribes user to program update notifications."""
        user_id = await self._get_user_db_id(user_telegram_id)
        stmt = select(ProgramSubscription).where(
            ProgramSubscription.user_id == user_id,
            ProgramSubscription.program_id == program_id
        )
        res = await self.session.execute(stmt)
        if res.scalar_one_or_none():
            return False

        sub = ProgramSubscription(user_id=user_id, program_id=program_id)
        self.session.add(sub)
        await self.session.commit()
        return True

    async def unsubscribe_from_updates(self, user_telegram_id: int, program_id: int) -> bool:
        """Unsubscribes user from program update notifications."""
        user_id = await self._get_user_db_id(user_telegram_id)
        stmt = delete(ProgramSubscription).where(
            ProgramSubscription.user_id == user_id,
            ProgramSubscription.program_id == program_id
        )
        res = await self.session.execute(stmt)
        await self.session.commit()
        return res.rowcount > 0

    async def is_subscribed(self, user_telegram_id: int, program_id: int) -> bool:
        """Checks if user is subscribed to update notifications for a program."""
        user_id = await self._get_user_db_id(user_telegram_id)
        stmt = select(ProgramSubscription).where(
            ProgramSubscription.user_id == user_id,
            ProgramSubscription.program_id == program_id
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none() is not None

    async def get_user_last_downloaded_version(
        self, user_telegram_id: int, program_id: int
    ) -> Optional[str]:
        """Fetch the version string of the program last downloaded by user."""
        user_id = await self._get_user_db_id(user_telegram_id)
        stmt = (
            select(ProgramVersion.version)
            .join(Download, Download.version_id == ProgramVersion.id)
            .where(Download.user_id == user_id, Download.program_id == program_id)
            .order_by(Download.created_at.desc())
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()
