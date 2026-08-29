"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  calculateTaxFiling,
  getTaxFiling,
  listDeductions,
  listWageTaxCertificates,
} from "@/lib/api";
import { useRequireAuth } from "@/lib/use-require-auth";
import { formatCents } from "@/lib/money";
import { Button, Card, ErrorBanner, PageHeading, StatusBadge } from "@/components/ui";
import type { Deduction, TaxFiling, WageTaxCertificate } from "@/lib/types";

export default function FilingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { token, isLoading: authLoading } = useRequireAuth();
  const router = useRouter();

  const [filing, setFiling] = useState<TaxFiling | null>(null);
  const [wageCerts, setWageCerts] = useState<WageTaxCertificate[]>([]);
  const [deductions, setDeductions] = useState<Deduction[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCalculating, setIsCalculating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadAll = useCallback(async () => {
    if (!token) return;
    const loadedFiling = await getTaxFiling(token, id);
    setFiling(loadedFiling);
    const [certs, deds] = await Promise.all([
      listWageTaxCertificates(token, loadedFiling.tax_year) as Promise<WageTaxCertificate[]>,
      listDeductions(token, loadedFiling.tax_year),
    ]);
    setWageCerts(certs);
    setDeductions(deds);
  }, [token, id]);

  useEffect(() => {
    if (!token) return;
    // Reset to loading on every (token, id) change -- App Router does not
    // remount this component when navigating between two filing detail
    // URLs, so without this the previous filing's data would flash before
    // the new fetch resolves.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setIsLoading(true);
    loadAll()
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load filing."))
      .finally(() => setIsLoading(false));
  }, [token, loadAll]);

  async function handleCalculate() {
    if (!token) return;
    setIsCalculating(true);
    setError(null);
    try {
      const updated = await calculateTaxFiling(token, id);
      setFiling(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Calculation failed.");
    } finally {
      setIsCalculating(false);
    }
  }

  if (authLoading || !token || isLoading || !filing) {
    return <div className="mx-auto max-w-3xl px-6 py-12 text-sm text-slate-500">Loading…</div>;
  }

  const totalGrossWage = wageCerts.reduce((sum, c) => sum + c.gross_wage_cents, 0);
  const canCalculate = wageCerts.length > 0;
  const isCalculated = filing.status !== "DRAFT";

  return (
    <div className="mx-auto max-w-3xl px-6 py-12">
      <div className="flex items-center gap-3">
        <PageHeading title={`Tax year ${filing.tax_year}`} />
        <div className="mb-8">
          <StatusBadge status={filing.status} />
        </div>
      </div>

      {error && <ErrorBanner message={error} />}

      <div className="space-y-6">
        <Card>
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-slate-900">Wage income</h2>
            <Button
              variant="secondary"
              onClick={() => router.push(`/filings/${id}/wage-income`)}
            >
              + Add employer
            </Button>
          </div>
          {wageCerts.length === 0 ? (
            <p className="mt-3 text-sm text-slate-500">
              No wage tax certificates yet. Add your Lohnsteuerbescheinigung to get started.
            </p>
          ) : (
            <ul className="mt-3 divide-y divide-slate-100">
              {wageCerts.map((cert) => (
                <li key={cert.id} className="flex justify-between py-2 text-sm">
                  <span className="text-slate-700">{cert.employer_name}</span>
                  <span className="font-medium text-slate-900">
                    {formatCents(cert.gross_wage_cents)}
                  </span>
                </li>
              ))}
              <li className="flex justify-between pt-2 text-sm font-semibold">
                <span>Total gross</span>
                <span>{formatCents(totalGrossWage)}</span>
              </li>
            </ul>
          )}
        </Card>

        <Card>
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-slate-900">Deductions</h2>
            <Button variant="secondary" onClick={() => router.push(`/filings/${id}/deductions`)}>
              + Add deduction
            </Button>
          </div>
          {deductions.length === 0 ? (
            <p className="mt-3 text-sm text-slate-500">
              No deductions yet — commute, home office, donations, and more can all lower
              your taxable income.
            </p>
          ) : (
            <ul className="mt-3 divide-y divide-slate-100">
              {deductions.map((d) => (
                <li key={d.id} className="flex justify-between py-2 text-sm">
                  <span className="text-slate-700">{d.category.replaceAll("_", " ")}</span>
                  <span className="font-medium text-slate-900">
                    {d.amount_claimed_cents !== null ? formatCents(d.amount_claimed_cents) : "computed"}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card>
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-slate-900">Calculation</h2>
            <Button onClick={handleCalculate} disabled={!canCalculate || isCalculating}>
              {isCalculating ? "Calculating…" : isCalculated ? "Recalculate" : "Calculate refund"}
            </Button>
          </div>
          {!canCalculate && (
            <p className="mt-3 text-sm text-slate-500">
              Add at least one wage tax certificate before calculating.
            </p>
          )}
          {isCalculated && (
            <dl className="mt-4 space-y-2 text-sm">
              <Row label="Taxable income (zvE)" value={formatCents(filing.taxable_income_cents)} />
              <Row label="Income tax" value={formatCents(filing.income_tax_cents)} />
              <Row label="Solidaritätszuschlag" value={formatCents(filing.solidarity_surcharge_cents)} />
              <Row label="Kirchensteuer" value={formatCents(filing.church_tax_cents)} />
              {filing.capital_gains_tax_cents !== null && filing.capital_gains_tax_cents > 0 && (
                <Row label="Capital gains tax" value={formatCents(filing.capital_gains_tax_cents)} />
              )}
              <div className="my-2 border-t border-slate-200" />
              <Row
                label="Estimated refund"
                value={formatCents(filing.estimated_refund_cents)}
                emphasize
              />
            </dl>
          )}
        </Card>

        {isCalculated && filing.status === "CALCULATED" && (
          <Card>
            <h2 className="font-semibold text-slate-900">Ready to file</h2>
            <p className="mt-2 text-sm text-slate-600">
              Pay the flat {formatCents(filing.processing_fee_cents)} processing fee to submit
              your return to the Finanzamt.
            </p>
            <Button className="mt-4" onClick={() => router.push(`/filings/${id}/pay`)}>
              Continue to payment
            </Button>
          </Card>
        )}

        {(filing.status === "FEE_PAID" ||
          filing.status === "SUBMITTED" ||
          filing.status === "ACCEPTED" ||
          filing.status === "REJECTED") && (
          <Card>
            <h2 className="font-semibold text-slate-900">Submission</h2>
            {filing.elster_transfer_ticket ? (
              <div className="mt-2 text-sm text-slate-600">
                <p>Transfer ticket: {filing.elster_transfer_ticket}</p>
                {filing.elster_accepted_at && <p className="mt-1 text-emerald-700">Accepted by the Finanzamt.</p>}
                {filing.elster_rejection_reason && (
                  <p className="mt-1 text-red-700">{filing.elster_rejection_reason}</p>
                )}
              </div>
            ) : (
              <p className="mt-2 text-sm text-slate-500">
                Fee paid — ready to submit. (Submission uses a test integration until a real
                ELSTER developer certificate is in place — see docs/ELSTER_ERIC_INTEGRATION.md.)
              </p>
            )}
          </Card>
        )}
      </div>
    </div>
  );
}

function Row({ label, value, emphasize = false }: { label: string; value: string; emphasize?: boolean }) {
  return (
    <div className={`flex justify-between ${emphasize ? "text-base font-semibold text-emerald-700" : "text-slate-600"}`}>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}
