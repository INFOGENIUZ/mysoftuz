import asyncio
import sys
import logging
from app.bot import start_bot

if __name__ == "__main__":
    try:
        asyncio.run(start_bot())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot application stopped manually.")
    except Exception as e:
        logging.critical(f"Fatal error starting bot: {e}", exc_info=True)
        sys.exit(1)
