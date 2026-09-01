// Edge runtime Sentry init, loaded by instrumentation.ts. See
// instrumentation-client.ts for why Session Replay is deliberately not
// enabled.

import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NODE_ENV,
  tracesSampleRate: 0,
  sendDefaultPii: false,
});
