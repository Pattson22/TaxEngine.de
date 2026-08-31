# TaxEngine.de vs. Taxfix — Gap Analysis

Comparison baseline: Taxfix's current public positioning — guided
interview-style Q&A flow, English-language interface for expats, ELSTER
submission via a backend integration, and documented support for
employment income, capital gains (Anlage KAP), rental income (Anlage V),
donations, childcare costs, and household/craftsperson services (§35a).
Sources: [Live In Germany — Best Tax Return Software 2026](https://liveingermany.de/best-tax-return-software-in-germany/), [CountryTaxCalc — German Tax Return Guide for Expats 2026](https://www.countrytaxcalc.com/tax-guides/germany-tax-return-guide-expats-2026/), [Taxfix — Kapitalerträge](https://support.taxfix.de/hc/en-us/articles/25293688896413-Capital-gains-in-the-tax-return), [Taxfix — Vermietung und Verpachtung](https://support.taxfix.de/hc/en-us/articles/24591090135325-Renting-and-leasing-in-the-Taxfix-app), [Taxfix — Kinderbetreuungskosten](https://taxfix.de/ratgeber/steuern-sparen/kinderbetreuungskosten-absetzen/), [§35a EStG](https://dejure.org/gesetze/EStG/35a.html).

**Pricing (2026-08 research)**: Taxfix charges €39.99/year (subscription)
or €49.99 one-time for an individual return, €59.99/€69.99 for joint —
plus a separate 20%-of-refund (min. €99.99) human-advisor Expert Service.
That's notably more than TaxEngine.de's flat €34.90, and unlike Taxfix
there's no subscription tier or refund-percentage pricing to compare
against — one flat fee, once, when you file. (An earlier version of this
doc incorrectly attributed TaxEngine.de's own €34.90 price to Taxfix —
corrected here.) Sources: [Taxfix — costs at a glance](https://taxfix.de/en/costs/), [Taxfix — Kosten im Überblick](https://taxfix.de/kosten/), [Taxfix — Experten-Service](https://taxfix.de/experten-service/).

## Current state

| Capability | Taxfix | TaxEngine.de |
|---|---|---|
| Employment income (Lohnsteuerbescheinigung) | ✅ | ✅ |
| Werbungskosten: commute, home office | ✅ | ✅ |
| Progressive tariff: Grundtarif + Splittingtarif | ✅ | ✅ |
| Solidaritätszuschlag (regular + flat capital-gains variant) | ✅ | ✅ |
| Kirchensteuer + Kappung (capping) | ✅ | ✅ (approximate state-level rate table, see `church_tax.py`) |
| Sonderausgaben (donations + carry-forward, childcare) | ✅ | ✅ |
| §35a Handwerkerleistungen credit | ✅ | ✅ |
| Capital gains (Anlage KAP, Abgeltungsteuer + Sparer-Pauschbetrag) | ✅ | ✅ (Günstigerprüfung election to use the progressive tariff instead is NOT modeled) |
| Rental income (Anlage V) | ✅ | ✅ (AfA depreciation schedule NOT modeled — expected pre-computed) |
| Self-employment / freelance (Anlage S, EÜR) | — (Taxfix targets employees/simple cases) | ✅ (Gewerbesteuer NOT modeled — correct for freelancers, understates Gewerbebetrieb) |
| Kinderfreibetrag vs. Kindergeld Günstigerprüfung | ✅ | ✅ (the calculation itself still treats children as a plain count — see `kinderfreibetrag.py`; children ARE first-class `app/models/child.py` entities for ELSTER submission identity data) |
| Real payment integration | ✅ | ✅ (Stripe PaymentIntent + verified webhook) |
| ELSTER submission | ✅ | 🔶 real `cffi` binding to the actual ERiC library, verified end-to-end (`EricCheckXML()` passes cleanly for wage/capital/rental/self-employment/children income together); `xml_builder.py` maps every real Anlage this project supports (donations/church-tax-paid still open); not yet wired into the FastAPI app (`NativeEricClient` belongs in a separate worker, see `docs/ELSTER_ERIC_INTEGRATION.md`); still blocked on a registered `HerstellerID` and each filer's Finanzamt BuFa-Nummer |
| Guided interview UX / mobile apps | ✅ | 🔶 a working Next.js web frontend exists (`frontend/`), click-tested through register → calculate → view-results in a real browser — no mobile apps, no guided-interview-style Q&A (it's a form-based flow), and Stripe Elements card entry itself is untested (no real test keys — see `frontend/README.md`) |
| Document OCR (auto-read Lohnsteuerbescheinigung) | ✅ | ❌ |
| Multi-language UI | ✅ (English for expats) | ❌ — English only, no i18n |
| Frontend forms for capital gains / rental / self-employment / Kinderfreibetrag | ✅ | ✅ — added `filings/[id]/{capital-income,rental-income,self-employment}` pages plus an inline Kinderfreibetrag form; previously these had working backend routes with no UI at all |
| Filing creation restricted to actually-supported tax years | — (Taxfix supports 2022–2025 retroactively) | ✅ — `GET /tax-filings/supported-years` + a frontend year picker, though only 2024 has reviewed constants right now (see "What's still a real gap" below) |

## What closed the gap

Everything marked ✅ above is real, tested code — `backend/tests/` (220
unit tests, 100% `tax_engine` coverage) plus live end-to-end smoke tests
against a real Dockerized Postgres for every feature, not just design
notes. A few highlights:

- **Splittingtarif** (`tax_brackets.calculate_income_tax_for_assessment`),
  **Solidaritätszuschlag** (`soli.py`, including the flat-rate-no-Freigrenze
  variant for capital gains), and **Kirchensteuer + Kappung**
  (`church_tax.py`) — the core surcharge/tariff machinery every other
  feature composes with.
- **Capital gains** (`capital_gains.py`) — the church-tax-reduced
  Abgeltungsteuer rate formula (`1/(4+k)`) was verified against the
  published ~24.45%/24.51% effective rates before implementation, not
  guessed at.
- **Rental & self-employment income** (`rental_income.py`,
  `self_employment_income.py`) — both return a SIGNED result (a loss is a
  legitimate negative number that offsets other income, §2 Abs. 3 EStG),
  which required extending `core.calculate_taxable_income` with a
  dedicated non-floored parameter rather than reusing the Werbungskosten
  pattern.
- **Kinderfreibetrag/Kindergeld Günstigerprüfung**
  (`kinderfreibetrag.py`) — runs both branches (keep Kindergeld vs. apply
  the allowance + claw back Kindergeld already received) and picks
  whichever is lower, exactly matching how the Finanzamt does it
  automatically.
- **Spendenvortrag** (`deductions/donations.py`) — donation carry-forward
  chained year-to-year via `tax_filings.donation_carryforward_out_cents`.
  Building this surfaced and fixed a real pre-existing bug: multiple
  donation rows in the same year were each being checked against the full
  20% cap independently, double-counting the allowance.
- **Real Stripe integration** (`services/payment_service.py`) replaces the
  original trust-the-client `/pay` placeholder — PaymentIntent creation
  plus signature-verified webhook handling, with the exact HMAC
  verification algorithm exercised in tests (no live Stripe keys needed to
  prove the verification logic itself is correct).
- **ERiC submission scaffold** (`app/eric/`) — real XML generation and a
  full validate→submit→persist orchestration wired to
  `POST /tax-filings/{id}/submit`, built against a `StubEricClient` since
  the real `NativeEricClient` needs a BZSt developer certificate this
  project doesn't have. The stub is explicit about what it is; it never
  pretends to be a real government submission.
- **Frontend** (`frontend/`) — Next.js + TypeScript, the golden path end to
  end (register → dashboard → add income/deductions → calculate → pay via
  Stripe Elements → submit). Verified via a clean production build, clean
  lint, and a real click-through in Chrome (register → dashboard → add
  wage income → add a commute deduction → calculate → view the refund
  breakdown), every displayed figure cross-checked against the backend's
  own numbers. That browser session caught a real bug: an unhandled Stripe
  API error reached FastAPI as a bare 500 with no CORS headers (Starlette's
  `ServerErrorMiddleware` bypasses `CORSMiddleware` for unhandled
  exceptions), so the browser reported an opaque "Failed to fetch" instead
  of a usable error — fixed by explicitly catching `stripe.StripeError` in
  `payment_service.py`, with a regression test.
- **Capital income / rental income / self-employment income / Kinderfreibetrag
  frontend forms** (`filings/[id]/{capital-income,rental-income,self-employment}`
  + the filing detail page's inline "Children" section) — these calculation
  paths were fully built and unit-tested earlier but had no way to reach
  them through the UI; the backend routes existed with zero frontend
  callers. Also fixed `canCalculate` on the filing detail page, which
  previously required a wage tax certificate even when a filer only had
  e.g. self-employment income. Verified with a real browser click-through
  (Trade Republic capital income, a loss-making Berlin rental property, a
  profitable freelance business, 1 child) — the resulting taxable income
  (9.234,00 €), capital gains tax (250,00 €), and total owed (263,00 €)
  were hand-verified against the Pauschbetrag/Sparer-Pauschbetrag math,
  and the rental loss correctly rendered as a negative (clay) ledger line.

## What's still a real gap

1. **Guided interview-style UX, mobile apps, document OCR/photo upload,
   multi-language UI, ELSTER prefill (Vorausgefüllte Steuererklärung /
   Belegabruf)** — the current frontend is a straightforward form-based
   flow (every income/deduction type now has its own add-form, per the
   table above), not a guided Q&A interview, and has no mobile app,
   document scanning, i18n, or ELSTER data-prefill integration. This is
   still the largest remaining gap. OCR and ELSTER prefill in particular
   require infrastructure (an OCR service, a real ELSTER Belegabruf
   integration) this project doesn't have — not attempted here.
2. **Retroactive filing for prior tax years** — Taxfix supports 2022–2025.
   `SUPPORTED_TAX_YEARS` (`tax_engine/constants.py`) only has a reviewed
   entry for 2024; the year-picker mechanism (`GET
   /tax-filings/supported-years`) is built to extend cleanly, but adding
   e.g. 2022/2023 constants requires sourcing and verifying that year's
   exact Grundfreibetrag/bracket thresholds/Pauschbeträge against the
   official BMF publication — deliberately not guessed at here, since
   `constants.py`'s own docstring treats it as "a compliance artifact, not
   just code."
3. **Wiring `NativeEricClient` into a real submission** — the client itself
   is real and verified against the actual ERiC library (`EricCheckXML()`
   passes cleanly for wage/capital/rental/self-employment/children income
   together), but still needs a registered `HerstellerID`, each filer's
   Finanzamt BuFa-Nummer, and a separate `eric-submitter` worker process
   (ERiC must never load inside the FastAPI web process). See
   `docs/ELSTER_ERIC_INTEGRATION.md` for exactly what's left.
4. **Smaller, explicitly-documented approximations** worth revisiting
   before this handles real filings: the §32d Abs. 6 EStG capital-gains
   Günstigerprüfung election, AfA depreciation schedules, Gewerbesteuer,
   partial-year Kinderfreibetrag eligibility and the non-custodial-parent
   half-transfer (children ARE now first-class entities with real
   identity data for submission purposes, see `app/models/child.py` —
   what's still simplified is the Günstigerprüfung calculation itself,
   per `kinderfreibetrag.py`'s docstring), and the Kirchensteuer Kappung
   rate table's per-state-not-per-denomination simplification.
