"use client";

import { useState, type FormEvent } from "react";
import { updateCurrentUser } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { useRequireAuth } from "@/lib/use-require-auth";
import { Button, Card, ErrorBanner, Eyebrow, Input, Label, PageHeading, Select } from "@/components/ui";
import type { ChurchTaxType, FederalState, TaxClass } from "@/lib/types";

const FEDERAL_STATES: FederalState[] = [
  "BADEN_WUERTTEMBERG",
  "BAYERN",
  "BERLIN",
  "BRANDENBURG",
  "BREMEN",
  "HAMBURG",
  "HESSEN",
  "MECKLENBURG_VORPOMMERN",
  "NIEDERSACHSEN",
  "NORDRHEIN_WESTFALEN",
  "RHEINLAND_PFALZ",
  "SAARLAND",
  "SACHSEN",
  "SACHSEN_ANHALT",
  "SCHLESWIG_HOLSTEIN",
  "THUERINGEN",
];

const TAX_CLASSES: TaxClass[] = ["I", "II", "III", "IV", "V", "VI"];

const CHURCH_TAX_TYPES: { value: ChurchTaxType; label: string }[] = [
  { value: "NONE", label: "None" },
  { value: "ROEMISCH_KATHOLISCH", label: "Roman Catholic (röm.-kath.)" },
  { value: "EVANGELISCH", label: "Protestant (evangelisch)" },
  { value: "OTHER", label: "Other" },
];

export default function ProfilePage() {
  const { token, isLoading: authLoading } = useRequireAuth();
  const { user, refreshUser } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<number | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  if (authLoading || !token || !user) {
    return <div className="mx-auto max-w-md px-6 py-14 text-sm text-ink/40">Loading…</div>;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSavedAt(null);
    setIsSaving(true);

    const formData = new FormData(event.currentTarget);
    const steuerId = String(formData.get("tax_identification_number") ?? "").trim();
    const dateOfBirth = String(formData.get("date_of_birth") ?? "").trim();
    const street = String(formData.get("street") ?? "").trim();
    const houseNumber = String(formData.get("house_number") ?? "").trim();
    const postalCode = String(formData.get("postal_code") ?? "").trim();
    const city = String(formData.get("city") ?? "").trim();
    const steuernummer = String(formData.get("steuernummer") ?? "").trim();

    try {
      await updateCurrentUser(token as string, {
        first_name: String(formData.get("first_name")),
        last_name: String(formData.get("last_name")),
        residence_state: String(formData.get("residence_state")) as FederalState,
        tax_class: String(formData.get("tax_class")) as TaxClass,
        church_tax_type: String(formData.get("church_tax_type")) as ChurchTaxType,
        is_joint_assessment: formData.get("is_joint_assessment") === "on",
        tax_identification_number: steuerId === "" ? null : steuerId,
        date_of_birth: dateOfBirth === "" ? null : dateOfBirth,
        street: street === "" ? null : street,
        house_number: houseNumber === "" ? null : houseNumber,
        postal_code: postalCode === "" ? null : postalCode,
        city: city === "" ? null : city,
        steuernummer: steuernummer === "" ? null : steuernummer,
      });
      await refreshUser();
      setSavedAt(Date.now());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't save your details.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-md px-6 py-20">
      <div className="mb-10">
        <Eyebrow>Deine Angaben — your details</Eyebrow>
        <PageHeading
          title="Personal information"
          subtitle="What the Finanzamt needs to know you by — kept on file for every return you file."
        />
      </div>
      <Card>
        {error && <ErrorBanner message={error} />}
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <Label htmlFor="first_name">First name</Label>
              <Input id="first_name" name="first_name" defaultValue={user.first_name} required />
            </div>
            <div>
              <Label htmlFor="last_name">Last name</Label>
              <Input id="last_name" name="last_name" defaultValue={user.last_name} required />
            </div>
          </div>

          <div>
            <Label htmlFor="email">Email</Label>
            <Input id="email" value={user.email} disabled className="disabled:text-ink/40" />
          </div>

          <div>
            <Label htmlFor="tax_identification_number">Steuer-ID</Label>
            <Input
              id="tax_identification_number"
              name="tax_identification_number"
              defaultValue={user.tax_identification_number ?? ""}
              placeholder="11 digits"
              pattern="\d{11}"
              title="Your Steuer-ID is 11 digits."
              inputMode="numeric"
            />
            <p className="mt-1.5 text-xs text-ink/40">
              Required before a return can be submitted to the Finanzamt. Find it on any prior
              tax assessment or your Lohnsteuerbescheinigung.
            </p>
          </div>

          <div>
            <Label htmlFor="date_of_birth">Date of birth</Label>
            <Input
              id="date_of_birth"
              name="date_of_birth"
              type="date"
              defaultValue={user.date_of_birth ?? ""}
            />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-[1fr_auto]">
            <div>
              <Label htmlFor="street">Street</Label>
              <Input id="street" name="street" defaultValue={user.street ?? ""} />
            </div>
            <div>
              <Label htmlFor="house_number">No.</Label>
              <Input
                id="house_number"
                name="house_number"
                defaultValue={user.house_number ?? ""}
                className="sm:w-20"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-[auto_1fr]">
            <div>
              <Label htmlFor="postal_code">Postal code</Label>
              <Input
                id="postal_code"
                name="postal_code"
                defaultValue={user.postal_code ?? ""}
                pattern="\d{5}"
                title="5 digits."
                inputMode="numeric"
                className="sm:w-24"
              />
            </div>
            <div>
              <Label htmlFor="city">City</Label>
              <Input id="city" name="city" defaultValue={user.city ?? ""} />
            </div>
          </div>

          <div>
            <Label htmlFor="steuernummer">Steuernummer</Label>
            <Input id="steuernummer" name="steuernummer" defaultValue={user.steuernummer ?? ""} />
            <p className="mt-1.5 text-xs text-ink/40">
              Issued by your local Finanzamt — different from your Steuer-ID above.
            </p>
          </div>

          <div>
            <Label htmlFor="residence_state">State (Bundesland)</Label>
            <Select id="residence_state" name="residence_state" defaultValue={user.residence_state} required>
              {FEDERAL_STATES.map((state) => (
                <option key={state} value={state}>
                  {state.replaceAll("_", " ")}
                </option>
              ))}
            </Select>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <Label htmlFor="tax_class">Tax class (Steuerklasse)</Label>
              <Select id="tax_class" name="tax_class" defaultValue={user.tax_class} required>
                {TAX_CLASSES.map((taxClass) => (
                  <option key={taxClass} value={taxClass}>
                    {taxClass}
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <Label htmlFor="church_tax_type">Church tax (Kirchensteuer)</Label>
              <Select id="church_tax_type" name="church_tax_type" defaultValue={user.church_tax_type} required>
                {CHURCH_TAX_TYPES.map(({ value, label }) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </Select>
            </div>
          </div>

          <label className="flex items-start gap-2.5 pt-1 text-sm text-ink/60">
            <input
              type="checkbox"
              name="is_joint_assessment"
              defaultChecked={user.is_joint_assessment}
              className="mt-0.5 accent-brass"
            />
            I&apos;m filing jointly with my spouse (Zusammenveranlagung)
          </label>

          <div className="flex items-center gap-4 pt-2">
            <Button type="submit" disabled={isSaving}>
              {isSaving ? "Saving…" : "Save changes"}
            </Button>
            {savedAt && <span className="text-sm text-sage">Saved.</span>}
          </div>
        </form>
      </Card>
    </div>
  );
}
