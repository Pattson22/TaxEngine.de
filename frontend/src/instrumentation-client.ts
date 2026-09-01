// Client-side (browser) Sentry init. Unset NEXT_PUBLIC_SENTRY_DSN
// disables the SDK entirely -- safe default for local dev/CI. No
// Session Replay/screen-recording integration here on purpose: this
// app's screens routinely show a taxpayer's real financial and tax
// figures, and enabling that later needs an explicit, deliberate
// decision (with masking configured), not a side effect of adding
// basic error monitoring.

import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NODE_ENV,
  tracesSampleRate: 0,
  sendDefaultPii: false,
});

export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;
