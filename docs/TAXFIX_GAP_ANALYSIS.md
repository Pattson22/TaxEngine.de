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
| ELSTER submission | ✅ | 🔶 real `cffi` binding to the actual ERiC library, verified end-to-end — `EricCheckXML()` passes cleanly for a document combining wages, capital/rental/self-employment/children income, donations, church tax paid, AND a real Vorsatz cover-sheet block (Steuernummer converted via the real `EricMakeElsterStnr()`); `xml_builder.py` maps every real Anlage this project's data model supports; Finanzamt routing (`User.finanzamt_bufa_nummer`) is collected and wired through automatically; the approved `HerstellerID` (**`04505`**, assigned to "TaxEngine.de" specifically) is wired through `app/config.py`; the `eric-submitter` worker (`app/eric_submitter/worker.py` + an `eric_submission_jobs` queue table) is deployed as its own Railway service with `NativeEricClient` loading the real Linux `ericapi.dll` (`EricInitialisiere()`/`EricCheckXML()` both verified inside the deployed container) — `POST /tax-filings/{id}/submit` queues jobs onto it (`202 Accepted` + `GET /{id}/submission-job` polling); `submit_filing()`/`StubEricClient` remain only as directly-tested helpers, no route calls them. Everything needed for a real submission is now live; **no submission has actually been sent to a Finanzamt yet** — that first attempt is being treated deliberately carefully (small filing, reviewed XML, someone watching the worker's logs) |
| Guided interview UX / mobile apps | ✅ | 🔶 a working Next.js web frontend exists (`frontend/`), deployed live at meinetaxengine.de, click-tested through register → onboarding → income (wage/capital/rental/self-employment) → deductions → calculate → view-results in a real browser — no mobile apps, no guided-interview-style Q&A (it's a form-based flow); a live PaymentElement-mounting bug was found and fixed in production (see `frontend/README.md`) but not yet re-verified live after the fix |
| Document OCR (auto-read Lohnsteuerbescheinigung) | ✅ | ❌ |
| Multi-language UI | ✅ (English for expats) | ❌ — English only, no i18n |
| Frontend forms for capital gains / rental / self-employment / Kinderfreibetrag | ✅ | ✅ — added `filings/[id]/{capital-income,rental-income,self-employment}` pages plus an inline Kinderfreibetrag form; previously these had working backend routes with no UI at all |
| Filing creation restricted to actually-supported tax years | — (Taxfix supports 2022–2025 retroactively) | ✅ — `GET /tax-filings/supported-years` + a frontend year picker; 2022/2023/2024 now all have reviewed constants (2025 still pending final BMF bracket coefficients) |

## What closed the gap

Everything marked ✅ above is real, tested code — `backend/tests/` (367
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
- **ERiC submission** (`app/eric/`) — real XML generation and a full
  validate→submit→persist orchestration; `POST /tax-filings/{id}/submit`
  queues onto the `eric-submitter` worker, which is the only place the
  real `NativeEricClient` (cffi binding to `ericapi.dll`/`.so`) is ever
  instantiated, deliberately kept out of the FastAPI web process.
  `StubEricClient` remains a real, directly-tested implementation used
  for local dev/tests, not a placeholder standing in for something that
  can't exist — the approved `HerstellerID` and a real ERiC developer
  certificate mean `NativeEricClient` no longer needs anything this
  project doesn't have.
- **Frontend** (`frontend/`) — Next.js + TypeScript, the golden path end to
  end (register → onboarding → dashboard → add income/deductions →
  calculate → pay via Stripe Elements → submit), plus profile editing and
  legal pages (Impressum/Datenschutz/AGB/ELSTER privacy notice). Verified
  via a clean production build, clean lint, and a real click-through in
  Chrome (register → dashboard → add wage income → add a commute
  deduction → calculate → view the refund breakdown), every displayed
  figure cross-checked against the backend's own numbers. That browser
  session caught a real bug: an unhandled Stripe API error reached
  FastAPI as a bare 500 with no CORS headers (Starlette's
  `ServerErrorMiddleware` bypasses `CORSMiddleware` for unhandled
  exceptions), so the browser reported an opaque "Failed to fetch" instead
  of a usable error — fixed by explicitly catching `stripe.StripeError` in
  `payment_service.py`, with a regression test. Now deployed live at
  meinetaxengine.de on Railway, which caught two further production-only
  bugs: `<PaymentElement>` silently never mounting (a mistyped character
  in the live Stripe publishable key) and homepage edits not appearing
  after deploy (Railway's edge cache doesn't purge on deploy the way
  Vercel's does) — see `frontend/README.md` for both.
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
2. ~~**Retroactive filing for prior tax years**~~ — CLOSED. `2022` and
   `2023` now have reviewed `TaxYearConstants` entries alongside `2024`
   (`tax_engine/constants.py`), matching Taxfix's 2022–2025 range except
   for 2025 itself (still pending final BMF bracket coefficients, see
   `TAX_YEAR_2024`'s own docstring). Each figure was cross-checked against
   lohn-info.de's published tariff tables plus multiple independent
   secondary sources, not guessed at -- `constants.py`'s docstring still
   treats this as "a compliance artifact, not just code," so re-verify
   against the official BMF publication before relying on either year for
   a real filing. Two real structural changes between years required
   care, not just different numbers: 2022's Altersvorsorgeaufwendungen
   were only 94% deductible (100% only from 2023), and 2022's Kindergeld
   was tiered by child count rather than a flat per-child amount (this
   project's `kindergeld_monthly_cents_per_child` constant turned out to
   be unused by any actual calculation, so the tiering doesn't affect
   correctness -- see that field's docstring).
3. **An actual completed submission to a real Finanzamt** — everything
   needed for one is now live: `NativeEricClient` is verified against the
   actual ERiC library (`EricCheckXML()` passes cleanly for wage/capital/
   rental/self-employment/children income, donations, church tax paid,
   and a real Vorsatz block, all together), each filer's Finanzamt
   BuFa-Nummer is collected, the `HerstellerID` is approved (`04505`),
   and `POST /tax-filings/{id}/submit` queues onto a real, deployed
   `eric-submitter` worker (its own Railway service, `ERIC_SDK_PATH` set,
   `EricInitialisiere()` verified against the real Linux library in that
   deployed container). What hasn't happened yet is the first actual
   `EricBearbeiteVorgang()` call reaching BZSt's servers for a real
   filing — deliberately being treated with care (small filing, reviewed
   XML, someone watching the worker's logs) rather than as a routine
   deploy. See `docs/ELSTER_ERIC_INTEGRATION.md` for exactly where this
   stands.
4. **Smaller, explicitly-documented approximations** worth revisiting
   before this handles real filings: the §32d Abs. 6 EStG capital-gains
   Günstigerprüfung election, AfA depreciation schedules, Gewerbesteuer,
   partial-year Kinderfreibetrag eligibility and the non-custodial-parent
   half-transfer (children ARE now first-class entities with real
   identity data for submission purposes, see `app/models/child.py` —
   what's still simplified is the Günstigerprüfung calculation itself,
   per `kinderfreibetrag.py`'s docstring), and the Kirchensteuer Kappung
   rate table's per-state-not-per-denomination simplification.
5. **No frontend for the `/children` CRUD API and no automated frontend
   tests.** The backend `/children` route, first-class
   `app/models/child.py` entities, and their Anlage Kind XML mapping all
   exist and work — a filer just can't reach them through the UI yet
   (the frontend's inline "Kinderfreibetrag" input is only the plain
   child *count* used by the Günstigerprüfung calculation, a separate
   concern from these per-child identity records). Frontend verification
   is real click-throughs (local and, for two bugs, live in production —
   see `frontend/README.md`) plus `build`/`lint`/`tsc`, not an automated
   test suite (no Jest/Playwright/Vitest set up).
