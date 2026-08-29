"""
tax_engine — pure-Python, framework-free German income tax calculation core.

Deliberately has zero FastAPI/SQLAlchemy imports: this package is the
auditable, unit-testable heart of the product and should be reviewable (and
eventually certifiable) in isolation from web/DB concerns. The API layer
(app/api/, not yet scaffolded) is responsible for loading DB rows, mapping
them into these functions' plain int/dataclass inputs, and persisting the
results.
"""
