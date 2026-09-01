"use client";

import { useState, type FormEvent } from "react";
import { useParams, useRouter } from "next/navigation";
import { createRentalPropertyStatement, getTaxFiling } from "@/lib/api";
import { useRequireOnboarding } from "@/lib/use-require-auth";
import { eurosToCents } from "@/lib/money";
import { Button, Card, ErrorBanner, Eyebrow, Input, Label, PageHeading } from "@/components/ui";

export default function AddRentalIncomePage() {
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
      const buildingCost = String(formData.get("building_acquisition_cost") || "");
      const completionYear = String(formData.get("building_completion_year") || "");
      await createRentalPropertyStatement(token, {
        tax_year: filing.tax_year,
        property_address: String(formData.get("property_address")),
        gross_rental_income_cents: eurosToCents(String(formData.get("gross_rental_income"))),
        deductible_expenses_cents: eurosToCents(String(formData.get("deductible_expenses") || "0")),
        ...(buildingCost ? { building_acquisition_cost_cents: eurosToCents(buildingCost) } : {}),
        ...(completionYear ? { building_completion_year: Number(completionYear) } : {}),
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
    <div className="mx-auto max-w-md px-6 py-20">
      <div className="mb-10">
        <Eyebrow tone="sage">Anlage V</Eyebrow>
        <PageHeading title="Add a rental property" subtitle="Vermietung und Verpachtung." />
      </div>
      <Card>
        {error && <ErrorBanner message={error} />}
        <form onSubmit={handleSubmit} className="space-y-6">
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
              Maintenance, interest, insurance, management fees, and similar — excluding AfA
              depreciation if you fill in the building details below (we&apos;ll compute that
              automatically); include it here yourself otherwise.
            </p>
          </div>
          <div>
            <Label htmlFor="building_acquisition_cost">Building acquisition cost, € (optional)</Label>
            <Input
              id="building_acquisition_cost"
              name="building_acquisition_cost"
              type="number"
              step="0.01"
              min="0"
            />
            <p className="mt-1.5 text-xs text-ink/40">
              The building&apos;s own purchase price, excluding land — land doesn&apos;t depreciate.
            </p>
          </div>
          <div>
            <Label htmlFor="building_completion_year">Building completion year (optional)</Label>
            <Input
              id="building_completion_year"
              name="building_completion_year"
              type="number"
              min="1800"
              max="2100"
              step="1"
            />
            <p className="mt-1.5 text-xs text-ink/40">
              When the building was completed (Baujahr) — sets the AfA rate (3% from 2023, 2%
              1925–2022, 2.5% before 1925). Both fields are needed for us to compute AfA for you.
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
