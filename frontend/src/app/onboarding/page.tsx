"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { updateCurrentUser } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { useRequireAuth } from "@/lib/use-require-auth";
import { isProfileComplete } from "@/lib/onboarding";
import { Button, Card, ErrorBanner, Eyebrow, Input, Label, PageHeading } from "@/components/ui";

export default function OnboardingPage() {
  const { token, isLoading: authLoading } = useRequireAuth();
  const { user, refreshUser } = useAuth();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const alreadyComplete = !authLoading && !!user && isProfileComplete(user);

  useEffect(() => {
    if (alreadyComplete) router.replace("/dashboard");
  }, [alreadyComplete, router]);

  if (authLoading || !token || !user || alreadyComplete) {
    return <div className="mx-auto max-w-md px-6 py-14 text-sm text-ink/40">Loading…</div>;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSaving(true);

    const formData = new FormData(event.currentTarget);
    try {
      await updateCurrentUser(token as string, {
        date_of_birth: String(formData.get("date_of_birth")),
        street: String(formData.get("street")),
        house_number: String(formData.get("house_number")),
        postal_code: String(formData.get("postal_code")),
        city: String(formData.get("city")),
        steuernummer: String(formData.get("steuernummer")),
      });
      await refreshUser();
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't save your details.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-md px-6 py-16">
      <Eyebrow>Bevor es losgeht — before we start</Eyebrow>
      <PageHeading
        title={`Welcome, ${user.first_name}`}
        subtitle="A few basics the Finanzamt needs on every return, collected once."
      />
      <Card>
        {error && <ErrorBanner message={error} />}
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <Label htmlFor="date_of_birth">Date of birth</Label>
            <Input id="date_of_birth" name="date_of_birth" type="date" required />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-[1fr_auto]">
            <div>
              <Label htmlFor="street">Street</Label>
              <Input id="street" name="street" required />
            </div>
            <div>
              <Label htmlFor="house_number">No.</Label>
              <Input id="house_number" name="house_number" className="sm:w-20" required />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-[auto_1fr]">
            <div>
              <Label htmlFor="postal_code">Postal code</Label>
              <Input
                id="postal_code"
                name="postal_code"
                inputMode="numeric"
                pattern="\d{5}"
                title="5 digits."
                className="sm:w-24"
                required
              />
            </div>
            <div>
              <Label htmlFor="city">City</Label>
              <Input id="city" name="city" required />
            </div>
          </div>

          <div>
            <Label htmlFor="steuernummer">Steuernummer</Label>
            <Input id="steuernummer" name="steuernummer" required />
            <p className="mt-1.5 text-xs text-ink/40">
              Issued by your local Finanzamt — different from your Steuer-ID. Find it on a prior
              tax assessment or by contacting your Finanzamt.
            </p>
          </div>

          <Button type="submit" disabled={isSaving} className="mt-2 w-full">
            {isSaving ? "Saving…" : "Continue"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
