"""Shared error type for the deductions package."""

from __future__ import annotations


class DeductionValidationError(ValueError):
    """Raised when a deduction's structured input fails validation
    (negative distance/days, out-of-range values, etc.).

    Subclasses ValueError so callers that already catch ValueError at an API
    boundary (e.g. FastAPI/Pydantic error handlers) get consistent behavior,
    while still being specific enough to catch deliberately where needed.
    """
