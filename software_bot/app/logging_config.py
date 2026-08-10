import logging
import sys


def setup_logging() -> None:
    """
    Configures structured logging for the application.
    Prevents leaking secrets like BOT_TOKEN in logs.
    """
    logging_format = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"

    logging.basicConfig(
        level=logging.INFO,
        format=logging_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Reduce verbosity of third party libraries
    logging.getLogger("aiogram").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info("Logging initialized successfully.")
