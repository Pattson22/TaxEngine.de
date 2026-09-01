"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  createTaxFiling,
  getSupportedTaxYears,
  listCapitalIncomeStatements,
  listRentalPropertyStatements,
  listSelfEmploymentStatements,
  listTaxFilings,
  listWageTaxCertificates,
} from "@/lib/api";
import { useRequireOnboarding } from "@/lib/use-require-auth";
import { formatCents } from "@/lib/money";
import {
  Button,
  Card,
  CategoryTab,
  ErrorBanner,
  Eyebrow,
  Label,
  PageHeading,
  Select,
  StatusStamp,
} from "@/components/ui";
import type { TaxFiling } from "@/lib/types";

type Category = "wage" | "capital" | "rental" | "self_employment" | "children";

export default function DashboardPage() {
  const { token, isLoading: authLoading } = useRequireOnboarding();
  const router = useRouter();
  const [filings, setFilings] = useState<TaxFiling[]>([]);
  const [supportedYears, setSupportedYears] = useState<number[]>([]);
  const [selectedYear, setSelectedYear] = useState<number | null>(null);
  const [categoriesByYear, setCategoriesByYear] = useState<Record<number, Set<Category>>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    if (!token) return;
    Promise.all([
      listTaxFilings(token),
      getSupportedTaxYears(),
      listWageTaxCertificates(token),
      listCapitalIncomeStatements(token),
      listRentalPropertyStatements(token),
      listSelfEmploymentStatements(token),
    ])
      .then(([loadedFilings, years, wage, capital, rental, selfEmployment]) => {
        setFilings(loadedFilings);
        setSupportedYears(years);

        const byYear: Record<number, Set<Category>> = {};
        const mark = (year: number, category: Category) => {
          (byYear[year] ??= new Set()).add(category);
        };
        wage.forEach((c) => mark(c.tax_year, "wage"));
        capital.forEach((c) => mark(c.tax_year, "capital"));
        rental.forEach((r) => mark(r.tax_year, "rental"));
        selfEmployment.forEach((s) => mark(s.tax_year, "self_employment"));
        loadedFilings.forEach((f) => {
          if (f.number_of_children > 0) mark(f.tax_year, "children");
        });
        setCategoriesByYear(byYear);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Couldn't load your returns."))
      .finally(() => setIsLoading(false));
  }, [token]);

  // Years the filer can still request -- supported by the calculation
  // engine and not already started, most recent first.
  const requestableYears = supportedYears
    .filter((year) => !filings.some((f) => f.tax_year === year))
    .sort((a, b) => b - a);
  const yearToCreate = selectedYear ?? requestableYears[0];

  async function handleCreateFiling() {
    if (!token || yearToCreate === undefined) return;
    setIsCreating(true);
    setError(null);
    try {
      const filing = await createTaxFiling(token, yearToCreate);
      router.push(`/filings/${filing.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't start your return.");
    } finally {
      setIsCreating(false);
    }
  }

  if (authLoading || !token) return null;

  return (
    <div className="mx-auto max-w-5xl px-6 py-20 md:px-10 md:py-24">
      <div className="mb-12 flex items-end justify-between">
        <div>
          <Eyebrow>Your account</Eyebrow>
          <PageHeading title="Your returns" />
        </div>
        {requestableYears.length > 0 && (
          <div className="mb-8 flex items-end gap-3">
            <div>
              <Label htmlFor="start-year">Tax year</Label>
              <Select
                id="start-year"
                value={yearToCreate}
                onChange={(e) => setSelectedYear(Number(e.target.value))}
                className="w-24"
              >
                {requestableYears.map((year) => (
                  <option key={year} value={year}>
                    {year}
                  </option>
                ))}
              </Select>
            </div>
            <Button onClick={handleCreateFiling} disabled={isCreating}>
              {isCreating ? "Starting…" : "Start return"}
            </Button>
          </div>
        )}
      </div>

      {error && <ErrorBanner message={error} />}

      {isLoading ? (
        <p className="text-sm text-ink/40">Loading…</p>
      ) : filings.length === 0 ? (
        <Card className="border-dashed">
          <p className="text-sm text-ink/60">
            Nothing here yet. Start a return above to see what you get back — it&apos;s free
            until you file.
          </p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          {filings.map((filing) => {
            const hasRefund = filing.estimated_refund_cents !== null;
            const refundIsPositive = hasRefund && filing.estimated_refund_cents! >= 0;
            return (
              <button
                key={filing.id}
                onClick={() => router.push(`/filings/${filing.id}`)}
                className="group rounded-2xl border border-ink/6 bg-paper p-8 text-left shadow-[0_1px_2px_rgba(20,23,42,0.04),0_12px_32px_-16px_rgba(20,23,42,0.12)] transition-shadow hover:shadow-[0_1px_2px_rgba(20,23,42,0.06),0_16px_40px_-16px_rgba(20,23,42,0.18)]"
              >
                <div className="flex items-center justify-between">
                  <span className="font-display text-lg font-semibold tracking-tight text-ink">
                    {filing.tax_year}
                  </span>
                  <StatusStamp status={filing.status} />
                </div>
                <p
                  className={`tabular mt-6 font-display text-3xl font-semibold tracking-tight ${
                    !hasRefund ? "text-ink/20" : refundIsPositive ? "text-sage" : "text-clay"
                  }`}
                >
                  {hasRefund ? formatCents(Math.abs(filing.estimated_refund_cents!)) : "—,—— €"}
                </p>
                <p className="mt-1 text-xs text-ink/35">
                  {hasRefund ? (refundIsPositive ? "Estimated refund" : "You'd owe") : "Not yet calculated"}
                </p>
                {categoriesByYear[filing.tax_year] && categoriesByYear[filing.tax_year].size > 0 && (
                  <div className="mt-5 flex flex-wrap gap-1.5">
                    {[...categoriesByYear[filing.tax_year]].map((category) => (
                      <CategoryTab key={category} category={category} />
                    ))}
                  </div>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
