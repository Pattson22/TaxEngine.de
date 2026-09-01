from __future__ import annotations

from pydantic import BaseModel


class PaymentIntentRequest(BaseModel):
    # Must be True the first time a filing requests a payment intent --
    # required for the § 356 Abs. 4 BGB early expiry of the statutory
    # withdrawal right (see AGB § 5) to be effective. Defaults to False
    # so an omitted/empty body is rejected rather than silently treated
    # as consent.
    withdrawal_consent: bool = False


class PaymentIntentResponse(BaseModel):
    client_secret: str
    payment_intent_id: str
    amount_cents: int
