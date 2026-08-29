"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createTaxFiling, listTaxFilings } from "@/lib/api";
import { useRequireAuth } from "@/lib/use-require-auth";
import { formatCents } from "@/lib/money";
import { Button, Card, ErrorBanner, PageHeading, StatusBadge } from "@/components/ui";
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
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load filings."))
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
      setError(err instanceof Error ? err.message : "Failed to create filing.");
    } finally {
      setIsCreating(false);
    }
  }

  if (authLoading || !token) return null;

  return (
    <div className="mx-auto max-w-3xl px-6 py-12">
      <div className="flex items-center justify-between">
        <PageHeading title="Your tax filings" />
        {!filings.some((f) => f.tax_year === CURRENT_TAX_YEAR) && (
          <Button onClick={handleCreateFiling} disabled={isCreating}>
            {isCreating ? "Creating…" : `Start ${CURRENT_TAX_YEAR} return`}
          </Button>
        )}
      </div>

      {error && <ErrorBanner message={error} />}

      {isLoading ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : filings.length === 0 ? (
        <Card>
          <p className="text-sm text-slate-600">
            No filings yet. Start your {CURRENT_TAX_YEAR} return to get a free refund estimate.
          </p>
        </Card>
      ) : (
        <div className="space-y-3">
          {filings.map((filing) => (
            <Card key={filing.id} className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-3">
                  <span className="font-semibold text-slate-900">Tax year {filing.tax_year}</span>
                  <StatusBadge status={filing.status} />
                </div>
                <p className="mt-1 text-sm text-slate-500">
                  {filing.estimated_refund_cents !== null
                    ? `Estimated refund: ${formatCents(filing.estimated_refund_cents)}`
                    : "Not yet calculated"}
                </p>
              </div>
              <Button variant="secondary" onClick={() => router.push(`/filings/${filing.id}`)}>
                Open
              </Button>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
