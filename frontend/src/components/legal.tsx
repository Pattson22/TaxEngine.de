import type { ReactNode } from "react";

/** Shared shell for the Impressum and Datenschutzerklärung pages --
 * narrower than the app's data-entry pages (max-w-2xl) since this is
 * continuous prose, not a form or dashboard. */
export function LegalPage({ children }: { children: ReactNode }) {
  return <div className="mx-auto max-w-2xl px-6 py-20 md:py-24">{children}</div>;
}

/** A visible reminder that this page is not yet a finished legal
 * document. The identity details in lib/legal-info.ts are now real, so
 * that half of the original warning is done -- what remains is the
 * lawyer's review, which matters more than usual for a product that
 * handles taxpayers' full financial data and transmits it to the
 * Finanzamt. See lib/legal-info.ts's STATUS note for the open items. */
export function LegalDraftNotice() {
  return (
    <div className="mb-10 border-l-2 border-brass bg-brass-soft/10 px-4 py-3 text-sm text-ink/70">
      Diese Seite wurde noch nicht von einer Rechtsanwältin oder einem Rechtsanwalt für
      IT-/Datenschutzrecht geprüft.
    </div>
  );
}

export function LegalSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mt-10 first:mt-0">
      <h2 className="font-display text-lg font-semibold tracking-tight text-ink">{title}</h2>
      <div className="mt-3 space-y-3 text-[15px] leading-relaxed text-ink/70">{children}</div>
    </section>
  );
}
