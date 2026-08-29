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
    <div className="mx-auto max-w-3xl px-6 py-14">
      <div className="flex items-end justify-between">
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
        <div className="border-t border-ink/10">
          {filings.map((filing) => (
            <button
              key={filing.id}
              onClick={() => router.push(`/filings/${filing.id}`)}
              className="flex w-full flex-col gap-2.5 border-b border-ink/10 py-5 text-left transition-colors hover:bg-ink/[0.03]"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <span className="font-display text-lg font-medium text-ink">{filing.tax_year}</span>
                  <StatusStamp status={filing.status} />
                </div>
                <span
                  className={`tabular text-sm ${
                    filing.estimated_refund_cents === null
                      ? "text-ink/35"
                      : filing.estimated_refund_cents >= 0
                        ? "text-sage"
                        : "text-clay"
                  }`}
                >
                  {filing.estimated_refund_cents !== null
                    ? formatCents(filing.estimated_refund_cents)
                    : "Not yet calculated"}
                </span>
              </div>
              {categoriesByYear[filing.tax_year] && categoriesByYear[filing.tax_year].size > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {[...categoriesByYear[filing.tax_year]].map((category) => (
                    <CategoryTab key={category} category={category} />
                  ))}
                </div>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
