from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import User


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Fetch user by Telegram ID."""
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user(
        self,
        telegram_id: int,
        first_name: str,
        last_name: Optional[str] = None,
        username: Optional[str] = None,
        language_code: Optional[str] = None,
        is_admin: bool = False
    ) -> User:
        """Creates a new user record."""
        user = User(
            telegram_id=telegram_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
            language_code=language_code,
            is_admin=is_admin,
            last_activity=datetime.now(timezone.utc)
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update_user_activity(self, telegram_id: int) -> bool:
        """Updates last_activity timestamp for a user."""
        user = await self.get_user_by_telegram_id(telegram_id)
        if user:
            user.last_activity = datetime.now(timezone.utc)
            await self.session.commit()
            return True
        return False

    async def get_or_create_user(
        self,
        telegram_id: int,
        first_name: str,
        last_name: Optional[str] = None,
        username: Optional[str] = None,
        language_code: Optional[str] = None,
        is_admin: bool = False
    ) -> tuple[User, bool]:
        """
        Gets existing user or creates a new user.
        Returns: (User, created_bool)
        """
        user = await self.get_user_by_telegram_id(telegram_id)
        if user:
            updated = False
            if user.first_name != first_name:
                user.first_name = first_name
                updated = True
            if user.last_name != last_name:
                user.last_name = last_name
                updated = True
            if user.username != username:
                user.username = username
                updated = True
            if is_admin and not user.is_admin:
                user.is_admin = True
                updated = True

            user.last_activity = datetime.now(timezone.utc)
            await self.session.commit()
            return user, False

        new_user = await self.create_user(
            telegram_id=telegram_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
            language_code=language_code,
            is_admin=is_admin
        )
        return new_user, True

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Fetch user by database primary key ID."""
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_users_paginated(self, page: int = 1, page_size: int = 10) -> tuple[list[User], int]:
        """Fetches paginated list of users ordered by last_activity DESC."""
        from math import ceil
        from sqlalchemy import func

        count_stmt = select(func.count(User.id))
        total_count = (await self.session.execute(count_stmt)).scalar_one() or 0
        total_pages = max(1, ceil(total_count / page_size))

        offset = (max(1, page) - 1) * page_size
        stmt = select(User).order_by(User.last_activity.desc()).offset(offset).limit(page_size)
        res = await self.session.execute(stmt)
        users = list(res.scalars().all())

        return users, total_pages

