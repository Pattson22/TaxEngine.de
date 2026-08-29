# TaxEngine.de vs. Taxfix — Gap Analysis

Comparison baseline: Taxfix's current public positioning — guided
interview-style Q&A flow, English-language interface for expats, ELSTER
submission via a backend integration, ~€34.99/return, and documented
support for employment income, capital gains (Anlage KAP), rental income
(Anlage V), donations, childcare costs, and household/craftsperson services
(§35a). Sources: [Live In Germany — Best Tax Return Software 2026](https://liveingermany.de/best-tax-return-software-in-germany/), [CountryTaxCalc — German Tax Return Guide for Expats 2026](https://www.countrytaxcalc.com/tax-guides/germany-tax-return-guide-expats-2026/), [Taxfix — Kapitalerträge](https://support.taxfix.de/hc/en-us/articles/25293688896413-Capital-gains-in-the-tax-return), [Taxfix — Vermietung und Verpachtung](https://support.taxfix.de/hc/en-us/articles/24591090135325-Renting-and-leasing-in-the-Taxfix-app), [Taxfix — Kinderbetreuungskosten](https://taxfix.de/ratgeber/steuern-sparen/kinderbetreuungskosten-absetzen/), [§35a EStG](https://dejure.org/gesetze/EStG/35a.html).

## Where we stood before this pass

| Capability | Taxfix | TaxEngine.de (prior) |
|---|---|---|
| Employment income (Lohnsteuerbescheinigung) | ✅ | ✅ |
| Werbungskosten: commute, home office | ✅ | ✅ |
| Progressive tariff (Grundtarif, single) | ✅ | ✅ (placeholder) |
| **Splittingtarif (married/joint assessment)** | ✅ | ❌ — `users.is_joint_assessment` existed in the schema but nothing read it |
| **Solidaritätszuschlag** | ✅ | ❌ — column existed on `wage_tax_certificates` (withheld amount) but no final-liability calculation |
| **Kirchensteuer** | ✅ | ❌ — `church_tax_type`/`residence_state` existed but no calculation |
| **Sonderausgaben** (donations, childcare) | ✅ | ❌ — no Sonderausgaben concept at all |
| **§35a Handwerkerleistungen credit** | ✅ | ❌ |
| Capital gains (Anlage KAP, 25% Abgeltungsteuer) | ✅ | ❌ |
| Rental income (Anlage V) | ✅ | ❌ |
| Self-employment / freelance (Anlage S, EÜR) | — (Taxfix targets employees/simple cases) | ❌ |
| Kinderfreibetrag vs. Kindergeld Günstigerprüfung | ✅ | ❌ |
| Guided interview UX / mobile apps | ✅ | ❌ — no frontend built yet |
| Document OCR (auto-read Lohnsteuerbescheinigung) | ✅ | ❌ |
| Live ERiC submission | ✅ | 📄 documented architecture only, not implemented |
| Multi-language UI | ✅ (English for expats) | ❌ — no UI yet |

## What this pass closed

All of the following are real, tested code in `backend/app/tax_engine/`,
not just design notes — see the corresponding `tests/test_*.py` for
hand-verified reference values:

1. **Splittingtarif** (`tax_brackets.calculate_income_tax_for_assessment`) —
   dispatches to the Grundtarif or the halve/tax/double Splittingverfahren
   based on `is_joint_assessment`, per §32a Abs. 5 EStG.
2. **Solidaritätszuschlag** (`soli.py`) — Freigrenze, Milderungszone
   tapering, and flat-5.5% zones, with separate single/joint thresholds.
3. **Kirchensteuer** (`church_tax.py`) — 8% (Bayern/Baden-Württemberg) vs.
   9% (all other states) of assessed income tax, gated on
   `ChurchTaxType.NONE`.
4. **Sonderausgaben-Pauschbetrag** (`core.apply_sonderausgaben_pauschbetrag`)
   — same greater-of-actual-or-flat-rate pattern as the existing
   Werbungskosten logic, doubled for joint filers.
5. **Spenden / donations** (`deductions/donations.py`) — 20%-of-total-income
   cap, §10b EStG.
6. **Kinderbetreuungskosten / childcare** (`deductions/childcare.py`) — 2/3
   of cost, €4,000/child cap, §10 Abs. 1 Nr. 5 EStG.
7. **§35a Handwerkerleistungen** (`tax_credits/handwerkerleistungen.py`) —
   modeled correctly as a **credit against final tax liability**, not a
   deduction from taxable income — a distinction the schema and code now
   both make explicit (`tax_credits/` is a separate package from
   `deductions/`, and `tax_filings.tax_credits_applied_cents` is a
   separate column from the deduction-driven `taxable_income_cents`).

`db/schema.sql` was extended to match: `deduction_category_enum` gained
`DONATIONS`, `CHILDCARE`, `HANDWERKERLEISTUNGEN`, and `tax_filings` gained
`income_tax_cents`, `solidarity_surcharge_cents`, `church_tax_cents`, and
`tax_credits_applied_cents` so a filing can show a full Steuerbescheid-style
breakdown instead of just one refund number.

A composed worked example (married couple, €120,000 combined gross, NRW,
Catholic, commute + donations + childcare + Handwerkerleistungen all
applied together) was run end-to-end to confirm the new modules compose
correctly, not just pass in isolation.

## What's still a real gap (roadmap, not yet built)

Ranked by what would unlock the next slice of Taxfix's addressable market:

1. **Additional income categories** — capital gains (Anlage KAP, flat 25%
   Abgeltungsteuer + Sparer-Pauschbetrag), rental income (Anlage V),
   self-employment. Each needs its own income table alongside
   `wage_tax_certificates` and its own contribution to
   `calculate_taxable_income`. This is the single largest gap — most real
   filers eventually touch at least one of these.
2. **Kinderfreibetrag vs. Kindergeld Günstigerprüfung** — the Finanzamt
   automatically compares whether the family is better off with the
   Kinderfreibetrag (reduces zvE) or keeping the Kindergeld already paid
   monthly, and picks whichever is more favorable. Requires modeling
   children as first-class entities, not just an input count.
3. **Kappung** on Kirchensteuer for high earners (see the caveat already
   documented in `church_tax.py`).
4. **Spendenvortrag** (donation carry-forward) when the 20% cap is
   exceeded — needs a persisted per-user balance across tax years.
5. **Live ERiC integration** — `docs/ELSTER_ERIC_INTEGRATION.md` describes
   the architecture; the actual worker service, XML bundling, and BZSt
   developer-certificate onboarding are unbuilt.
6. **Guided interview UX, mobile apps, document OCR, multi-language UI** —
   entirely product/frontend work, no backend scaffolding exists yet.

Items 1–4 are pure `tax_engine` extensions (same pattern as everything
built in this pass: a constants entry, a pure function, hand-verified
tests) and are the natural next slice. Items 5–6 are cross-cutting
platform investments, not incremental additions to this module.
