// Thin typed fetch wrapper around the FastAPI backend. Every function here
// corresponds 1:1 to a route in backend/app/api/routes/ -- see that
// directory (or /docs on the running backend) for the authoritative
// request/response shapes this file mirrors.

import type {
  CapitalIncomeStatement,
  Deduction,
  DeductionCategory,
  PaymentIntentResponse,
  RentalPropertyStatement,
  SelfEmploymentStatement,
  TaxFiling,
  TokenResponse,
  User,
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  options: RequestInit & { token?: string | null } = {},
): Promise<T> {
  const { token, headers, ...rest } = options;

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    headers: {
      ...(rest.body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const body = await response.json().catch(() => null);

  if (!response.ok) {
    const detail =
      typeof body?.detail === "string"
        ? body.detail
        : Array.isArray(body?.detail)
          ? body.detail.map((e: { msg?: string }) => e.msg).join("; ")
          : `Request failed with status ${response.status}`;
    throw new ApiError(response.status, detail);
  }

  return body as T;
}

// --- Auth ---

export function register(payload: {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  residence_state: string;
  tax_class?: string;
  church_tax_type?: string;
  is_joint_assessment?: boolean;
}): Promise<TokenResponse> {
  return request<TokenResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function login(email: string, password: string): Promise<TokenResponse> {
  // The backend's OAuth2PasswordRequestForm expects form-encoded data with
  // a `username` field (the spec's name for it), not JSON.
  const body = new URLSearchParams({ username: email, password });
  return request<TokenResponse>("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
}

export function getCurrentUser(token: string): Promise<User> {
  return request<User>("/users/me", { token });
}

export function updateCurrentUser(token: string, payload: Partial<User>): Promise<User> {
  return request<User>("/users/me", { method: "PATCH", token, body: JSON.stringify(payload) });
}

// --- Tax filings ---

export function listTaxFilings(token: string): Promise<TaxFiling[]> {
  return request<TaxFiling[]>("/tax-filings", { token });
}

export function createTaxFiling(token: string, taxYear: number): Promise<TaxFiling> {
  return request<TaxFiling>("/tax-filings", {
    method: "POST",
    token,
    body: JSON.stringify({ tax_year: taxYear }),
  });
}

export function getTaxFiling(token: string, filingId: string): Promise<TaxFiling> {
  return request<TaxFiling>(`/tax-filings/${filingId}`, { token });
}

export function updateTaxFiling(
  token: string,
  filingId: string,
  payload: { number_of_children?: number; kindergeld_received_cents?: number },
): Promise<TaxFiling> {
  return request<TaxFiling>(`/tax-filings/${filingId}`, {
    method: "PATCH",
    token,
    body: JSON.stringify(payload),
  });
}

export function calculateTaxFiling(token: string, filingId: string): Promise<TaxFiling> {
  return request<TaxFiling>(`/tax-filings/${filingId}/calculate`, { method: "POST", token });
}

// Tax years the calculation engine has reviewed, published constants for
// -- the single source of truth for the dashboard's year picker, so it
// can never drift out of sync with the backend's tax_engine/constants.py.
export function getSupportedTaxYears(): Promise<number[]> {
  return request<number[]>("/tax-filings/supported-years");
}

export function createPaymentIntent(
  token: string,
  filingId: string,
): Promise<PaymentIntentResponse> {
  return request<PaymentIntentResponse>(`/tax-filings/${filingId}/payment-intent`, {
    method: "POST",
    token,
  });
}

export function submitTaxFiling(token: string, filingId: string): Promise<TaxFiling> {
  return request<TaxFiling>(`/tax-filings/${filingId}/submit`, { method: "POST", token });
}

// --- Wage tax certificates ---

export function listWageTaxCertificates(token: string, taxYear: number) {
  return request(`/wage-tax-certificates?tax_year=${taxYear}`, { token });
}

export function createWageTaxCertificate(
  token: string,
  payload: {
    tax_year: number;
    employer_name: string;
    gross_wage_cents: number;
    income_tax_withheld_cents?: number;
    solidarity_surcharge_cents?: number;
    church_tax_withheld_cents?: number;
  },
) {
  return request("/wage-tax-certificates", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

// --- Capital income (Anlage KAP) ---

export function listCapitalIncomeStatements(
  token: string,
  taxYear: number,
): Promise<CapitalIncomeStatement[]> {
  return request<CapitalIncomeStatement[]>(`/capital-income-statements?tax_year=${taxYear}`, {
    token,
  });
}

export function createCapitalIncomeStatement(
  token: string,
  payload: {
    tax_year: number;
    institution_name: string;
    gross_income_cents: number;
    kapitalertragsteuer_withheld_cents?: number;
    solidarity_surcharge_withheld_cents?: number;
    church_tax_withheld_cents?: number;
  },
): Promise<CapitalIncomeStatement> {
  return request<CapitalIncomeStatement>("/capital-income-statements", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

// --- Rental income (Anlage V) ---

export function listRentalPropertyStatements(
  token: string,
  taxYear: number,
): Promise<RentalPropertyStatement[]> {
  return request<RentalPropertyStatement[]>(`/rental-property-statements?tax_year=${taxYear}`, {
    token,
  });
}

export function createRentalPropertyStatement(
  token: string,
  payload: {
    tax_year: number;
    property_address: string;
    gross_rental_income_cents: number;
    deductible_expenses_cents?: number;
  },
): Promise<RentalPropertyStatement> {
  return request<RentalPropertyStatement>("/rental-property-statements", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

// --- Self-employment income (Anlage S / EÜR) ---

export function listSelfEmploymentStatements(
  token: string,
  taxYear: number,
): Promise<SelfEmploymentStatement[]> {
  return request<SelfEmploymentStatement[]>(`/self-employment-statements?tax_year=${taxYear}`, {
    token,
  });
}

export function createSelfEmploymentStatement(
  token: string,
  payload: {
    tax_year: number;
    business_name: string;
    gross_revenue_cents: number;
    deductible_expenses_cents?: number;
  },
): Promise<SelfEmploymentStatement> {
  return request<SelfEmploymentStatement>("/self-employment-statements", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

// --- Deductions ---

export function listDeductions(token: string, taxYear: number): Promise<Deduction[]> {
  return request<Deduction[]>(`/deductions?tax_year=${taxYear}`, { token });
}

export function createDeduction(
  token: string,
  payload: {
    tax_year: number;
    category: DeductionCategory;
    amount_claimed_cents?: number;
    details?: Record<string, unknown>;
  },
): Promise<Deduction> {
  return request<Deduction>("/deductions", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export function deleteDeduction(token: string, deductionId: string): Promise<void> {
  return request<void>(`/deductions/${deductionId}`, { method: "DELETE", token });
}
