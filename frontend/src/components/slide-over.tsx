"use client";

// Rule 3's answer to "where do legal tax-code explanations go": never
// inline, cluttering the data-entry space -- push them into a spacious,
// low-contrast slide-over the filer opens only when they want it.

import type { ReactNode } from "react";

export function InfoTrigger({ onClick, label }: { onClick: () => void; label: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      className="ml-2 inline-flex h-4 w-4 items-center justify-center rounded-full border border-ink/20 text-[10px] leading-none text-ink/40 transition-colors hover:border-ink/40 hover:text-ink/70"
    >
      i
    </button>
  );
}

export function SlideOver({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}) {
  return (
    <>
      <div
        aria-hidden
        onClick={onClose}
        className={`fixed inset-0 z-40 bg-ink/15 backdrop-blur-[1px] transition-opacity duration-300 ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
      />
      <aside
        role="dialog"
        aria-label={title}
        className={`fixed top-0 right-0 z-50 h-full w-full max-w-sm transform bg-paper px-9 py-12 shadow-2xl transition-transform duration-300 ease-out ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <button
          type="button"
          onClick={onClose}
          className="mb-10 text-[11px] font-medium tracking-[0.14em] text-ink/40 uppercase transition-colors hover:text-ink"
        >
          Close ×
        </button>
        <h2 className="font-display text-lg font-medium text-ink">{title}</h2>
        <div className="mt-5 space-y-4 text-sm leading-relaxed text-ink/55">{children}</div>
      </aside>
    </>
  );
}
