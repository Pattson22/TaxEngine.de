// Rule 2 of the premium redesign: an asymmetrical Bento Grid for the tax
// pillars instead of a uniform vertical list -- variable column spans by
// priority/data density, ultra-subtle sub-pixel borders instead of stark
// dividers, and a soft shadow rather than a hard box.

import type { ReactNode } from "react";

export function BentoGrid({ children }: { children: ReactNode }) {
  return <div className="grid grid-cols-1 gap-6 md:grid-cols-3">{children}</div>;
}

export function BentoTile({
  children,
  span = 1,
}: {
  children: ReactNode;
  span?: 1 | 2 | 3;
}) {
  const spanClass = span === 2 ? "md:col-span-2" : span === 3 ? "md:col-span-3" : "";
  return (
    <div
      className={`rounded-2xl border border-ink/6 bg-paper p-8 shadow-[0_1px_2px_rgba(20,23,42,0.04),0_12px_32px_-16px_rgba(20,23,42,0.12)] ${spanClass}`}
    >
      {children}
    </div>
  );
}
