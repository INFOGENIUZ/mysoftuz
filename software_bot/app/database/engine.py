import os
import logging
from typing import AsyncGenerator, Tuple
from sqlalchemy import event, text, select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings
from app.database.base import Base
import app.database.models  # noqa: F401
from app.database.models import Program, ProgramVersion

logger = logging.getLogger(__name__)

db_url = settings.DATABASE_URL
if "libsql" in db_url or not db_url:
    db_url = "sqlite+aiosqlite:////tmp/software_bot.db"

# Ensure data directory exists if relative path is used
if "sqlite+aiosqlite" in db_url:
    db_file_path = db_url.replace("sqlite+aiosqlite:///", "")
    dir_name = os.path.dirname(db_file_path)
    if dir_name and not dir_name.startswith("http") and not dir_name.startswith("/tmp"):
        try:
            os.makedirs(dir_name, exist_ok=True)
        except Exception as e:
            logger.warning(f"Directory creation notice ({dir_name}): {e}")

engine = create_async_engine(
    db_url,
    echo=False,
    future=True
)


# SQLite Production Hardening Listener
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if "sqlite" in settings.DATABASE_URL:
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys = ON;")
            cursor.execute("PRAGMA busy_timeout = 5000;")
            cursor.close()
        except Exception:
            pass


async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def ensure_composite_indexes(session: AsyncSession) -> None:
    """
    Creates performance composite indexes if they do not exist.
    """
    index_sql_statements = [
        "CREATE INDEX IF NOT EXISTS idx_dl_user_created ON downloads(user_id, created_at);",
        "CREATE INDEX IF NOT EXISTS idx_dl_prog_created ON downloads(program_id, created_at);",
        "CREATE INDEX IF NOT EXISTS idx_notif_user_read ON user_notifications(user_id, is_read, created_at);",
        "CREATE INDEX IF NOT EXISTS idx_njob_status_created ON notification_jobs(status, created_at);",
        "CREATE INDEX IF NOT EXISTS idx_sevent_query_created ON search_events(query_normalized, created_at);",
    ]
    for stmt in index_sql_statements:
        try:
            await session.execute(text(stmt))
        except Exception as idx_err:
            logger.warning(f"Index creation skipped/handled: {idx_err}")
    await session.commit()


async def run_database_integrity_check(session: AsyncSession) -> Tuple[bool, str]:
    """
    Executes SQLite 'PRAGMA integrity_check;' to verify database file health.
    Returns tuple: (is_healthy, result_message)
    """
    try:
        res = await session.execute(text("PRAGMA integrity_check;"))
        row = res.scalar()
        is_ok = (row == "ok")
        return is_ok, str(row)
    except Exception as e:
        logger.error(f"Integrity check failed: {e}")
        return False, str(e)


async def migrate_program_versions_if_needed(session: AsyncSession) -> int:
    """
    Safely migrates legacy programs to use ProgramVersion architecture.
    If a Program has file_id but no ProgramVersion entries, automatically seeds initial version.
    """
    stmt = select(Program)
    res = await session.execute(stmt)
    programs = list(res.scalars().all())
    migrated_count = 0

    for prog in programs:
        v_stmt = select(ProgramVersion).where(ProgramVersion.program_id == prog.id)
        v_res = await session.execute(v_stmt)
        if not list(v_res.scalars().all()) and prog.file_id:
            pv = ProgramVersion(
                program_id=prog.id,
                version=prog.version or "1.0.0",
                file_id=prog.file_id,
                file_unique_id=prog.file_unique_id,
                file_size=prog.file_size,
                release_notes="Dastlabki reliz versiyasi",
                is_current=True
            )
            session.add(pv)
            migrated_count += 1

    if migrated_count > 0:
        await session.commit()
        logger.info(f"Migrated {migrated_count} programs to ProgramVersion architecture.")
    return migrated_count


async def init_db() -> None:
    """Initializes the database schema, seeds categories, composite indexes, and migrates version data."""
    logger.info("Initializing database schema with SQLite WAL mode & Foreign Keys...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema initialized successfully.")

    # Seed default categories, composite indexes, super admins & migrate version data
    from app.services.category_service import CategoryService
    from app.database.models.admin import Admin
    async with async_session_maker() as session:
        cat_service = CategoryService(session)
        seeded = await cat_service.seed_default_categories()
        if seeded:
            logger.info(f"Seeded {len(seeded)} default categories.")

        admin_ids_to_seed = settings.ADMIN_IDS or [8887751785]
        for admin_id in admin_ids_to_seed:
            stmt = select(Admin).where(Admin.telegram_id == admin_id)
            existing_admin = (await session.execute(stmt)).scalar_one_or_none()
            if not existing_admin:
                new_admin = Admin(
                    telegram_id=admin_id,
                    full_name="Super Admin",
                    role="super_admin",
                    is_active=True
                )
                session.add(new_admin)
                logger.info(f"Seeded Super Admin ID: {admin_id}")
        await session.commit()

        await ensure_composite_indexes(session)
        await migrate_program_versions_if_needed(session)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency / helper generator for async database sessions."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
