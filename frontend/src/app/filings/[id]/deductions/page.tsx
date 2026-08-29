"use client";

import { useState, type FormEvent } from "react";
import { useParams, useRouter } from "next/navigation";
import { createDeduction, getTaxFiling } from "@/lib/api";
import { useRequireAuth } from "@/lib/use-require-auth";
import { eurosToCents } from "@/lib/money";
import { Button, Card, ErrorBanner, Eyebrow, Input, Label, PageHeading, Select } from "@/components/ui";
import type { DeductionCategory } from "@/lib/types";

const CATEGORIES: { value: DeductionCategory; label: string }[] = [
  { value: "COMMUTE", label: "Commute (Entfernungspauschale)" },
  { value: "HOME_OFFICE", label: "Home office (Homeoffice-Pauschale)" },
  { value: "DONATIONS", label: "Donations (Spenden)" },
  { value: "CHILDCARE", label: "Childcare costs (Kinderbetreuungskosten)" },
  { value: "HANDWERKERLEISTUNGEN", label: "Craftsperson services (§35a)" },
  { value: "WORK_EQUIPMENT", label: "Work equipment" },
  { value: "FURTHER_EDUCATION", label: "Further education" },
  { value: "DOUBLE_HOUSEHOLD", label: "Double household" },
  { value: "INSURANCE", label: "Insurance" },
  { value: "OTHER", label: "Other" },
];

// Categories the backend computes from structured `details` rather than a
// flat amount -- see backend/app/tax_engine for the algorithm behind each.
const COMPUTED_CATEGORIES = new Set<DeductionCategory>([
  "COMMUTE",
  "HOME_OFFICE",
  "DONATIONS",
  "CHILDCARE",
  "HANDWERKERLEISTUNGEN",
]);

export default function AddDeductionPage() {
  const { id } = useParams<{ id: string }>();
  const { token, isLoading: authLoading } = useRequireAuth();
  const router = useRouter();
  const [category, setCategory] = useState<DeductionCategory>("COMMUTE");
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
      const details = buildDetails(category, formData);
      await createDeduction(token, {
        tax_year: filing.tax_year,
        category,
        details,
        ...(COMPUTED_CATEGORIES.has(category)
          ? {}
          : { amount_claimed_cents: eurosToCents(String(formData.get("amount") || "0")) }),
      });
      router.push(`/filings/${id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't save this deduction.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (authLoading || !token) return null;

  return (
    <div className="mx-auto max-w-md px-6 py-14">
      <Eyebrow>Werbungskosten & Sonderausgaben</Eyebrow>
      <PageHeading title="Add a deduction" />
      <Card>
        {error && <ErrorBanner message={error} />}
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <Label htmlFor="category">Category</Label>
            <Select
              id="category"
              value={category}
              onChange={(e) => setCategory(e.target.value as DeductionCategory)}
            >
              {CATEGORIES.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </Select>
          </div>

          <CategoryFields category={category} />

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

function CategoryFields({ category }: { category: DeductionCategory }) {
  switch (category) {
    case "COMMUTE":
      return (
        <>
          <div>
            <Label htmlFor="distance_km">One-way distance (km)</Label>
            <Input id="distance_km" name="distance_km" type="number" min="0" required />
          </div>
          <div>
            <Label htmlFor="days_worked">Days worked on-site</Label>
            <Input id="days_worked" name="days_worked" type="number" min="0" required />
          </div>
        </>
      );
    case "HOME_OFFICE":
      return (
        <div>
          <Label htmlFor="days_claimed">Home office days</Label>
          <Input id="days_claimed" name="days_claimed" type="number" min="0" required />
        </div>
      );
    case "DONATIONS":
      return (
        <div>
          <Label htmlFor="amount_donated">Amount donated, €</Label>
          <Input id="amount_donated" name="amount_donated" type="number" step="0.01" min="0" required />
        </div>
      );
    case "CHILDCARE":
      return (
        <>
          <div>
            <Label htmlFor="total_costs">Total childcare costs, €</Label>
            <Input id="total_costs" name="total_costs" type="number" step="0.01" min="0" required />
          </div>
          <div>
            <Label htmlFor="number_of_children">Number of children</Label>
            <Input id="number_of_children" name="number_of_children" type="number" min="1" required />
          </div>
        </>
      );
    case "HANDWERKERLEISTUNGEN":
      return (
        <div>
          <Label htmlFor="labor_cost">Labor cost (excl. materials), €</Label>
          <Input id="labor_cost" name="labor_cost" type="number" step="0.01" min="0" required />
        </div>
      );
    default:
      return (
        <div>
          <Label htmlFor="amount">Amount, €</Label>
          <Input id="amount" name="amount" type="number" step="0.01" min="0" required />
        </div>
      );
  }
}

function buildDetails(category: DeductionCategory, formData: FormData): Record<string, unknown> {
  switch (category) {
    case "COMMUTE":
      return {
        distance_km: Number(formData.get("distance_km")),
        days_worked: Number(formData.get("days_worked")),
      };
    case "HOME_OFFICE":
      return { days_claimed: Number(formData.get("days_claimed")) };
    case "DONATIONS":
      return { amount_donated_cents: eurosToCents(String(formData.get("amount_donated"))) };
    case "CHILDCARE":
      return {
        total_costs_cents: eurosToCents(String(formData.get("total_costs"))),
        number_of_children: Number(formData.get("number_of_children")),
      };
    case "HANDWERKERLEISTUNGEN":
      return { labor_cost_cents: eurosToCents(String(formData.get("labor_cost"))) };
    default:
      return {};
  }
}
