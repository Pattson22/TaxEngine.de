"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  calculateTaxFiling,
  downloadCoverSheet,
  getTaxFiling,
  listCapitalIncomeStatements,
  listDeductions,
  listRentalPropertyStatements,
  listSelfEmploymentStatements,
  listWageTaxCertificates,
  markCoverSheetMailed,
  submitTaxFiling,
  updateTaxFiling,
} from "@/lib/api";
import { useRequireOnboarding } from "@/lib/use-require-auth";
import { eurosToCents, formatCents } from "@/lib/money";
import { Button, CategoryTab, Card, ErrorBanner, Eyebrow, Input, Label, StatusStamp } from "@/components/ui";
import { Ledger, LedgerLine } from "@/components/ledger";
import type {
  CapitalIncomeStatement,
  Deduction,
  RentalPropertyStatement,
  SelfEmploymentStatement,
  TaxFiling,
  WageTaxCertificate,
} from "@/lib/types";

export default function FilingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { token, isLoading: authLoading } = useRequireOnboarding();
  const router = useRouter();

  const [filing, setFiling] = useState<TaxFiling | null>(null);
  const [wageCerts, setWageCerts] = useState<WageTaxCertificate[]>([]);
  const [deductions, setDeductions] = useState<Deduction[]>([]);
  const [capitalIncome, setCapitalIncome] = useState<CapitalIncomeStatement[]>([]);
  const [rentalIncome, setRentalIncome] = useState<RentalPropertyStatement[]>([]);
  const [selfEmployment, setSelfEmployment] = useState<SelfEmploymentStatement[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCalculating, setIsCalculating] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDownloadingCoverSheet, setIsDownloadingCoverSheet] = useState(false);
  const [isMarkingMailed, setIsMarkingMailed] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadAll = useCallback(async () => {
    if (!token) return;
    const loadedFiling = await getTaxFiling(token, id);
    setFiling(loadedFiling);
    const [certs, deds, capital, rental, selfEmp] = await Promise.all([
      listWageTaxCertificates(token, loadedFiling.tax_year) as Promise<WageTaxCertificate[]>,
      listDeductions(token, loadedFiling.tax_year),
      listCapitalIncomeStatements(token, loadedFiling.tax_year),
      listRentalPropertyStatements(token, loadedFiling.tax_year),
      listSelfEmploymentStatements(token, loadedFiling.tax_year),
    ]);
    setWageCerts(certs);
    setDeductions(deds);
    setCapitalIncome(capital);
    setRentalIncome(rental);
    setSelfEmployment(selfEmp);
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

  async function handleSubmit() {
    if (!token) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const updated = await submitTaxFiling(token, id);
      setFiling(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't submit this return.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDownloadCoverSheet() {
    if (!token) return;
    setIsDownloadingCoverSheet(true);
    setError(null);
    try {
      const blob = await downloadCoverSheet(token, id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `komprimierte-steuererklaerung-${filing?.tax_year ?? ""}.pdf`;
      link.click();
      URL.revokeObjectURL(url);
      const updated = await getTaxFiling(token, id);
      setFiling(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't download the cover sheet.");
    } finally {
      setIsDownloadingCoverSheet(false);
    }
  }

  async function handleMarkMailed() {
    if (!token) return;
    setIsMarkingMailed(true);
    setError(null);
    try {
      const updated = await markCoverSheetMailed(token, id);
      setFiling(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't record that.");
    } finally {
      setIsMarkingMailed(false);
    }
  }

  if (authLoading || !token || isLoading) {
    return <div className="mx-auto max-w-3xl px-6 py-14 text-sm text-ink/40">Loading…</div>;
  }

  if (!filing) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-14">
        <ErrorBanner message={error ?? "Couldn't load this return."} />
        <Link href="/dashboard" className="text-sm text-ink/60 underline hover:text-ink">
          Back to your returns
        </Link>
      </div>
    );
  }

  const totalGrossWage = wageCerts.reduce((sum, c) => sum + c.gross_wage_cents, 0);
  const totalWithheldCents =
    wageCerts.reduce(
      (sum, c) => sum + c.income_tax_withheld_cents + c.solidarity_surcharge_cents + c.church_tax_withheld_cents,
      0,
    ) +
    capitalIncome.reduce(
      (sum, s) =>
        sum +
        s.kapitalertragsteuer_withheld_cents +
        s.solidarity_surcharge_withheld_cents +
        s.church_tax_withheld_cents,
      0,
    );
  const canCalculate =
    wageCerts.length > 0 ||
    capitalIncome.length > 0 ||
    rentalIncome.length > 0 ||
    selfEmployment.length > 0;
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
            <div className="flex items-center gap-2.5">
              <CategoryTab category="wage" />
              <h2 className="font-display text-sm font-medium tracking-wide text-ink/70 uppercase">
                Wage income
              </h2>
            </div>
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
            <div className="flex items-center gap-2.5">
              <CategoryTab category="capital" />
              <h2 className="font-display text-sm font-medium tracking-wide text-ink/70 uppercase">
                Capital income
              </h2>
            </div>
            <button
              onClick={() => router.push(`/filings/${id}/capital-income`)}
              className="border-b border-indigo/40 text-sm text-indigo transition-colors hover:border-indigo"
            >
              + Add
            </button>
          </div>
          {capitalIncome.length === 0 ? (
            <p className="text-sm text-ink/45">
              Interest, dividends, or fund gains (Anlage KAP) — taxed separately at the flat
              Abgeltungsteuer rate.
            </p>
          ) : (
            <Ledger>
              {capitalIncome.map((c, i) => (
                <LedgerLine
                  key={c.id}
                  label={c.institution_name}
                  value={formatCents(c.gross_income_cents)}
                  delay={i * 60}
                />
              ))}
            </Ledger>
          )}
        </section>

        <section>
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <CategoryTab category="rental" />
              <h2 className="font-display text-sm font-medium tracking-wide text-ink/70 uppercase">
                Rental income
              </h2>
            </div>
            <button
              onClick={() => router.push(`/filings/${id}/rental-income`)}
              className="border-b border-sage/40 text-sm text-sage transition-colors hover:border-sage"
            >
              + Add property
            </button>
          </div>
          {rentalIncome.length === 0 ? (
            <p className="text-sm text-ink/45">Vermietung und Verpachtung (Anlage V).</p>
          ) : (
            <Ledger>
              {rentalIncome.map((r, i) => {
                const netCents = r.gross_rental_income_cents - r.deductible_expenses_cents;
                return (
                  <LedgerLine
                    key={r.id}
                    label={r.property_address}
                    value={formatCents(netCents)}
                    tone={netCents >= 0 ? "positive" : "negative"}
                    delay={i * 60}
                  />
                );
              })}
            </Ledger>
          )}
        </section>

        <section>
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <CategoryTab category="self_employment" />
              <h2 className="font-display text-sm font-medium tracking-wide text-ink/70 uppercase">
                Self-employment income
              </h2>
            </div>
            <button
              onClick={() => router.push(`/filings/${id}/self-employment`)}
              className="border-b border-terracotta/40 text-sm text-terracotta transition-colors hover:border-terracotta"
            >
              + Add
            </button>
          </div>
          {selfEmployment.length === 0 ? (
            <p className="text-sm text-ink/45">Freelance or business income (Anlage S / EÜR).</p>
          ) : (
            <Ledger>
              {selfEmployment.map((s, i) => {
                const netCents = s.gross_revenue_cents - s.deductible_expenses_cents;
                return (
                  <LedgerLine
                    key={s.id}
                    label={s.business_name}
                    value={formatCents(netCents)}
                    tone={netCents >= 0 ? "positive" : "negative"}
                    delay={i * 60}
                  />
                );
              })}
            </Ledger>
          )}
        </section>

        <KinderfreibetragSection filing={filing} token={token} onUpdated={setFiling} />

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
            <p className="text-sm text-ink/45">
              Add at least one source of income first — wage, capital, rental, or
              self-employment.
            </p>
          ) : (
            isCalculated && (
              <Card className="border-ink/15">
                <Ledger className="border-none py-0">
                  {filing.net_rental_income_cents !== null && filing.net_rental_income_cents !== 0 && (
                    <LedgerLine
                      label="Net rental income"
                      value={formatCents(filing.net_rental_income_cents)}
                      tone={filing.net_rental_income_cents >= 0 ? "default" : "negative"}
                    />
                  )}
                  {filing.net_self_employment_income_cents !== null &&
                    filing.net_self_employment_income_cents !== 0 && (
                      <LedgerLine
                        label="Net self-employment income"
                        value={formatCents(filing.net_self_employment_income_cents)}
                        tone={filing.net_self_employment_income_cents >= 0 ? "default" : "negative"}
                      />
                    )}
                  <LedgerLine label="Taxable income (zvE)" value={formatCents(filing.taxable_income_cents)} />
                  <LedgerLine label="Income tax" value={formatCents(filing.income_tax_cents)} />
                  <LedgerLine
                    label="Solidaritätszuschlag"
                    value={formatCents(filing.solidarity_surcharge_cents)}
                  />
                  <LedgerLine label="Kirchensteuer" value={formatCents(filing.church_tax_cents)} />
                  {filing.capital_gains_tax_cents !== null && filing.capital_gains_tax_cents > 0 && (
                    <LedgerLine
                      label="Capital gains tax (Abgeltungsteuer)"
                      value={formatCents(filing.capital_gains_tax_cents)}
                    />
                  )}
                  {filing.capital_gains_soli_cents !== null && filing.capital_gains_soli_cents > 0 && (
                    <LedgerLine
                      label="Soli on capital gains"
                      value={formatCents(filing.capital_gains_soli_cents)}
                    />
                  )}
                  {filing.capital_gains_church_tax_cents !== null &&
                    filing.capital_gains_church_tax_cents > 0 && (
                      <LedgerLine
                        label="Kirchensteuer on capital gains"
                        value={formatCents(filing.capital_gains_church_tax_cents)}
                      />
                    )}
                  {totalWithheldCents > 0 && (
                    <LedgerLine label="Bereits einbehalten" value={formatCents(totalWithheldCents)} />
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
              <div className="mt-3">
                <p className="text-sm text-ink/45">
                  Fee paid — ready to submit. (Uses a test integration until the real ERiC
                  library is wired in.)
                </p>
                <Button className="mt-3" onClick={handleSubmit} disabled={isSubmitting}>
                  {isSubmitting ? "Submitting…" : "Submit to the Finanzamt"}
                </Button>
              </div>
            )}
          </section>
        )}

        {filing.elster_transfer_ticket && filing.submission_mode === "KOMPRIMIERT" && (
          <section className="border border-brass/30 bg-brass-soft/15 p-6">
            <h2 className="font-display text-base font-medium text-ink">
              Finish by mail (komprimiert)
            </h2>
            {filing.cover_sheet_mailed_at ? (
              <p className="mt-1.5 text-sm text-sage">
                Marked as mailed — your filing is complete once the Finanzamt receives it.
              </p>
            ) : (
              <>
                <p className="mt-1.5 text-sm text-ink/60">
                  This submission went out unauthenticated (no personal ELSTER certificate on
                  file yet), so it isn&apos;t legally binding until you print, sign, and mail the
                  cover sheet below to your Finanzamt.
                </p>
                <div className="mt-4 flex flex-wrap gap-3">
                  <Button
                    variant="secondary"
                    onClick={handleDownloadCoverSheet}
                    disabled={isDownloadingCoverSheet}
                  >
                    {isDownloadingCoverSheet ? "Preparing…" : "Download cover sheet"}
                  </Button>
                  <Button
                    onClick={handleMarkMailed}
                    disabled={isMarkingMailed || !filing.cover_sheet_generated_at}
                  >
                    {isMarkingMailed ? "Saving…" : "I've mailed it"}
                  </Button>
                </div>
              </>
            )}
          </section>
        )}
      </div>
    </div>
  );
}

function KinderfreibetragSection({
  filing,
  token,
  onUpdated,
}: {
  filing: TaxFiling;
  token: string;
  onUpdated: (filing: TaxFiling) => void;
}) {
  const [numberOfChildren, setNumberOfChildren] = useState(String(filing.number_of_children));
  const [kindergeldReceived, setKindergeldReceived] = useState(
    (filing.kindergeld_received_cents / 100).toFixed(2),
  );
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    setIsSaving(true);
    setError(null);
    try {
      const updated = await updateTaxFiling(token, filing.id, {
        number_of_children: Number(numberOfChildren) || 0,
        kindergeld_received_cents: eurosToCents(kindergeldReceived || "0"),
      });
      onUpdated(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't save this.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <section>
      <div className="mb-3 flex items-center gap-2.5">
        <CategoryTab category="children" />
        <h2 className="font-display text-sm font-medium tracking-wide text-ink/70 uppercase">
          Children
        </h2>
      </div>
      {error && <ErrorBanner message={error} />}
      <div className="flex flex-wrap items-end gap-3">
        <div>
          <Label htmlFor="number_of_children">Number of children</Label>
          <Input
            id="number_of_children"
            type="number"
            min="0"
            value={numberOfChildren}
            onChange={(e) => setNumberOfChildren(e.target.value)}
            className="w-24"
          />
        </div>
        <div>
          <Label htmlFor="kindergeld_received">Kindergeld received this year, €</Label>
          <Input
            id="kindergeld_received"
            type="number"
            step="0.01"
            min="0"
            value={kindergeldReceived}
            onChange={(e) => setKindergeldReceived(e.target.value)}
            className="w-36"
          />
        </div>
        <Button onClick={handleSave} disabled={isSaving} variant="secondary">
          {isSaving ? "Saving…" : "Save"}
        </Button>
      </div>
      {filing.kinderfreibetrag_applied !== null && (
        <p className="mt-2.5 text-xs text-ink/40">
          {filing.kinderfreibetrag_applied
            ? `Günstigerprüfung: the Kinderfreibetrag (${formatCents(filing.kinderfreibetrag_total_cents ?? 0)}) worked out better than keeping the Kindergeld you received.`
            : "Günstigerprüfung: keeping the Kindergeld you already received worked out better than the Kinderfreibetrag."}
        </p>
      )}
    </section>
  );
}
