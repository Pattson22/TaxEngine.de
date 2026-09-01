"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Elements, PaymentElement, useElements, useStripe } from "@stripe/react-stripe-js";
import { createPaymentIntent } from "@/lib/api";
import { useRequireOnboarding } from "@/lib/use-require-auth";
import { getStripe } from "@/lib/stripe";
import { formatCents } from "@/lib/money";
import { Button, Card, ErrorBanner, Eyebrow, PageHeading } from "@/components/ui";

export default function PayFilingPage() {
  const { id } = useParams<{ id: string }>();
  const { token, isLoading: authLoading } = useRequireOnboarding();
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [amountCents, setAmountCents] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    createPaymentIntent(token, id)
      .then((intent) => {
        setClientSecret(intent.client_secret);
        setAmountCents(intent.amount_cents);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Couldn't start the payment."));
  }, [token, id]);

  if (authLoading || !token) return null;

  return (
    <div className="mx-auto max-w-md px-6 py-20">
      <div className="mb-10">
        <Eyebrow>Bearbeitungsgebühr</Eyebrow>
        <PageHeading
          title="Pay the processing fee"
          subtitle={amountCents !== null ? `Flat fee: ${formatCents(amountCents)}` : undefined}
        />
      </div>
      {error && <ErrorBanner message={error} />}
      <Card>
        {clientSecret ? (
          <Elements stripe={getStripe()} options={{ clientSecret }}>
            <CheckoutForm filingId={id} />
          </Elements>
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
