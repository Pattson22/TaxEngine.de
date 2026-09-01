"use client";

import { useEffect } from "react";
import * as Sentry from "@sentry/nextjs";
import "./globals.css";

// Only fires for errors the root layout itself can't recover from --
// this replaces the ENTIRE page (own <html>/<body>), so it can't rely
// on RootLayout's providers/fonts and imports globals.css directly.
export default function GlobalError({ error }: { error: Error & { digest?: string } }) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <html lang="en">
      <body className="flex min-h-screen items-center justify-center bg-paper px-6 text-center">
        <div>
          <p className="mb-3 text-[11px] font-medium tracking-[0.14em] text-clay uppercase">
            Etwas ist schiefgelaufen
          </p>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">
            Something went wrong
          </h1>
          <p className="mt-3 text-sm text-ink/60">
            We&apos;ve been notified. Please try reloading the page.
          </p>
          <button
            onClick={() => window.location.reload()}
            className="mt-6 inline-flex items-center justify-center rounded-sm bg-ink px-5 py-2.5 text-sm font-medium text-paper transition-colors hover:bg-brass hover:text-ink"
          >
            Reload
          </button>
        </div>
      </body>
    </html>
  );
}
