"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { Elements, PaymentElement, useElements, useStripe } from "@stripe/react-stripe-js";
import { createPaymentIntent, getTaxFiling } from "@/lib/api";
import { useRequireOnboarding } from "@/lib/use-require-auth";
import { getStripe } from "@/lib/stripe";
import { formatCents } from "@/lib/money";
import { Button, Card, ErrorBanner, Eyebrow, PageHeading } from "@/components/ui";
import type { TaxFiling } from "@/lib/types";

export default function PayFilingPage() {
  const { id } = useParams<{ id: string }>();
  const { token, isLoading: authLoading } = useRequireOnboarding();
  const [filing, setFiling] = useState<TaxFiling | null>(null);
  const [hasConsented, setHasConsented] = useState(false);
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [amountCents, setAmountCents] = useState<number | null>(null);
  const [isStartingPayment, setIsStartingPayment] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    getTaxFiling(token, id)
      .then((loaded) => {
        setFiling(loaded);
        // A retried payment attempt on a filing that already has consent
        // on record (see AGB § 5) can skip straight to the payment form
        // -- see the backend's withdrawal_consent_at handling.
        if (loaded.withdrawal_consent_at) startPayment();
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Couldn't load this return."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, id]);

  async function startPayment() {
    if (!token) return;
    setIsStartingPayment(true);
    setError(null);
    try {
      const intent = await createPaymentIntent(token, id, true);
      setClientSecret(intent.client_secret);
      setAmountCents(intent.amount_cents);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't start the payment.");
    } finally {
      setIsStartingPayment(false);
    }
  }

  if (authLoading || !token) return null;

  return (
    <div className="mx-auto max-w-md px-6 py-20">
      <div className="mb-10">
        <Eyebrow>Bearbeitungsgebühr</Eyebrow>
        <PageHeading
          title="Pay the processing fee"
          subtitle={
            amountCents !== null
              ? `Flat fee: ${formatCents(amountCents)}`
              : filing
                ? `Flat fee: ${formatCents(filing.processing_fee_cents)}`
                : undefined
          }
        />
      </div>
      {error && <ErrorBanner message={error} />}
      <Card>
        {clientSecret ? (
          <Elements stripe={getStripe()} options={{ clientSecret }}>
            <CheckoutForm filingId={id} />
          </Elements>
        ) : filing && !filing.withdrawal_consent_at ? (
          <div className="space-y-5">
            <label className="flex items-start gap-2.5 text-sm text-ink/70">
              <input
                type="checkbox"
                checked={hasConsented}
                onChange={(e) => setHasConsented(e.target.checked)}
                className="mt-0.5 accent-brass"
              />
              Ich verlange ausdrücklich, dass die Übermittlung an das Finanzamt sofort nach
              Zahlung beginnt, und weiß, dass ich dadurch mein 14-tägiges Widerrufsrecht
              verliere, sobald die Übermittlung abgeschlossen ist (§ 356 Abs. 4 BGB, siehe{" "}
              <Link href="/agb" className="underline hover:text-ink" target="_blank">
                AGB § 5
              </Link>
              ).
            </label>
            <Button
              onClick={startPayment}
              disabled={!hasConsented || isStartingPayment}
              className="w-full"
            >
              {isStartingPayment ? "Preparing…" : "Continue to payment"}
            </Button>
          </div>
        ) : (
          !error && <p className="text-sm text-ink/40">Preparing payment…</p>
        )}
      </Card>
    </div>
  );
}

function CheckoutForm({ filingId }: { filingId: string }) {
  const stripe = useStripe();
  const elements = useElements();
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!stripe || !elements) return;
    setIsSubmitting(true);
    setError(null);

    const { error: confirmError } = await stripe.confirmPayment({
      elements,
      confirmParams: {
        return_url: `${window.location.origin}/filings/${filingId}`,
      },
    });

    if (confirmError) {
      setError(confirmError.message ?? "Payment failed.");
      setIsSubmitting(false);
      return;
    }

    // On success, Stripe redirects to return_url. If confirmPayment
    // resolves without redirecting (e.g. certain payment methods), fall
    // back to navigating there manually.
    router.push(`/filings/${filingId}`);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {error && <ErrorBanner message={error} />}
      <PaymentElement />
      <Button type="submit" disabled={!stripe || isSubmitting} className="w-full">
        {isSubmitting ? "Processing…" : "Pay now"}
      </Button>
      <p className="text-xs text-ink/40">
        Your return updates to &quot;fee paid&quot; automatically once Stripe confirms the
        charge — this can take a few seconds.
      </p>
    </form>
  );
}
