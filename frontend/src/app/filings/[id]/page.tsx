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
import { Button, Card, ErrorBanner, Eyebrow, StatusStamp } from "@/components/ui";
import { Ledger, LedgerLine } from "@/components/ledger";
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
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setIsLoading(true);
    loadAll()
      .catch((err) => setError(err instanceof Error ? err.message : "Couldn't load this return."))
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
      setError(err instanceof Error ? err.message : "Couldn't calculate this return.");
    } finally {
      setIsCalculating(false);
    }
  }

  if (authLoading || !token || isLoading || !filing) {
    return <div className="mx-auto max-w-3xl px-6 py-14 text-sm text-ink/40">Loading…</div>;
  }

  const totalGrossWage = wageCerts.reduce((sum, c) => sum + c.gross_wage_cents, 0);
  const canCalculate = wageCerts.length > 0;
  const isCalculated = filing.status !== "DRAFT";
  const refundIsPositive = (filing.estimated_refund_cents ?? 0) >= 0;

  return (
    <div className="mx-auto max-w-3xl px-6 py-14">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <Eyebrow>Steuererklärung</Eyebrow>
          <h1 className="font-display text-[28px] leading-tight font-medium text-ink">
            Tax year {filing.tax_year}
          </h1>
        </div>
        <StatusStamp status={filing.status} />
      </div>

      {error && <ErrorBanner message={error} />}

      <div className="space-y-10">
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-display text-sm font-medium tracking-wide text-ink/70 uppercase">
              Wage income
            </h2>
            <button
              onClick={() => router.push(`/filings/${id}/wage-income`)}
              className="border-b border-brass/40 text-sm text-brass transition-colors hover:border-brass"
            >
              + Add employer
            </button>
          </div>
          {wageCerts.length === 0 ? (
            <p className="text-sm text-ink/45">
              Add your Lohnsteuerbescheinigung to get started.
            </p>
          ) : (
            <Ledger>
              {wageCerts.map((cert, i) => (
                <LedgerLine
                  key={cert.id}
                  label={cert.employer_name}
                  value={formatCents(cert.gross_wage_cents)}
                  delay={i * 60}
                />
              ))}
              <LedgerLine label="Total gross" value={formatCents(totalGrossWage)} tone="total" />
            </Ledger>
          )}
        </section>

        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-display text-sm font-medium tracking-wide text-ink/70 uppercase">
              Deductions
            </h2>
            <button
              onClick={() => router.push(`/filings/${id}/deductions`)}
              className="border-b border-brass/40 text-sm text-brass transition-colors hover:border-brass"
            >
              + Add deduction
            </button>
          </div>
          {deductions.length === 0 ? (
            <p className="text-sm text-ink/45">
              Commute, home office, donations, childcare — add anything that applies.
            </p>
          ) : (
            <Ledger>
              {deductions.map((d, i) => (
                <LedgerLine
                  key={d.id}
                  label={d.category.replaceAll("_", " ").toLowerCase()}
                  value={d.amount_claimed_cents !== null ? formatCents(d.amount_claimed_cents) : "computed"}
                  delay={i * 60}
                />
              ))}
            </Ledger>
          )}
        </section>

        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-display text-sm font-medium tracking-wide text-ink/70 uppercase">
              Calculation
            </h2>
            <Button onClick={handleCalculate} disabled={!canCalculate || isCalculating}>
              {isCalculating ? "Calculating…" : isCalculated ? "Recalculate" : "Calculate refund"}
            </Button>
          </div>
          {!canCalculate ? (
            <p className="text-sm text-ink/45">Add at least one wage tax certificate first.</p>
          ) : (
            isCalculated && (
              <Card className="border-ink/15">
                <Ledger className="border-none py-0">
                  <LedgerLine label="Taxable income (zvE)" value={formatCents(filing.taxable_income_cents)} />
                  <LedgerLine label="Income tax" value={formatCents(filing.income_tax_cents)} />
                  <LedgerLine
                    label="Solidaritätszuschlag"
                    value={formatCents(filing.solidarity_surcharge_cents)}
                  />
                  <LedgerLine label="Kirchensteuer" value={formatCents(filing.church_tax_cents)} />
                  {filing.capital_gains_tax_cents !== null && filing.capital_gains_tax_cents > 0 && (
                    <LedgerLine
                      label="Capital gains tax"
                      value={formatCents(filing.capital_gains_tax_cents)}
                    />
                  )}
                </Ledger>
                <div className="mt-2 flex items-baseline justify-between border-t border-ink/15 pt-4">
                  <span className="font-display text-base font-medium text-ink">
                    {refundIsPositive ? "Estimated refund" : "You'd owe"}
                  </span>
                  <span
                    className={`tabular font-display text-2xl font-medium ${refundIsPositive ? "text-sage" : "text-clay"}`}
                  >
                    {formatCents(
                      refundIsPositive
                        ? filing.estimated_refund_cents
                        : Math.abs(filing.estimated_refund_cents ?? 0),
                    )}
                  </span>
                </div>
              </Card>
            )
          )}
        </section>

        {isCalculated && filing.status === "CALCULATED" && (
          <section className="border border-brass/30 bg-brass-soft/15 p-6">
            <h2 className="font-display text-base font-medium text-ink">Ready to file</h2>
            <p className="mt-1.5 text-sm text-ink/60">
              Pay the flat {formatCents(filing.processing_fee_cents)} fee and we&apos;ll submit
              this to the Finanzamt.
            </p>
            <Button className="mt-4" onClick={() => router.push(`/filings/${id}/pay`)}>
              Continue to payment
            </Button>
          </section>
        )}

        {["FEE_PAID", "SUBMITTED", "ACCEPTED", "REJECTED"].includes(filing.status) && (
          <section className="border-t border-ink/10 pt-6">
            <h2 className="font-display text-sm font-medium tracking-wide text-ink/70 uppercase">
              Submission
            </h2>
            {filing.elster_transfer_ticket ? (
              <div className="mt-3 text-sm text-ink/60">
                <p className="tabular">Transfer ticket: {filing.elster_transfer_ticket}</p>
                {filing.elster_accepted_at && (
                  <p className="mt-1.5 text-sage">Accepted by the Finanzamt.</p>
                )}
                {filing.elster_rejection_reason && (
                  <p className="mt-1.5 text-clay">{filing.elster_rejection_reason}</p>
                )}
              </div>
            ) : (
              <p className="mt-3 text-sm text-ink/45">
                Fee paid — ready to submit. (Uses a test integration until a real ELSTER
                developer certificate is in place.)
              </p>
            )}
          </section>
        )}
      </div>
    </div>
  );
}
