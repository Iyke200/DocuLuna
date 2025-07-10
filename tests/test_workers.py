import pytest
import logging
from unittest.mock import AsyncMock, patch
from workers.tasks import send_notification
# Note: convert_pdf_to_docx test is limited due to file operation complexity

# Configure logging for debugging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_send_notification():
    logger.debug("Starting test_send_notification")
    try:
        with patch("bot.handlers.context.bot.send_message", new=AsyncMock()) as mock_send:
            logger.debug("Mocking send_message for user 12345")
            await send_notification(12345)
            logger.debug("send_notification executed")
        assert mock_send.called, "send_message was not called"
        call_args = mock_send.call_args[1]
        assert "You've used all 3 free conversions" in call_args["text"], f"Expected notification message, got {call_args['text']}"
        assert call_args["chat_id"] == 12345, f"Expected chat_id 12345, got {call_args['chat_id']}"
        logger.info("test_send_notification passed")
    except Exception as e:
        logger.error(f"test_send_notification failed: {str(e)}")
        raise