"use client";

import { useState, type FormEvent } from "react";
import { useParams, useRouter } from "next/navigation";
import { createDeduction, getTaxFiling } from "@/lib/api";
import { useRequireOnboarding } from "@/lib/use-require-auth";
import { eurosToCents } from "@/lib/money";
import { Button, Card, ErrorBanner, Eyebrow, Input, Label, PageHeading, Select } from "@/components/ui";
import { InfoTrigger, SlideOver } from "@/components/slide-over";
import type { DeductionCategory } from "@/lib/types";

const LEGAL_EXPLANATIONS: Partial<Record<DeductionCategory, { title: string; body: string[] }>> = {
  COMMUTE: {
    title: "Entfernungspauschale",
    body: [
      "§9 Abs. 1 Satz 3 Nr. 4 EStG — the commuter allowance applies per working day, per one-way kilometer between home and your first place of work (erste Tätigkeitsstätte), regardless of how you actually travel.",
      "€0.30 per kilometer for the first 20 km, then €0.38 for every kilometer beyond that.",
      "The Finanzamt automatically compares this to your Arbeitnehmer-Pauschbetrag (€1,230) and uses whichever documented total is higher.",
    ],
  },
  HOME_OFFICE: {
    title: "Homeoffice-Pauschale",
    body: [
      "§4 Abs. 5 Satz 1 Nr. 6c EStG — a flat daily allowance for days worked mainly from home, no separate room or receipts required.",
      "€6 per day, up to 210 days a year (a maximum of €1,260) — the post-2023 rate this project uses.",
      "You can combine this with the commuter allowance on a different day, but not for the same calendar day.",
    ],
  },
};

function LabelWithInfo({
  htmlFor,
  children,
  onInfoClick,
}: {
  htmlFor: string;
  children: string;
  onInfoClick: () => void;
}) {
  return (
    <label
      htmlFor={htmlFor}
      className="mb-2.5 flex items-center text-[11px] font-medium tracking-[0.08em] text-ink/50 uppercase"
    >
      {children}
      <InfoTrigger onClick={onInfoClick} label={`More about ${children}`} />
    </label>
  );
}

const CATEGORIES: { value: DeductionCategory; label: string }[] = [
  { value: "COMMUTE", label: "Commute (Entfernungspauschale)" },
  { value: "HOME_OFFICE", label: "Home office (Homeoffice-Pauschale)" },
  { value: "DONATIONS", label: "Donations (Spenden)" },
  { value: "CHILDCARE", label: "Childcare costs (Kinderbetreuungskosten)" },
  { value: "HANDWERKERLEISTUNGEN", label: "Craftsperson services (§35a)" },
  { value: "AUSSERGEWOEHNLICHE_BELASTUNG", label: "Extraordinary burdens (außergewöhnliche Belastungen)" },
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
  const { token, isLoading: authLoading } = useRequireOnboarding();
  const router = useRouter();
  const [category, setCategory] = useState<DeductionCategory>("COMMUTE");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [openInfo, setOpenInfo] = useState<DeductionCategory | null>(null);
  const activeExplanation = openInfo ? LEGAL_EXPLANATIONS[openInfo] : null;

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
    <div className="mx-auto max-w-md px-6 py-20">
      <Eyebrow>Werbungskosten & Sonderausgaben</Eyebrow>
      <PageHeading title="Add a deduction" />
      <Card>
        {error && <ErrorBanner message={error} />}
        <form onSubmit={handleSubmit} className="space-y-8">
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

          <CategoryFields category={category} onInfoClick={setOpenInfo} />

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

      <SlideOver open={openInfo !== null} onClose={() => setOpenInfo(null)} title={activeExplanation?.title ?? ""}>
        {activeExplanation?.body.map((paragraph, i) => <p key={i}>{paragraph}</p>)}
      </SlideOver>
    </div>
  );
}

function CategoryFields({
  category,
  onInfoClick,
}: {
  category: DeductionCategory;
  onInfoClick: (category: DeductionCategory) => void;
}) {
  switch (category) {
    case "COMMUTE":
      return (
        <>
          <div>
            <LabelWithInfo htmlFor="distance_km" onInfoClick={() => onInfoClick("COMMUTE")}>
              One-way distance (km)
            </LabelWithInfo>
            <Input id="distance_km" name="distance_km" type="number" min="0" required />
          </div>
          <div>
            <Label
              htmlFor="days_worked"
              hint="How many days during the tax year you actually commuted to your first place of work — not vacation, sick, or home-office days."
            >
              Days worked on-site
            </Label>
            <Input id="days_worked" name="days_worked" type="number" min="0" required />
          </div>
        </>
      );
    case "HOME_OFFICE":
      return (
        <div>
          <LabelWithInfo htmlFor="days_claimed" onInfoClick={() => onInfoClick("HOME_OFFICE")}>
            Home office days
          </LabelWithInfo>
          <Input id="days_claimed" name="days_claimed" type="number" min="0" required />
        </div>
      );
    case "DONATIONS":
      return (
        <div>
          <Label
            htmlFor="amount_donated"
            hint="Total given during the tax year to a registered charity or nonprofit (gemeinnützige Organisation). Keep the donation receipt (Zuwendungsbestätigung)."
          >
            Amount donated, €
          </Label>
          <Input id="amount_donated" name="amount_donated" type="number" step="0.01" min="0" required />
        </div>
      );
    case "CHILDCARE":
      return (
        <>
          <div>
            <Label
              htmlFor="total_costs"
              hint="What you paid during the year for childcare (Kita, Tagesmutter, etc.) for children under 14. Two-thirds is deductible, up to €4,000 per child."
            >
              Total childcare costs, €
            </Label>
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
          <Label
            htmlFor="labor_cost"
            hint="Labor cost only, excluding materials — 20% is credited directly against your tax, up to €1,200/year. Must be paid by bank transfer, not cash, to qualify."
          >
            Labor cost (excl. materials), €
          </Label>
          <Input id="labor_cost" name="labor_cost" type="number" step="0.01" min="0" required />
        </div>
      );
    default:
      return (
        <div>
          <Label
            htmlFor="amount"
            hint="The total amount you're claiming for this category during the tax year."
          >
            Amount, €
          </Label>
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
