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

Two Anlagen remain deliberately unmapped, each for a specific, real
reason rather than "not gotten to yet":
- `SA/KiSt` (church tax PAID, e.g. direct payments to the
  Kirchensteueramt): its own field documentation explicitly EXCLUDES
  church tax already withheld as an Abgeltungsteuer surcharge -- i.e. it's
  a legally different figure from what `N`/`KAP` already declare as
  withheld, not a restatement of it. This project doesn't collect "church
  tax paid directly, outside withholding" anywhere, so deriving this box
  from already-withheld figures would misrepresent what it means.
- The KOMPRIMIERT cover-sheet block (`Vorsatz`) needs the filer's
  Steuernummer in ERiC's own unified 13-digit format, produced by
  `EricMakeElsterStnr()` -- not yet bound in `native_bindings.py` (which
  only declares the subset of the API the KOMPRIMIERT-unauthenticated
  flow needs today). Real, separate work, not a drive-by addition.

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
