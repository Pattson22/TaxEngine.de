# TaxEngine.de vs. Taxfix — Gap Analysis

Comparison baseline: Taxfix's current public positioning — guided
interview-style Q&A flow, English-language interface for expats, ELSTER
submission via a backend integration, ~€34.99/return, and documented
support for employment income, capital gains (Anlage KAP), rental income
(Anlage V), donations, childcare costs, and household/craftsperson services
(§35a). Sources: [Live In Germany — Best Tax Return Software 2026](https://liveingermany.de/best-tax-return-software-in-germany/), [CountryTaxCalc — German Tax Return Guide for Expats 2026](https://www.countrytaxcalc.com/tax-guides/germany-tax-return-guide-expats-2026/), [Taxfix — Kapitalerträge](https://support.taxfix.de/hc/en-us/articles/25293688896413-Capital-gains-in-the-tax-return), [Taxfix — Vermietung und Verpachtung](https://support.taxfix.de/hc/en-us/articles/24591090135325-Renting-and-leasing-in-the-Taxfix-app), [Taxfix — Kinderbetreuungskosten](https://taxfix.de/ratgeber/steuern-sparen/kinderbetreuungskosten-absetzen/), [§35a EStG](https://dejure.org/gesetze/EStG/35a.html).

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
| Kinderfreibetrag vs. Kindergeld Günstigerprüfung | ✅ | ✅ (children as a plain count, not first-class entities — see `kinderfreibetrag.py`) |
| Real payment integration | ✅ | ✅ (Stripe PaymentIntent + verified webhook) |
| ELSTER submission | ✅ | 🔶 full orchestration + XML generation built and tested; blocked on an actual BZSt developer certificate (`NativeEricClient` is an explicit stub, not a fake success path) |
| Guided interview UX / mobile apps | ✅ | 🔶 a working Next.js web frontend exists (`frontend/`), click-tested through register → calculate → view-results in a real browser — no mobile apps, no guided-interview-style Q&A (it's a form-based flow), and Stripe Elements card entry itself is untested (no real test keys — see `frontend/README.md`) |
| Document OCR (auto-read Lohnsteuerbescheinigung) | ✅ | ❌ |
| Multi-language UI | ✅ (English for expats) | ❌ — English only, no i18n |

## What closed the gap

Everything marked ✅ above is real, tested code — `backend/tests/` (215
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

## What's still a real gap

1. **Guided interview-style UX, mobile apps, document OCR, multi-language
   UI** — the current frontend is a straightforward form-based flow
   covering wage income and five deduction categories, not a guided Q&A
   interview, and has no mobile app, OCR, or i18n. Capital gains, rental
   income, self-employment income, and the Kinderfreibetrag/Kindergeld
   inputs all have working backend routes but no frontend form yet — see
   `frontend/README.md`'s "Known simplifications". This is still the
   largest remaining gap, just a narrower one than "no frontend at all".
2. **A real `NativeEricClient`** — requires a signed BZSt developer
   agreement, the actual ERiC SDK, and a registered Herstellernummer/
   Softwarezertifikat. See `docs/ELSTER_ERIC_INTEGRATION.md` and
   `app/eric/client.py`'s docstring for exactly what's needed.
3. **Smaller, explicitly-documented approximations** worth revisiting
   before this handles real filings: the §32d Abs. 6 EStG capital-gains
   Günstigerprüfung election, AfA depreciation schedules, Gewerbesteuer,
   Kinderfreibetrag as first-class child entities (birthdates, custody
   splits, the non-custodial-parent half-transfer), and the Kirchensteuer
   Kappung rate table's per-state-not-per-denomination simplification.
