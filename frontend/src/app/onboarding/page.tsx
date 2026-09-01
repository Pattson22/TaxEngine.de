"use client";

import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { confirmElsterPrivacyNotice, updateCurrentUser } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { useRequireAuth } from "@/lib/use-require-auth";
import { isBasicProfileComplete, isProfileComplete } from "@/lib/onboarding";
import { Button, ErrorBanner, Input, StatusStamp } from "@/components/ui";
import { SegmentedDigitInput, dobToIso } from "@/components/tax-form-boxes";

export default function OnboardingPage() {
  const { token, isLoading: authLoading } = useRequireAuth();
  const { user, refreshUser } = useAuth();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [hasConfirmedPrivacyNotice, setHasConfirmedPrivacyNotice] = useState(false);

  const alreadyComplete = !authLoading && !!user && isProfileComplete(user);
  // A user who already completed the basic profile before the privacy-
  // notice confirmation existed only needs that one extra step, not the
  // whole form again -- see lib/onboarding.ts's isBasicProfileComplete.
  const onlyNeedsPrivacyNoticeConfirmation =
    !authLoading && !!user && isBasicProfileComplete(user) && !alreadyComplete;

  useEffect(() => {
    if (alreadyComplete) router.replace("/dashboard");
  }, [alreadyComplete, router]);

  if (authLoading || !token || !user || alreadyComplete) {
    return <div className="mx-auto max-w-2xl px-6 py-14 text-sm text-ink/40">Loading…</div>;
  }

  async function handleConfirmPrivacyNoticeOnly() {
    setError(null);
    if (!hasConfirmedPrivacyNotice) {
      setError("Please confirm you've read the notice before continuing.");
      return;
    }
    setIsSaving(true);
    try {
      await confirmElsterPrivacyNotice(token as string);
      await refreshUser();
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't save your confirmation.");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const formData = new FormData(event.currentTarget);
    const dateOfBirth = String(formData.get("date_of_birth") ?? "");
    const postalCode = String(formData.get("postal_code") ?? "");
    const street = String(formData.get("street") ?? "").trim();
    const houseNumber = String(formData.get("house_number") ?? "").trim();
    const city = String(formData.get("city") ?? "").trim();
    const steuernummer = String(formData.get("steuernummer") ?? "").trim();

    if (!/^\d{4}-\d{2}-\d{2}$/.test(dateOfBirth)) {
      setError("Fill in a complete date of birth.");
      return;
    }
    if (!/^\d{5}$/.test(postalCode)) {
      setError("Postal code needs all 5 digits.");
      return;
    }
    if (!street || !houseNumber || !city || !steuernummer) {
      setError("Every line on this page is required.");
      return;
    }
    if (!hasConfirmedPrivacyNotice) {
      setError("Please confirm you've read the ELSTER privacy notice before continuing.");
      return;
    }

    setIsSaving(true);
    try {
      await updateCurrentUser(token as string, {
        date_of_birth: dateOfBirth,
        street,
        house_number: houseNumber,
        postal_code: postalCode,
        city,
        steuernummer,
      });
      await confirmElsterPrivacyNotice(token as string);
      await refreshUser();
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't save your details.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-6 py-14 sm:py-16">
      <header className="mb-8 flex items-end justify-between gap-6 border-b border-ink/10 pb-5">
        <div>
          <p className="mb-2 text-[11px] font-medium tracking-[0.14em] text-brass uppercase">
            Bevor es losgeht — before we start
          </p>
          <h1 className="font-display text-[26px] leading-tight font-semibold tracking-tight text-ink">
            Welcome, {user.first_name}
          </h1>
          <p className="mt-2 max-w-sm text-sm text-ink/55">
            A few lines the Finanzamt expects on every return — fill them in once, use them for
            every year you file.
          </p>
        </div>
        <div className="hidden sm:block">
          <StatusStamp status="Erstangaben" />
        </div>
      </header>

      {error && <ErrorBanner message={error} />}

      {onlyNeedsPrivacyNoticeConfirmation ? (
        <div className="border border-ink/15 bg-paper">
          <div className="px-6 py-6">
            <PrivacyNoticeCheckbox
              checked={hasConfirmedPrivacyNotice}
              onChange={setHasConfirmedPrivacyNotice}
            />
          </div>
          <div className="flex items-center justify-end border-t border-paper-line bg-paper-dim/40 px-6 py-4">
            <Button
              type="button"
              onClick={handleConfirmPrivacyNoticeOnly}
              disabled={!hasConfirmedPrivacyNotice || isSaving}
            >
              {isSaving ? "Saving…" : "Continue"}
            </Button>
          </div>
        </div>
      ) : (
      <form onSubmit={handleSubmit} className="border border-ink/15 bg-paper">
        <FormLine n={1} label="Geburtsdatum" hint="Date of birth" delay={0}>
          <SegmentedDigitInput
            name="date_of_birth"
            segments={[2, 2, 4]}
            separator="."
            ariaLabel="Date of birth"
            toValue={dobToIso}
          />
        </FormLine>

        <FormLine n={2} label="Anschrift" hint="Street and house number" delay={70}>
          <div className="grid grid-cols-[1fr_5rem] gap-3">
            <Input name="street" placeholder="Straße" required />
            <Input name="house_number" placeholder="Nr." required />
          </div>
        </FormLine>

        <FormLine n={3} label="Wohnort" hint="Postal code and city" delay={140}>
          <div className="grid grid-cols-[auto_1fr] items-center gap-4">
            <SegmentedDigitInput name="postal_code" segments={[5]} ariaLabel="Postal code" />
            <Input name="city" placeholder="Ort" required />
          </div>
        </FormLine>

        <FormLine n={4} label="Steuernummer" hint="Issued by your local Finanzamt" delay={210} last>
          <Input
            name="steuernummer"
            placeholder="z. B. 13/391/08153"
            required
            className="max-w-xs font-mono"
          />
          <p className="mt-2 text-xs text-ink/40">
            Different from your Steuer-ID — find it on a prior tax assessment, or ask your
            Finanzamt.
          </p>
        </FormLine>

        <div className="border-t border-paper-line px-6 py-6">
          <PrivacyNoticeCheckbox
            checked={hasConfirmedPrivacyNotice}
            onChange={setHasConfirmedPrivacyNotice}
          />
        </div>

        <div className="flex items-center justify-end border-t border-paper-line bg-paper-dim/40 px-6 py-4">
          <Button type="submit" disabled={!hasConfirmedPrivacyNotice || isSaving}>
            {isSaving ? "Saving…" : "Continue"}
          </Button>
        </div>
      </form>
      )}
    </div>
  );
}

function PrivacyNoticeCheckbox({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex items-start gap-2.5 text-sm text-ink/70">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-0.5 accent-brass"
      />
      Ich habe den{" "}
      <Link href="/elster-datenschutzhinweis" className="underline hover:text-ink" target="_blank">
        Datenschutzhinweis der Finanzverwaltung
      </Link>{" "}
      zur Übermittlung meiner Steuerdaten über ELSTER zur Kenntnis genommen.
    </label>
  );
}

function FormLine({
  n,
  label,
  hint,
  children,
  delay = 0,
  last = false,
}: {
  n: number;
  label: string;
  hint: string;
  children: ReactNode;
  delay?: number;
  last?: boolean;
}) {
  return (
    <div
      className={`animate-rise-in flex gap-5 px-6 py-6 ${!last ? "border-b border-paper-line" : ""}`}
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="w-16 flex-none pt-0.5">
        <span className="font-mono text-[11px] text-brass">Zeile {n}</span>
      </div>
      <div className="flex-1">
        <div className="mb-2.5 flex items-baseline gap-2">
          <span className="font-display text-sm font-medium text-ink">{label}</span>
          <span className="text-xs text-ink/40">— {hint}</span>
        </div>
        {children}
      </div>
    </div>
  );
}
