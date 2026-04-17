from __future__ import annotations

import logging

import stripe
from supabase import Client

from app.core.config import Settings
from app.models.enums import TransactionType

logger = logging.getLogger("picvibez.billing")

PLAN_PRICES = {
    "base_plan": 4999,  # $49.99 in cents
}
STORAGE_PRICE_PER_GB = 199  # $1.99 per GB

PRO_STORAGE_LIMIT = 10_737_418_240  # 10 GB


async def create_checkout_session(
    settings: Settings,
    *,
    user_id: str,
    event_id: str,
    txn_type: TransactionType,
    storage_gb: int | None = None,
    success_url: str = "",
    cancel_url: str = "",
) -> dict:
    if txn_type == TransactionType.BASE_PLAN:
        amount = PLAN_PRICES["base_plan"]
        description = "PicVibez Pro Plan - Remove watermarks, AI tagging, 10GB storage"
    elif txn_type == TransactionType.STORAGE_ADDON and storage_gb:
        amount = STORAGE_PRICE_PER_GB * storage_gb
        description = f"PicVibez Storage Add-on: +{storage_gb}GB"
    else:
        raise ValueError("Invalid checkout parameters")

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": description},
                "unit_amount": amount,
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=success_url or f"https://picvibez.com/payment-success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=cancel_url or "https://picvibez.com/payment-cancel",
        metadata={
            "user_id": user_id,
            "event_id": event_id,
            "type": txn_type.value,
            "storage_gb": str(storage_gb or 0),
        },
    )

    return {"checkout_url": session.url, "session_id": session.id}


async def handle_checkout_completed(db: Client, session: dict) -> None:
    metadata = session.get("metadata", {})
    user_id = metadata.get("user_id")
    event_id = metadata.get("event_id")
    txn_type = metadata.get("type")
    storage_gb = int(metadata.get("storage_gb", 0))

    if not all([user_id, event_id, txn_type]):
        logger.error("Incomplete metadata in checkout session: %s", session.get("id"))
        return

    db.table("transactions").insert({
        "event_id": event_id,
        "user_id": user_id,
        "stripe_payment_id": session.get("payment_intent", session.get("id")),
        "type": txn_type,
        "amount_cents": session.get("amount_total", 0),
        "purchased_bytes": storage_gb * 1_073_741_824 if storage_gb else None,
    }).execute()

    if txn_type == TransactionType.BASE_PLAN.value:
        db.table("events").update({
            "is_watermark_enabled": False,
            "storage_limit_bytes": PRO_STORAGE_LIMIT,
        }).eq("id", event_id).execute()
        logger.info("Event %s upgraded to Pro plan", event_id)

    elif txn_type == TransactionType.STORAGE_ADDON.value and storage_gb:
        event = db.table("events").select("storage_limit_bytes").eq("id", event_id).single().execute()
        new_limit = (event.data["storage_limit_bytes"] or 0) + (storage_gb * 1_073_741_824)
        db.table("events").update({"storage_limit_bytes": new_limit}).eq("id", event_id).execute()
        logger.info("Event %s storage increased by %dGB", event_id, storage_gb)
