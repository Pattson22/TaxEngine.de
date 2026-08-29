"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { register } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Button, Card, ErrorBanner, Eyebrow, Input, Label, PageHeading, Select } from "@/components/ui";
import type { FederalState } from "@/lib/types";

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

export default function RegisterPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    const formData = new FormData(event.currentTarget);
    try {
      const { access_token } = await register({
        email: String(formData.get("email")),
        password: String(formData.get("password")),
        first_name: String(formData.get("first_name")),
        last_name: String(formData.get("last_name")),
        residence_state: String(formData.get("residence_state")),
        is_joint_assessment: formData.get("is_joint_assessment") === "on",
      });
      await login(access_token);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-md px-6 py-16">
      <Eyebrow>Neu hier — new account</Eyebrow>
      <PageHeading title="Set up your return" subtitle="Free to estimate. Pay only when you file." />
      <Card>
        {error && <ErrorBanner message={error} />}
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <Label htmlFor="first_name">First name</Label>
              <Input id="first_name" name="first_name" required />
            </div>
            <div>
              <Label htmlFor="last_name">Last name</Label>
              <Input id="last_name" name="last_name" required />
            </div>
          </div>
          <div>
            <Label htmlFor="email">Email</Label>
            <Input id="email" name="email" type="email" required />
          </div>
          <div>
            <Label htmlFor="password">Password</Label>
            <Input id="password" name="password" type="password" minLength={12} required />
            <p className="mt-1.5 text-xs text-ink/40">At least 12 characters.</p>
          </div>
          <div>
            <Label htmlFor="residence_state">State (Bundesland)</Label>
            <Select id="residence_state" name="residence_state" required defaultValue="">
              <option value="" disabled>
                Where do you live?
              </option>
              {FEDERAL_STATES.map((state) => (
                <option key={state} value={state}>
                  {state.replaceAll("_", " ")}
                </option>
              ))}
            </Select>
          </div>
          <label className="flex items-start gap-2.5 pt-1 text-sm text-ink/60">
            <input type="checkbox" name="is_joint_assessment" className="mt-0.5 accent-brass" />
            I&apos;m filing jointly with my spouse (Zusammenveranlagung)
          </label>
          <Button type="submit" disabled={isSubmitting} className="mt-2 w-full">
            {isSubmitting ? "Setting up…" : "Create account"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
