import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  LabelHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
} from "react";

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "danger" }) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-sm px-5 py-2.5 text-sm font-medium tracking-wide transition-colors disabled:cursor-not-allowed disabled:opacity-40";
  const variants: Record<string, string> = {
    primary: "bg-ink text-paper hover:bg-brass hover:text-ink",
    secondary: "border border-ink/15 bg-transparent text-ink hover:border-ink/40",
    danger: "border border-clay/30 bg-clay-soft text-clay hover:border-clay/60",
  };
  return <button className={`${base} ${variants[variant]} ${className}`} {...props} />;
}

export function Input({ className = "", ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={`w-full border-0 border-b border-ink/20 bg-transparent px-0.5 py-2 text-sm text-ink outline-none transition-colors placeholder:text-ink/30 focus:border-brass ${className}`}
      {...props}
    />
  );
}

export function Select({
  className = "",
  children,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={`w-full border-0 border-b border-ink/20 bg-transparent px-0.5 py-2 text-sm text-ink outline-none transition-colors focus:border-brass ${className}`}
      {...props}
    >
      {children}
    </select>
  );
}

export function Label({ className = "", ...props }: LabelHTMLAttributes<HTMLLabelElement>) {
  return (
    <label
      className={`mb-2.5 block text-[11px] font-medium tracking-[0.08em] text-ink/50 uppercase ${className}`}
      {...props}
    />
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-2xl border border-ink/8 bg-paper p-8 ${className}`}>{children}</div>
  );
}

const EYEBROW_TONE: Record<string, string> = {
  brass: "text-brass",
  indigo: "text-indigo",
  sage: "text-sage",
  terracotta: "text-terracotta",
  mauve: "text-mauve",
};

export function Eyebrow({
  children,
  tone = "brass",
}: {
  children: ReactNode;
  tone?: keyof typeof EYEBROW_TONE;
}) {
  return (
    <p className={`mb-3 text-[11px] font-medium tracking-[0.14em] uppercase ${EYEBROW_TONE[tone]}`}>
      {children}
    </p>
  );
}

const CATEGORY_TAB: Record<string, { label: string; dot: string; text: string; bg: string }> = {
  wage: { label: "Lohn", dot: "bg-brass", text: "text-brass", bg: "bg-brass-soft/20" },
  capital: { label: "Kapital", dot: "bg-indigo", text: "text-indigo", bg: "bg-indigo-soft/20" },
  rental: { label: "Miete", dot: "bg-sage", text: "text-sage", bg: "bg-sage-soft" },
  self_employment: {
    label: "Selbstständig",
    dot: "bg-terracotta",
    text: "text-terracotta",
    bg: "bg-terracotta-soft/20",
  },
  children: { label: "Kinder", dot: "bg-mauve", text: "text-mauve", bg: "bg-mauve-soft/20" },
};

/** A small colored tab marking which income category a section belongs
 * to -- like a real ledger's divider tabs. Marks the CATEGORY only; a
 * value's sign (a rental loss, say) stays sage/clay on the figure itself,
 * same as before -- see LedgerLine. */
export function CategoryTab({ category }: { category: keyof typeof CATEGORY_TAB }) {
  const tab = CATEGORY_TAB[category];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-sm px-2 py-0.5 font-mono text-[10px] tracking-wide uppercase ${tab.bg} ${tab.text}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${tab.dot}`} />
      {tab.label}
    </span>
  );
}

export function PageHeading({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-8">
      <h1 className="font-display text-[28px] leading-tight font-medium text-ink">{title}</h1>
      {subtitle && <p className="mt-2 text-sm text-ink/55">{subtitle}</p>}
    </div>
  );
}

export function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="mb-5 border-l-2 border-clay bg-clay-soft px-4 py-3 text-sm text-clay">
      {message}
    </div>
  );
}

const STATUS_LABEL: Record<string, string> = {
  DRAFT: "Entwurf",
  CALCULATED: "Calculated",
  FEE_PAID: "Fee paid",
  SUBMITTED: "Submitted",
  ACCEPTED: "Accepted",
  REJECTED: "Rejected",
};

const STATUS_TONE: Record<string, string> = {
  DRAFT: "border-ink/25 text-ink/60",
  CALCULATED: "border-brass text-brass",
  FEE_PAID: "border-brass text-brass",
  SUBMITTED: "border-ink/40 text-ink/70",
  ACCEPTED: "border-sage text-sage",
  REJECTED: "border-clay text-clay",
};

/** A rotated, double-ruled "stamp" -- the Finanzamt's own visual language
 * (an official stamp on a processed document), borrowed rather than a
 * generic colored pill, and turned into something reassuring instead of
 * bureaucratic: your document has been stamped, not stuck in a queue. */
export function StatusStamp({ status }: { status: string }) {
  return (
    <span
      className={`inline-block -rotate-2 border-2 border-double px-2.5 py-0.5 font-display text-[11px] font-medium tracking-[0.08em] uppercase ${STATUS_TONE[status] ?? "border-ink/25 text-ink/60"}`}
    >
      {STATUS_LABEL[status] ?? status}
    </span>
  );
}
