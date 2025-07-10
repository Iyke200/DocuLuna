

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    telegram_id = Column(Integer, primary_key=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    is_premium = Column(Boolean, default=False)
    trial_expiry = Column(DateTime, nullable=True)
    referral_code = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True)
    referral_balance = Column(Integer, default=0)
    bank_account_number = Column(String(20), nullable=True)
    bank_code = Column(String(10), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Usage(Base):
    __tablename__ = "usage"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer)
    date = Column(DateTime, default=datetime.utcnow)
    conversion_count = Column(Integer, default=0)
    notification_sent = Column(Boolean, default=False)

class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer)
    message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class Analytics(Base):
    __tablename__ = "analytics"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer)
    action = Column(String(255))
    status = Column(String(50))
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Referral(Base):
    __tablename__ = "referrals"
    id = Column(Integer, primary_key=True)
    referrer_id = Column(Integer)
    referred_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

