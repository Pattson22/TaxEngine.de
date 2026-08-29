"use client";

import { useRef, useState, type FormEvent } from "react";
import { useParams, useRouter } from "next/navigation";
import { createWageTaxCertificate, extractWageTaxCertificate, getTaxFiling } from "@/lib/api";
import { useRequireOnboarding } from "@/lib/use-require-auth";
import { centsToEuroInputValue, eurosToCents } from "@/lib/money";
import { Button, Card, ErrorBanner, Eyebrow, Input, Label, PageHeading } from "@/components/ui";

const ACCEPTED_TYPES =
  "application/pdf,image/png,image/jpeg,application/vnd.openxmlformats-officedocument.wordprocessingml.document";

export default function AddWageIncomePage() {
  const { id } = useParams<{ id: string }>();
  const { token, isLoading: authLoading } = useRequireOnboarding();
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isReading, setIsReading] = useState(false);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [sourceDocumentUrl, setSourceDocumentUrl] = useState<string | null>(null);

  const [employerName, setEmployerName] = useState("");
  const [grossWage, setGrossWage] = useState("");
  const [incomeTaxWithheld, setIncomeTaxWithheld] = useState("");
  const [solidaritySurcharge, setSolidaritySurcharge] = useState("");
  const [churchTaxWithheld, setChurchTaxWithheld] = useState("");

  async function handleFileSelected(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file || !token) return;
    setError(null);
    setWarnings([]);
    setIsReading(true);
    try {
      const extraction = await extractWageTaxCertificate(token, file);
      if (extraction.employer_name) setEmployerName(extraction.employer_name);
      if (extraction.gross_wage_cents !== null) setGrossWage(centsToEuroInputValue(extraction.gross_wage_cents));
      if (extraction.income_tax_withheld_cents !== null)
        setIncomeTaxWithheld(centsToEuroInputValue(extraction.income_tax_withheld_cents));
      if (extraction.solidarity_surcharge_cents !== null)
        setSolidaritySurcharge(centsToEuroInputValue(extraction.solidarity_surcharge_cents));
      if (extraction.church_tax_withheld_cents !== null)
        setChurchTaxWithheld(centsToEuroInputValue(extraction.church_tax_withheld_cents));
      setWarnings(extraction.warnings);
      setSourceDocumentUrl(extraction.source_document_url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't read that document.");
    } finally {
      setIsReading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    setError(null);
    setIsSubmitting(true);

    try {
      const filing = await getTaxFiling(token, id);
      await createWageTaxCertificate(token, {
        tax_year: filing.tax_year,
        employer_name: employerName,
        gross_wage_cents: eurosToCents(grossWage),
        income_tax_withheld_cents: eurosToCents(incomeTaxWithheld || "0"),
        solidarity_surcharge_cents: eurosToCents(solidaritySurcharge || "0"),
        church_tax_withheld_cents: eurosToCents(churchTaxWithheld || "0"),
        ...(sourceDocumentUrl ? { source_document_url: sourceDocumentUrl } : {}),
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

      <label
        htmlFor="document-upload"
        className={`mb-6 flex cursor-pointer flex-col items-center gap-1.5 border border-dashed px-6 py-8 text-center transition-colors ${
          isReading ? "border-brass/50 bg-brass-soft/10" : "border-ink/20 hover:border-brass/50"
        }`}
      >
        <span className="font-display text-sm font-medium text-ink">
          {isReading ? "Reading your document…" : "Upload your Lohnsteuerbescheinigung"}
        </span>
        <span className="text-xs text-ink/45">
          PDF, PNG, JPEG, or Word — we&apos;ll read it and fill in the fields below to check.
        </span>
        <input
          ref={fileInputRef}
          id="document-upload"
          type="file"
          accept={ACCEPTED_TYPES}
          onChange={handleFileSelected}
          disabled={isReading}
          className="hidden"
        />
      </label>

      {warnings.length > 0 && (
        <div className="mb-5 border-l-2 border-brass bg-brass-soft/15 px-4 py-3 text-sm text-ink/70">
          <p className="mb-1 font-medium text-ink">Couldn&apos;t read everything confidently:</p>
          <ul className="list-inside list-disc space-y-0.5">
            {warnings.map((warning, i) => (
              <li key={i}>{warning}</li>
            ))}
          </ul>
        </div>
      )}

      <Card>
        {error && <ErrorBanner message={error} />}
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <Label htmlFor="employer_name">Employer name</Label>
            <Input
              id="employer_name"
              name="employer_name"
              value={employerName}
              onChange={(e) => setEmployerName(e.target.value)}
              required
            />
          </div>
          <div>
            <Label htmlFor="gross_wage">Gross wage (Bruttoarbeitslohn), €</Label>
            <Input
              id="gross_wage"
              name="gross_wage"
              type="number"
              step="0.01"
              min="0"
              value={grossWage}
              onChange={(e) => setGrossWage(e.target.value)}
              required
            />
          </div>
          <div>
            <Label htmlFor="income_tax_withheld">Income tax withheld (Lohnsteuer), €</Label>
            <Input
              id="income_tax_withheld"
              name="income_tax_withheld"
              type="number"
              step="0.01"
              min="0"
              value={incomeTaxWithheld}
              onChange={(e) => setIncomeTaxWithheld(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="solidarity_surcharge">Solidarity surcharge withheld, €</Label>
            <Input
              id="solidarity_surcharge"
              name="solidarity_surcharge"
              type="number"
              step="0.01"
              min="0"
              value={solidaritySurcharge}
              onChange={(e) => setSolidaritySurcharge(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="church_tax_withheld">Church tax withheld, €</Label>
            <Input
              id="church_tax_withheld"
              name="church_tax_withheld"
              type="number"
              step="0.01"
              min="0"
              value={churchTaxWithheld}
              onChange={(e) => setChurchTaxWithheld(e.target.value)}
            />
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
