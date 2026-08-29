import { loadStripe, type Stripe } from "@stripe/stripe-js";

let stripePromise: Promise<Stripe | null> | null = null;

// Singleton -- loadStripe() should only be called once per publishable key
// for the lifetime of the page (Stripe's own recommendation).
export function getStripe(): Promise<Stripe | null> {
  if (!stripePromise) {
    const publishableKey = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY;
    if (!publishableKey) {
      console.warn(
        "NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY is not set -- the payment page will not work. See .env.local.example.",
      );
    }
    stripePromise = loadStripe(publishableKey ?? "");
  }
  return stripePromise;
}
