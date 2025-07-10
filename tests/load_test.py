import pytest
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update
from db.database import get_db
from db.queries import get_user, increment_usage, get_referral_balance
from db.models import Base, User, Usage
from datetime import datetime

# Configure logging for debugging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# In-memory SQLite for testing
DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def override_get_db():
    async with async_session() as session:
        yield session

@pytest.mark.asyncio
async def test_get_user():
    logger.debug("Starting test_get_user")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.debug("Created database tables")
        async with async_session() as session:
            user = await get_user(12345, session)
            logger.debug(f"Retrieved user: {user}")
        assert user["telegram_id"] == 12345, f"Expected telegram_id 12345, got {user['telegram_id']}"
        assert user["referral_code"] is not None, "Expected non-null referral_code"
        assert user["referral_balance"] == 0, f"Expected referral_balance 0, got {user['referral_balance']}"
        logger.info("test_get_user passed")
    except Exception as e:
        logger.error(f"test_get_user failed: {str(e)}")
        raise

@pytest.mark.asyncio
async def test_increment_usage():
    logger.debug("Starting test_increment_usage")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.debug("Created database tables")
        async with async_session() as session:
            await increment_usage(12345, session)
            query = select(Usage).where(Usage.telegram_id == 12345)
            result = await session.execute(query)
            usage = result.scalars().first()
            logger.debug(f"Retrieved usage: {usage.__dict__}")
        assert usage is not None, "Usage record not created"
        assert usage.conversion_count == 1, f"Expected conversion_count 1, got {usage.conversion_count}"
        assert usage.telegram_id == 12345, f"Expected telegram_id 12345, got {usage.telegram_id}"
        logger.info("test_increment_usage passed")
    except Exception as e:
        logger.error(f"test_increment_usage failed: {str(e)}")
        raise

@pytest.mark.asyncio
async def test_get_referral_balance():
    logger.debug("Starting test_get_referral_balance")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.debug("Created database tables")
        async with async_session() as session:
            await get_user(12345, session)  # Create user
            query = update(User).where(User.telegram_id == 12345).values(referral_balance=20000)
            await session.execute(query)
            await session.commit()
            logger.debug("Updated referral_balance to 20000")
            balance = await get_referral_balance(12345, session)
            logger.debug(f"Retrieved balance: {balance}")
        assert balance == 20000, f"Expected balance 20000, got {balance}"
        logger.info("test_get_referral_balance passed")
    except Exception as e:
        logger.error(f"test_get_referral_balance failed: {str(e)}")
        raise