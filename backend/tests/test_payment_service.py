"""
Unit tests for the parts of payment_service.py that don't require a live
Stripe API call: the pre-network guard rail in
create_payment_intent_for_filing, and the FULL webhook signature
verification + event handling in handle_stripe_webhook_event (which is
pure local HMAC verification + JSON parsing -- no network call at all --
so it's tested for real here, not mocked, using the exact signing
algorithm Stripe's own SDK uses). The DB session is mocked since these
tests don't need a real database to prove this module's own logic.

Live end-to-end verification (a real HTTP round-trip through
/tax-filings/{id}/payment-intent and /webhooks/stripe against a real
Postgres) was additionally performed manually against a throwaway
Dockerized database during development -- see the session's smoke-test
history; not reproduced here since this test suite intentionally stays
DB-free like the rest of tests/.
"""

import hashlib
import hmac
import json
import time
from unittest.mock import MagicMock, patch

import pytest
import stripe

from app.config import settings
from app.models.enums import FilingStatus
from app.models.tax_filing import TaxFiling
from app.services.payment_service import (
    PaymentError,
    create_payment_intent_for_filing,
    handle_stripe_webhook_event,
)


def _sign(payload: bytes, secret: str, timestamp: int | None = None) -> str:
    """Replicates stripe.WebhookSignature._compute_signature exactly, so
    these tests exercise the real verification path in
    stripe.Webhook.construct_event rather than mocking it away."""
    timestamp = timestamp if timestamp is not None else int(time.time())
    signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
    signature = hmac.new(
        secret.encode("utf-8"), signed_payload.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return f"t={timestamp},v1={signature}"


class TestCreatePaymentIntentGuardRail:
    def test_rejects_draft_filing_without_touching_stripe(self):
        filing = TaxFiling(status=FilingStatus.DRAFT, processing_fee_cents=3490)
        with pytest.raises(PaymentError, match="CALCULATED"):
            create_payment_intent_for_filing(filing)

    def test_rejects_already_fee_paid_filing(self):
        filing = TaxFiling(status=FilingStatus.FEE_PAID, processing_fee_cents=3490)
        with pytest.raises(PaymentError):
            create_payment_intent_for_filing(filing)

    def test_rejects_submitted_filing(self):
        filing = TaxFiling(status=FilingStatus.SUBMITTED, processing_fee_cents=3490)
        with pytest.raises(PaymentError):
            create_payment_intent_for_filing(filing)


class TestCreatePaymentIntentStripeErrorHandling:
    """Regression test: a real (invalid Stripe key) run against a live
    browser surfaced this exact failure mode -- an unhandled
    stripe.StripeError reached FastAPI as a bare 500 with no CORS headers
    (Starlette's ServerErrorMiddleware generates that response outside the
    path CORSMiddleware hooks into), so the browser reported an opaque
    "Failed to fetch" with the real error completely invisible. This must
    never reach the caller as anything other than PaymentError."""

    def test_stripe_authentication_error_is_wrapped_as_payment_error(self):
        filing = TaxFiling(status=FilingStatus.CALCULATED, processing_fee_cents=3490)

        with patch(
            "stripe.PaymentIntent.create",
            side_effect=stripe.AuthenticationError("Invalid API Key provided"),
        ):
            with pytest.raises(PaymentError):
                create_payment_intent_for_filing(filing)

    def test_stripe_api_connection_error_is_wrapped_as_payment_error(self):
        filing = TaxFiling(status=FilingStatus.CALCULATED, processing_fee_cents=3490)

        with patch(
            "stripe.PaymentIntent.create",
            side_effect=stripe.APIConnectionError("Could not connect to Stripe"),
        ):
            with pytest.raises(PaymentError):
                create_payment_intent_for_filing(filing)

    def test_stripe_error_does_not_set_payment_provider_ref(self):
        # If PaymentError is raised, the filing must NOT look like it has
        # a live PaymentIntent -- otherwise a later webhook lookup could
        # be confused by a ref that was never actually created.
        filing = TaxFiling(status=FilingStatus.CALCULATED, processing_fee_cents=3490)

        with patch(
            "stripe.PaymentIntent.create",
            side_effect=stripe.AuthenticationError("Invalid API Key provided"),
        ):
            with pytest.raises(PaymentError):
                create_payment_intent_for_filing(filing)

        assert filing.payment_provider_ref is None


class TestWebhookSignatureVerification:
    def test_forged_signature_is_rejected_before_touching_db(self):
        db = MagicMock()
        payload = b'{"type": "payment_intent.succeeded"}'

        with pytest.raises(PaymentError):
            handle_stripe_webhook_event(payload, "t=1,v1=deadbeef", db)

        db.get.assert_not_called()

    def test_missing_signature_header_is_rejected(self):
        db = MagicMock()
        with pytest.raises(PaymentError):
            handle_stripe_webhook_event(b"{}", "", db)
        db.get.assert_not_called()

    def test_valid_signature_with_irrelevant_event_type_is_a_noop(self):
        db = MagicMock()
        payload = json.dumps({"type": "charge.refunded", "data": {"object": {}}}).encode()
        header = _sign(payload, settings.stripe_webhook_secret)

        handle_stripe_webhook_event(payload, header, db)  # must not raise

        db.get.assert_not_called()

    def test_valid_signature_missing_filing_id_metadata_is_a_noop(self):
        db = MagicMock()
        payload = json.dumps(
            {"type": "payment_intent.succeeded", "data": {"object": {"metadata": {}}}}
        ).encode()
        header = _sign(payload, settings.stripe_webhook_secret)

        handle_stripe_webhook_event(payload, header, db)

        db.get.assert_not_called()

    def test_valid_signature_marks_calculated_filing_as_fee_paid(self):
        db = MagicMock()
        fake_filing = TaxFiling(status=FilingStatus.CALCULATED, processing_fee_cents=3490)
        db.get.return_value = fake_filing

        payload = json.dumps(
            {
                "type": "payment_intent.succeeded",
                "data": {"object": {"metadata": {"filing_id": "11111111-1111-1111-1111-111111111111"}}},
            }
        ).encode()
        header = _sign(payload, settings.stripe_webhook_secret)

        handle_stripe_webhook_event(payload, header, db)

        assert fake_filing.status == FilingStatus.FEE_PAID
        assert fake_filing.fee_paid_at is not None
        db.commit.assert_called_once()

    def test_filing_not_in_calculated_status_is_left_unchanged(self):
        # Idempotency guard: a filing already FEE_PAID (e.g. Stripe
        # retried the webhook) should not be re-processed/re-committed.
        db = MagicMock()
        fake_filing = TaxFiling(status=FilingStatus.FEE_PAID, processing_fee_cents=3490)
        db.get.return_value = fake_filing

        payload = json.dumps(
            {
                "type": "payment_intent.succeeded",
                "data": {"object": {"metadata": {"filing_id": "11111111-1111-1111-1111-111111111111"}}},
            }
        ).encode()
        header = _sign(payload, settings.stripe_webhook_secret)

        handle_stripe_webhook_event(payload, header, db)

        assert fake_filing.status == FilingStatus.FEE_PAID  # unchanged
        db.commit.assert_not_called()

    def test_filing_not_found_is_a_noop(self):
        db = MagicMock()
        db.get.return_value = None
        payload = json.dumps(
            {
                "type": "payment_intent.succeeded",
                "data": {"object": {"metadata": {"filing_id": "11111111-1111-1111-1111-111111111111"}}},
            }
        ).encode()
        header = _sign(payload, settings.stripe_webhook_secret)

        handle_stripe_webhook_event(payload, header, db)  # must not raise

        db.commit.assert_not_called()
