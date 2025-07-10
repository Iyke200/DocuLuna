import pytest
import logging
from fastapi.testclient import TestClient
from api.main import app
from unittest.mock import AsyncMock, patch
from db.models import Analytics
from os import getenv

# Configure logging for debugging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

client = TestClient(app)

@pytest.mark.asyncio
async def test_health_check():
    logger.debug("Starting test_health_check")
    try:
        response = client.get("/health")
        assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
        assert response.json() == {"status": "healthy"}, f"Expected {'status': 'healthy'}, got {response.json()}"
        logger.info("test_health_check passed")
    except Exception as e:
        logger.error(f"test_health_check failed: {str(e)}")
        raise

@pytest.mark.asyncio
async def test_paystack_webhook_invalid_signature():
    logger.debug("Starting test_paystack_webhook_invalid_signature")
    try:
        if not getenv("PAYSTACK_SECRET_KEY"):
            logger.warning("PAYSTACK_SECRET_KEY not set, using test_secret")
        with patch("os.getenv", return_value="test_secret"):
            response = client.post(
                "/webhook/paystack",
                json={"event": "charge.success"},
                headers={"x-paystack-signature": "invalid"}
            )
        assert response.status_code == 400, f"Expected status 400, got {response.status_code}"
        assert response.json() == {"detail": "Invalid signature"}, f"Expected invalid signature, got {response.json()}"
        logger.info("test_paystack_webhook_invalid_signature passed")
    except Exception as e:
        logger.error(f"test_paystack_webhook_invalid_signature failed: {str(e)}")
        raise

@pytest.mark.asyncio
async def test_paystack_webhook_success():
    logger.debug("Starting test_paystack_webhook_success")
    try:
        data = {
            "event": "charge.success",
            "data": {"metadata": {"telegram_id": 12345}}
        }
        signature = "valid_signature"
        with patch("os.getenv", return_value="test_secret"):
            with patch("hmac.compare_digest", return_value=True):
                with patch("api.routes.webhook.get_db", new=AsyncMock()) as mock_db:
                    mock_db().__aenter__.return_value.execute = AsyncMock()
                    logger.debug("Mocking get_db and hmac.compare_digest")
                    response = client.post(
                        "/webhook/paystack",
                        json=data,
                        headers={"x-paystack-signature": signature}
                    )
                    logger.debug("Webhook request sent")
        assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
        assert response.json() == {"status": "success"}, f"Expected {'status': 'success'}, got {response.json()}"
        assert mock_db().__aenter__.return_value.execute.called, "Database update was not called"
        logger.info("test_paystack_webhook_success passed")
    except Exception as e:
        logger.error(f"test_paystack_webhook_success failed: {str(e)}")
        raise

@pytest.mark.asyncio
async def test_admin_users_unauthorized():
    logger.debug("Starting test_admin_users_unauthorized")
    try:
        response = client.get("/admin/users/12345", headers={"x-api-key": "wrong_key"})
        assert response.status_code == 401, f"Expected status 401, got {response.status_code}"
        assert response.json() == {"detail": "Invalid API key"}, f"Expected invalid API key, got {response.json()}"
        logger.info("test_admin_users_unauthorized passed")
    except Exception as e:
        logger.error(f"test_admin_users_unauthorized failed: {str(e)}")
        raise

@pytest.mark.asyncio
async def test_admin_users_success():
    logger.debug("Starting test_admin_users_success")
    try:
        with patch("os.getenv", return_value="secret"):
            with patch("api.routes.admin.get_user", return_value={"telegram_id": 12345, "first_name": "Test"}) as mock_get_user:
                logger.debug("Mocking get_user with telegram_id=12345")
                response = client.get("/admin/users/12345", headers={"x-api-key": "secret"})
                logger.debug("Admin users request sent")
        assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
        assert response.json() == {"telegram_id": 12345, "first_name": "Test"}, f"Expected user data, got {response.json()}"
        logger.info("test_admin_users_success passed")
    except Exception as e:
        logger.error(f"test_admin_users_success failed: {str(e)}")
        raise

@pytest.mark.asyncio
async def test_admin_analytics():
    logger.debug("Starting test_admin_analytics")
    try:
        with patch("os.getenv", return_value="secret"):
            with patch("api.routes.admin.get_db", new=AsyncMock()) as mock_db:
                mock_db().__aenter__.return_value.execute.return_value.scalars.return_value.all.return_value = [
                    Analytics(telegram_id=12345, action="conversion", status="success")
                ]
                logger.debug("Mocking get_db with analytics data")
                response = client.get("/admin/analytics", headers={"x-api-key": "secret"})
                logger.debug("Admin analytics request sent")
        assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
        assert len(response.json()) == 1, f"Expected 1 record, got {len(response.json())}"
        assert response.json()[0]["telegram_id"] == 12345, f"Expected telegram_id 12345, got {response.json()[0]}"
        logger.info("test_admin_analytics passed")
    except Exception as e:
        logger.error(f"test_admin_analytics failed: {str(e)}")
        raise