import logging
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import UserNotificationSetting, User

logger = logging.getLogger(__name__)


class UserSettingsService:
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

    async def get_or_create_settings(self, telegram_id: int) -> UserNotificationSetting:
        """Fetch or initialize default notification settings for user."""
        user_id = await self._get_user_db_id(telegram_id)
        stmt = select(UserNotificationSetting).where(UserNotificationSetting.user_id == user_id)
        res = await self.session.execute(stmt)
        setting = res.scalar_one_or_none()

        if not setting:
            setting = UserNotificationSetting(
                user_id=user_id,
                software_updates=True,
                new_programs=False,
                important_announcements=True
            )
            self.session.add(setting)
            await self.session.commit()
            await self.session.refresh(setting)

        return setting

    async def toggle_setting(self, telegram_id: int, field_name: str) -> bool:
        """Toggles a boolean notification setting for user."""
        setting = await self.get_or_create_settings(telegram_id)
        if hasattr(setting, field_name):
            curr_val = getattr(setting, field_name)
            setattr(setting, field_name, not curr_val)
            await self.session.commit()
            await self.session.refresh(setting)
            return getattr(setting, field_name)
        return False
