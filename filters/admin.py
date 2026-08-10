import logging
from aiogram.filters import Filter
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select

from config import config
from software_bot.app.database.engine import async_session_maker
from software_bot.app.database.models import Admin, User

logger = logging.getLogger(__name__)


class AdminFilter(Filter):
    """
    Filter that checks if user is an Administrator:
    - Listed in ADMIN_IDS from config/env
    - Or has Admin record in database with is_active = True
    """
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user_id = event.from_user.id if event.from_user else None
        if not user_id:
            return False

        # Fast path: check config admin_ids
        if user_id in config.admin_ids:
            return True

        # Database path: check Admin table
        async with async_session_maker() as session:
            u_stmt = select(User).where(User.telegram_id == user_id)
            user = (await session.execute(u_stmt)).scalar_one_or_none()
            if user:
                a_stmt = select(Admin).where(Admin.user_id == user.id, Admin.is_active == True)
                admin_rec = (await session.execute(a_stmt)).scalar_one_or_none()
                if admin_rec:
                    return True

        return False
