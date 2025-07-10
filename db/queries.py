from sqlalchemy import select, update, insert
from db.models import User, Usage, Feedback, Analytics, Referral
from datetime import datetime, timedelta
import uuid

async def get_user(telegram_id: int, session):
    query = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(query)
    user = result.scalars().first()
    if not user:
        query = insert(User).values(
            telegram_id=telegram_id,
            referral_code=str(uuid.uuid4()),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        await session.execute(query)
        await session.commit()
        query = select(User).where(User.telegram_id == telegram_id)
        result = await session.execute(query)
        user = result.scalars().first()
    return {
        "telegram_id": user.telegram_id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_premium": user.is_premium,
        "trial_expiry": user.trial_expiry,
        "referral_code": user.referral_code,
        "referral_balance": user.referral_balance,
        "bank_account_number": user.bank_account_number,
        "bank_code": user.bank_code
    }

async def check_usage_limit(telegram_id: int, session, daily_limit: int = 3):
    today = datetime.utcnow().date()
    query = select(Usage).where(
        Usage.telegram_id == telegram_id,
        Usage.date >= today,
        Usage.date < today + timedelta(days=1)
    )
    result = await session.execute(query)
    usage = result.scalars().first()
    if not usage:
        query = insert(Usage).values(
            telegram_id=telegram_id,
            date=datetime.utcnow(),
            conversion_count=0
        )
        await session.execute(query)
        await session.commit()
        return True
    return usage.conversion_count < daily_limit

async def increment_usage(telegram_id: int, session):
    today = datetime.utcnow().date()
    query = select(Usage).where(
        Usage.telegram_id == telegram_id,
        Usage.date >= today,
        Usage.date < today + timedelta(days=1)
    )
    result = await session.execute(query)
    usage = result.scalars().first()
    if usage:
        query = update(Usage).where(
            Usage.telegram_id == telegram_id,
            Usage.date >= today,
            Usage.date < today + timedelta(days=1)
        ).values(conversion_count=Usage.conversion_count + 1)
    else:
        query = insert(Usage).values(
            telegram_id=telegram_id,
            date=datetime.utcnow(),
            conversion_count=1
        )
    await session.execute(query)
    await session.commit()

async def save_feedback(telegram_id: int, message: str, session):
    if len(message) > 1000:
        raise ValueError("Feedback must be 1000 characters or less")
    query = insert(Feedback).values(
        telegram_id=telegram_id,
        message=message,
        created_at=datetime.utcnow()
    )
    await session.execute(query)
    await session.commit()

async def log_conversion(telegram_id: int, status: str, session, details: str = None):
    query = insert(Analytics).values(
        telegram_id=telegram_id,
        action="conversion",
        status=status,
        details=details,
        created_at=datetime.utcnow()
    )
    await session.execute(query)
    await session.commit()

async def record_referral(referrer_id: int, referred_id: int, session):
    query = insert(Referral).values(
        referrer_id=referrer_id,
        referred_id=referred_id,
        created_at=datetime.utcnow()
    )
    await session.execute(query)
    query = update(User).where(User.telegram_id == referrer_id).values(
        referral_balance=User.referral_balance + 20000
    )
    await session.execute(query)
    await session.commit()

async def get_referral_balance(telegram_id: int, session):
    query = select(User.referral_balance).where(User.telegram_id == telegram_id)
    result = await session.execute(query)
    return result.scalars().first() or 0

async def save_bank_details(telegram_id: int, account_number: str, bank_code: str, session):
    query = update(User).where(User.telegram_id == telegram_id).values(
        bank_account_number=account_number,
        bank_code=bank_code,
        updated_at=datetime.utcnow()
    )
    await session.execute(query)
    await session.commit()

async def has_notification_been_sent(telegram_id: int, session):
    today = datetime.utcnow().date()
    query = select(Usage).where(
        Usage.telegram_id == telegram_id,
        Usage.date >= today,
        Usage.date < today + timedelta(days=1)
    )
    result = await session.execute(query)
    usage = result.scalars().first()
    return usage.notification_sent if usage else False

async def mark_notification_sent(telegram_id: int, session):
    today = datetime.utcnow().date()
    query = update(Usage).where(
        Usage.telegram_id == telegram_id,
        Usage.date >= today,
        Usage.date < today + timedelta(days=1)
    ).values(notification_sent=True)
    await session.execute(query)
    await session.commit()