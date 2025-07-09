import logging
import os
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
)
from telegram.constants import ParseMode
from db.database import get_db
from db.queries import (
    get_user,
    increment_usage,
    check_usage_limit,
    save_feedback,
    log_conversion,
    record_referral,
    get_referral_balance,
    save_bank_details,
    has_notification_been_sent,
    mark_notification_sent,
)
from workers.tasks import convert_pdf_to_docx, send_notification
from bot.utils import send_file
from datetime import datetime, timedelta
from PyPDF2 import PdfReader
from os import getenv
from db.models import User

logger = logging.getLogger(__name__)
LAUNCH_DATE = datetime(2025, 7, 5)
REFERRAL_REWARD = 20000
REWARD_PERIOD = timedelta(days=14)

def setup_handlers(application: Application):
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("trial", trial))
    application.add_handler(CommandHandler("refer", refer))
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CommandHandler("withdraw", withdraw))
    application.add_handler(CommandHandler("feedback", feedback))
    application.add_handler(CommandHandler("unlock", unlock))
    application.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_feedback))
    application.add_handler(CallbackQueryHandler(button_callback))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    async with get_db() as session:
        user_data = await get_user(user.id, session)
    referral_code = context.args[0] if context.args else None
    if referral_code and user_data["referral_code"] != referral_code:
        async with get_db() as session:
            referrer = await get_user_by_referral_code(referral_code, session)
            if referrer and datetime.utcnow() <= LAUNCH_DATE + REWARD_PERIOD:
                await record_referral(referrer["telegram_id"], user.id, session)
    reply_text = (
        f"Welcome to **DocuLuna**, {user.first_name}! 🚀\n"
        "Transform your PDFs into editable Word documents in seconds! 📄✨\n"
        "Free users get 3 conversions/day, or try a 1-day Premium trial with /trial!\n"
        "Premium users unlock **encrypted PDF conversion** and **multi-file uploads**! 💎\n"
        "➡️ Upload a PDF, type /upgrade, or invite friends with /refer to earn ₦200 per referral!"
    )
    await update.message.reply_text(reply_text, parse_mode=ParseMode.MARKDOWN)

async def get_user_by_referral_code(referral_code: str, session):
    from sqlalchemy import select
    query = select(User).where(User.referral_code == referral_code)
    result = await session.execute(query)
    return result.scalars().first()

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📚 **DocuLuna Commands**:\n"
        "/start - Begin your journey\n"
        "/help - Show this guide\n"
        "/trial - Start a 1-day Premium trial\n"
        "/refer - Get your referral link\n"
        "/balance - Check referral earnings\n"
        "/withdraw - Cash out referral earnings\n"
        "/feedback <message> - Share your thoughts\n"
        "/unlock <password> - Set password for encrypted PDFs\n"
        "📄 Upload a PDF to convert it to Word!\n"
        "Free users: 3 conversions/day. Premium: unlimited + advanced features! Type /upgrade."
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def trial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    async with get_db() as session:
        user_data = await get_user(user.id, session)
        if user_data["is_premium"] or (user_data["trial_expiry"] and datetime.utcnow() < user_data["trial_expiry"]):
            await update.message.reply_text("You're already on Premium or an active trial! 😎")
            return
        from sqlalchemy import update
        query = update(User).where(User.telegram_id == user.id).values(
            trial_expiry=datetime.utcnow() + timedelta(days=1)
        )
        await session.execute(query)
        await session.commit()
        await update.message.reply_text(
            "🎉 You've activated a 1-day Premium trial! Enjoy unlimited conversions, encrypted PDF unlocking, and multi-file uploads! 💎"
        )

async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    async with get_db() as session:
        user_data = await get_user(user.id, session)
        balance = await get_referral_balance(user.id, session)
    referral_link = f"https://t.me/{context.bot.username}?start={user_data['referral_code']}"
    reply_text = (
        f"📣 Invite friends to DocuLuna and earn ₦200 per referral until {LAUNCH_DATE + REWARD_PERIOD:%B %d, %Y}!\n"
        f"Your referral link: {referral_link}\n"
        f"Current balance: ₦{balance / 100:.2f}\n"
        "Use /balance to check earnings or /withdraw to cash out!"
    )
    await update.message.reply_text(reply_text, parse_mode=ParseMode.MARKDOWN)

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    async with get_db() as session:
        balance = await get_referral_balance(user.id, session)
    await update.message.reply_text(
        f"💰 Your referral balance is ₦{balance / 100:.2f}. Withdraw with /withdraw!"
    )

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    async with get_db() as session:
        balance = await get_referral_balance(user.id, session)
        if balance < 1000:
            await update.message.reply_text("Minimum withdrawal is ₦10. Keep referring! 📣")
            return
        user_data = await get_user(user.id, session)
        if not user_data.get("bank_account_number") or not user_data.get("bank_code"):
            keyboard = [[InlineKeyboardButton("Add Bank Details", callback_data="add_bank")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "Please add your bank details to withdraw.", reply_markup=reply_markup
            )
            return
        from api.main import initiate_payout
        await initiate_payout(user.id, balance, session)
        query = update(User).where(User.telegram_id == user.id).values(referral_balance=0)
        await session.execute(query)
        await session.commit()
        await update.message.reply_text(f"🎉 Payout of ₦{balance / 100:.2f} initiated! Check your bank account soon.")

async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["awaiting_feedback"] = True
    await update.message.reply_text("Please share your feedback (max 1000 characters):")

async def handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_feedback"):
        return
    feedback_text = update.message.text
    try:
        async with get_db() as session:
            await save_feedback(update.effective_user.id, feedback_text, session)
        await update.message.reply_text("Thank you for your feedback! 😊")
    except ValueError as e:
        await update.message.reply_text(str(e))
    finally:
        context.user_data["awaiting_feedback"] = False

async def unlock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    async with get_db() as session:
        user_data = await get_user(user.id, session)
        if not user_data["is_premium"] and (not user_data["trial_expiry"] or datetime.utcnow() >= user_data["trial_expiry"]):
            await update.message.reply_text(
                "🔒 Encrypted PDF unlocking is a Premium feature. Type /upgrade or /trial to unlock!"
            )
            return
    if not context.args:
        await update.message.reply_text("Please provide a password: /unlock <password>")
        return
    context.user_data["pdf_password"] = context.args[0]
    await update.message.reply_text("Password set! Upload your encrypted PDF to convert it.")

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    async with get_db() as session:
        user_data = await get_user(user.id, session)
        if not await check_usage_limit(user.id, session) and (not user_data["is_premium"] and (not user_data["trial_expiry"] or datetime.utcnow() >= user_data["trial_expiry"])):
            if not await has_notification_been_sent(user.id, session):
                await mark_notification_sent(user.id, session)
                await send_notification.delay(user.id)
            await update.message.reply_text(
                "😔 You've reached the daily limit of 3 free conversions. Upgrade to Premium with /upgrade or try a 1-day trial with /trial! 💎"
            )
            return
        await increment_usage(user.id, session)
    document = update.message.document
    if not document.file_name.lower().endswith(".pdf"):
        await update.message.reply_text("Please upload a PDF file.")
        return
    file_name = document.file_name
    file = await document.get_file()
    file_path = f"{getenv('UPLOAD_DIR', '/app/storage/uploads')}/{user.id}_{uuid.uuid4()}_{file_name}"
    await file.download_to_drive(file_path)
    pdf = PdfReader(file_path)
    if pdf.is_encrypted and not context.user_data.get("pdf_password"):
        await update.message.reply_text(
            "🔒 This PDF is encrypted. Provide a password with /unlock <password> first."
        )
        return
    if pdf.is_encrypted and (not user_data["is_premium"] and (not user_data["trial_expiry"] or datetime.utcnow() >= user_data["trial_expiry"])):
        await update.message.reply_text(
            "🔒 Encrypted PDF unlocking is a Premium feature. Type /upgrade or /trial to unlock!"
        )
        return
    try:
        task = convert_pdf_to_docx.delay(
            user.id, file_path, context.user_data.get("pdf_password") if pdf.is_encrypted else None
        )
        await update.message.reply_text(
            f"🎉 Converting {file_name} to Word! You'll receive updates soon. 🕒"
        )
    except Exception as e:
        logger.error("Error starting conversion for user %s: %s", user.id, e)
        await update.message.reply_text(
            "😔 Something went wrong. Try again or contact support. Premium users get priority help! /upgrade"
        )
        await log_conversion(user.id, "failed", str(e))

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "add_bank":
        await query.message.reply_text(
            "Please provide your bank account number and bank code (e.g., /bank 1234567890 044)"
        )
    elif query.data == "progress":
        pass  # Progress button is just for visual feedback