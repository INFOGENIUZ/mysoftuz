import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings, validate_environment
from app.core.logging_config import setup_logging
from app.database.engine import init_db
from app.handlers import setup_handlers
from app.handlers.errors import router as errors_router, global_error_handler
from app.middlewares import AdminMiddleware, MaintenanceMiddleware, ThrottlingMiddleware, AntiSpamMiddleware, UserTrackingMiddleware

logger = logging.getLogger(__name__)


async def start_bot() -> None:
    """
    Initializes logging, validates environment variables, sets up database schema,
    registers middlewares & handlers, and starts polling loop with graceful shutdown.
    """
    setup_logging()

    # Environment Validation
    validate_environment()

    # Database Initialization (with SQLite WAL Mode & Foreign Keys)
    await init_db()

    # Initialize Bot & Dispatcher
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Register Global Errors Router
    dp.include_router(errors_router)

    # Middleware Registration Order: UserTracking -> AntiSpam -> Throttling -> Admin -> Maintenance
    dp.message.outer_middleware(UserTrackingMiddleware())
    dp.message.outer_middleware(AntiSpamMiddleware())
    dp.message.outer_middleware(ThrottlingMiddleware())
    dp.message.outer_middleware(AdminMiddleware())
    dp.message.outer_middleware(MaintenanceMiddleware())

    dp.callback_query.outer_middleware(UserTrackingMiddleware())
    dp.callback_query.outer_middleware(AntiSpamMiddleware())
    dp.callback_query.outer_middleware(ThrottlingMiddleware())
    dp.callback_query.outer_middleware(AdminMiddleware())
    dp.callback_query.outer_middleware(MaintenanceMiddleware())


    # Register Application Handlers
    main_router = setup_handlers()
    dp.include_router(main_router)

    # Drop pending updates
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("Production-ready Bot application initialized (Stage 11 Hardening). Starting polling loop...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Unexpected error occurred during polling: {e}", exc_info=True)
    finally:
        await bot.session.close()
        logger.info("Bot session and HTTP connections closed successfully.")
