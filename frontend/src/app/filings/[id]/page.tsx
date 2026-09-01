"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  calculateTaxFiling,
  downloadCoverSheet,
  getSubmissionJob,
  getTaxFiling,
  listCapitalIncomeStatements,
  listDeductions,
  listRentalPropertyStatements,
  listSelfEmploymentStatements,
  listSubmissionJobs,
  listWageTaxCertificates,
  markCoverSheetMailed,
  submitTaxFiling,
  updateTaxFiling,
} from "@/lib/api";
import { useRequireOnboarding } from "@/lib/use-require-auth";
import { eurosToCents, formatCents } from "@/lib/money";
import { Button, CategoryTab, Card, ErrorBanner, Eyebrow, Input, Label, StatusStamp } from "@/components/ui";
import { Ledger, LedgerLine } from "@/components/ledger";
import { RefundAnchor } from "@/components/refund-anchor";
import { BentoGrid, BentoTile } from "@/components/bento";
import type {
  CapitalIncomeStatement,
  Deduction,
  EricSubmissionJob,
  RentalPropertyStatement,
  SelfEmploymentStatement,
  TaxFiling,
  WageTaxCertificate,
} from "@/lib/types";

const SUBMISSION_POLL_INTERVAL_MS = 3000;

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
  const [submissionJob, setSubmissionJob] = useState<EricSubmissionJob | null>(null);
  const [submissionHistory, setSubmissionHistory] = useState<EricSubmissionJob[]>([]);
  const [isDownloadingCoverSheet, setIsDownloadingCoverSheet] = useState(false);
  const [isMarkingMailed, setIsMarkingMailed] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isMountedRef = useRef(true);
  useEffect(() => {
    // Reset (not just declare) on every effect run: React's dev-mode
    // StrictMode double-invokes effects (mount -> cleanup -> mount), so
    // without resetting here, the simulated cleanup would leave this
    // false forever after the remount, silently dropping every state
    // update handleSubmit's polling loop makes afterward.
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const loadAll = useCallback(async () => {
    if (!token) return;
    const loadedFiling = await getTaxFiling(token, id);
    setFiling(loadedFiling);
    const [certs, deds, capital, rental, selfEmp, jobs] = await Promise.all([
      listWageTaxCertificates(token, loadedFiling.tax_year) as Promise<WageTaxCertificate[]>,
      listDeductions(token, loadedFiling.tax_year),
      listCapitalIncomeStatements(token, loadedFiling.tax_year),
      listRentalPropertyStatements(token, loadedFiling.tax_year),
      listSelfEmploymentStatements(token, loadedFiling.tax_year),
      listSubmissionJobs(token, id),
    ]);
    setWageCerts(certs);
    setDeductions(deds);
    setCapitalIncome(capital);
    setRentalIncome(rental);
    setSelfEmployment(selfEmp);
    setSubmissionHistory(jobs);
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
    setSubmissionJob(null);
    try {
      // Submitting only queues an EricSubmissionJob -- the separate
      // eric-submitter worker process claims and processes it against
      // the real ERiC library (see backend/app/eric_submitter/worker.py).
      // Poll until it reaches a terminal status, then refresh the filing.
      let job = await submitTaxFiling(token, id);
      if (isMountedRef.current) setSubmissionJob(job);

      while (job.status === "PENDING" || job.status === "PROCESSING") {
        await new Promise((resolve) => setTimeout(resolve, SUBMISSION_POLL_INTERVAL_MS));
        if (!isMountedRef.current) return;
        job = await getSubmissionJob(token, id);
        if (isMountedRef.current) setSubmissionJob(job);
      }

      const jobs = await listSubmissionJobs(token, id);
      if (isMountedRef.current) setSubmissionHistory(jobs);

      if (job.status === "SUCCEEDED") {
        const updated = await getTaxFiling(token, id);
        if (isMountedRef.current) setFiling(updated);
      } else if (job.status === "FAILED" && isMountedRef.current) {
        setError(job.error_message ?? "The eric-submitter worker couldn't submit this return.");
      }
    } catch (err) {
      if (isMountedRef.current) setError(err instanceof Error ? err.message : "Couldn't submit this return.");
    } finally {
      if (isMountedRef.current) setIsSubmitting(false);
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

  return (
    <div className="mx-auto max-w-6xl px-6 py-20 md:px-10 md:py-24">
      <div className="mb-12 flex items-center justify-between">
        <div>
          <Eyebrow>Steuererklärung</Eyebrow>
          <h1 className="font-display text-[28px] leading-tight font-semibold tracking-tight text-ink">
            Tax year {filing.tax_year}
          </h1>
        </div>
        <StatusStamp status={filing.status} />
      </div>

      {error && <ErrorBanner message={error} />}

      <div className="mb-12">
        <RefundAnchor amountCents={filing.estimated_refund_cents} isCalculated={isCalculated} />
      </div>

      <div className="space-y-12">
        <BentoGrid>
        <BentoTile span={2}>
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <CategoryTab category="wage" />
              <h2 className="font-display text-sm font-medium tracking-[0.08em] text-ink/70 uppercase">
                Wage income
              </h2>
            </div>
            <button
              onClick={() => router.push(`/filings/${id}/wage-income`)}
              className="border-b border-brass/40 text-sm text-brass transition-colors hover:border-brass"
            >
              + Add
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
        </BentoTile>

        <BentoTile>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-display text-sm font-medium tracking-[0.08em] text-ink/70 uppercase">
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
        </BentoTile>

        <BentoTile>
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <CategoryTab category="capital" />
              <h2 className="font-display text-sm font-medium tracking-[0.08em] text-ink/70 uppercase">
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
        </BentoTile>

        <BentoTile>
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <CategoryTab category="rental" />
              <h2 className="font-display text-sm font-medium tracking-[0.08em] text-ink/70 uppercase">
                Rental income
              </h2>
            </div>
            <button
              onClick={() => router.push(`/filings/${id}/rental-income`)}
              className="border-b border-sage/40 text-sm text-sage transition-colors hover:border-sage"
            >
              + Add
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
        </BentoTile>

        <BentoTile>
          <div className="mb-3 flex flex-wrap items-center justify-between gap-y-1.5">
            <div className="flex items-center gap-2.5">
              <CategoryTab category="self_employment" />
              <h2 className="font-display text-sm font-medium tracking-[0.08em] text-ink/70 uppercase">
                Self-employment
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
        </BentoTile>

        <BentoTile>
          <KinderfreibetragSection filing={filing} token={token} onUpdated={setFiling} />
        </BentoTile>
        </BentoGrid>

        <section>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-display text-sm font-medium tracking-[0.08em] text-ink/70 uppercase">
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
              <Card>
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
                  {filing.altersvorsorge_deduction_cents !== null &&
                    filing.altersvorsorge_deduction_cents > 0 && (
                      <LedgerLine
                        label="Altersvorsorgeaufwendungen"
                        value={formatCents(filing.altersvorsorge_deduction_cents)}
                        tone="negative"
                      />
                    )}
                  {filing.sonstige_vorsorgeaufwendungen_deduction_cents !== null &&
                    filing.sonstige_vorsorgeaufwendungen_deduction_cents > 0 && (
                      <LedgerLine
                        label="Sonstige Vorsorgeaufwendungen"
                        value={formatCents(filing.sonstige_vorsorgeaufwendungen_deduction_cents)}
                        tone="negative"
                      />
                    )}
                  {filing.aussergewoehnliche_belastungen_deduction_cents !== null &&
                    filing.aussergewoehnliche_belastungen_deduction_cents > 0 && (
                      <LedgerLine
                        label="Außergewöhnliche Belastungen"
                        value={formatCents(filing.aussergewoehnliche_belastungen_deduction_cents)}
                        tone="negative"
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
                  {filing.capital_gains_progressive_election_applied && (
                    <p className="pb-2 text-xs text-ink/40">
                      Günstigerprüfung: your capital gains were taxed at your regular income tax
                      rate instead of the flat Abgeltungsteuer, since that worked out cheaper.
                    </p>
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
                <p className="mt-4 text-xs text-ink/35">
                  This is what produced the figure in your refund anchor above.
                </p>
              </Card>
            )
          )}
        </section>

        {isCalculated && filing.status === "CALCULATED" && (
          <section className="rounded-2xl border border-brass/25 bg-brass-soft/10 p-8">
            <h2 className="font-display text-base font-semibold tracking-tight text-ink">Ready to file</h2>
            <p className="mt-2 text-sm text-ink/60">
              Pay the flat {formatCents(filing.processing_fee_cents)} fee and we&apos;ll submit
              this to the Finanzamt.
            </p>
            <Button className="mt-5" onClick={() => router.push(`/filings/${id}/pay`)}>
              Continue to payment
            </Button>
          </section>
        )}

        {["FEE_PAID", "SUBMITTED", "ACCEPTED", "REJECTED"].includes(filing.status) && (
          <section className="border-t border-ink/8 pt-8">
            <h2 className="font-display text-sm font-medium tracking-[0.08em] text-ink/70 uppercase">
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
                  {submissionJob?.status === "PROCESSING"
                    ? "The eric-submitter worker is processing this now…"
                    : submissionJob?.status === "PENDING"
                      ? "Queued — waiting for the eric-submitter worker to pick this up…"
                      : submissionHistory.some((job) => job.status === "SUCCEEDED")
                        ? "Fee paid — ready to submit your amended return."
                        : "Fee paid — ready to submit."}
                </p>
                <Button className="mt-3" onClick={handleSubmit} disabled={isSubmitting}>
                  {isSubmitting ? "Submitting…" : "Submit to the Finanzamt"}
                </Button>
              </div>
            )}
            {submissionHistory.length > 1 && (
              <div className="mt-5 border-t border-ink/10 pt-4">
                <h3 className="text-xs font-medium tracking-[0.08em] text-ink/50 uppercase">
                  Submission history
                </h3>
                <ul className="mt-2 space-y-1.5 text-sm text-ink/60">
                  {submissionHistory.map((job) => (
                    <li key={job.id} className="tabular">
                      {job.is_amendment ? "Amendment" : "Original"} — {job.status}
                      {job.transfer_ticket ? ` — ${job.transfer_ticket}` : ""}
                      {job.error_message ? ` — ${job.error_message}` : ""}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        )}

        {filing.elster_transfer_ticket && filing.submission_mode === "KOMPRIMIERT" && (
          <section className="rounded-2xl border border-brass/25 bg-brass-soft/10 p-8">
            <h2 className="font-display text-base font-semibold tracking-tight text-ink">
              Finish by mail (komprimiert)
            </h2>
            {filing.cover_sheet_mailed_at ? (
              <p className="mt-2 text-sm text-sage">
                Marked as mailed — your filing is complete once the Finanzamt receives it.
              </p>
            ) : (
              <>
                <p className="mt-2 text-sm text-ink/60">
                  This submission went out unauthenticated (no personal ELSTER certificate on
                  file yet), so it isn&apos;t legally binding until you print, sign, and mail the
                  cover sheet below to your Finanzamt.
                </p>
                <div className="mt-5 flex flex-wrap gap-3">
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
    <>
      <div className="mb-3 flex items-center gap-2.5">
        <CategoryTab category="children" />
        <h2 className="font-display text-sm font-medium tracking-[0.08em] text-ink/70 uppercase">
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
    </>
  );
}
