import logging
from celery import Celery
from os import getenv
from workers.converters import pdf_to_docx
from bot.utils import send_file
from db.queries import log_conversion
from db.database import get_db
import zipfile
import os

logger = logging.getLogger(__name__)

app = Celery(
    "tasks",
    broker=getenv("CELERY_BROKER_URL", "redis://redis:6379/0"),
    backend=getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0"),
)
app.conf.task_serializer = "json"
app.conf.result_serializer = "json"
app.conf.accept_content = ["json"]
app.conf.task_track_started = True
app.conf.task_time_limit = 600
app.conf.task_soft_time_limit = 540

@app.task(bind=True, max_retries=3)
async def convert_pdf_to_docx(self, user_id: int, input_path: str, password: str = None):
    try:
        logger.info("Starting PDF conversion for user %s: %s", user_id, input_path)
        file_name = os.path.basename(input_path)
        output_path = f"{getenv('RESULT_DIR', '/app/storage/results')}/{user_id}_{file_name.replace('.pdf', '.docx')}"
        pdf_to_docx(input_path, output_path, password)
        zip_path = f"{output_path}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(output_path, os.path.basename(output_path))
        async with get_db() as session:
            await log_conversion(user_id, "success", session=session)
        from bot.handlers import context
        await send_file(
            update=None,
            context=context,
            file_path=zip_path,
            caption=f"🎉 Your DOCX file ({file_name.replace('.pdf', '.docx')}) is ready (zipped for faster delivery)! Want unlimited conversions? Type /upgrade! 💎",
            chat_id=user_id
        )
        logger.info("Conversion completed for user %s: %s", user_id, input_path)
    except Exception as e:
        logger.error("Conversion failed for user %s: %s", user_id, e)
        async with get_db() as session:
            await log_conversion(user_id, "failed", str(e), session=session)
        self.retry(countdown=60, exc=e)

@app.task
async def send_notification(user_id: int):
    try:
        from bot.handlers import context
        paystack_url = f"https://paystack.com/pay/doculuna-premium?telegram_id={user_id}"
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "🎉 You've used all 3 free conversions today! 😞\n"
                "Unlock **unlimited conversions**, **encrypted PDF unlocking**, and **multi-file uploads** with Premium! 💎\n"
                f"Upgrade now: {paystack_url}\n"
                "Or try a 1-day Premium trial with /trial! 🚀"
            ),
            parse_mode="Markdown"
        )
        logger.info("Sent limit notification to user %s", user_id)
    except Exception as e:
        logger.error("Failed to send notification to user %s: %s", user_id, e)