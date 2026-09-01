import type { ReactNode } from "react";

/** Shared shell for the Impressum and Datenschutzerklärung pages --
 * narrower than the app's data-entry pages (max-w-2xl) since this is
 * continuous prose, not a form or dashboard. */
export function LegalPage({ children }: { children: ReactNode }) {
  return <div className="mx-auto max-w-2xl px-6 py-20 md:py-24">{children}</div>;
}

/** A visible reminder that this page is a compliance draft, not a
 * finished legal document -- the bracketed placeholders in
 * lib/legal-info.ts need real details, and the whole page needs a
 * lawyer's review before it goes live, especially given how sensitive
 * the data this product handles is. */
export function LegalDraftNotice() {
  return (
    <div className="mb-10 border-l-2 border-brass bg-brass-soft/10 px-4 py-3 text-sm text-ink/70">
      Entwurf -- vor dem Livegang durch die tatsächlichen Angaben ersetzen und von einer
      Rechtsanwältin oder einem Rechtsanwalt für IT-/Datenschutzrecht prüfen lassen.
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
