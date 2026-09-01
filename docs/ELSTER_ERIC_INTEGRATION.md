# ELSTER / ERiC Integration Engine

## Implementation status

**Update**: ELSTER Developer Area access was obtained and the license
agreement for ERiC 44 accepted (free, per the correction below). The real
SDK -- `ericapi.dll`/`libericapi.so`, the full API reference, and the real
Datenartenkatalog schemas/examples for every Elster data type including
`ESt` -- has been downloaded and `app/eric/native_bindings.py` now binds
to it for real via `cffi`, not `ctypes` guesswork: every declared
signature was copied verbatim from the SDK's own `include/ericapi.h`, and
`NativeEricClient` (`client.py`) was verified end-to-end against the real
Windows x86_64 library -- `EricInitialisiere()` succeeds, `EricCheckXML()`
correctly rejects garbage XML with a genuine German plausibility error,
and correctly accepts the SDK's own `est_e10_2024.xml` example. What's
still open, deliberately not attempted in that same pass:

- **`xml_builder.py`'s payload below `<Steuerfall>` is still
  illustrative**, not the real E10 schema -- the real schema uses opaque
  numeric field identifiers (e.g. `E0100001`) nested under semantic
  groups, nothing like the current placeholder shape. A real
  `EricCheckXML()` call against today's generated XML will legitimately
  fail; rewriting it against `Dokumentation/Datenarten/ElsterErklaerung/ESt/`
  in the SDK (schemas, `Jahresdokumentation` field-mapping spreadsheets,
  and example XML per year) is its own project, not a drive-by fix.
- **`NativeEricClient` is not wired into `submission_service.py`'s
  default path** -- per §2 below, ERiC must never load inside the main
  FastAPI web process, so it's only meant to be instantiated by a future
  separate `eric-submitter` worker (also not built yet). It's fully usable
  standalone today (e.g. from a script) for integration testing against
  the real library.
- The datenartVersion for an income tax return is `ESt_<Jahr>` (e.g.
  `"ESt_2024"`), confirmed against the SDK's `Datenartversionmatrix.ods`
  and threaded through `EricClient.validate_xml()`/`submit()` from
  `TaxFiling.tax_year`.

**Second update**: `xml_builder.py` now maps a real subset of the E10
schema instead of an illustrative placeholder -- the transfer envelope,
`ESt1A` personal data (primary filer + spouse when jointly assessed), and
`N` (Anlage N wage income). Every `E0######` field code was cross-checked
against the SDK's own `E10-2024.xsd` `<xs:documentation>` annotations, not
guessed. Capital income (`KAP`), rental income (`V`), self-employment
(ambiguously `G` or `S` in the real schema -- this project's data model
doesn't distinguish which), children (`Kind`), and donations/church tax
(`SA`) are deliberately NOT serialized yet -- see `xml_builder.py`'s module
docstring. There is also no "computed tax" element in the real schema at
all; the old illustrative `<Berechnung>` block (which submitted
`tax_engine`'s own totals) is gone -- ERiC/the Finanzamt compute the
assessment from declared income, never the other way around.

Generated output was round-tripped through the real `EricCheckXML()`
against `datenartVersion="ESt_2024"` (not just unit-tested), which caught
two real bugs neither code review nor the SDK's prose would have surfaced:
decimal fields need a COMMA separator (`"67554,76"`, matching German
number formatting), not a period, and `NutzdatenTicket` has a 32-character
max length, so a dashed UUID (36 chars) is rejected -- `.hex` fixes it.
After both fixes, a filing with wage income, a supplied `HerstellerID`,
and a supplied Finanzamt BuFa-Nummer passes `EricCheckXML()` cleanly
(`ERIC_OK`).

**Third update**: `xml_builder.py` now also maps capital income (`KAP`),
rental income (`V`), and self-employment (`S`) -- the previously
deliberately-omitted Anlagen. `S`, not `G`, was the correct pick:
`tax_engine/self_employment_income.py`'s own docstring already says its
math is "correct for freelancers/liberal professions", which is exactly
what `S` (§18 EStG) represents in the real schema, vs. `G` (§15 EStG,
Gewerbebetrieb, which would also need unmodeled Gewerbesteuer). Anlage S
only carries the aggregated net profit -- a full itemized
Einnahmen-Überschuss-Rechnung is a separate Datenart (`EUER`) this project
doesn't build. `V`'s per-property expenses are filed under the schema's
generic "Sonstiges" bucket, not a specific category like AfA, since this
project doesn't compute a depreciation schedule and claiming one would
misrepresent the expense type. Children (`Kind`) stay unmapped -- blocked
on the same "children as a plain count, not first-class entities" gap
`kinderfreibetrag.py` already documents, not a missing-schema-research
problem like the others were.

Real-library round-tripping again caught a bug unit tests alone couldn't:
`KiSt_Pfl`'s church-tax-liability flag (`E1900601`) is typed
`Ja1BaseCType` (valid value `"1"`), not the `JaXBaseCType` (`"X"`) used
everywhere else in this file -- `EricCheckXML()` rejected `"X"` with a
real `'value 'X' not in enumeration'` error. After the fix, a single
document combining wage income, capital income, two rental properties,
self-employment, and (separately) joint assessment with a spouse and two
rental properties all pass `EricCheckXML()` cleanly (`ERIC_OK`).

**Fourth update**: the "children as a plain count" data-model gap flagged
above is now closed for submission purposes. `app/models/child.py` adds a
first-class `children` table (name, DOB, Steuer-ID, and the real 3-value
Kindschaftsverhältnis enum verified against
`Enum_Kind_K_Verh_K_Verh_A_E0500807_CType`), with a `/children` CRUD API
mirroring every other income-source route. `xml_builder.py` now maps
`Kind` (identity in `Ang_Kind/Allg`, relationship in `K_Verh`, both
spouses' `K_Verh_A`/`K_Verh_B` when filing jointly) under the same
full-calendar-year simplification the rest of this module already uses.
Deliberately NOT changed: `kinderfreibetrag.py`'s Günstigerprüfung
calculation still runs on `TaxFiling.number_of_children` (a plain count) —
the two are independent by design, since redesigning the calculation's
own input path was a bigger, riskier change than this data-model gap
required; see `Child`'s own docstring. A document combining joint
assessment, wage income, and two children (one biological with a
Steuer-ID, one foster with a different surname) passes `EricCheckXML()`
cleanly (`ERIC_OK`). Only donations/church-tax-paid (`SA`) and the
KOMPRIMIERT cover-sheet block (`Vorsatz`) remain unmapped now.

**Fifth update**: `xml_builder.py` now also maps donations
(`SA/Zuw/Sp_MB/Foerd_st_beg_Zw_Inl`), aggregated across every
DONATIONS-category `deductions` row with the exact same rule
`tax_calculation_service._aggregate_donations_this_year` already uses (the
20% cap applies to the combined total, not per-row -- the same real bug
that function's own docstring documents). Always filed as domestic
(`Foerd_st_beg_Zw_Inl`), never `Foerd_st_beg_Zw_EU_EWR` -- the data model
doesn't collect a recipient organization or country, so foreign
recipients can never be distinguished and are never assumed. A document
combining every mapped Anlage at once (wages, capital income, a rental
property, self-employment, a child, and donations) passes `EricCheckXML()`
cleanly (`ERIC_OK`).

**Sixth update**: the two remaining Anlagen are now closed, plus the
Finanzamt-routing gap:

- **`User.finanzamt_bufa_nummer`** is a new field (migration
  `f4b1c9a02e7d`), collected the same way `steuernummer` already is.
  `submission_service.py` now passes it through automatically -- the
  `NutzdatenHeader` Finanzamt-routing gap is closed for any user who's
  entered theirs.
- **`SA/KiSt` (church tax PAID)** turned out to need real data collection,
  not just plumbing: its field documentation explicitly EXCLUDES church
  tax already withheld as an Abgeltungsteuer surcharge (a legally
  different figure from what `N`/`KAP` declare as withheld), and this
  project had nowhere to collect "church tax paid directly" at all. A new
  `DeductionCategory.CHURCH_TAX_PAID` (migration `b6e7f3a19c04`) closes
  that gap for real -- wired into `apply_sonderausgaben_pauschbetrag`
  (fully deductible, no 20% cap) exactly as that function's own docstring
  already described "church tax paid" as an expected Sonderausgabe, and
  mapped to `KiSt/Gezahlt/Sum/E0107601` in `xml_builder.py`.
- **`Vorsatz` (the KOMPRIMIERT cover-sheet block)** needed one thing this
  project genuinely couldn't compute itself: the filer's Steuernummer in
  ERiC's unified 13-digit format. `EricMakeElsterStnr()` is now bound in
  `native_bindings.py` and exposed as
  `NativeEricClient.format_steuernummer_for_elster()` -- verified against
  the real library: converting `"181/815/08155"` with
  `bundesfinanzamtsnr="9181"` really returns `"9181081508155"`, matching
  the SDK's own example. `xml_builder.py` accepts the pre-computed result
  (staying ERiC/DLL-free itself, per its own design) and omits the whole
  block without it. A document combining wages and a real Vorsatz block
  (real StNr, both filer IDs, sender address mirroring
  `cover_sheet.py`'s existing logic) passes `EricCheckXML()` cleanly
  (`ERIC_OK`).

Every real Anlage this project's data model can support is now mapped in
`xml_builder.py`.

**Seventh update**: the `eric-submitter` worker §2 describes as a design
now exists as real, working code -- `app/eric_submitter/worker.py`, plus
an `eric_submission_jobs` Postgres-backed queue table (migration
`a1d8e4f36b52`) and `submission_service.enqueue_submission()` to insert a
job. The worker's claim/process/persist loop is real: `SELECT ... FOR
UPDATE SKIP LOCKED` for concurrent-safe claiming, the same FEE_PAID/
Steuer-ID pre-flight checks `submit_filing()` runs (re-checked at claim
time, since a job can sit queued for a while), the idempotency check this
doc's §5 already specified (never re-submit a filing that already has a
`elster_transfer_ticket`), a real `format_steuernummer_for_elster()` call
for `Vorsatz` (non-fatal if it fails -- the block is just omitted), and
`EricBeende()` guaranteed via `finally` on worker shutdown.
`submission_service.build_submission_xml()` was extracted so
`submit_filing()`'s synchronous path and the worker's async one can never
silently diverge on what XML gets built for a given filing.

**Deliberately NOT done** (at the time of the Seventh update): the worker
is explicitly a reference implementation, not a production deployment --
no supervisor/restart policy, no concurrency beyond one job at a time, no
graceful-shutdown signal handling (see the module's own docstring). That
part is still true; the "not wired into any route yet" part below is not
-- see the Ninth update.

**Eighth update**: the Manufacturer ID (`HerstellerID`) application has
been submitted via the real ELSTER Developer Area form
(`elsterweb/entwickler/antrag-hersteller-id`) -- product "TaxEngine.de",
interface ERiC, no prior manufacturer ID -- confirmed with a real
ÜbermittlungsId (`b064de96-e903-439b-a82d-b7d6f92fddbb`) on 2026-08-31.
Now pending Bayerisches Landesamt für Steuern review/approval; once the
real 5-digit ID arrives, it replaces `settings.eric_hersteller_id`'s
placeholder (`app/config.py`) and the `HerstellerID` this project sends
in every `TransferHeader` stops being a placeholder value ERiC would
reject.

**Ninth update**: `POST /tax-filings/{id}/submit` now calls
`enqueue_submission()`, not `submit_filing()` -- the async, worker-backed
path from the Seventh update is wired in as the only submission path the
API exposes. The route re-checks FEE_PAID/Steuer-ID itself (so a bad
request fails immediately with a 409, rather than sitting in the queue
until the worker's own re-check fails it) then returns the queued
`EricSubmissionJob` (`202 Accepted`, `EricSubmissionJobRead`). A new
`GET /{id}/submission-job` returns the most recent job for a filing; the
frontend (`filings/[id]/page.tsx`) polls it every 3s after submitting
until it reaches `SUCCEEDED`/`FAILED`, then refetches the filing to pick
up the worker's status/`elster_transfer_ticket` update.
`submit_filing()`/`StubEricClient` still exist and are still tested
directly (`tests/test_eric.py`) -- no route calls either any more, but
they remain a valid synchronous, dependency-injectable entry point (e.g.
for a future ops/retry script).

One consequence worth being explicit about: a submitted job now sits
PENDING until an `eric-submitter` worker process is actually running
(`python -m app.eric_submitter.worker`) to claim it -- unlike the old
synchronous path, nothing about the web request itself fails if no
worker is listening. In any environment where a filer might click
"Submit to the Finanzamt", the worker process must be running alongside
the API for their submission to ever leave PENDING.

What's left before a real submission is possible is no longer schema
research, worker architecture, or an unstarted registration: it's waiting
on that approval, then wiring `NativeEricClient` into a hardened version
of `app/eric_submitter/worker.py` and giving each filer a way to enter
their Finanzamt BuFa-Nummer (the field already exists on `User`, just no
frontend form yet).

**Tenth update**: amended-return support (Berichtigte Steuererklärung).
A real, verified finding first: the E10 (ESt) Datenart has NO "corrected
declaration" checkbox at all -- confirmed by grepping the actual
`E10-2024.xsd` for every plausible field name and finding nothing, then
finding the real thing (`E3000601`, a `Ja1BaseCType` field inside a
`Ber_Erkl_...CType` complex type, documented literally as "Berichtigte
Steuererklärung") only in the USt (VAT) schema, `E50-2024.xsd`. So for
income tax specifically, marking a submission as a correction is purely
this project's own bookkeeping -- nothing about it is transmitted in the
XML, which simplified this feature a lot.

The mechanics: `tax_calculation_service.calculate_tax_filing()` now
clears `elster_transfer_ticket`/`elster_submitted_at`/`elster_accepted_at`/
`elster_rejection_reason` back to `NULL` whenever it recalculates a
filing that was already `SUBMITTED`/`ACCEPTED`/`REJECTED` -- the filer
editing income/deductions and clicking Recalculate IS what starts an
amendment, since this project's income/deduction rows are keyed to
`(user_id, tax_year)`, not to a specific `TaxFiling` row (an early design
constraint discovered while scoping this feature, which is also why
amendments reuse the SAME `TaxFiling` row rather than creating a linked
new one). Clearing those fields flips the filing back through
`CALCULATED` -> (pay again) -> `FEE_PAID` using the EXISTING status
machine unchanged -- no new `FilingStatus` value was needed.
`EricSubmissionJob` gained one column, `is_amendment`, set once at
enqueue time by checking whether a SUCCEEDED job already exists for that
filing_id (not by checking `elster_transfer_ticket`, which is already
NULL by the time an amendment is enqueued). The worker's idempotency
check (`_process_job`) now reads `filing.elster_transfer_ticket and not
job.is_amendment` instead of just the ticket, so a genuine amendment
isn't mistaken for an accidental duplicate of the original. The full
history of every attempt (original and every amendment) is permanently
queryable via the new `GET /tax-filings/{id}/submission-jobs` (plural),
since the `TaxFiling` row itself only ever reflects the CURRENT attempt.

Verified against the real Postgres DB (not just unit tests): staged a
filing as ACCEPTED with a real-shaped ticket and a SUCCEEDED job,
recalculated it (confirmed the stale fields cleared and status returned
to CALCULATED), re-enqueued (confirmed `is_amendment=True` via the prior
job history), and confirmed the full two-job history came back correctly
ordered and flagged via the live API. The frontend
(`filings/[id]/page.tsx`) shows a "Submission history" list once more
than one job exists, and adjusts the ready-to-submit copy to say
"amended return" when a prior submission succeeded.

Deliberately NOT done: Einspruch (formal objection to an assessment) is
a different legal mechanism with its own XML/deadline logic and depends
on Bescheiddatenabruf existing first (there is no assessment to object
to yet) -- out of scope here, same blocker as Bescheiddatenabruf itself.
Whether an amendment should cost a second €34,90 fee was left as the
natural default of the unchanged status machine (recalculating requires
re-paying to reach FEE_PAID again) rather than specially cased either
way -- revisit if that's not the intended pricing.

**Eleventh update**: the real HerstellerID has arrived --
**`04505`**, assigned to the product name "TaxEngine.de" specifically
(confirmed via `statistikauswertung@elster.de` on 2026-09-01; the
ÜbermittlungsId from the Eighth update was `b064de96-e903-439b-a82d-b7d6f92fddbb`).
Set in the local `.env` as `ERIC_HERSTELLER_ID=04505` (never committed --
see `.env.example` for the template) and read by
`app/config.py`'s `eric_hersteller_id` setting, which
`xml_builder.build_est_xml()` already threads into every `TransferHeader`
it builds. Per the approval email, a HerstellerID is bound to this exact
product name, not to the company -- a differently-named product would
need its own separate application.

This closes the LAST missing piece from the Ninth update's async
submission wiring, EXCEPT one: `app/eric_submitter/worker.py` still
needs a real `ERIC_SDK_PATH` pointing at the extracted SDK before it can
actually start (`run_forever()` raises otherwise) -- the SDK itself has
been on disk since the Third/Fourth updates, just never wired into a
running worker process. Once that's set and the worker is started
alongside the API, a filer clicking "Submit to the Finanzamt" reaches a
real `EricBearbeiteVorgang()` call for the first time this project has
ever made outside of manual SDK-example testing -- worth treating that
first real attempt with real care (a small, low-stakes filing, reviewed
XML, someone watching the worker's logs), not as a routine deploy.

**Twelfth update**: `ERIC_SDK_PATH` is now set and verified --
`NativeEricClient` loads the real Windows x86_64 `ericapi.dll` and
`EricInitialisiere()`/`EricBeende()` both succeed cleanly. Before starting
the worker for real, a genuine risk surfaced: `app/eric_submitter/worker.py`
polls whatever `DATABASE_URL` it's given and submits anything PENDING
there for real -- and that had been the SAME Postgres database used all
along for manual UI/browser testing (`taxengine`), which already had a
leftover `PENDING` job from testing the amendment flow (deleted before
this could bite). Running the real worker against that database even
once would eventually transmit fabricated test data to the actual
Finanzamt under this project's real HerstellerID.

Fixed by giving the worker its own database, never shared with anything
else: a new `taxengine_live` database (same Postgres instance, `CREATE
DATABASE taxengine_live`), migrated to the same head revision as
`taxengine` -- via the same enum-double-create workaround the dev
database needed earlier (this venv's newer SQLAlchemy version tries to
create an inline enum twice when it's used as a column type in the same
migration that also calls `.create()` on it explicitly; pre-creating the
type via raw SQL and stamping past it sidesteps the bug without touching
the migration files themselves). Verified schema-identical to `taxengine`
(same 10 tables, same enum values, `eric_submission_jobs.is_amendment`
present with the right default) before use.

The worker now gets its OWN env file, `backend/.env.worker.local`
(gitignored, matches the existing `.env.*.local` pattern; template at
`.env.worker.local.example`) -- `DATABASE_URL=.../taxengine_live` plus
the same `ERIC_SDK_PATH`/`ERIC_HERSTELLER_ID`, sourced as real
environment variables (not just written to `backend/.env`, which the dev
API/tests keep using unchanged) before running `python -m
app.eric_submitter.worker`. One portability bug caught while building
this: `source`-ing a file from bash silently strips unquoted backslashes,
corrupting a Windows-style `ERIC_SDK_PATH` -- the file uses forward
slashes instead, which Windows/cffi's `dlopen()` both accept fine.

Verified end-to-end: started the real worker against the empty, isolated
`taxengine_live` -- clean startup log, no errors, correctly found nothing
to claim -- then stopped it again, since nothing can land a real job in
that database's queue until an actual FastAPI deployment is pointed at
it (a separate, larger step this update deliberately does NOT take:
provisioning a real customer-facing deployment -- hosting, a production
Stripe key, a real domain -- is its own project, not a side effect of
unblocking the worker).

**Correction to the Twelfth update above**: the enum-double-create bug is
NOT a throwaway-venv/newer-SQLAlchemy artifact as claimed there. Building
`backend/Dockerfile` and running `alembic upgrade head` against a
genuinely clean `docker compose` Postgres, with the exact pinned
`sqlalchemy==2.0.35` from `requirements.txt`, reproduced the identical
`type "child_relationship_type_enum" already exists` failure. The real
cause: three migrations (`d2d49df071e7_add_children.py`,
`a1d8e4f36b52_add_eric_submission_jobs.py`, and
`7a3f9c2e5b41_add_cover_sheet_tracking.py`) explicitly call `.create()`
on a `postgresql.ENUM(...)` object and then ALSO use that same object as
a column type in `op.create_table`/`op.add_column` in the same
migration — `op.create_table` compiles a real `CreateTable` DDL
construct that auto-creates any enum column type unless
`create_type=False` is set, so it tried to create the type a second
time. Fixed by adding `create_type=False` to all three enum
definitions (harmless where `op.add_column` turned out not to trigger
the double-create either way — kept for consistency rather than relying
on that distinction). This means the earlier manual
pre-create-then-stamp workaround used for both `taxengine` and
`taxengine_live` was masking a real bug, not sidestepping a fake one —
worth knowing if either database is ever rebuilt from scratch instead of
migrated forward.

**Thirteenth update**: added real deployment infrastructure --
`backend/Dockerfile` (the same image serves both the FastAPI web process
and, with a different `command:`, the `eric-submitter` worker — neither
bakes in the ERiC SDK itself, which the worker still gets via a
bind-mounted volume + `ERIC_SDK_PATH` at container runtime, exactly like
local development), `frontend/Dockerfile` (Next.js standalone build),
`docker-compose.yml`, and `.github/workflows/ci.yml` (backend `pytest`
+ frontend `lint`/`tsc`/`build` on every push/PR). The worker is
DELIBERATELY not part of the default `docker compose up` service set —
it's behind a `worker` Compose profile, same isolation principle as the
Twelfth update's `taxengine_live` split, so routine local use of this
compose file can never accidentally start a real ERiC-capable process.

All of this was verified for real, not just written and assumed
correct: both images were built and run locally (backend image imports
`app.main` cleanly; frontend image serves a real 200), and the full
`postgres` → `migrate` → `backend` dependency chain was run end-to-end
against a freshly created, empty Postgres via `docker compose up`,
which is what caught the enum bug above in the first place. Cleaned up
afterward (`docker compose down -v`, ad-hoc test images removed) — this
compose stack is for local smoke-testing and CI-adjacent verification,
not a production deployment target by itself; provisioning a real host,
domain, TLS, and live Stripe/S3 credentials remains open (see the
Twelfth update's closing paragraph).

**Correction to an earlier version of this doc**: obtaining the ERiC
library itself is a *free developer registration* at
elster.de/eportal/infoseite/entwickler, reviewed by the Bayerisches
Landesamt für Steuern (typically approved within days, no fee) — not a
gated "signed agreement" in the sense of a hard business blocker. What
*is* a hard constraint, and doesn't go away once that registration is
done, is §6 below: authentication is per-taxpayer, not per-vendor.

## What ERiC actually is (and why that shapes the architecture)

ERiC (**E**lster **Ri**ch **C**lient) is a proprietary, closed-source
**C library** (shared object / DLL, not a REST API) distributed by the
Bundeszentralamt für Steuern (BZSt) under a signed software-developer
agreement. It performs three jobs no third party is allowed to
reimplement: plausibility-checking a tax filing against the current year's
official schema, encrypting/signing the transmission, and talking to the
Elster servers over the government's own protocol. There is no public HTTP
API — **every** German tax-filing SaaS (WISO Steuer, Taxfix, smartsteuer,
etc.) embeds this same C library somewhere in its stack. That constraint
drives every decision below.

## 1. Lifecycle Overview

```
[Internal domain model]           Our own Pydantic/SQLAlchemy objects
        │  (tax_filings, deductions, wage_tax_certificates rows)
        ▼
[XML bundling]                    Serialize into the official Elster
        │                         "Datenart" XML schema for the ESt-Formular
        │                         (schema published/updated annually by BZSt)
        ▼
[ERiC pre-flight validation]      EricCheckXML / EricPruefeXML — plausibility
        │                         checks (Vollständigkeitsprüfung) against
        │                         the current schema, BEFORE spending a
        │                         transmission attempt
        ▼
[ERiC transmission]               EricBearbeiteVorgang — encrypts, signs
        │                         with the org certificate, and transmits
        │                         over Elster's TLS channel to BZSt servers
        ▼
[Transferticket]                  BZSt returns a unique Transferticket +
        │                         acceptance/rejection status synchronously
        │                         (typically seconds, occasionally longer)
        ▼
[Persist + reconcile]             Write elster_transfer_ticket,
                                   elster_submitted_at/accepted_at, and
                                   status transition back into tax_filings
```

## 2. Bridging Python ↔ the C ERiC Library

**Now implemented** (see the "Seventh update" above): `app/eric_submitter/
worker.py` is a real, working reference implementation of the shape
described below -- a Postgres-backed job table
(`eric_submission_jobs`) rather than gRPC/Redis/SQS (simplest option that
needs no new infra, explicitly named below as acceptable), a real
claim/process/persist loop, and `NativeEricClient` (cffi bindings to
`ericapi.dll`/`libericapi.so`) instantiated ONLY inside that worker
process, never the FastAPI app. It's a reference implementation to
harden before production use (no supervisor/restart policy yet), not a
placeholder -- the parts that matter for correctness (the SKIP LOCKED
claim query, the idempotency check, the ERiC lifecycle) are real.

**Never load `libericapi.so`/`eric.dll` inside the main FastAPI web
process.** Reasons:

- **Crash isolation** — a segfault or unhandled exception inside a C
  library takes down the entire process, including unrelated in-flight
  requests. An ERiC crash must only ever kill one submission worker.
- **Licensing/versioning** — BZSt ships a new ERiC version yearly (and
  sometimes mid-year for bugfixes); pinning it to one isolated service lets
  you upgrade ERiC without redeploying the whole API.
- **Memory safety** — `ctypes`/`cffi` bindings to a large stateful C library
  are exactly the kind of surface you want behind a process boundary with
  its own restart/health-check policy, not inline with request handling.

**Recommended shape:**

```
┌─────────────────┐   gRPC / internal HTTP   ┌───────────────────────┐
│  FastAPI web app │ ───────────────────────► │  eric-submitter worker │
│  (public-facing) │ ◄─────────────────────── │  (own container)       │
└─────────────────┘      job status/result    │  - cffi bindings to    │
                                               │    libericapi          │
                                               │  - holds the org cert  │
                                               └───────────────────────┘
```

- The web app enqueues a submission job (`tax_filings.id`) onto an internal
  queue (e.g. a Postgres-backed job table or Redis/SQS) rather than calling
  ERiC synchronously in the request path — submissions can take seconds and
  must survive a web-process restart.
- The `eric-submitter` worker is the **only** process that links against
  ERiC, via `cffi` (preferred over raw `ctypes` for a large C API — cffi's
  ABI/API modes give cleaner struct marshaling for ERiC's parameter structs).
- The worker polls/consumes jobs, builds the XML (see §3), calls
  `EricCheckXML` then `EricBearbeiteVorgang`, and writes the result back via
  the same internal channel — never direct DB access shared with the web
  tier's connection pool, to keep the failure domains separate.

## 3. Validation & XML Bundling

Two validation passes, not one:

1. **Pre-validation in Python**, before handing anything to ERiC — check
   required fields are present, monetary values are internally consistent
   (e.g. `taxable_income_cents` actually equals the recomputed value from
   `tax_engine.core`), and the XML we're about to generate is well-formed
   against a local copy of the schema (`lxml` + XSD). This catches ~90% of
   errors cheaply and lets us return a specific, field-level error to the
   user in our own UI language instead of a raw ERiC error code.
2. **ERiC's own `EricCheckXML`/plausibility layer** — the authoritative
   check. ERiC error codes must be mapped through a translation table back
   onto our internal deduction/field identifiers so the user sees "your
   commute distance looks inconsistent with your address" instead of a
   BZSt error code.

XML bundling itself is a pure function: `tax_filing_row -> XML string`,
unit-testable without touching ERiC at all — keep it in the shared library
so both the pre-validation pass and the worker use the exact same
serialization.

## 4. Security

- **Organzertifikat / Softwarezertifikat**: ERiC requires a registered
  certificate (`.pfx`) tied to TaxEngine.de's BZSt developer registration.
  Store it in a secrets manager (e.g. AWS Secrets Manager / HashiCorp
  Vault), never on disk in the container image or in source control; the
  worker fetches it into memory at startup only.
- **Mutual TLS** to the Elster servers is handled internally by ERiC using
  that certificate — our job is solely to keep the certificate's private
  key encrypted at rest and rotate it before expiry (BZSt certs have fixed
  validity windows).
- **PII/tax-data encryption at rest**: the wage_tax_certificates and
  deductions tables contain sensitive financial data — enable Postgres
  column- or disk-level encryption (e.g. pgcrypto for specific columns, or
  full-disk encryption at the managed-DB layer) and restrict the
  eric-submitter worker's DB credentials to only the tables/rows it needs.
- **Audit logging**: every call into ERiC (attempt, XML payload hash,
  result code, Transferticket) is written to an append-only audit log
  table, separate from `tax_filings`, satisfying both GoBD (Grundsätze zur
  ordnungsmäßigen Führung und Aufbewahrung von Büchern) recordkeeping
  expectations and internal fraud/dispute investigation needs.
- **Least privilege**: only the eric-submitter worker holds ERiC
  credentials; the web tier and any analytics/BI access never touch the
  certificate or raw XML payloads.

## 5. Operational Notes

- **Sandbox vs. production endpoints**: ERiC exposes a test system
  (`EricTestmode`) that validates and round-trips submissions without
  actually filing with the Finanzamt — the full CI/staging pipeline runs
  against this before any deploy touches the production BZSt endpoint.
- **Idempotency**: a submission job must be safe to retry (e.g. worker
  crash mid-call). Before re-submitting, check whether a
  `elster_transfer_ticket` already exists for this `tax_filings.id` —
  ERiC/BZSt do not want duplicate filings for the same taxpayer/year, and
  `tax_filings` already enforces `UNIQUE (user_id, tax_year)` at the DB
  layer as a backstop.
- **Reconciliation**: on success, transition `tax_filings.status` from
  `SUBMITTED` to `ACCEPTED` (or `REJECTED` with
  `elster_rejection_reason` populated) — this state machine is the
  single source of truth the frontend polls/subscribes to, not raw ERiC
  return codes.

## 6. Authentication is per-taxpayer, not per-vendor — the KOMPRIMIERT path

ELSTER submissions are authenticated with the individual taxpayer's own
personal ELSTER certificate (registered by them directly via
ElsterOnline, using name, date of birth, email, Finanzamt, and tax
number — data our onboarding flow already collects) or a security
stick/signature card. There is no vendor-wide certificate that lets
TaxEngine.de authenticate submissions on a user's behalf; a
Softwarezertifikat only gates access to BZSt's own portals (like the
BOP), not third-party ESt filings made through ERiC.

Until users can link their own certificate (not implemented), every
filing this project submits uses `SubmissionMode.KOMPRIMIERT`: ERiC still
transmits the XML (`Vorgang = send-NoSig` in `xml_builder.py`), but
without a personal signature it isn't legally binding on its own. The
taxpayer must additionally print, sign, and mail a paper cover sheet
referencing the same submission — `app/eric/cover_sheet.py` generates a
functional stand-in for this (NOT the official barcode-bearing BZSt
printout, which only a real ERiC call can produce), served from
`GET /tax-filings/{id}/cover-sheet` once a filing is
SUBMITTED/ACCEPTED/REJECTED. `POST /tax-filings/{id}/mark-mailed` records
the taxpayer's own attestation that they mailed it — self-reported, not
verified against the Finanzamt, since we have no channel to confirm paper
receipt.

`SubmissionMode.AUTHENTIFIZIERT` is reserved on the model for the fully
paperless path once per-user certificate linking exists, so adding it
later doesn't need a second migration.

## 7. AUTHENTIFIZIERT mode — design (not yet implemented)

This section scopes what building the paperless path actually requires.
Nothing below is built yet — no migration, no upload endpoint, no wiring
into `submission_service.py`. The real ERiC struct/function signatures
here are copied verbatim from the local SDK
(`eric-sdk/.../include/eric_types.h` and `ericapi.h`, ERiC 44.2.4.0), not
guessed — this replaces the "opaque struct" placeholder that
`native_bindings.py` deliberately used until now.

### 7.1 What ERiC actually needs

`eric_verschluesselungs_parameter_t` (`eric_types.h:298-318`), the struct
`client.py` currently passes as `ffi.NULL`:

```c
typedef struct {
    uint32_t version;                    // must be 3 (checked by ERiC)
    EricZertifikatHandle zertifikatHandle; // from EricGetHandleToCertificate()
    const byteChar *pin;                 // the taxpayer's certificate PIN
} eric_verschluesselungs_parameter_t;
```

`zertifikatHandle` is not the raw certificate bytes — it's an opaque
handle obtained first via a separate call:

```c
int EricGetHandleToCertificate(
    EricZertifikatHandle* hToken,
    uint32_t* iInfoPinSupport,
    const byteChar* pathToKeystore);
```

For the case that matters here (a taxpayer's own ElsterOnline-issued
certificate — ERiC calls this a "Software-Portalzertifikat"),
`pathToKeystore` is a filesystem path to a `.pfx` file. Notably, no PIN is
passed to `EricGetHandleToCertificate` itself — the PIN is only supplied
later, in `eric_verschluesselungs_parameter_t.pin`, at the actual
`EricBearbeiteVorgang()` call. The handle must be released afterward via
`EricCloseHandleToCertificate(hToken)`.

So the real sequence for one AUTHENTIFIZIERT submission is: write the
taxpayer's `.pfx` to a temp path the worker process can read → open a
handle to it → build the crypto-parameter struct with that handle plus
the PIN entered for this submission → call `EricBearbeiteVorgang` with
that struct instead of `NULL` → close the handle → discard the temp file
and the PIN from memory.

### 7.2 What this means for storage and handling

This is qualitatively different from anything credential-related handled
so far this project (Stripe keys, JWT secrets) — a `.pfx` + PIN pair is
the taxpayer's actual legal signature on a tax return, not an API
credential we control. Consequences:

- **The `.pfx` file needs encrypted-at-rest storage**, scoped per user,
  separate from the general document-upload S3 bucket (`config.py`'s
  `s3_*` settings) given the sensitivity difference — likely its own
  bucket/prefix with stricter access, or client-side encryption before
  upload.
- **The PIN must never be stored.** ERiC's own API shape supports this
  naturally — the PIN is only needed transiently, once, at submission
  time. The right UX is almost certainly "enter your ELSTER PIN" as a
  step in the submit flow (not saved on the profile), same trust
  boundary as a card CVC.
- **The cert file and PIN can only ever touch the `eric-submitter`
  worker process**, never the FastAPI web process — same rule that
  already keeps `NativeEricClient`/`ericapi.dll` out of the web process
  (§2), now doubly true because this data is more sensitive than
  anything currently in that worker.
- **`EricGetHandleToCertificate` can return PIN-related failure codes**
  (locked PIN, wrong PIN, etc. — see `EricGetPinStatus()` in the SDK) that
  need surfacing back to the user as an actionable error, not a generic
  submission failure.

### 7.3 Code paths that would change

- `native_bindings.py`: declare `EricZertifikatHandle`,
  `eric_verschluesselungs_parameter_t` (non-opaque),
  `EricGetHandleToCertificate`, `EricCloseHandleToCertificate` in `_CDEF`.
- `client.py`: `submit()` gains a way to pass a real crypto parameter
  (e.g. an optional `certificate_path`/`pin` pair, or a small
  context-manager wrapping the handle open/close) instead of always
  `ffi.NULL`.
- `xml_builder.py:336`: `Vorgang` becomes conditional on
  `filing.submission_mode` instead of hardcoded `"send-NoSig"` — the
  correct value for the authenticated path needs confirming against the
  SDK's `ericdemo` sample / Entwicklerhandbuch (not guessed here; this is
  the one remaining unconfirmed detail).
- `submission_service.py`: routes AUTHENTIFIZIERT filings through the new
  crypto-parameter path; still never loads `ericapi.dll` outside the
  worker.
- New model/migration: where the encrypted `.pfx` reference lives (e.g.
  an `elster_certificate` table or columns on `User`), plus an upload
  endpoint and a PIN-entry step in the submit flow — none of this exists
  today.
- `cover_sheet.py` / `mark-mailed`: become conditional on
  `submission_mode == KOMPRIMIERT`, since an AUTHENTIFIZIERT filing has no
  paper cover sheet at all.

### 7.4 Open questions before implementation starts

- Exact `Vorgang` value ERiC expects for an authenticated send (needs the
  Entwicklerhandbuch or `ericdemo-cpp` sample, not yet checked).
- Where/how the `.pfx` gets from the user's browser to the worker's
  filesystem without ever passing through the web process in plaintext.
- Retention: does the encrypted cert get deleted after each submission
  (re-upload every time) or kept for repeat filers? Re-upload-per-filing
  is simpler and reduces the sensitive-data footprint but is worse UX.
- Legal/compliance review of storing a taxpayer's signing certificate at
  all, independent of the technical implementation.
