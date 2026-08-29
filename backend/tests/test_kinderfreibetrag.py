"""
Reference values computed by running the already-independently-verified
`tax_brackets.calculate_income_tax_for_assessment` (see
test_splitting_tarif.py for its own hand-verified reference values) through
both Günstigerprüfung branches, rather than re-deriving the tariff by hand
a third time -- this file's job is to verify the COMPARISON/branching logic
that's new here, not the tariff itself.

High earner, joint, 1 child, zvE=200,000 EUR, Kindergeld=3,000 EUR:
    tax_without = 62,794 EUR (matches test_splitting_tarif.py's own
        independently hand-verified reference for this exact zvE/assessment)
    kinderfreibetrag = 9,540 EUR -> zve_with = 190,460 EUR
    tax_with = tax(190,460 EUR, joint) + 3,000 EUR = 61,788 EUR
    -> Kinderfreibetrag wins (61,788 < 62,794)

Modest earner, joint, 1 child, zvE=40,000 EUR, Kindergeld=3,000 EUR:
    tax_without = 3,518 EUR
    zve_with = 40,000 - 9,540 = 30,460 EUR
    tax_with = tax(30,460 EUR, joint) + 3,000 EUR = 4,256 EUR
    -> Kindergeld wins (3,518 < 4,256)
"""

import pytest

from app.tax_engine.core import InvalidIncomeError
from app.tax_engine.kinderfreibetrag import (
    apply_kinderfreibetrag_guenstigerpruefung,
    calculate_kinderfreibetrag_total,
)


class TestCalculateKinderfreibetragTotal:
    def test_joint_single_child(self):
        assert calculate_kinderfreibetrag_total(1, is_joint_assessment=True) == 9_540_00

    def test_joint_two_children_scales_linearly(self):
        assert calculate_kinderfreibetrag_total(2, is_joint_assessment=True) == 19_080_00

    def test_single_assessment_is_half_of_joint(self):
        single = calculate_kinderfreibetrag_total(1, is_joint_assessment=False)
        joint = calculate_kinderfreibetrag_total(1, is_joint_assessment=True)
        assert single == joint // 2 == 4_770_00

    def test_zero_children_returns_zero(self):
        assert calculate_kinderfreibetrag_total(0, is_joint_assessment=True) == 0

    def test_rejects_negative_children(self):
        with pytest.raises(InvalidIncomeError):
            calculate_kinderfreibetrag_total(-1, is_joint_assessment=True)


class TestGuenstigerpruefungHighEarnerFavorsKinderfreibetrag:
    def test_kinderfreibetrag_is_applied(self):
        result = apply_kinderfreibetrag_guenstigerpruefung(
            zve_before_kinderfreibetrag_cents=200_000_00,
            number_of_children=1,
            is_joint_assessment=True,
            kindergeld_received_cents=3_000_00,
        )
        assert result.kinderfreibetrag_applied is True
        assert result.income_tax_without_kinderfreibetrag_cents == 62_794_00
        assert result.income_tax_with_kinderfreibetrag_cents == 61_788_00
        assert result.final_income_tax_cents == 61_788_00
        assert result.final_income_tax_cents < result.income_tax_without_kinderfreibetrag_cents

    def test_more_children_increases_the_saving(self):
        one_child = apply_kinderfreibetrag_guenstigerpruefung(
            200_000_00, 1, True, 3_000_00
        )
        two_children = apply_kinderfreibetrag_guenstigerpruefung(
            200_000_00, 2, True, 6_000_00
        )
        assert two_children.final_income_tax_cents < one_child.final_income_tax_cents


class TestGuenstigerpruefungModestEarnerFavorsKindergeld:
    def test_kinderfreibetrag_is_not_applied(self):
        result = apply_kinderfreibetrag_guenstigerpruefung(
            zve_before_kinderfreibetrag_cents=40_000_00,
            number_of_children=1,
            is_joint_assessment=True,
            kindergeld_received_cents=3_000_00,
        )
        assert result.kinderfreibetrag_applied is False
        assert result.income_tax_without_kinderfreibetrag_cents == 3_518_00
        assert result.income_tax_with_kinderfreibetrag_cents == 4_256_00
        assert result.final_income_tax_cents == 3_518_00
        # The taxpayer is never worse off than the better of the two paths.
        assert result.final_income_tax_cents <= result.income_tax_with_kinderfreibetrag_cents


class TestZeroChildren:
    def test_no_children_trivially_keeps_kindergeld_path(self):
        result = apply_kinderfreibetrag_guenstigerpruefung(
            zve_before_kinderfreibetrag_cents=100_000_00,
            number_of_children=0,
            is_joint_assessment=True,
            kindergeld_received_cents=0,
        )
        assert result.kinderfreibetrag_applied is False
        assert result.kinderfreibetrag_total_cents == 0
        from app.tax_engine.tax_brackets import calculate_income_tax_for_assessment

        assert result.final_income_tax_cents == calculate_income_tax_for_assessment(
            100_000_00, 2024, is_joint_assessment=True
        )


class TestNeverWorseThanBothPaths:
    def test_final_tax_is_always_the_minimum_of_the_two_paths(self):
        for zve_eur, children, kindergeld_eur, joint in (
            (0, 1, 3_000, True),
            (15_000, 1, 3_000, False),
            (300_000, 3, 9_000, True),
            (50_000, 2, 6_000, True),
        ):
            result = apply_kinderfreibetrag_guenstigerpruefung(
                zve_eur * 100, children, joint, kindergeld_eur * 100
            )
            assert result.final_income_tax_cents == min(
                result.income_tax_without_kinderfreibetrag_cents,
                result.income_tax_with_kinderfreibetrag_cents,
            )


class TestInputValidation:
    def test_rejects_negative_zve(self):
        with pytest.raises(InvalidIncomeError):
            apply_kinderfreibetrag_guenstigerpruefung(-1, 1, True, 3_000_00)

    def test_rejects_negative_kindergeld(self):
        with pytest.raises(InvalidIncomeError):
            apply_kinderfreibetrag_guenstigerpruefung(100_000_00, 1, True, -1)

    def test_rejects_unsupported_tax_year(self):
        with pytest.raises(ValueError):
            apply_kinderfreibetrag_guenstigerpruefung(
                100_000_00, 1, True, 3_000_00, tax_year=1999
            )
