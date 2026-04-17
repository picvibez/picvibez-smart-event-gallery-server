from __future__ import annotations

import stripe

from app.core.config import get_settings


def configure_stripe() -> None:
    settings = get_settings()
    stripe.api_key = settings.STRIPE_SECRET_KEY


def get_stripe():
    """Return the stripe module (already configured)."""
    return stripe
