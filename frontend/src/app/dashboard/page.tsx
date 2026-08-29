"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createTaxFiling, getSupportedTaxYears, listTaxFilings } from "@/lib/api";
import { useRequireAuth } from "@/lib/use-require-auth";
import { formatCents } from "@/lib/money";
import { Button, Card, ErrorBanner, Eyebrow, Label, PageHeading, Select, StatusStamp } from "@/components/ui";
import type { TaxFiling } from "@/lib/types";

export default function DashboardPage() {
  const { token, isLoading: authLoading } = useRequireAuth();
  const router = useRouter();
  const [filings, setFilings] = useState<TaxFiling[]>([]);
  const [supportedYears, setSupportedYears] = useState<number[]>([]);
  const [selectedYear, setSelectedYear] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    if (!token) return;
    Promise.all([listTaxFilings(token), getSupportedTaxYears()])
      .then(([loadedFilings, years]) => {
        setFilings(loadedFilings);
        setSupportedYears(years);
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
              className="flex w-full items-center justify-between border-b border-ink/10 py-5 text-left transition-colors hover:bg-ink/[0.03]"
            >
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
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
