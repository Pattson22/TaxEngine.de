"""Deduction (Werbungskosten) algorithm modules.

Each module in this package implements ONE deduction category end-to-end:
structured input -> validation -> statutory formula -> cents amount. Callers
(API layer) wrap the result in a `core.DeductionLine` before handing it to
`core.calculate_werbungskosten`.
"""

from app.tax_engine.deductions.errors import DeductionValidationError

__all__ = ["DeductionValidationError"]
