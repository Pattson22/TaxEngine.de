// Every amount from the API is integer CENTS (see the backend's "Financial
// Data Integrity Principles" in README.md) -- always divide by 100 and
// format via Intl.NumberFormat, never do ad-hoc string concatenation with
// a "€" prefix, which breaks for negative amounts (rental/self-employment
// losses) and locale formatting.

const EUR_FORMATTER = new Intl.NumberFormat("de-DE", {
  style: "currency",
  currency: "EUR",
});

export function formatCents(cents: number | null | undefined): string {
  if (cents === null || cents === undefined) return "—";
  return EUR_FORMATTER.format(cents / 100);
}

export function eurosToCents(euros: string | number): number {
  const value = typeof euros === "string" ? Number.parseFloat(euros.replace(",", ".")) : euros;
  if (Number.isNaN(value)) return 0;
  return Math.round(value * 100);
}

/** Plain "45000.00" for a number input's value -- not formatCents()'s
 * currency-symbol-and-thousands-separator display string. */
export function centsToEuroInputValue(cents: number | null | undefined): string {
  if (cents === null || cents === undefined) return "";
  return (cents / 100).toFixed(2);
}
