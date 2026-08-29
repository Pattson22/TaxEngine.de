"""
Import every model here so `Base.metadata` is fully populated as soon as
`app.models` is imported once — this matters for two things:
  1. SQLAlchemy relationship() string references (e.g. "WageTaxCertificate")
     can only resolve once every mapped class has actually been imported
     somewhere in the process.
  2. A future Alembic `env.py` importing `app.models.Base` for autogenerate
     support needs every table registered on that one Base.
"""

from app.database import Base
from app.models.deduction import Deduction
from app.models.tax_filing import TaxFiling
from app.models.user import User
from app.models.wage_tax_certificate import WageTaxCertificate

__all__ = ["Base", "Deduction", "TaxFiling", "User", "WageTaxCertificate"]
