import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from PyPDF2 import PdfReader
import os

logger = logging.getLogger(__name__)

async def send_file(update: Update, context: ContextTypes.DEFAULT_TYPE, file_path: str, caption: str, chat_id: int = None):
    try:
        if chat_id:
            await context.bot.send_document(chat_id=chat_id, document=open(file_path, 'rb'), caption=caption)
        else:
            await update.message.reply_document(document=open(file_path, 'rb'), caption=caption)
        logger.info("Sent file %s to user %s", file_path, chat_id or update.effective_user.id)
    except Exception as e:
        logger.error("Error sending file %s: %s", file_path, e)
        raise

def is_valid_pdf(file_path: str) -> bool:
    try:
        PdfReader(file_path)
        return True
    except Exception as e:
        logger.error("Invalid PDF %s: %s", file_path, e)
        return False
