"""Sentry error monitoring, initialized once at process startup.

Deliberately more locked-down than sentry-sdk's defaults: this app's
request bodies routinely contain a taxpayer's full financial and tax
data (income, Steuer-ID, address, bank figures), which must never leave
this process on an error event, even accidentally. Two independent
layers enforce that:

    1. `max_request_body_size="never"` -- the FastAPI/Starlette
       integration never attaches request bodies to events at all,
       regardless of `send_default_pii`.
    2. `_scrub_event` -- a `before_send` hook that recursively redacts
       any dict key matching a sensitive-name denylist, as a backstop
       for anything reaching Sentry through `extra`/breadcrumbs/manual
       `capture_message` calls rather than through request-body capture.

`send_default_pii` stays False (the sentry-sdk default) so cookies,
unfiltered headers, and the user's IP address are never sent either.

Call `init_sentry()` once, before the FastAPI app is constructed (see
app/main.py) -- integrations patch on init, so anything imported/run
before this point isn't instrumented.
"""

from __future__ import annotations

import re
from typing import Any

from app.config import settings

_SENSITIVE_KEY_PATTERN = re.compile(
    r"(password|passwort|secret|token|steuer|tax_id|iban|kontonummer|"
    r"authorization|cookie|api_key|kindergeld|gehalt|lohn|einkommen)",
    re.IGNORECASE,
)


def _scrub_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[Filtered]" if _SENSITIVE_KEY_PATTERN.search(str(key)) else _scrub_value(val)
            for key, val in value.items()
        }
    if isinstance(value, list):
        return [_scrub_value(item) for item in value]
    return value


def _scrub_event(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any]:
    for field in ("extra", "contexts", "request"):
        if field in event:
            event[field] = _scrub_value(event[field])
    return event


def init_sentry() -> None:
    if not settings.sentry_dsn:
        return

    import sentry_sdk

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        send_default_pii=False,
        max_request_body_size="never",
        before_send=_scrub_event,
    )
