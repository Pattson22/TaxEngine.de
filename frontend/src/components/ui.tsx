import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  LabelHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
} from "react";

/** Every visual choice lives in a `variant`/`size` here, deliberately --
 * NOT in a `className` the caller tacks on. Conflicting Tailwind utilities
 * resolve by stylesheet order, not by their order in the class attribute,
 * so a passed-in `bg-brass` does NOT reliably beat a variant's `bg-ink`:
 * it silently loses and the caller gets the variant's colour with no error
 * anywhere. That exact bug shipped -- the landing page's primary CTA
 * passed `bg-brass text-ink` and rendered `bg-ink` on the `bg-ink` hero,
 * i.e. an invisible button on the highest-traffic page in the product.
 * Hence the `hero` variant below rather than a colour override, and a
 * `size` prop rather than a padding override (padding is out of `base`
 * for the same reason -- it would conflict too). `className` is for
 * LAYOUT only: margins, width. Never colour, never padding. */
export function Button({
  variant = "primary",
  size = "md",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger" | "hero";
  size?: "md" | "lg";
}) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-sm text-sm font-medium tracking-wide transition-colors disabled:cursor-not-allowed disabled:opacity-40";
  const sizes: Record<string, string> = {
    md: "px-5 py-2.5",
    lg: "px-6 py-3",
  };
  const variants: Record<string, string> = {
    primary: "bg-ink text-paper hover:bg-brass hover:text-ink",
    secondary: "border border-ink/15 bg-transparent text-ink hover:border-ink/40",
    danger: "border border-clay/30 bg-clay-soft text-clay hover:border-clay/60",
    // For placement ON the dark ink hero, where `primary` would be
    // invisible: brass on ink, inverted from primary's ink on paper.
    hero: "bg-brass text-ink hover:bg-brass-soft",
  };
  return (
    <button className={`${base} ${sizes[size]} ${variants[variant]} ${className}`} {...props} />
  );
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

/** A small circular "?" that reveals a plain-language explanation of what
 * a field is asking for on hover/focus -- distinct from InfoTrigger/
 * SlideOver (slide-over.tsx), which is reserved for citing the actual tax
 * law behind a computed deduction. This one just answers "what number goes
 * here," so it's a lighter hover popover rather than a click-to-open panel. */
export function InfoTooltip({ text }: { text: string }) {
  return (
    <span className="group/tooltip relative inline-flex shrink-0">
      <span
        tabIndex={0}
        aria-label="More information"
        className="flex h-4 w-4 cursor-help items-center justify-center rounded-full bg-indigo-soft/25 text-[10px] leading-none font-semibold text-indigo-soft outline-none transition-colors hover:bg-indigo-soft/40 focus-visible:ring-2 focus-visible:ring-indigo-soft/60"
      >
        ?
      </span>
      <span
        role="tooltip"
        className="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 w-48 -translate-x-1/2 rounded-lg border border-ink/10 bg-ink px-3 py-2 text-[11px] leading-relaxed normal-case text-paper opacity-0 shadow-xl transition-opacity duration-150 group-hover/tooltip:opacity-100 group-focus-within/tooltip:opacity-100"
      >
        {text}
      </span>
    </span>
  );
}

export function Label({
  className = "",
  children,
  hint,
  ...props
}: LabelHTMLAttributes<HTMLLabelElement> & { hint?: string }) {
  return (
    <label
      className={`mb-2.5 flex items-center gap-1.5 text-[11px] font-medium tracking-[0.08em] text-ink/50 uppercase ${className}`}
      {...props}
    >
      {children}
      {hint && <InfoTooltip text={hint} />}
    </label>
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

/** UI chrome is English (the app is `lang="en"` and aimed at expats --
 * see the root README); German is reserved for terms that ARE the German
 * thing being named: form and Anlage names, statutory concepts
 * (Werbungskosten, Entfernungspauschale, Anlage KAP), and the legally
 * German pages (Impressum/Datenschutz/AGB). These labels used to be
 * German and sat directly beside their own English headings -- "Kapital"
 * next to "Capital income" -- which read as unfinished rather than as
 * flavour. The "Zeile" numbering on the landing page is deliberate German
 * flavour and stays: it labels the tax form's own line numbers. */
const CATEGORY_TAB: Record<string, { label: string; dot: string; text: string; bg: string }> = {
  wage: { label: "Wage", dot: "bg-brass", text: "text-brass", bg: "bg-brass-soft/20" },
  capital: { label: "Capital", dot: "bg-indigo", text: "text-indigo", bg: "bg-indigo-soft/20" },
  rental: { label: "Rental", dot: "bg-sage", text: "text-sage", bg: "bg-sage-soft" },
  self_employment: {
    label: "Self-employed",
    dot: "bg-terracotta",
    text: "text-terracotta",
    bg: "bg-terracotta-soft/20",
  },
  children: { label: "Children", dot: "bg-mauve", text: "text-mauve", bg: "bg-mauve-soft/20" },
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
      <h1 className="font-display text-[28px] leading-tight font-semibold tracking-tight text-ink">
        {title}
      </h1>
      {subtitle && <p className="mt-2 text-sm text-ink/55">{subtitle}</p>}
    </div>
  );
}

export function ErrorBanner({ message }: { message: string }) {
  return (
    // role="alert" carries an implicit aria-live="assertive": a failed
    // calculation, payment or submission is worth interrupting for, and it
    // is otherwise signalled only by colour and position.
    <div
      role="alert"
      className="mb-5 border-l-2 border-clay bg-clay-soft px-4 py-3 text-sm text-clay"
    >
      {message}
    </div>
  );
}

const STATUS_LABEL: Record<string, string> = {
  // English, like every other status here -- see CATEGORY_TAB's note.
  DRAFT: "Draft",
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
