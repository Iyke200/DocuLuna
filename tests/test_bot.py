import pytest
import logging
from telegram import Update, User, Message, Document, Chat
from telegram.ext import Application, ContextTypes
from bot.handlers import start, help_command, trial, refer, handle_pdf
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta
from db.models import User
import os

# Configure logging for debugging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_start():
    logger.debug("Starting test_start")
    try:
        update = Update(
            update_id=1,
            message=Message(
                message_id=1,
                chat=Chat(id=12345, type="private"),
                from_user=User(id=12345, first_name="Test", is_bot=False),
                text="/start"
            )
        )
        context = ContextTypes.DEFAULT_TYPE()
        context.bot = AsyncMock()
        context.bot.send_message = AsyncMock()
        with patch("bot.handlers.get_user", return_value={"telegram_id": 12345, "first_name": "Test", "referral_code": "abc123"}) as mock_get_user:
            logger.debug("Mocking get_user with telegram_id=12345")
            await start(update, context)
            logger.debug("start handler executed")
        assert context.bot.send_message.called, "send_message was not called"
        call_args = context.bot.send_message.call_args[1]
        assert "Welcome to **DocuLuna**, Test!" in call_args["text"], f"Expected welcome message, got: {call_args['text']}"
        logger.info("test_start passed")
    except Exception as e:
        logger.error(f"test_start failed: {str(e)}")
        raise

@pytest.mark.asyncio
async def test_help_command():
    logger.debug("Starting test_help_command")
    try:
        update = Update(
            update_id=1,
            message=Message(
                message_id=1,
                chat=Chat(id=12345, type="private"),
                from_user=User(id=12345, first_name="Test", is_bot=False),
                text="/help"
            )
        )
        context = ContextTypes.DEFAULT_TYPE()
        context.bot = AsyncMock()
        context.bot.send_message = AsyncMock()
        await help_command(update, context)
        assert context.bot.send_message.called, "send_message was not called"
        call_args = context.bot.send_message.call_args[1]
        assert "DocuLuna Commands" in call_args["text"], f"Expected help message, got: {call_args['text']}"
        logger.info("test_help_command passed")
    except Exception as e:
        logger.error(f"test_help_command failed: {str(e)}")
        raise

@pytest.mark.asyncio
async def test_trial_non_premium():
    logger.debug("Starting test_trial_non_premium")
    try:
        update = Update(
            update_id=1,
            message=Message(
                message_id=1,
                chat=Chat(id=12345, type="private"),
                from_user=User(id=12345, first_name="Test", is_bot=False),
                text="/trial"
            )
        )
        context = ContextTypes.DEFAULT_TYPE()
        context.bot = AsyncMock()
        context.bot.send_message = AsyncMock()
        with patch("bot.handlers.get_user", return_value={"telegram_id": 12345, "is_premium": False, "trial_expiry": None}) as mock_get_user:
            with patch("bot.handlers.session.execute", new=AsyncMock()) as mock_execute:
                logger.debug("Mocking get_user and session.execute")
                await trial(update, context)
                logger.debug("trial handler executed")
        assert context.bot.send_message.called, "send_message was not called"
        call_args = context.bot.send_message.call_args[1]
        assert "1-day Premium trial" in call_args["text"], f"Expected trial message, got: {call_args['text']}"
        assert mock_execute.called, "Database update was not called"
        logger.info("test_trial_non_premium passed")
    except Exception as e:
        logger.error(f"test_trial_non_premium failed: {str(e)}")
        raise

@pytest.mark.asyncio
async def test_refer():
    logger.debug("Starting test_refer")
    try:
        update = Update(
            update_id=1,
            message=Message(
                message_id=1,
                chat=Chat(id=12345, type="private"),
                from_user=User(id=12345, first_name="Test", is_bot=False),
                text="/refer"
            )
        )
        context = ContextTypes.DEFAULT_TYPE()
        context.bot = AsyncMock()
        context.bot.send_message = AsyncMock()
        context.bot.username = "DocuLunaBot"
        with patch("bot.handlers.get_user", return_value={"telegram_id": 12345, "referral_code": "abc123"}) as mock_get_user:
            with patch("bot.handlers.get_referral_balance", return_value=20000) as mock_balance:
                logger.debug("Mocking get_user and get_referral_balance")
                await refer(update, context)
                logger.debug("refer handler executed")
        assert context.bot.send_message.called, "send_message was not called"
        call_args = context.bot.send_message.call_args[1]
        assert "Your referral link" in call_args["text"], f"Expected referral link, got: {call_args['text']}"
        assert "Current balance: ₦200.00" in call_args["text"], f"Expected balance, got: {call_args['text']}"
        logger.info("test_refer passed")
    except Exception as e:
        logger.error(f"test_refer failed: {str(e)}")
        raise

@pytest.mark.asyncio
async def test_handle_pdf_non_pdf():
    logger.debug("Starting test_handle_pdf_non_pdf")
    try:
        update = Update(
            update_id=1,
            message=Message(
                message_id=1,
                chat=Chat(id=12345, type="private"),
                from_user=User(id=12345, first_name="Test", is_bot=False),
                document=Document(file_id="123", file_name="test.txt", mime_type="text/plain")
            )
        )
        context = ContextTypes.DEFAULT_TYPE()
        context.bot = AsyncMock()
        context.bot.send_message = AsyncMock()
        await handle_pdf(update, context)
        context.bot.send_message.assert_called_with(
            chat_id=12345, text="Please upload a PDF file."
        )
        logger.info("test_handle_pdf_non_pdf passed")
    except Exception as e:
        logger.error(f"test_handle_pdf_non_pdf failed: {str(e)}")
        raise