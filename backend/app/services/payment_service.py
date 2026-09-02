"""
Stripe integration for the flat €34.90 processing fee.

Two operations:
    1. `create_payment_intent_for_filing` -- called from an authenticated
       API route once the user is ready to pay; creates a Stripe
       PaymentIntent and returns it (the route hands the client_secret to
       the frontend to complete via Stripe.js/Elements -- card details
       never touch our backend, so PCI scope stays with Stripe).
    2. `handle_stripe_webhook_event` -- called from the UNAUTHENTICATED
       webhook route. The ONLY trust boundary there is Stripe's own
       signature verification (`stripe.Webhook.construct_event`), not our
       JWT auth -- Stripe itself is the caller, so there is no bearer
       token to check.

This replaces the earlier `/tax-filings/{id}/pay` placeholder, which
trusted a bare authenticated client call with no actual payment
verification -- that endpoint has been removed.

Idempotency: a filing keeps its PaymentIntent id in `payment_provider_ref`
once created. Marking a filing FEE_PAID is naturally idempotent (setting
the same status/timestamp twice has no additional effect), which matters
because Stripe retries webhook delivery on any non-2xx response.
"""

from __future__ import annotations

from datetime import datetime, timezone

import stripe
from sqlalchemy.orm import Session

from app.config import settings
from app.models.enums import FilingStatus
from app.models.tax_filing import TaxFiling

stripe.api_key = settings.stripe_secret_key


class PaymentError(ValueError):
    """A payment-flow error the API layer should surface as a 4xx
    response (an unpayable filing state, or a webhook whose signature
    can't be verified)."""


def create_payment_intent_for_filing(filing: TaxFiling) -> stripe.PaymentIntent:
    """Create a Stripe PaymentIntent for a filing's processing fee and
    record its id on the filing.

    Raises:
        PaymentError: if the filing isn't in a payable state. Requiring
            CALCULATED (not just any status) ensures the user has seen a
            real refund estimate before being asked to pay -- charging
            for an un-calculated filing would be charging for nothing.
    """
    if filing.status != FilingStatus.CALCULATED:
        raise PaymentError(
            "Filing must be in CALCULATED status to create a payment intent "
            f"(current status: {filing.status.value})."
        )

    try:
        intent = stripe.PaymentIntent.create(
            amount=filing.processing_fee_cents,
            currency="eur",
            metadata={"filing_id": str(filing.id), "user_id": str(filing.user_id)},
            # Card-only for the MVP. automatic_payment_methods was tried
            # live while debugging PaymentElement never mounting in live
            # mode -- confirmed via Stripe's own dashboard that it correctly
            # expanded "Allowed payment methods" to Card/Bancontact/Klarna/
            # PayPal/etc, so it reached Stripe fine, but the client-side
            # mount was still completely dead (same zero-iframe,
            # zero-console-output signature as with an explicit ["card"]
            # list). Reverted rather than leave unreviewed payment methods
            # live in checkout for a fix that didn't work.
            payment_method_types=["card"],
        )
    except stripe.StripeError as exc:
        # Card-specific declines can't happen here (no card is attached
        # yet at PaymentIntent-creation time -- that only happens later,
        # client-side, via Stripe.js). Everything stripe.StripeError can
        # raise at this call site is an account/connectivity problem (a
        # bad API key, Stripe being unreachable, a malformed request) --
        # i.e. OUR fault or Stripe's, never the taxpayer's, so a generic
        # message is appropriate rather than relaying exc's internals.
        #
        # This catch matters beyond a nicer error message: an uncaught
        # exception here reaches FastAPI as an unhandled 500, and Starlette's
        # ServerErrorMiddleware generates that 500 OUTSIDE the normal
        # response path CORSMiddleware hooks into -- so the response has
        # NO CORS headers, and the browser reports a bare "Failed to fetch"
        # with the real error completely invisible. Confirmed by reproducing
        # this exact failure against a real (deliberately invalid) Stripe
        # key: curl saw a plain 500 with no access-control-allow-origin
        # header, and the browser correctly refused to expose it to JS.
        raise PaymentError(
            "Could not start the payment -- the payment system is temporarily unavailable. Please try again shortly."
        ) from exc

    filing.payment_provider_ref = intent.id
    return intent


def handle_stripe_webhook_event(payload: bytes, signature_header: str, db: Session) -> None:
    """Verify and process an incoming Stripe webhook event.

    Args:
        payload: the RAW request body bytes (signature verification
            depends on the exact bytes Stripe signed -- a route MUST NOT
            parse-then-reserialize the body before calling this).
        signature_header: the `Stripe-Signature` request header.
        db: session to persist the resulting filing status change.

    Raises:
        PaymentError: if the signature can't be verified. This is the
            ENTIRE authentication boundary for the webhook route -- it
            has no JWT auth of its own.
    """
    try:
        event = stripe.Webhook.construct_event(payload, signature_header, settings.stripe_webhook_secret)
    except (stripe.SignatureVerificationError, ValueError) as exc:
        raise PaymentError(f"Could not verify Stripe webhook signature: {exc}") from exc

    if event["type"] != "payment_intent.succeeded":
        return  # not an event type this endpoint acts on

    payment_intent = event["data"]["object"]
    filing_id = payment_intent.get("metadata", {}).get("filing_id")
    if filing_id is None:
        return  # not a PaymentIntent created by create_payment_intent_for_filing

    filing = db.get(TaxFiling, filing_id)
    if filing is None:
        return  # filing was deleted after the PaymentIntent was created

    if filing.status == FilingStatus.CALCULATED:
        filing.status = FilingStatus.FEE_PAID
        filing.fee_paid_at = datetime.now(timezone.utc)
        db.commit()
