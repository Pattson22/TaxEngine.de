# ELSTER / ERiC Integration Engine

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
