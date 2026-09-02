"use client";

import { useRef, useState, type FormEvent } from "react";
import { useParams, useRouter } from "next/navigation";
import { createWageTaxCertificate, getTaxFiling, uploadWageTaxCertificateDocument } from "@/lib/api";
import { useRequireOnboarding } from "@/lib/use-require-auth";
import { eurosToCents } from "@/lib/money";
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
  const [isUploading, setIsUploading] = useState(false);
  const [attachedFileName, setAttachedFileName] = useState<string | null>(null);
  const [sourceDocumentUrl, setSourceDocumentUrl] = useState<string | null>(null);

  const [employerName, setEmployerName] = useState("");
  const [grossWage, setGrossWage] = useState("");
  const [incomeTaxWithheld, setIncomeTaxWithheld] = useState("");
  const [solidaritySurcharge, setSolidaritySurcharge] = useState("");
  const [churchTaxWithheld, setChurchTaxWithheld] = useState("");
  const [pensionInsurance, setPensionInsurance] = useState("");
  const [healthInsurance, setHealthInsurance] = useState("");
  const [longTermCareInsurance, setLongTermCareInsurance] = useState("");
  const [unemploymentInsurance, setUnemploymentInsurance] = useState("");

  async function handleFileSelected(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file || !token) return;
    setError(null);
    setIsUploading(true);
    try {
      const result = await uploadWageTaxCertificateDocument(token, file);
      setSourceDocumentUrl(result.source_document_url);
      setAttachedFileName(file.name);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't upload that document.");
    } finally {
      setIsUploading(false);
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
        pension_insurance_employee_cents: eurosToCents(pensionInsurance || "0"),
        health_insurance_employee_cents: eurosToCents(healthInsurance || "0"),
        long_term_care_insurance_employee_cents: eurosToCents(longTermCareInsurance || "0"),
        unemployment_insurance_employee_cents: eurosToCents(unemploymentInsurance || "0"),
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
    <div className="mx-auto max-w-md px-6 py-20">
      <div className="mb-10">
        <Eyebrow>Lohnsteuerbescheinigung</Eyebrow>
        <PageHeading title="Add an employer" subtitle="From your electronic wage tax certificate." />
      </div>

      <label
        htmlFor="document-upload"
        className={`mb-6 flex cursor-pointer flex-col items-center gap-1.5 rounded-2xl border border-dashed px-6 py-8 text-center transition-colors ${
          isUploading ? "border-brass/50 bg-brass-soft/10" : "border-ink/20 hover:border-brass/50"
        }`}
      >
        <span className="font-display text-sm font-medium text-ink">
          {isUploading
            ? "Uploading…"
            : attachedFileName
              ? `Attached: ${attachedFileName}`
              : "Attach your Lohnsteuerbescheinigung"}
        </span>
        <span className="text-xs text-ink/45">
          PDF, PNG, JPEG, or Word — kept for your own records and linked to this entry. Fill in the fields below yourself.
        </span>
        <input
          ref={fileInputRef}
          id="document-upload"
          type="file"
          accept={ACCEPTED_TYPES}
          onChange={handleFileSelected}
          disabled={isUploading}
          className="hidden"
        />
      </label>

      <Card>
        {error && <ErrorBanner message={error} />}
        <form onSubmit={handleSubmit} className="space-y-6">
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
            <Label
              htmlFor="gross_wage"
              hint="Your total pay before any tax or insurance was deducted — Zeile 3 on your Lohnsteuerbescheinigung."
            >
              Gross wage (Bruttoarbeitslohn), €
            </Label>
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
            <Label
              htmlFor="income_tax_withheld"
              hint="Wage tax your employer already withheld and paid to the Finanzamt on your behalf — Zeile 4."
            >
              Income tax withheld (Lohnsteuer), €
            </Label>
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
            <Label
              htmlFor="solidarity_surcharge"
              hint="The Solidaritätszuschlag withheld from your pay — Zeile 5. Leave at 0 if none was withheld."
            >
              Solidarity surcharge withheld, €
            </Label>
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
            <Label
              htmlFor="church_tax_withheld"
              hint="Only applies if you're a registered member of a church that levies Kirchensteuer — Zeile 6. Leave blank otherwise."
            >
              Church tax withheld, €
            </Label>
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
          <div>
            <Label
              htmlFor="pension_insurance"
              hint="Your employee share of statutory pension contributions — Zeile 22a. This and the three insurance fields below are deductible as Vorsorgeaufwendungen."
            >
              Pension insurance (Rentenversicherung), €
            </Label>
            <Input
              id="pension_insurance"
              name="pension_insurance"
              type="number"
              step="0.01"
              min="0"
              value={pensionInsurance}
              onChange={(e) => setPensionInsurance(e.target.value)}
            />
          </div>
          <div>
            <Label
              htmlFor="health_insurance"
              hint="Your employee share of statutory or private health insurance contributions (basic coverage only) — Zeile 25."
            >
              Health insurance (Krankenversicherung), €
            </Label>
            <Input
              id="health_insurance"
              name="health_insurance"
              type="number"
              step="0.01"
              min="0"
              value={healthInsurance}
              onChange={(e) => setHealthInsurance(e.target.value)}
            />
          </div>
          <div>
            <Label
              htmlFor="long_term_care_insurance"
              hint="Your employee share of long-term care insurance contributions — Zeile 26."
            >
              Long-term care insurance (Pflegeversicherung), €
            </Label>
            <Input
              id="long_term_care_insurance"
              name="long_term_care_insurance"
              type="number"
              step="0.01"
              min="0"
              value={longTermCareInsurance}
              onChange={(e) => setLongTermCareInsurance(e.target.value)}
            />
          </div>
          <div>
            <Label
              htmlFor="unemployment_insurance"
              hint="Your employee share of unemployment insurance contributions — Zeile 27."
            >
              Unemployment insurance (Arbeitslosenversicherung), €
            </Label>
            <Input
              id="unemployment_insurance"
              name="unemployment_insurance"
              type="number"
              step="0.01"
              min="0"
              value={unemploymentInsurance}
              onChange={(e) => setUnemploymentInsurance(e.target.value)}
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
