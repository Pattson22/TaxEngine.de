-- =============================================================================
-- TaxEngine.de — Core PostgreSQL Schema
-- =============================================================================
-- ** HISTORICAL REFERENCE — superseded by Alembic as of 2026-08-29. **
-- This file is kept as a human-readable snapshot of the schema and for any
-- environment that provisions a DB without running migrations. It is no
-- longer the authoritative source of truth: `backend/alembic/versions/
-- c0a6f1bd5e3b_initial_schema.py` recreates this exact schema (verified
-- byte-for-byte equivalent via a pg_dump diff) and all FUTURE schema
-- changes must go through a new Alembic revision, not an edit to this
-- file. To provision a new database, run `alembic upgrade head` from
-- `backend/` instead of applying this file directly (see README.md). If
-- you have an existing database that WAS provisioned from this file
-- before Alembic was introduced, run `alembic stamp head` instead of
-- `upgrade head` to mark it current without re-running DDL that already
-- exists.
-- =============================================================================
--
-- Design principles (financial-system grade):
--   1. All monetary values are stored as BIGINT cents. Never FLOAT/NUMERIC-money
--      mixed arithmetic — integer cents avoid IEEE-754 rounding drift entirely.
--   2. Every column that mirrors an official German tax form field is commented
--      with the field it maps to, so audits can trace DB -> form -> law.
--   3. Soft business-rule constraints (CHECK) are enforced at the DB layer as a
--      last line of defense, in addition to Pydantic validation in the app layer.
--   4. UUID primary keys (not sequential ints) to avoid enumeration of user/filing
--      records and to support future multi-region sharding.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto"; -- for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "citext";   -- case-insensitive email uniqueness

-- -----------------------------------------------------------------------------
-- ENUM TYPES
-- -----------------------------------------------------------------------------

-- Steuerklasse I–VI (§38b EStG)
CREATE TYPE tax_class_enum AS ENUM ('I', 'II', 'III', 'IV', 'V', 'VI');

-- The 16 Bundesländer — drives regional Kirchensteuer rate (8% BY/BW, 9% elsewhere)
-- and the responsible Finanzamt routing for ELSTER submission.
CREATE TYPE federal_state_enum AS ENUM (
    'BADEN_WUERTTEMBERG', 'BAYERN', 'BERLIN', 'BRANDENBURG', 'BREMEN',
    'HAMBURG', 'HESSEN', 'MECKLENBURG_VORPOMMERN', 'NIEDERSACHSEN',
    'NORDRHEIN_WESTFALEN', 'RHEINLAND_PFALZ', 'SAARLAND', 'SACHSEN',
    'SACHSEN_ANHALT', 'SCHLESWIG_HOLSTEIN', 'THUERINGEN'
);

CREATE TYPE church_tax_type_enum AS ENUM ('NONE', 'ROEMISCH_KATHOLISCH', 'EVANGELISCH', 'OTHER');

-- Werbungskosten categories. JSONB `details` on the `deductions` table carries
-- the category-specific structured payload (see table comment below).
CREATE TYPE deduction_category_enum AS ENUM (
    'COMMUTE',              -- Entfernungspauschale, §9 Abs. 1 Nr. 4 EStG
    'HOME_OFFICE',          -- Homeoffice-Pauschale, §4 Abs. 5 Satz 1 Nr. 6c EStG
    'WORK_EQUIPMENT',       -- Arbeitsmittel (laptop, desk, literature, ...)
    'FURTHER_EDUCATION',    -- Fortbildungskosten
    'DOUBLE_HOUSEHOLD',     -- Doppelte Haushaltsführung
    'INSURANCE',            -- Sonderausgaben-adjacent insurance premiums
    'DONATIONS',            -- Spenden, §10b Abs. 1 EStG (Sonderausgabe)
    'CHILDCARE',            -- Kinderbetreuungskosten, §10 Abs. 1 Nr. 5 EStG (Sonderausgabe)
    'HANDWERKERLEISTUNGEN', -- §35a Abs. 3 EStG — processed as a CREDIT against
                             -- final tax, not a deduction; see tax_credits/
    'OTHER'
);

CREATE TYPE filing_status_enum AS ENUM (
    'DRAFT', 'CALCULATED', 'FEE_PAID', 'SUBMITTED', 'ACCEPTED', 'REJECTED'
);

-- -----------------------------------------------------------------------------
-- USERS
-- -----------------------------------------------------------------------------
CREATE TABLE users (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email                   CITEXT NOT NULL UNIQUE,
    password_hash           TEXT NOT NULL,                 -- argon2id hash, never plaintext
    first_name              TEXT NOT NULL,
    last_name               TEXT NOT NULL,
    tax_identification_number TEXT,                        -- Steuer-ID (11-digit), nullable until KYC step
    residence_state         federal_state_enum NOT NULL,
    tax_class                tax_class_enum NOT NULL DEFAULT 'I',
    church_tax_type          church_tax_type_enum NOT NULL DEFAULT 'NONE',
    is_joint_assessment      BOOLEAN NOT NULL DEFAULT FALSE, -- Zusammenveranlagung with spouse
    spouse_user_id           UUID REFERENCES users(id) ON DELETE SET NULL,
    is_active                BOOLEAN NOT NULL DEFAULT TRUE,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at               TIMESTAMPTZ,                   -- soft delete: GDPR-friendly, preserves FK integrity for filed returns

    CONSTRAINT chk_steuer_id_format CHECK (
        tax_identification_number IS NULL OR tax_identification_number ~ '^\d{11}$'
    )
);

CREATE INDEX idx_users_email ON users (email) WHERE deleted_at IS NULL;

-- -----------------------------------------------------------------------------
-- WAGE TAX CERTIFICATES (Lohnsteuerbescheinigung — one per employer per year)
-- -----------------------------------------------------------------------------
-- Column names deliberately mirror the official electronic wage tax certificate
-- (elektronische Lohnsteuerbescheinigung) field semantics so a support agent or
-- auditor can map DB rows straight back to the certificate the user uploaded.
CREATE TABLE wage_tax_certificates (
    id                                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tax_year                         SMALLINT NOT NULL,
    employer_name                    TEXT NOT NULL,
    employer_tax_number              TEXT,

    -- Zeile 3: Bruttoarbeitslohn
    gross_wage_cents                 BIGINT NOT NULL,
    -- Zeile 4: Einbehaltene Lohnsteuer
    income_tax_withheld_cents        BIGINT NOT NULL DEFAULT 0,
    -- Zeile 5: Solidaritätszuschlag
    solidarity_surcharge_cents       BIGINT NOT NULL DEFAULT 0,
    -- Zeile 6: Einbehaltene Kirchensteuer
    church_tax_withheld_cents        BIGINT NOT NULL DEFAULT 0,

    -- Zeile 22a: Arbeitnehmeranteil Rentenversicherung
    pension_insurance_employee_cents         BIGINT NOT NULL DEFAULT 0,
    -- Zeile 25: Arbeitnehmeranteil Krankenversicherung (gesetzlich/privat)
    health_insurance_employee_cents          BIGINT NOT NULL DEFAULT 0,
    -- Zeile 26: Arbeitnehmeranteil Pflegeversicherung
    long_term_care_insurance_employee_cents  BIGINT NOT NULL DEFAULT 0,
    -- Zeile 27: Arbeitnehmeranteil Arbeitslosenversicherung
    unemployment_insurance_employee_cents    BIGINT NOT NULL DEFAULT 0,

    source_document_url              TEXT,   -- pointer to the encrypted-at-rest uploaded PDF/XML
    created_at                       TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT chk_wtc_tax_year CHECK (tax_year BETWEEN 2015 AND 2100),
    CONSTRAINT chk_wtc_gross_wage_nonneg CHECK (gross_wage_cents >= 0),
    CONSTRAINT chk_wtc_income_tax_nonneg CHECK (income_tax_withheld_cents >= 0),
    CONSTRAINT chk_wtc_soli_nonneg CHECK (solidarity_surcharge_cents >= 0),
    CONSTRAINT chk_wtc_church_tax_nonneg CHECK (church_tax_withheld_cents >= 0),
    CONSTRAINT chk_wtc_pension_nonneg CHECK (pension_insurance_employee_cents >= 0),
    CONSTRAINT chk_wtc_health_nonneg CHECK (health_insurance_employee_cents >= 0),
    CONSTRAINT chk_wtc_ltc_nonneg CHECK (long_term_care_insurance_employee_cents >= 0),
    CONSTRAINT chk_wtc_unemployment_nonneg CHECK (unemployment_insurance_employee_cents >= 0)
);

CREATE INDEX idx_wtc_user_year ON wage_tax_certificates (user_id, tax_year);

-- -----------------------------------------------------------------------------
-- DEDUCTIONS (Werbungskosten)
-- -----------------------------------------------------------------------------
-- `details` JSONB carries the category-specific structured input so the
-- calculation engine can recompute deterministically rather than trusting a
-- pre-summed figure. Examples:
--   COMMUTE:      {"distance_km": 18, "days_worked": 220}
--   HOME_OFFICE:  {"days_claimed": 140}
--   WORK_EQUIPMENT: {"item": "Laptop", "purchase_date": "2024-03-01"}
-- `amount_claimed_cents` is nullable: for computed categories (COMMUTE,
-- HOME_OFFICE) the engine derives the amount from `details` at calculation
-- time rather than trusting a client-submitted total.
CREATE TABLE deductions (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id               UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tax_year             SMALLINT NOT NULL,
    category              deduction_category_enum NOT NULL,
    amount_claimed_cents  BIGINT,
    details               JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT chk_deductions_tax_year CHECK (tax_year BETWEEN 2015 AND 2100),
    CONSTRAINT chk_deductions_amount_nonneg CHECK (amount_claimed_cents IS NULL OR amount_claimed_cents >= 0)
);

CREATE INDEX idx_deductions_user_year_category ON deductions (user_id, tax_year, category);
-- GIN index to support querying inside the JSONB payload (e.g. "all commute
-- deductions with distance_km > 30" for anomaly/fraud review tooling).
CREATE INDEX idx_deductions_details_gin ON deductions USING GIN (details);

-- -----------------------------------------------------------------------------
-- TAX FILINGS
-- -----------------------------------------------------------------------------
CREATE TABLE tax_filings (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                   UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tax_year                 SMALLINT NOT NULL,
    status                    filing_status_enum NOT NULL DEFAULT 'DRAFT',

    estimated_refund_cents    BIGINT,             -- signed: negative means additional payment owed
    taxable_income_cents      BIGINT,             -- zu versteuerndes Einkommen at last calculation

    -- Full assessed-tax breakdown, so the UI can show a Steuerbescheid-style
    -- itemization instead of just a single refund number. Each is the
    -- FINAL computed liability, distinct from wage_tax_certificates'
    -- already-withheld amounts (the delta between the two drives the
    -- refund/back-payment figure above).
    income_tax_cents          BIGINT,             -- tax_brackets.calculate_income_tax_for_assessment output
    solidarity_surcharge_cents BIGINT,             -- soli.calculate_solidaritaetszuschlag output
    church_tax_cents          BIGINT,             -- church_tax.calculate_kirchensteuer output
    tax_credits_applied_cents BIGINT NOT NULL DEFAULT 0,  -- e.g. §35a Handwerkerleistungen, already netted into income_tax_cents

    processing_fee_cents      BIGINT NOT NULL DEFAULT 3490,  -- flat €34.90 fee, in cents
    fee_paid_at               TIMESTAMPTZ,
    payment_provider_ref      TEXT,               -- Stripe/Adyen charge id

    -- ELSTER/ERiC submission tracking
    elster_transfer_ticket    TEXT,               -- returned by ERiC on successful transfer
    elster_submitted_at       TIMESTAMPTZ,
    elster_accepted_at        TIMESTAMPTZ,
    elster_rejection_reason   TEXT,

    created_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT chk_filings_tax_year CHECK (tax_year BETWEEN 2015 AND 2100),
    CONSTRAINT uq_filings_user_year UNIQUE (user_id, tax_year),
    CONSTRAINT chk_filings_income_tax_nonneg CHECK (income_tax_cents IS NULL OR income_tax_cents >= 0),
    CONSTRAINT chk_filings_soli_nonneg CHECK (solidarity_surcharge_cents IS NULL OR solidarity_surcharge_cents >= 0),
    CONSTRAINT chk_filings_church_tax_nonneg CHECK (church_tax_cents IS NULL OR church_tax_cents >= 0),
    CONSTRAINT chk_filings_credits_nonneg CHECK (tax_credits_applied_cents >= 0)
);

CREATE INDEX idx_filings_status ON tax_filings (status);

-- -----------------------------------------------------------------------------
-- updated_at auto-touch trigger (applied to mutable tables)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_deductions_updated_at BEFORE UPDATE ON deductions
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_filings_updated_at BEFORE UPDATE ON tax_filings
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
