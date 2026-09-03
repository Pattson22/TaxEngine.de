"use client";

// Rule 1 of the premium redesign: ONE dedicated, unmissable home for the
// live refund/liability figure -- everything else on the page (the Bento
// grid, the calculation ledger) feeds this, never repeats it. Deep
// monochrome backdrop (--color-abyss) with the digits themselves in a
// muted alpine green/warm clay -- never a loud neon "number go up" green.
//
// Copy is English like the rest of the app chrome (see ui.tsx's
// CATEGORY_TAB note); "§32a EStG" stays German because it is the statute's
// actual name. The figure is announced politely to screen readers rather
// than silently swapped in -- it is the single number the whole page
// exists to deliver, and it appears with no other visible signal.

import { CountUpEuro } from "./ledger";

export function RefundAnchor({
  amountCents,
  isCalculated,
}: {
  amountCents: number | null;
  isCalculated: boolean;
}) {
  const isPositive = (amountCents ?? 0) >= 0;

  return (
    <div
      className="relative overflow-hidden rounded-2xl bg-abyss px-8 py-14 md:px-16 md:py-20"
      aria-live="polite"
      // The digits animate up via CountUpEuro, so the DOM text changes on
      // every frame. `aria-atomic` makes assistive tech announce the whole
      // region once it settles rather than reading each intermediate
      // number, and `polite` waits for a pause instead of interrupting.
      aria-atomic="true"
    >
      <div
        aria-hidden
        className={`pointer-events-none absolute -top-32 -right-32 h-96 w-96 rounded-full blur-3xl ${
          isCalculated ? (isPositive ? "bg-alpine/10" : "bg-alpine-warn/10") : "bg-white/5"
        }`}
      />
      <p className="relative text-[11px] font-medium tracking-[0.2em] text-white/35 uppercase">
        {isCalculated && !isPositive ? "You still owe" : "Estimated refund"}
      </p>

      {isCalculated ? (
        <p
          className={`tabular relative mt-5 font-display text-6xl font-semibold tracking-tight md:text-7xl ${
            isPositive ? "text-alpine" : "text-alpine-warn"
          }`}
        >
          <CountUpEuro cents={Math.abs(amountCents ?? 0)} />
        </p>
      ) : (
        <p className="tabular relative mt-5 font-display text-6xl font-semibold tracking-tight text-white/20 md:text-7xl">
          —,—— €
        </p>
      )}

      <div className="relative mt-7 flex flex-wrap items-center gap-x-5 gap-y-1.5 text-xs text-white/30">
        <span>Calculated per §32a EStG</span>
        <span aria-hidden>·</span>
        <span>{isCalculated ? "Current as of the last calculation" : "Not calculated yet"}</span>
      </div>
    </div>
  );
}
