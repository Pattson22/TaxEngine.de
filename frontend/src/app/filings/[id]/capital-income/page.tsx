"use client";

import { useState, type FormEvent } from "react";
import { useParams, useRouter } from "next/navigation";
import { createCapitalIncomeStatement, getTaxFiling } from "@/lib/api";
import { useRequireAuth } from "@/lib/use-require-auth";
import { eurosToCents } from "@/lib/money";
import { Button, Card, ErrorBanner, Eyebrow, Input, Label, PageHeading } from "@/components/ui";

export default function AddCapitalIncomePage() {
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
      await createCapitalIncomeStatement(token, {
        tax_year: filing.tax_year,
        institution_name: String(formData.get("institution_name")),
        gross_income_cents: eurosToCents(String(formData.get("gross_income"))),
        kapitalertragsteuer_withheld_cents: eurosToCents(
          String(formData.get("kapitalertragsteuer_withheld") || "0"),
        ),
        solidarity_surcharge_withheld_cents: eurosToCents(
          String(formData.get("solidarity_surcharge_withheld") || "0"),
        ),
        church_tax_withheld_cents: eurosToCents(String(formData.get("church_tax_withheld") || "0")),
      });
      router.push(`/filings/${id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't save this statement.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (authLoading || !token) return null;

  return (
    <div className="mx-auto max-w-md px-6 py-14">
      <Eyebrow>Anlage KAP</Eyebrow>
      <PageHeading
        title="Add capital income"
        subtitle="From your bank or broker's annual tax certificate (Steuerbescheinigung)."
      />
      <Card>
        {error && <ErrorBanner message={error} />}
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <Label htmlFor="institution_name">Bank or broker</Label>
            <Input id="institution_name" name="institution_name" required />
          </div>
          <div>
            <Label htmlFor="gross_income">Gross capital income, €</Label>
            <Input id="gross_income" name="gross_income" type="number" step="0.01" min="0" required />
          </div>
          <div>
            <Label htmlFor="kapitalertragsteuer_withheld">Kapitalertragsteuer withheld, €</Label>
            <Input
              id="kapitalertragsteuer_withheld"
              name="kapitalertragsteuer_withheld"
              type="number"
              step="0.01"
              min="0"
            />
          </div>
          <div>
            <Label htmlFor="solidarity_surcharge_withheld">Solidarity surcharge withheld, €</Label>
            <Input
              id="solidarity_surcharge_withheld"
              name="solidarity_surcharge_withheld"
              type="number"
              step="0.01"
              min="0"
            />
          </div>
          <div>
            <Label htmlFor="church_tax_withheld">Church tax withheld, €</Label>
            <Input id="church_tax_withheld" name="church_tax_withheld" type="number" step="0.01" min="0" />
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
