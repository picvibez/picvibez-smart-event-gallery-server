from __future__ import annotations

import logging
from typing import Annotated

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.config import Settings
from app.core.dependencies import CurrentUser, get_config, get_current_user, get_db
from app.models.schemas import CheckoutRequest, CheckoutResponse, MessageResponse
from app.services.billing_service import create_checkout_session, handle_checkout_completed

logger = logging.getLogger("picvibez.billing")
router = APIRouter(prefix="/billing", tags=["billing"])


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    body: CheckoutRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    settings: Settings = Depends(get_config),
):
    try:
        result = await create_checkout_session(
            settings,
            user_id=user.id,
            event_id=str(body.event_id),
            txn_type=body.type,
            storage_gb=body.storage_gb,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/webhook", response_model=MessageResponse)
async def stripe_webhook(
    request: Request,
    db=Depends(get_db),
    settings: Settings = Depends(get_config),
):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        await handle_checkout_completed(db, session)
        logger.info("Processed checkout.session.completed: %s", session.get("id"))

    return MessageResponse(message="Webhook received")
