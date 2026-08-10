import logging
import aiosqlite
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import text, select, func

from config import config
from software_bot.app.database.engine import (
    engine,
    async_session_maker,
    init_db as software_bot_init_db,
    run_database_integrity_check,
    ensure_composite_indexes,
)
from software_bot.app.database.models import User as ORMUser, Program, Download

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.engine = engine
        self.session_maker = async_session_maker

    async def connect(self) -> None:
        """
        Initializes SQLite database tables with WAL mode, foreign keys,
        busy timeout, composite indexes, and seeds default categories.
        """
        logger.info("Initializing SQLite production database connection layer...")
        await software_bot_init_db()

    async def add_user(self, telegram_id: int, full_name: str, username: Optional[str] = None) -> bool:
        """Adds a new user if not existing, or updates full_name and username."""
        async with self.session_maker() as session:
            stmt = select(ORMUser).where(ORMUser.telegram_id == telegram_id)
            res = await session.execute(stmt)
            user = res.scalar_one_or_none()

            if not user:
                first = full_name.split()[0] if full_name else "User"
                last = " ".join(full_name.split()[1:]) if len(full_name.split()) > 1 else ""
                new_user = ORMUser(
                    telegram_id=telegram_id,
                    first_name=first,
                    last_name=last,
                    username=username
                )
                session.add(new_user)
                await session.commit()
                return True
            else:
                first = full_name.split()[0] if full_name else user.first_name
                user.first_name = first
                user.username = username or user.username
                await session.commit()
                return False

    async def get_user(self, telegram_id: int) -> Optional[ORMUser]:
        """Fetches user model by telegram_id."""
        async with self.session_maker() as session:
            stmt = select(ORMUser).where(ORMUser.telegram_id == telegram_id)
            res = await session.execute(stmt)
            return res.scalar_one_or_none()

    async def get_all_users(self) -> List[ORMUser]:
        """Fetches all users ordered by creation date descending."""
        async with self.session_maker() as session:
            stmt = select(ORMUser).order_by(ORMUser.created_at.desc())
            res = await session.execute(stmt)
            return list(res.scalars().all())

    async def count_users(self) -> int:
        """Returns total user count."""
        async with self.session_maker() as session:
            stmt = select(func.count(ORMUser.id))
            res = await session.execute(stmt)
            return res.scalar_one() or 0

    async def run_integrity_check(self) -> Tuple[bool, str]:
        """Executes SQLite PRAGMA integrity_check."""
        async with self.session_maker() as session:
            return await run_database_integrity_check(session)

    async def ensure_indexes(self) -> None:
        """Creates composite indexes for performance optimization."""
        async with self.session_maker() as session:
            await ensure_composite_indexes(session)


db = Database(config.db_name)
