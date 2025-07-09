import logging
from telegram.ext import Application
from os import getenv
from bot.handlers import setup_handlers
from dotenv import load_dotenv
import sentry_sdk

load_dotenv()
logging.basicConfig(
    level=getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(getenv("LOG_FILE", "/app/logs/doculuna.log")),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

sentry_dsn = getenv("SENTRY_DSN")
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        traces_sample_rate=1.0,
        environment="production"
    )

async def main():
    try:
        logger.info("Starting DocuLuna bot")
        bot_token = getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            logger.error("TELEGRAM_BOT_TOKEN not set")
            raise ValueError("TELEGRAM_BOT_TOKEN not set")
        application = Application.builder().token(bot_token).build()
        setup_handlers(application)
        await application.run_polling(allowed_updates=["message", "callback_query"])
    except Exception as e:
        logger.error("Bot crashed: %s", e)
        raise

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 
