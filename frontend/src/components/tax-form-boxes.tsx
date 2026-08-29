"use client";

// The boxed single-character cell a paper Finanzamt form (and ELSTER's own
// online form) uses for fixed-length numeric fields -- one box per digit,
// not a plain text input. Used here for date of birth and postal code,
// the two fields on the onboarding page with a genuinely fixed shape.
// Steuernummer is deliberately NOT boxed: its digit count and grouping
// vary by Bundesland, so a fixed grid would misrepresent it.

import { useRef, useState, type KeyboardEvent, type ClipboardEvent } from "react";

interface SegmentedDigitInputProps {
  /** Name of the hidden input that carries the assembled value on submit. */
  name: string;
  /** Digit-group lengths, e.g. [2, 2, 4] for DD MM YYYY, or [5] for a PLZ. */
  segments: number[];
  /** Character shown between groups, e.g. "." for a date. */
  separator?: string;
  ariaLabel: string;
  /** Assembles the flat digit array into the hidden field's value.
   * Defaults to a plain join -- pass a custom one to reorder groups
   * (a date's day/month/year boxes fill left to right, but the value
   * submitted needs to be ISO YYYY-MM-DD). */
  toValue?: (digits: string[]) => string;
  className?: string;
}

export function SegmentedDigitInput({
  name,
  segments,
  separator = "",
  ariaLabel,
  toValue,
  className = "",
}: SegmentedDigitInputProps) {
  const total = segments.reduce((a, b) => a + b, 0);
  const [digits, setDigits] = useState<string[]>(() => Array(total).fill(""));
  const refs = useRef<(HTMLInputElement | null)[]>([]);

  function handleChange(i: number, raw: string) {
    const char = raw.replace(/\D/g, "").slice(-1);
    const next = [...digits];
    next[i] = char;
    setDigits(next);
    if (char && i < total - 1) refs.current[i + 1]?.focus();
  }

  function handleKeyDown(i: number, e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Backspace" && digits[i] === "" && i > 0) {
      const next = [...digits];
      next[i - 1] = "";
      setDigits(next);
      refs.current[i - 1]?.focus();
    } else if (e.key === "ArrowLeft" && i > 0) {
      refs.current[i - 1]?.focus();
    } else if (e.key === "ArrowRight" && i < total - 1) {
      refs.current[i + 1]?.focus();
    }
  }

  function handlePaste(i: number, e: ClipboardEvent<HTMLInputElement>) {
    const text = e.clipboardData.getData("text").replace(/\D/g, "");
    if (!text) return;
    e.preventDefault();
    const next = [...digits];
    let j = i;
    for (const ch of text) {
      if (j >= total) break;
      next[j] = ch;
      j++;
    }
    setDigits(next);
    refs.current[Math.min(j, total - 1)]?.focus();
  }

  const value = toValue ? toValue(digits) : digits.join("");

  const groups = segments.reduce<{ start: number; len: number }[]>((acc, len) => {
    const start = acc.length > 0 ? acc[acc.length - 1].start + acc[acc.length - 1].len : 0;
    return [...acc, { start, len }];
  }, []);

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {groups.map((g, gi) => (
        <div key={g.start} className="flex items-center gap-2">
          {gi > 0 && separator && (
            <span aria-hidden className="font-mono text-sm text-ink/30">
              {separator}
            </span>
          )}
          <div className="flex gap-1" role="group" aria-label={`${ariaLabel}, group ${gi + 1}`}>
            {Array.from({ length: g.len }).map((_, li) => {
              const i = g.start + li;
              return (
                <input
                  key={i}
                  ref={(el) => {
                    refs.current[i] = el;
                  }}
                  value={digits[i]}
                  onChange={(e) => handleChange(i, e.target.value)}
                  onKeyDown={(e) => handleKeyDown(i, e)}
                  onPaste={(e) => handlePaste(i, e)}
                  maxLength={1}
                  inputMode="numeric"
                  autoComplete="off"
                  aria-label={`${ariaLabel}, digit ${i + 1} of ${total}`}
                  className="h-11 w-8 border border-ink/25 bg-transparent text-center font-mono text-base text-ink outline-none transition-colors focus:border-brass sm:h-12 sm:w-9"
                />
              );
            })}
          </div>
        </div>
      ))}
      <input type="hidden" name={name} value={value} />
    </div>
  );
}

/** Assembles day/month/year digit boxes (segments [2, 2, 4]) into an ISO
 * date string, or "" until every box is filled. */
export function dobToIso(digits: string[]): string {
  const day = digits.slice(0, 2).join("");
  const month = digits.slice(2, 4).join("");
  const year = digits.slice(4, 8).join("");
  if (day.length === 2 && month.length === 2 && year.length === 4) {
    return `${year}-${month}-${day}`;
  }
  return "";
}
