"""Unit tests for Settings' live-Stripe-key startup guard (see
app/config.py) -- the same isolation principle as the eric-submitter
worker's database split, applied to payment credentials: a live secret
key must never be active anywhere routine local/test usage could charge
a real card."""

import pytest
from pydantic import ValidationError

from app.config import Settings


class TestLiveStripeKeyGuard:
    def test_live_key_outside_production_is_rejected(self):
        with pytest.raises(ValidationError, match="LIVE key"):
            Settings(stripe_secret_key="sk_live_abc123", environment="development")

    def test_live_key_in_test_environment_is_rejected(self):
        with pytest.raises(ValidationError, match="LIVE key"):
            Settings(stripe_secret_key="sk_live_abc123", environment="test")

    def test_live_key_in_production_is_allowed(self):
        settings = Settings(stripe_secret_key="sk_live_abc123", environment="production")
        assert settings.stripe_secret_key == "sk_live_abc123"

    def test_test_key_outside_production_is_allowed(self):
        settings = Settings(stripe_secret_key="sk_test_abc123", environment="development")
        assert settings.stripe_secret_key == "sk_test_abc123"

    def test_placeholder_default_outside_production_is_allowed(self):
        settings = Settings(environment="development")
        assert settings.stripe_secret_key.startswith("sk_test_")
