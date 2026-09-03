// Mirrors backend/app/schemas/*.py and backend/app/models/enums.py.
// Kept as a single hand-maintained file for this scaffold rather than
// generated from the OpenAPI schema -- see README.md's "Next steps" for
// why codegen (e.g. openapi-typescript) is the right move once the API
// surface stabilizes.

export type FederalState =
  | "BADEN_WUERTTEMBERG"
  | "BAYERN"
  | "BERLIN"
  | "BRANDENBURG"
  | "BREMEN"
  | "HAMBURG"
  | "HESSEN"
  | "MECKLENBURG_VORPOMMERN"
  | "NIEDERSACHSEN"
  | "NORDRHEIN_WESTFALEN"
  | "RHEINLAND_PFALZ"
  | "SAARLAND"
  | "SACHSEN"
  | "SACHSEN_ANHALT"
  | "SCHLESWIG_HOLSTEIN"
  | "THUERINGEN";

export type TaxClass = "I" | "II" | "III" | "IV" | "V" | "VI";

export type ChurchTaxType = "NONE" | "ROEMISCH_KATHOLISCH" | "EVANGELISCH" | "OTHER";

export type DeductionCategory =
  | "COMMUTE"
  | "HOME_OFFICE"
  | "WORK_EQUIPMENT"
  | "FURTHER_EDUCATION"
  | "DOUBLE_HOUSEHOLD"
  | "INSURANCE"
  | "DONATIONS"
  | "CHILDCARE"
  | "HANDWERKERLEISTUNGEN"
  | "AUSSERGEWOEHNLICHE_BELASTUNG"
  | "OTHER";

export type FilingStatus =
  | "DRAFT"
  | "CALCULATED"
  | "FEE_PAID"
  | "SUBMITTED"
  | "ACCEPTED"
  | "REJECTED";

export type SubmissionMode = "KOMPRIMIERT" | "AUTHENTIFIZIERT";

export type EricSubmissionJobStatus = "PENDING" | "PROCESSING" | "SUCCEEDED" | "FAILED";

export interface EricSubmissionJob {
  id: string;
  tax_filing_id: string;
  status: EricSubmissionJobStatus;
  is_amendment: boolean;
  error_message: string | null;
  transfer_ticket: string | null;
  claimed_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  tax_identification_number: string | null;
  date_of_birth: string | null;
  street: string | null;
  house_number: string | null;
  postal_code: string | null;
  city: string | null;
  steuernummer: string | null;
  residence_state: FederalState;
  tax_class: TaxClass;
  church_tax_type: ChurchTaxType;
  is_joint_assessment: boolean;
  is_active: boolean;
  elster_privacy_notice_confirmed_at: string | null;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface DocumentUploadResult {
  source_document_url: string;
}

export interface WageTaxCertificate {
  id: string;
  tax_year: number;
  employer_name: string;
  employer_tax_number: string | null;
  gross_wage_cents: number;
  income_tax_withheld_cents: number;
  solidarity_surcharge_cents: number;
  church_tax_withheld_cents: number;
  pension_insurance_employee_cents: number;
  health_insurance_employee_cents: number;
  long_term_care_insurance_employee_cents: number;
  unemployment_insurance_employee_cents: number;
  source_document_url: string | null;
  created_at: string;
}

export interface Deduction {
  id: string;
  tax_year: number;
  category: DeductionCategory;
  amount_claimed_cents: number | null;
  details: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface TaxFiling {
  id: string;
  tax_year: number;
  status: FilingStatus;

  number_of_children: number;
  kindergeld_received_cents: number;
  kinderfreibetrag_applied: boolean | null;
  kinderfreibetrag_total_cents: number | null;

  estimated_refund_cents: number | null;
  taxable_income_cents: number | null;
  income_tax_cents: number | null;
  solidarity_surcharge_cents: number | null;
  church_tax_cents: number | null;
  tax_credits_applied_cents: number;

  capital_gains_tax_cents: number | null;
  capital_gains_soli_cents: number | null;
  capital_gains_church_tax_cents: number | null;
  capital_gains_progressive_election_applied: boolean | null;

  net_rental_income_cents: number | null;
  net_self_employment_income_cents: number | null;

  donation_carryforward_out_cents: number | null;

  altersvorsorge_deduction_cents: number | null;
  sonstige_vorsorgeaufwendungen_deduction_cents: number | null;
  aussergewoehnliche_belastungen_deduction_cents: number | null;

  processing_fee_cents: number;
  fee_paid_at: string | null;
  withdrawal_consent_at: string | null;

  elster_transfer_ticket: string | null;
  elster_submitted_at: string | null;
  elster_accepted_at: string | null;
  elster_rejection_reason: string | null;

  submission_mode: SubmissionMode;
  cover_sheet_generated_at: string | null;
  cover_sheet_mailed_at: string | null;

  created_at: string;
  updated_at: string;
}

export interface CapitalIncomeStatement {
  id: string;
  tax_year: number;
  institution_name: string;
  gross_income_cents: number;
  kapitalertragsteuer_withheld_cents: number;
  solidarity_surcharge_withheld_cents: number;
  church_tax_withheld_cents: number;
  created_at: string;
}

export interface RentalPropertyStatement {
  id: string;
  tax_year: number;
  property_address: string;
  gross_rental_income_cents: number;
  deductible_expenses_cents: number;
  building_acquisition_cost_cents: number | null;
  building_completion_year: number | null;
  // Derived by the backend from the two fields above -- never recompute
  // these client-side. `deductible_expenses_cents` alone EXCLUDES AfA, so
  // subtracting it from gross yields a net figure the backend's own
  // calculation disagrees with (and the §7 Abs. 4 rate table lives in
  // tax_engine/constants.py, not here).
  afa_deduction_cents: number;
  total_deductible_expenses_cents: number;
  net_rental_income_cents: number;
  created_at: string;
}

export interface SelfEmploymentStatement {
  id: string;
  tax_year: number;
  business_name: string;
  gross_revenue_cents: number;
  deductible_expenses_cents: number;
  created_at: string;
}

export interface PaymentIntentResponse {
  client_secret: string;
  payment_intent_id: string;
  amount_cents: number;
}
