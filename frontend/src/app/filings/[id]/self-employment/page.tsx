"use client";

import { useState, type FormEvent } from "react";
import { useParams, useRouter } from "next/navigation";
import { createSelfEmploymentStatement, getTaxFiling } from "@/lib/api";
import { useRequireOnboarding } from "@/lib/use-require-auth";
import { eurosToCents } from "@/lib/money";
import { Button, Card, ErrorBanner, Eyebrow, Input, Label, PageHeading } from "@/components/ui";

export default function AddSelfEmploymentPage() {
  const { id } = useParams<{ id: string }>();
  const { token, isLoading: authLoading } = useRequireOnboarding();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    setError(null);
    setIsSubmitting(true);

    const formData = new FormData(event.currentTarget);
    try {
      const filing = await getTaxFiling(token, id);
      await createSelfEmploymentStatement(token, {
        tax_year: filing.tax_year,
        business_name: String(formData.get("business_name")),
        gross_revenue_cents: eurosToCents(String(formData.get("gross_revenue"))),
        deductible_expenses_cents: eurosToCents(String(formData.get("deductible_expenses") || "0")),
      });
      router.push(`/filings/${id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't save this business.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (authLoading || !token) return null;

  return (
    <div className="mx-auto max-w-md px-6 py-20">
      <div className="mb-10">
        <Eyebrow tone="terracotta">Anlage S / EÜR</Eyebrow>
        <PageHeading title="Add self-employment income" subtitle="Freelance or business income." />
      </div>
      <Card>
        {error && <ErrorBanner message={error} />}
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <Label htmlFor="business_name">Business or freelance activity</Label>
            <Input id="business_name" name="business_name" required />
          </div>
          <div>
            <Label htmlFor="gross_revenue">Gross revenue, €</Label>
            <Input id="gross_revenue" name="gross_revenue" type="number" step="0.01" min="0" required />
          </div>
          <div>
            <Label htmlFor="deductible_expenses">Deductible business expenses, €</Label>
            <Input id="deductible_expenses" name="deductible_expenses" type="number" step="0.01" min="0" />
            <p className="mt-1.5 text-xs text-ink/40">
              Gewerbesteuer (trade tax) isn&apos;t modeled yet — this understates the total tax due
              for Gewerbebetrieb activity. Correct for most freelance/liberal professions
              (freiberuflich), which aren&apos;t subject to it.
            </p>
          </div>
          <div className="flex gap-3 pt-2">
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Saving…" : "Save"}
            </Button>
            <Button type="button" variant="secondary" onClick={() => router.push(`/filings/${id}`)}>
              Cancel
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
