import logging
from typing import List, Tuple, Optional
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    NotificationJob,
    UserNotification,
    ProgramSubscription,
    Download,
    Favorite,
    User,
    Program,
    ProgramVersion,
)
from app.utils.pagination import get_pagination

logger = logging.getLogger(__name__)


class NotificationService:
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

    async def enqueue_update_notifications(self, program_id: int, version_id: int) -> int:
        """
        Enqueues update notification jobs for users who:
        1. Explicitly subscribed to program updates
        2. Previously downloaded or favorited this program
        Guarantees non-blocked, active users only, and prevents duplicate jobs for same version.
        Returns count of queued jobs.
        """
        # Gather candidate user IDs
        sub_users = set((await self.session.execute(
            select(ProgramSubscription.user_id).where(ProgramSubscription.program_id == program_id)
        )).scalars().all())

        dl_users = set((await self.session.execute(
            select(Download.user_id).where(Download.program_id == program_id)
        )).scalars().all())

        fav_users = set((await self.session.execute(
            select(Favorite.user_id).where(Favorite.program_id == program_id)
        )).scalars().all())

        candidate_user_ids = (sub_users | dl_users | fav_users)
        if not candidate_user_ids:
            return 0

        # Filter only active, non-blocked users
        active_users_stmt = select(User.id).where(
            User.id.in_(candidate_user_ids),
            User.is_active == True,
            User.is_blocked == False
        )
        target_user_ids = list((await self.session.execute(active_users_stmt)).scalars().all())

        queued_count = 0
        for uid in target_user_ids:
            # Check idempotency: avoid duplicate jobs for same user + version
            existing_stmt = select(NotificationJob).where(
                NotificationJob.user_id == uid,
                NotificationJob.version_id == version_id
            )
            if (await self.session.execute(existing_stmt)).scalar_one_or_none():
                continue

            job = NotificationJob(
                user_id=uid,
                program_id=program_id,
                version_id=version_id,
                status="pending"
            )
            self.session.add(job)
            queued_count += 1

        if queued_count > 0:
            await self.session.commit()

        logger.info(f"Enqueued {queued_count} notification jobs for program_id={program_id}, version_id={version_id}")
        return queued_count

    async def create_user_notification(
        self,
        user_telegram_id: int,
        title: str,
        message: str,
        notif_type: str = "update",
        program_id: Optional[int] = None,
        version_id: Optional[int] = None
    ) -> UserNotification:
        """Creates an in-app user notification for the Notification Center."""
        user_id = await self._get_user_db_id(user_telegram_id)
        notif = UserNotification(
            user_id=user_id,
            title=title,
            message=message,
            type=notif_type,
            program_id=program_id,
            version_id=version_id,
            is_read=False
        )
        self.session.add(notif)
        await self.session.commit()
        await self.session.refresh(notif)
        return notif

    async def get_user_notifications_paginated(
        self, user_telegram_id: int, page: int = 1, page_size: int = 5
    ) -> Tuple[List[UserNotification], int]:
        """Fetch user's in-app notifications sorted by created_at DESC."""
        user_id = await self._get_user_db_id(user_telegram_id)
        count_stmt = select(func.count(UserNotification.id)).where(UserNotification.user_id == user_id)
        total_items = (await self.session.execute(count_stmt)).scalar_one() or 0

        pagination = get_pagination(total_items=total_items, page=page, per_page=page_size)

        stmt = (
            select(UserNotification)
            .where(UserNotification.user_id == user_id)
            .order_by(UserNotification.is_read.asc(), UserNotification.created_at.desc())
            .limit(page_size)
            .offset(pagination.offset)
        )
        res = await self.session.execute(stmt)
        notifs = list(res.scalars().all())
        return notifs, pagination.total_pages

    async def get_unread_count(self, user_telegram_id: int) -> int:
        """Returns unread notification count for user."""
        user_id = await self._get_user_db_id(user_telegram_id)
        stmt = select(func.count(UserNotification.id)).where(UserNotification.user_id == user_id, UserNotification.is_read == False)
        res = await self.session.execute(stmt)
        return res.scalar_one() or 0

    async def mark_all_as_read(self, user_telegram_id: int) -> int:
        """Marks all unread notifications for user as read."""
        user_id = await self._get_user_db_id(user_telegram_id)
        stmt = (
            update(UserNotification)
            .where(UserNotification.user_id == user_id, UserNotification.is_read == False)
            .values(is_read=True)
        )
        res = await self.session.execute(stmt)
        await self.session.commit()
        return res.rowcount

    async def get_notification_by_id(self, notif_id: int) -> Optional[UserNotification]:
        """Fetch notification by ID and mark it as read."""
        stmt = select(UserNotification).where(UserNotification.id == notif_id)
        res = await self.session.execute(stmt)
        notif = res.scalar_one_or_none()
        if notif and not notif.is_read:
            notif.is_read = True
            await self.session.commit()
        return notif
