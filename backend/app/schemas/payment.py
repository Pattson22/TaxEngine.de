from __future__ import annotations

from pydantic import BaseModel


class PaymentIntentResponse(BaseModel):
    client_secret: str
    payment_intent_id: str
    amount_cents: int
