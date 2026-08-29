"use client";

import { useState, type FormEvent } from "react";
import { useParams, useRouter } from "next/navigation";
import { createWageTaxCertificate, getTaxFiling } from "@/lib/api";
import { useRequireAuth } from "@/lib/use-require-auth";
import { eurosToCents } from "@/lib/money";
import { Button, Card, ErrorBanner, Eyebrow, Input, Label, PageHeading } from "@/components/ui";

export default function AddWageIncomePage() {
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
      await createWageTaxCertificate(token, {
        tax_year: filing.tax_year,
        employer_name: String(formData.get("employer_name")),
        gross_wage_cents: eurosToCents(String(formData.get("gross_wage"))),
        income_tax_withheld_cents: eurosToCents(String(formData.get("income_tax_withheld") || "0")),
        solidarity_surcharge_cents: eurosToCents(String(formData.get("solidarity_surcharge") || "0")),
        church_tax_withheld_cents: eurosToCents(String(formData.get("church_tax_withheld") || "0")),
      });
      router.push(`/filings/${id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't save this employer.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (authLoading || !token) return null;

  return (
    <div className="mx-auto max-w-md px-6 py-14">
      <Eyebrow>Lohnsteuerbescheinigung</Eyebrow>
      <PageHeading title="Add an employer" subtitle="From your electronic wage tax certificate." />
      <Card>
        {error && <ErrorBanner message={error} />}
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <Label htmlFor="employer_name">Employer name</Label>
            <Input id="employer_name" name="employer_name" required />
          </div>
          <div>
            <Label htmlFor="gross_wage">Gross wage (Bruttoarbeitslohn), €</Label>
            <Input id="gross_wage" name="gross_wage" type="number" step="0.01" min="0" required />
          </div>
          <div>
            <Label htmlFor="income_tax_withheld">Income tax withheld (Lohnsteuer), €</Label>
            <Input id="income_tax_withheld" name="income_tax_withheld" type="number" step="0.01" min="0" />
          </div>
          <div>
            <Label htmlFor="solidarity_surcharge">Solidarity surcharge withheld, €</Label>
            <Input id="solidarity_surcharge" name="solidarity_surcharge" type="number" step="0.01" min="0" />
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
