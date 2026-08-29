"use client";

import { useState, type FormEvent } from "react";
import { useParams, useRouter } from "next/navigation";
import { createRentalPropertyStatement, getTaxFiling } from "@/lib/api";
import { useRequireAuth } from "@/lib/use-require-auth";
import { eurosToCents } from "@/lib/money";
import { Button, Card, ErrorBanner, Eyebrow, Input, Label, PageHeading } from "@/components/ui";

export default function AddRentalIncomePage() {
  const { id } = useParams<{ id: string }>();
  const { token, isLoading: authLoading } = useRequireAuth();
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
      await createRentalPropertyStatement(token, {
        tax_year: filing.tax_year,
        property_address: String(formData.get("property_address")),
        gross_rental_income_cents: eurosToCents(String(formData.get("gross_rental_income"))),
        deductible_expenses_cents: eurosToCents(String(formData.get("deductible_expenses") || "0")),
      });
      router.push(`/filings/${id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't save this property.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (authLoading || !token) return null;

  return (
    <div className="mx-auto max-w-md px-6 py-14">
      <Eyebrow>Anlage V</Eyebrow>
      <PageHeading title="Add a rental property" subtitle="Vermietung und Verpachtung." />
      <Card>
        {error && <ErrorBanner message={error} />}
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <Label htmlFor="property_address">Property address</Label>
            <Input id="property_address" name="property_address" required />
          </div>
          <div>
            <Label htmlFor="gross_rental_income">Gross rental income, €</Label>
            <Input
              id="gross_rental_income"
              name="gross_rental_income"
              type="number"
              step="0.01"
              min="0"
              required
            />
          </div>
          <div>
            <Label htmlFor="deductible_expenses">Deductible expenses, €</Label>
            <Input id="deductible_expenses" name="deductible_expenses" type="number" step="0.01" min="0" />
            <p className="mt-1.5 text-xs text-ink/40">
              Maintenance, interest, insurance, management fees, and similar — not the AfA
              depreciation schedule, which this MVP doesn&apos;t compute automatically yet.
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
