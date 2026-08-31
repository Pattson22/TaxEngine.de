"""
Import every model here so `Base.metadata` is fully populated as soon as
`app.models` is imported once — this matters for two things:
  1. SQLAlchemy relationship() string references (e.g. "WageTaxCertificate")
     can only resolve once every mapped class has actually been imported
     somewhere in the process.
  2. Alembic's `env.py` imports `app.models.Base` for autogenerate support,
     which needs every table registered on that one Base.
"""

from app.database import Base
from app.models.capital_income_statement import CapitalIncomeStatement
from app.models.child import Child
from app.models.deduction import Deduction
from app.models.eric_submission_job import EricSubmissionJob
from app.models.rental_property_statement import RentalPropertyStatement
from app.models.self_employment_statement import SelfEmploymentStatement
from app.models.tax_filing import TaxFiling
from app.models.user import User
from app.models.wage_tax_certificate import WageTaxCertificate

__all__ = [
    "Base",
    "CapitalIncomeStatement",
    "Child",
    "Deduction",
    "EricSubmissionJob",
    "RentalPropertyStatement",
    "SelfEmploymentStatement",
    "TaxFiling",
    "User",
    "WageTaxCertificate",
]
