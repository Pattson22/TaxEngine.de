# TaxEngine.de

Consumer FinTech SaaS: German tax residents enter income/deductions for
free, get an estimated refund, and pay a flat €34.90 processing fee to
electronically submit their return to the Finanzamt via ELSTER. Operates
purely as tax-preparation software (no advisory service), staying inside
the Steuerberatungsgesetz software safe-harbor.

## Directory Map

```
TaxEngine.de/
├── db/
│   └── schema.sql                  HISTORICAL reference snapshot (superseded
│                                    by alembic/ below — see its header comment)
├── docs/
│   ├── ELSTER_ERIC_INTEGRATION.md  Government submission architecture + implementation status
│   └── TAXFIX_GAP_ANALYSIS.md      Competitive gap analysis + roadmap
├── frontend/                        Next.js + TypeScript + Tailwind (see frontend/README.md)
│   └── src/
│       ├── lib/                      Typed API client, auth context, money formatting
│       ├── components/               Shared UI (Button/Input/Card/Nav/...)
│       └── app/                      Landing, auth, dashboard, filings/[id]/* (income,
│                                     deductions, calculate, pay, submit)
└── backend/
    ├── requirements.txt
    ├── pytest.ini
    ├── alembic.ini
    ├── alembic/                     Migrations -- authoritative schema source
    │   ├── env.py                   Wired to app.config.settings + app.models.Base
    │   └── versions/                One migration per schema change, in order
    ├── .env.example                 Copy to .env for local development
    ├── tests/                       215 unit tests, 100% line coverage of tax_engine
    └── app/
        ├── main.py                  FastAPI app entrypoint (uvicorn app.main:app)
        ├── config.py                 Settings (env-driven, see .env.example)
        ├── database.py               SQLAlchemy engine/session, get_db dependency
        ├── security.py               Password hashing (argon2id) + JWT tokens
        ├── models/                   SQLAlchemy ORM models, 1:1 with the schema
        │   ├── enums.py               TaxClass / DeductionCategory / FilingStatus / ChildRelationshipType
        │   ├── user.py
        │   ├── wage_tax_certificate.py
        │   ├── capital_income_statement.py
        │   ├── rental_property_statement.py
        │   ├── self_employment_statement.py
        │   ├── child.py               First-class Kinderfreibetrag child entities (name/DOB/Steuer-ID)
        │   ├── deduction.py
        │   ├── eric_submission_job.py  Postgres-backed queue table for the eric-submitter worker
        │   └── tax_filing.py
        ├── schemas/                  Pydantic request/response models
        ├── services/
        │   ├── tax_calculation_service.py   Bridges DB rows <-> tax_engine
        │   └── payment_service.py           Stripe PaymentIntent + webhook verification
        ├── eric/                     ELSTER/ERiC submission scaffold (see docs/ELSTER_ERIC_INTEGRATION.md)
        │   ├── xml_builder.py         Domain model -> real E10 schema XML, verified against real ERiC
        │   ├── native_bindings.py     cffi bindings to the real ericapi.dll/.so
        │   ├── client.py              EricClient abstraction: StubEricClient + NativeEricClient (both real)
        │   └── submission_service.py  Validate -> submit -> persist orchestration (+ enqueue_submission)
        ├── eric_submitter/           SEPARATE process/package -- the only place NativeEricClient
        │   └── worker.py              may actually be instantiated (never inside the FastAPI app)
        ├── api/routes/               auth, users, wage-tax-certificates,
        │                             capital-income-statements, rental-property-statements,
        │                             self-employment-statements, children, deductions,
        │                             tax-filings, webhooks
        └── tax_engine/               Framework-free calculation core
            ├── constants.py          Year-versioned legal constants (single
            │                         source of truth for every Euro figure)
            ├── enums.py               FederalState / ChurchTaxType (mirror DB enums)
            ├── core.py               Werbungskosten & Sonderausgaben Pauschbeträge -> zvE
            │                         (now composes rental/self-employment via a signed
            │                         other_income_categories_cents parameter)
            ├── tax_brackets.py       §32a EStG tariff: Grundtarif + Splittingtarif
            ├── soli.py               Solidaritätszuschlag (regular + flat capital-gains variant)
            ├── church_tax.py         Kirchensteuer + Kappung (capping)
            ├── capital_gains.py      Abgeltungsteuer (§32d EStG) + Sparer-Pauschbetrag
            ├── rental_income.py      §21 EStG net rental income (signed -- losses offset other income)
            ├── self_employment_income.py   §15/§18 EStG simplified EÜR (Gewerbesteuer NOT modeled)
            ├── kinderfreibetrag.py   Kinderfreibetrag vs. Kindergeld Günstigerprüfung (§31 EStG)
            ├── deductions/
            │   ├── commute.py        Entfernungspauschale
            │   ├── home_office.py    Homeoffice-Pauschale
            │   ├── donations.py      Spenden (§10b EStG) + Spendenvortrag carry-forward
            │   └── childcare.py      Kinderbetreuungskosten (§10 Abs. 1 Nr. 5 EStG)
            └── tax_credits/
                └── handwerkerleistungen.py   §35a credit against final tax
```

## Setup

```bash
# 1. Backend dependencies
cd backend
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt

# 2. Configure
cp .env.example .env   # edit DATABASE_URL / JWT_SECRET_KEY / STRIPE_* to match your setup

# 3. Database -- create an empty Postgres database, then:
alembic upgrade head

# 4. Run the API
uvicorn app.main:app --reload
# -> interactive API docs at http://localhost:8000/docs

# 5. Frontend (separate terminal)
cd ../frontend
npm install
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL should point at the backend above
npm run dev
# -> http://localhost:3000 (see frontend/README.md for what's built/not built)
```

### Migrations

`db/schema.sql` is a frozen historical snapshot only (see its header) --
Alembic is authoritative going forward:

```bash
alembic upgrade head                              # apply all pending migrations
alembic revision --autogenerate -m "add X"         # generate a new migration from model changes
alembic downgrade -1                               # roll back one migration
```

`alembic/env.py` pulls the connection string from `app.config.settings`
(i.e. `DATABASE_URL`/`.env`), not from `alembic.ini`, so there is exactly
one place the DB URL is configured. `create_type=False` on every enum
column in `app/models/enums.py` is what stops `Base.metadata` (used
implicitly by `--autogenerate`) from trying to redundantly manage type
lifecycle outside of migrations — Postgres ENUM `CREATE TYPE`/`DROP TYPE`
is handled explicitly in the migration file itself.

### API surface (v0)

| Route | Purpose |
|---|---|
| `POST /auth/register`, `POST /auth/login` | Account creation, JWT session token |
| `GET /users/me`, `PATCH /users/me` | Profile (tax class, church tax, joint assessment, Steuer-ID, ...) |
| `POST/GET /wage-tax-certificates`, `GET/DELETE .../{id}` | Lohnsteuerbescheinigung data |
| `POST/GET /capital-income-statements`, `GET/DELETE .../{id}` | Kapitalerträge (Anlage KAP) |
| `POST/GET /rental-property-statements`, `GET/DELETE .../{id}` | Vermietung und Verpachtung (Anlage V) |
| `POST/GET /self-employment-statements`, `GET/DELETE .../{id}` | Simplified EÜR (Anlage S) |
| `POST/GET /children`, `GET/DELETE .../{id}` | First-class Kinderfreibetrag child records (Anlage Kind identity data) |
| `POST/GET /deductions`, `GET/DELETE .../{id}` | Werbungskosten/Sonderausgaben/credit line items |
| `POST/GET /tax-filings`, `GET/PATCH .../{id}` | Per-year filing record; PATCH sets Günstigerprüfung inputs |
| `POST /tax-filings/{id}/calculate` | Runs the full `tax_engine` pipeline, persists the refund breakdown |
| `POST /tax-filings/{id}/payment-intent` | Creates a Stripe PaymentIntent for the flat fee |
| `POST /webhooks/stripe` | Stripe webhook (signature-verified, no JWT) — marks the fee paid |
| `POST /tax-filings/{id}/submit` | Submits to ELSTER via the ERiC scaffold (`StubEricClient` by default — `NativeEricClient` is real and verified against the actual ERiC library but not yet wired into this route, see `docs/ELSTER_ERIC_INTEGRATION.md`) |

`POST /tax-filings/{id}/calculate` is the integration point worth reading
first: `app/services/tax_calculation_service.py` loads a user's wage
certificates, capital income, rental properties, self-employment
statements, and deductions for a tax year, dispatches each deduction
category to the matching `tax_engine` function, runs the Günstigerprüfung
and Kirchensteuer Kappung, and writes the resulting income tax / Soli /
church tax / capital gains tax / refund estimate back onto the
`tax_filings` row.

## Financial Data Integrity Principles

These are non-negotiable across the codebase:

- **Integer cents, never float, for any money value** — in the DB
  (`BIGINT ... _cents` columns) and in Python (`int`, or `Decimal` only
  where legally-mandated formulas require intermediate fractional
  precision).
- **Every legal constant lives in one place** (`tax_engine/constants.py`),
  versioned per tax year, never inlined — an annual bracket/rate update is
  a one-file, reviewable diff.
- **Computed deductions are recomputed from structured inputs**, not
  trusted as client-submitted totals — `deductions.details` (JSONB) stores
  `distance_km`/`days_worked`/etc., and the engine derives the amount. The
  `DeductionCreate` Pydantic schema validates that payload against the
  category's expected shape at WRITE time (a malformed request 422s
  immediately), not just when a filing is calculated.
- **Donations are aggregated across ALL of a user's DONATIONS rows before
  the 20% cap is applied**, never checked per-row — checking each row
  independently would let each one claim the full cap on its own (a real
  bug caught and fixed while building Spendenvortrag carry-forward).
- **Signed vs. floored income categories are kept distinct**: rental and
  self-employment results can legitimately be negative (a loss offsets
  other income, §2 Abs. 3 EStG) and are never floored before combining;
  Werbungskosten/Sonderausgaben Pauschbeträge, by contrast, are a strict
  "greater of actual-or-flat" floor. Mixing these up silently would
  produce a materially wrong taxable income.
- **Deductions vs. credits are architecturally separate**: `deductions/`
  reduces taxable income before the tariff applies; `tax_credits/`
  subtracts directly from the final assessed tax. `tax_engine/` has zero
  web/DB imports either way — `app/services/tax_calculation_service.py` is
  the one place DB rows and `tax_engine` inputs/outputs meet.
- **Alembic migrations are the authoritative schema source**, not
  `Base.metadata.create_all()` and not `db/schema.sql` (now a frozen
  reference) — every SQLAlchemy model declares its CHECK constraints and
  indexes via `__table_args__` specifically so `alembic revision
  --autogenerate` produces an accurate diff.
- **Payment and government-submission trust boundaries are explicit**:
  `/webhooks/stripe` authenticates via Stripe's own signature, never JWT;
  `NativeEricClient` fails loudly with `NotImplementedError` rather than
  silently pretending to submit to a real Finanzamt.
- **The §32a bracket calculation and the Kirchensteuer Kappung rate table
  are explicitly-labeled approximations** — see their module docstrings
  for exactly what's simplified and why. The only value transmitted to
  the Finanzamt must come from the certified ERiC library, not from this
  scaffold's approximation.

## Verification

- `backend/tests/` — 215 pytest unit tests, 100% line coverage of
  `tax_engine`, run with `python -m pytest`.
- Every feature above was additionally smoke-tested end-to-end against a
  real, throwaway Dockerized Postgres instance through the actual HTTP
  stack (register → build up income/deduction data → calculate → pay →
  submit), not just at the unit-test level. Several of those live runs
  caught real bugs before they shipped: multi-row donations being
  double-counted against the 20% cap, Postgres ENUM types not being
  dropped on migration downgrade, and a deduction-detail write-time
  validation gap — all fixed and re-verified.
- The initial Alembic migration was verified against `db/schema.sql` by
  applying each to a separate throwaway Postgres container and diffing
  `pg_dump --schema-only` output — confirmed byte-for-byte equivalent.

## Status

Backend is feature-complete for the roadmap in `docs/TAXFIX_GAP_ANALYSIS.md`:
employee income, capital gains, rental income, self-employment income,
Splittingtarif, Kinderfreibetrag/Kindergeld Günstigerprüfung, Soli,
Kirchensteuer + Kappung, Spendenvortrag carry-forward, the §35a
Handwerkerleistungen credit, real Stripe payment integration, and a real
`cffi` binding to the ERiC library — verified end-to-end against the
actual proprietary DLL, including a real `EricCheckXML()` pass for a
filing combining wage, capital, rental, self-employment, and children's
income, donations, church tax paid, and a real Vorsatz cover-sheet block
(Steuernummer converted via the real `EricMakeElsterStnr()`) all
together. `xml_builder.py`'s payload is now mapped to the real E10 schema
for every income type, deduction, and cover-sheet field this project's
data model supports (children are now first-class `app/models/child.py`
entities, not a plain count; church tax paid directly is a new
`DeductionCategory`; each filer's Finanzamt is now collected via
`User.finanzamt_bufa_nummer` and wired through automatically); see
`docs/ELSTER_ERIC_INTEGRATION.md` for exactly what's mapped and the one
remaining blocker (a registered `HerstellerID`) before a real submission
is possible.

Frontend (`frontend/`) covers the golden path — register, dashboard, add
wage income, add a deduction, calculate, view the refund breakdown, pay via
Stripe Elements, submit — but is not a guided interview-style flow, and has
no form for capital gains/rental/self-employment income or the
Kinderfreibetrag inputs (those backend routes exist and work, just
unreached from the UI yet). The register → calculate → view-results path
was click-tested in a real browser, not just built; see
`frontend/README.md` for exactly what that run covered and the real bug
(an unhandled Stripe error losing its CORS headers) it caught and fixed.

Not yet implemented: capital-gains Günstigerprüfung (§32d Abs. 6 EStG
election to use the progressive tariff instead of Abgeltungsteuer),
partial-year Kinderfreibetrag eligibility and the non-custodial-parent
half-transfer (the Günstigerprüfung *calculation* still treats children
as a plain count — see `kinderfreibetrag.py`'s docstring; children ARE
first-class `app/models/child.py` entities now, with a real `/children`
CRUD API and a real Anlage Kind mapping in `xml_builder.py`, but there's
no frontend form for them yet), AfA depreciation schedules for rental income,
Gewerbesteuer for self-employment, a registered ELSTER `HerstellerID`
(the one remaining blocker before `NativeEricClient` can be pointed at a
real submission — see `docs/ELSTER_ERIC_INTEGRATION.md`; per-filer
Finanzamt routing is now collected via `User.finanzamt_bufa_nummer`),
frontend forms for the remaining income types (including a `/children`
form and a church-tax-paid/donations deductions form), and automated
frontend tests.
