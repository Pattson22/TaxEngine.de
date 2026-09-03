"use client";

// The product's one recurring visual idea: every amount is presented like
// a line on a Beleg (receipt/statement) -- a label, a dotted leader, and a
// right-aligned tabular figure. It's the same component whether it's a
// marketing demo on the landing page or a real calculation result, on
// purpose: what we show is exactly what the backend computed, nothing
// prettied up for the pitch and simplified for the product.

import { useEffect, useRef, useState } from "react";

export function Ledger({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`border-t border-b border-paper-line/60 py-1 ${className}`}>{children}</div>
  );
}

type LineTone = "default" | "positive" | "negative" | "total";

export function LedgerLine({
  label,
  value,
  tone = "default",
  delay = 0,
}: {
  label: string;
  value: string;
  tone?: LineTone;
  delay?: number;
}) {
  const isTotal = tone === "total";
  const valueColor =
    tone === "positive" ? "text-sage" : tone === "negative" ? "text-clay" : "text-ink";

  return (
    <div
      className={`flex animate-rise-in items-baseline gap-2 py-2 ${isTotal ? "border-t border-paper-line mt-1 pt-3" : ""}`}
      style={{ animationDelay: `${delay}ms` }}
    >
      {/* The label is the side that gives: `min-w-0` lets it shrink below
          its content width (flex items refuse to by default) and `truncate`
          ellipsises what is left over, with the full text on `title` so
          nothing becomes unreachable. The AMOUNT never shrinks or wraps --
          a half-shown figure in a money column is worse than useless -- so
          it keeps `whitespace-nowrap` and gets `shrink-0`. Measured: a
          realistic address ("Musterstraße 123, 10115 Berlin-Prenzlauer
          Berg") needed 400px in the 311px a 375px phone actually leaves
          inside a p-8 tile, and overflowed the row before this. */}
      <span
        title={label}
        className={`min-w-0 truncate text-sm ${isTotal ? "font-medium text-ink" : "text-ink/60"}`}
      >
        {label}
      </span>
      <span
        className="mb-[4px] h-[3px] min-w-3 flex-1 self-end"
        style={{
          backgroundImage: "radial-gradient(circle, var(--color-ink) 1px, transparent 1.3px)",
          backgroundSize: "6px 3px",
          backgroundRepeat: "repeat-x",
          backgroundPosition: "left bottom",
          opacity: 0.32,
        }}
        aria-hidden
      />
      <span
        className={`tabular shrink-0 whitespace-nowrap ${isTotal ? "text-lg font-medium" : "text-sm"} ${valueColor}`}
      >
        {value}
      </span>
    </div>
  );
}

const EUR_FORMATTER = new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR" });

/** Animates a cents value counting up from 0 on mount. Renders the final
 * value immediately if the user prefers reduced motion. */
export function CountUpEuro({ cents, durationMs = 900 }: { cents: number; durationMs?: number }) {
  const [display, setDisplay] = useState(0);
  const frame = useRef<number | undefined>(undefined);

  useEffect(() => {
    // matchMedia is a browser-only API -- this can't be read during render
    // (would break SSR/hydration), so seeding state from it necessarily
    // happens here, in the effect, on mount.
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setDisplay(cents);
      return;
    }

    const start = performance.now();
    function tick(now: number) {
      const progress = Math.min((now - start) / durationMs, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(Math.round(cents * eased));
      if (progress < 1) frame.current = requestAnimationFrame(tick);
    }
    frame.current = requestAnimationFrame(tick);
    return () => {
      if (frame.current) cancelAnimationFrame(frame.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cents]);

  return <>{EUR_FORMATTER.format(display / 100)}</>;
}
