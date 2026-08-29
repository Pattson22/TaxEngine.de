"""
Webhook endpoints — deliberately OUTSIDE the JWT auth boundary
(`app.api.deps.get_current_user` is never used here) because the caller is
an external service (Stripe), not one of our users. Each handler is
responsible for its own authentication — for Stripe, that's verifying the
`Stripe-Signature` header against the raw request body.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.payment_service import PaymentError, handle_stripe_webhook_event

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/stripe", status_code=status.HTTP_204_NO_CONTENT)
async def stripe_webhook(request: Request, db: Session = Depends(get_db)) -> None:
    """Receives Stripe webhook events. Must read the RAW body (not a
    parsed JSON model) since signature verification is computed over the
    exact bytes Stripe signed."""
    payload = await request.body()
    signature_header = request.headers.get("stripe-signature", "")

    try:
        handle_stripe_webhook_event(payload, signature_header, db)
    except PaymentError as exc:
        # A 4xx here tells Stripe NOT to retry (this webhook is
        # unverifiable/malformed, retrying won't fix that) -- contrast
        # with a 5xx, which Stripe interprets as "try again later".
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
