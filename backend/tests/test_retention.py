"""Unit tests for app/retention/purge_expired_data.py. Mocks the DB
session the same way tests/test_eric_submitter_worker.py mocks it for
worker job-processing logic -- no real database needed to prove the
cutoff math and the delete-order/call-shape are correct."""

import uuid
from datetime import date
from unittest.mock import MagicMock, call

from app.documents.storage import DocumentStorage
from app.models.capital_income_statement import CapitalIncomeStatement
from app.models.child import Child
from app.models.deduction import Deduction
from app.models.rental_property_statement import RentalPropertyStatement
from app.models.self_employment_statement import SelfEmploymentStatement
from app.models.tax_filing import TaxFiling
from app.models.wage_tax_certificate import WageTaxCertificate
from app.retention.purge_expired_data import _cutoff_tax_year, purge_expired_tax_years


class TestCutoffTaxYear:
    def test_ten_year_retention_from_start_of_year(self):
        # 2015-12-31 (end of tax_year 2015) plus 10 full years is
        # 2025-12-31, already past by 2026-01-01 -- so 2015 is eligible.
        assert _cutoff_tax_year(retention_years=10, as_of=date(2026, 1, 1)) == 2015

    def test_ten_year_retention_one_day_earlier_is_not_yet_eligible(self):
        # On 2025-12-31 itself, 2015-12-31 + 10 years hasn't fully
        # elapsed yet by this module's conservative (year-granularity)
        # measure -- still excludes tax_year 2015.
        assert _cutoff_tax_year(retention_years=10, as_of=date(2025, 12, 31)) == 2014

    def test_zero_retention_years_still_requires_the_year_to_have_ended(self):
        assert _cutoff_tax_year(retention_years=0, as_of=date(2026, 6, 1)) == 2025


def _make_document_storage_mock() -> DocumentStorage:
    return MagicMock(spec=DocumentStorage)


class TestPurgeExpiredTaxYears:
    def test_deletes_each_income_and_deduction_table_filtered_by_cutoff(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []
        db.query.return_value.filter.return_value.delete.return_value = 1
        storage = _make_document_storage_mock()

        result = purge_expired_tax_years(db, storage, retention_years=10, as_of=date(2026, 1, 1))

        assert result.cutoff_tax_year == 2015
        for model in (
            WageTaxCertificate,
            CapitalIncomeStatement,
            RentalPropertyStatement,
            SelfEmploymentStatement,
            Child,
            Deduction,
            TaxFiling,
        ):
            assert call(model) in db.query.call_args_list

        assert result.capital_income_statements_deleted == 1
        assert result.rental_property_statements_deleted == 1
        assert result.self_employment_statements_deleted == 1
        assert result.children_deleted == 1
        assert result.deductions_deleted == 1
        assert result.tax_filings_deleted == 1
        db.commit.assert_called_once()

    def test_deletes_wage_certificate_files_before_their_db_rows(self):
        db = MagicMock()
        with_file = WageTaxCertificate(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            tax_year=2010,
            employer_name="ACME",
            gross_wage_cents=100_00,
            source_document_url="wage-tax-certificates/abc/def.pdf",
        )
        without_file = WageTaxCertificate(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            tax_year=2010,
            employer_name="ACME",
            gross_wage_cents=100_00,
            source_document_url=None,
        )
        db.query.return_value.filter.return_value.all.return_value = [with_file, without_file]
        db.query.return_value.filter.return_value.delete.return_value = 0
        storage = _make_document_storage_mock()

        result = purge_expired_tax_years(db, storage, retention_years=10, as_of=date(2026, 1, 1))

        storage.delete.assert_called_once_with("wage-tax-certificates/abc/def.pdf")
        assert db.delete.call_args_list == [call(with_file), call(without_file)]
        assert result.wage_tax_certificates_deleted == 2

    def test_never_deletes_a_certificate_file_that_was_never_uploaded(self):
        db = MagicMock()
        no_document = WageTaxCertificate(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            tax_year=2010,
            employer_name="ACME",
            gross_wage_cents=100_00,
            source_document_url=None,
        )
        db.query.return_value.filter.return_value.all.return_value = [no_document]
        db.query.return_value.filter.return_value.delete.return_value = 0
        storage = _make_document_storage_mock()

        purge_expired_tax_years(db, storage, retention_years=10, as_of=date(2026, 1, 1))

        storage.delete.assert_not_called()
