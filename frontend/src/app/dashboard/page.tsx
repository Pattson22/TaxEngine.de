"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createTaxFiling, listTaxFilings } from "@/lib/api";
import { useRequireAuth } from "@/lib/use-require-auth";
import { formatCents } from "@/lib/money";
import { Button, Card, ErrorBanner, Eyebrow, PageHeading, StatusStamp } from "@/components/ui";
import type { TaxFiling } from "@/lib/types";

const CURRENT_TAX_YEAR = 2024; // only tax_year=2024 has reviewed backend constants right now

export default function DashboardPage() {
  const { token, isLoading: authLoading } = useRequireAuth();
  const router = useRouter();
  const [filings, setFilings] = useState<TaxFiling[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    if (!token) return;
    listTaxFilings(token)
      .then(setFilings)
      .catch((err) => setError(err instanceof Error ? err.message : "Couldn't load your returns."))
      .finally(() => setIsLoading(false));
  }, [token]);

  async function handleCreateFiling() {
    if (!token) return;
    setIsCreating(true);
    setError(null);
    try {
      const filing = await createTaxFiling(token, CURRENT_TAX_YEAR);
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
        {!filings.some((f) => f.tax_year === CURRENT_TAX_YEAR) && (
          <Button onClick={handleCreateFiling} disabled={isCreating} className="mb-8">
            {isCreating ? "Starting…" : `Start ${CURRENT_TAX_YEAR}`}
          </Button>
        )}
      </div>

      {error && <ErrorBanner message={error} />}

      {isLoading ? (
        <p className="text-sm text-ink/40">Loading…</p>
      ) : filings.length === 0 ? (
        <Card className="border-dashed">
          <p className="text-sm text-ink/60">
            Nothing here yet. Start your {CURRENT_TAX_YEAR} return to see what you get back —
            it&apos;s free until you file.
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
