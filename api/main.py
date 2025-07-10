from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from db.database import get_db
from db.queries import get_user, log_conversion, get_referral_balance
from sqlalchemy.ext.asyncio import AsyncSession
import hmac
import hashlib
from os import getenv
import logging
import httpx

app = FastAPI()
logger = logging.getLogger(__name__)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/webhook/paystack")
async def paystack_webhook(request: Request):
    secret = getenv("PAYSTACK_SECRET_KEY")
    if not secret:
        logger.error("PAYSTACK_SECRET_KEY not set")
        raise HTTPException(status_code=500, detail="Server configuration error")
    body = await request.body()
    signature = request.headers.get("x-paystack-signature")
    computed_signature = hmac.new(
        secret.encode(), body, hashlib.sha512
    ).hexdigest()
    if not hmac.compare_digest(signature.encode(), computed_signature.encode()):
        logger.error("Invalid Paystack webhook signature")
        raise HTTPException(status_code=400, detail="Invalid signature")
    data = await request.json()
    event = data.get("event")
    if event == "charge.success":
        telegram_id = data.get("data", {}).get("metadata", {}).get("telegram_id")
        if telegram_id:
            async with get_db() as session:
                query = update(User).where(User.telegram_id == telegram_id).values(
                    is_premium=True,
                    trial_expiry=None,
                    updated_at=datetime.utcnow()
                )
                await session.execute(query)
                await session.commit()
                logger.info("User %s upgraded to Premium", telegram_id)
    return JSONResponse(status_code=200, content={"status": "success"})

async def verify_api_key(request: Request):
    api_key = request.headers.get("x-api-key")
    if api_key != getenv("ADMIN_API_KEY"):
        raise HTTPException(status_code=401, detail="Invalid API key")

@app.get("/admin/users/{telegram_id}", dependencies=[Depends(verify_api_key)])
async def get_user_data(telegram_id: int, db: AsyncSession = Depends(get_db)):
    user = await get_user(telegram_id, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.get("/admin/analytics", dependencies=[Depends(verify_api_key)])
async def get_analytics(db: AsyncSession = Depends(get_db)):
    query = select(Analytics)
    result = await db.execute(query)
    return result.scalars().all()

async def initiate_payout(telegram_id: int, amount: int, session: AsyncSession):
    user = await get_user(telegram_id, session)
    if not user.get("bank_account_number") or not user.get("bank_code"):
        raise ValueError("Bank details not set")
    paystack_url = "https://api.paystack.co/transfer"
    headers = {"Authorization": f"Bearer {getenv('PAYSTACK_SECRET_KEY')}"}
    data = {
        "source": "balance",
        "amount": amount,
        "recipient": {
            "type": "nuban",
            "account_number": user["bank_account_number"],
            "bank_code": user["bank_code"]
        },
        "reason": "DocuLuna Referral Payout"
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(paystack_url, headers=headers, json=data)
        if response.status_code != 200:
            logger.error("Payout failed for user %s: %s", telegram_id, response.text)
            raise HTTPException(status_code=500, detail="Payout failed")
        logger.info("Payout initiated for user %s: %s", telegram_id, amount)