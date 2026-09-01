"""Unit tests for app/monitoring.py's before_send scrubber -- the
backstop that redacts sensitive field names from anything reaching
Sentry outside of request-body capture (which is separately disabled
entirely via max_request_body_size="never" in init_sentry())."""

from app.monitoring import _scrub_event


class TestScrubEvent:
    def test_redacts_sensitive_keys_in_extra(self):
        event = {
            "extra": {
                "steuernummer": "13/391/08153",
                "tax_identification_number": "12345678901",
                "note": "not sensitive",
            }
        }

        result = _scrub_event(event, {})

        assert result["extra"]["steuernummer"] == "[Filtered]"
        assert result["extra"]["tax_identification_number"] == "[Filtered]"
        assert result["extra"]["note"] == "not sensitive"

    def test_redacts_nested_and_list_values(self):
        event = {
            "contexts": {
                "filing": {"gross_wage_cents": 5200000, "password": "hunter2"},
                "items": [{"iban": "DE00..."}, {"ok": "fine"}],
            }
        }

        result = _scrub_event(event, {})

        assert result["contexts"]["filing"]["password"] == "[Filtered]"
        assert result["contexts"]["filing"]["gross_wage_cents"] == 5200000
        assert result["contexts"]["items"][0]["iban"] == "[Filtered]"
        assert result["contexts"]["items"][1]["ok"] == "fine"

    def test_leaves_event_without_scrubbed_fields_untouched(self):
        event = {"level": "error", "message": "boom"}

        result = _scrub_event(event, {})

        assert result == {"level": "error", "message": "boom"}
