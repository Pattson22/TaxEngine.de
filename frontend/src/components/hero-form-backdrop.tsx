// The homepage hero backdrop: a drawn German tax form, not a photograph.
//
// This replaced a stock photo that, read closely, was a US IRS Form 1040
// -- "Form 1040 (2020)", standard deductions of $12,400/$24,800/$18,650,
// and chocolate coins stamped "UNITED STATES OF AMERICA" -- sitting
// behind the headline of a service that files with a German Finanzamt.
// At 85% overlay it was almost invisible, which is exactly the problem:
// the only visitors who ever resolved the detail were the ones looking
// hard enough to be deciding whether to trust us with a Steuer-ID.
//
// Drawing it instead of sourcing another photo means no licensing
// question, no image payload (the JPEG was ~580KB), crispness at any
// width, and -- the actual point -- the vocabulary is genuinely German:
// real Anlage N field names, Zeile numbers in the left margin, the
// EUR|Ct split that German amount fields use, and per-digit boxes the
// way ELSTER's own forms set fixed-length fields (the same convention
// components/tax-form-boxes.tsx uses for real input).
//
// Two layout constraints drove the shape of this. The rows bleed past
// both edges of the viewBox rather than sitting on a drawn "sheet": a
// sheet has a border, and at hero aspect ratios that border lands
// mid-canvas as a hard vertical line that reads as a rendering bug. And
// every row is self-similar, so the vertical cropping that
// `preserveAspectRatio="slice"` does at wide viewports simply shows
// fewer rows instead of decapitating a masthead.

type Row = {
  /** Printed in the left margin, exactly as a real form numbers its lines. */
  zeile: number;
  /** A real Anlage N / Mantelbogen field name, or null to draw a plain rule. */
  label: string | null;
  /** Right-hand field: a Euro amount, or a group of per-digit boxes. */
  field: "amount" | "digits";
  /** Digit-box count, when `field` is "digits". */
  digits?: number;
  /** Draws the amount in brass -- one accent line, standing in for the computed total. */
  accent?: boolean;
};

const ROWS: Row[] = [
  { zeile: 4, label: "Steuernummer", field: "digits", digits: 11 },
  { zeile: 6, label: "Bruttoarbeitslohn", field: "amount" },
  { zeile: 7, label: "Lohnsteuer", field: "amount" },
  { zeile: 8, label: "Solidaritätszuschlag", field: "amount" },
  { zeile: 11, label: "Kirchensteuer", field: "amount" },
  { zeile: 12, label: null, field: "digits", digits: 7 },
  { zeile: 31, label: "Entfernungspauschale", field: "amount" },
  { zeile: 36, label: "Werbungskosten", field: "amount" },
  { zeile: 42, label: null, field: "amount" },
  { zeile: 47, label: "Sonderausgaben", field: "amount", accent: true },
];

const PAPER = "#eeefea";
const BRASS = "#d8b876";

const VIEW_W = 1440;
const VIEW_H = 620;

const MARGIN_X = 132; // the form's left margin rule
const LABEL_X = 168;
const FIELD_X = 1010;

const ROW_TOP = 62;
const ROW_GAP = 58;

// Anchored left, not centred. At desktop aspect ratios `slice` scales to the
// width and crops vertically, so the horizontal anchor is moot. At phone
// widths it scales to the HEIGHT and crops horizontally instead -- centred,
// that would discard both the Zeile numbers and field names (left) and the
// amount fields (right), leaving nothing on screen but bare horizontal rules.
// xMin keeps the identity-carrying half of the form visible.
const ASPECT = "xMinYMid slice";

export function HeroFormBackdrop() {
  return (
    <svg
      viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
      preserveAspectRatio={ASPECT}
      className="h-full w-full"
      aria-hidden="true"
      focusable="false"
    >
      {/* One slight rotation: a form set down on a desk, not a UI mock
          pinned to a grid. Rows are drawn well past both edges so the
          rotation never exposes a corner. */}
      <g transform={`rotate(-0.9 ${VIEW_W / 2} ${VIEW_H / 2})`}>
        {/* The form's left margin rule, which the Zeile numbers sit outside of. */}
        <line
          x1={MARGIN_X}
          x2={MARGIN_X}
          y1={-40}
          y2={VIEW_H + 40}
          stroke={PAPER}
          strokeOpacity="0.07"
          strokeWidth="1"
        />

        {/* Column headings: German amount fields are always split Euro | Cent
            and labelled exactly this way. */}
        <text
          x={FIELD_X + 132}
          y={ROW_TOP - 22}
          textAnchor="end"
          fill={PAPER}
          fillOpacity="0.14"
          fontFamily="var(--font-mono), monospace"
          fontSize="12"
          letterSpacing="1.5"
        >
          EUR
        </text>
        <text
          x={FIELD_X + 202}
          y={ROW_TOP - 22}
          textAnchor="end"
          fill={PAPER}
          fillOpacity="0.14"
          fontFamily="var(--font-mono), monospace"
          fontSize="12"
          letterSpacing="1.5"
        >
          Ct
        </text>

        {ROWS.map((row, i) => {
          const y = ROW_TOP + i * ROW_GAP;
          return (
            <g key={row.zeile}>
              {/* Zeile number, right-aligned into the margin. */}
              <text
                x={MARGIN_X - 20}
                y={y + 20}
                textAnchor="end"
                fill={PAPER}
                fillOpacity="0.16"
                fontFamily="var(--font-mono), monospace"
                fontSize="13"
              >
                {row.zeile}
              </text>

              {row.label ? (
                <text
                  x={LABEL_X}
                  y={y + 20}
                  fill={PAPER}
                  fillOpacity="0.13"
                  fontFamily="var(--font-sans), system-ui, sans-serif"
                  fontSize="15"
                >
                  {row.label}
                </text>
              ) : (
                // A continuation line: drawn as a rule rather than invented
                // German, which would read as wrong to anyone who could
                // actually make it out at this opacity.
                <rect
                  x={LABEL_X}
                  y={y + 9}
                  width="236"
                  height="7"
                  rx="1.5"
                  fill={PAPER}
                  fillOpacity="0.07"
                />
              )}

              {row.field === "amount" ? (
                <AmountField x={FIELD_X} y={y - 4} accent={row.accent} />
              ) : (
                <DigitBoxes x={FIELD_X} y={y - 4} count={row.digits ?? 8} />
              )}

              {/* The form's own ruling, bled past both edges. */}
              <line
                x1={-40}
                x2={VIEW_W + 40}
                y1={y + 38}
                y2={y + 38}
                stroke={PAPER}
                strokeOpacity="0.05"
                strokeWidth="1"
              />
            </g>
          );
        })}
      </g>
    </svg>
  );
}

/** The EUR | Ct pair a German amount field is always set as. */
function AmountField({ x, y, accent }: { x: number; y: number; accent?: boolean }) {
  const stroke = accent ? BRASS : PAPER;
  const opacity = accent ? 0.32 : 0.13;
  return (
    <g>
      <rect
        x={x}
        y={y}
        width="140"
        height="32"
        rx="2"
        fill={PAPER}
        fillOpacity="0.02"
        stroke={stroke}
        strokeOpacity={opacity}
        strokeWidth="1"
      />
      {/* Cent column: narrower and shaded, exactly as the paper form prints it. */}
      <rect
        x={x + 144}
        y={y}
        width="58"
        height="32"
        rx="2"
        fill={PAPER}
        fillOpacity="0.05"
        stroke={stroke}
        strokeOpacity={opacity}
        strokeWidth="1"
      />
    </g>
  );
}

/** Fixed-length numeric field: one box per digit, the way ELSTER sets them. */
function DigitBoxes({ x, y, count }: { x: number; y: number; count: number }) {
  const w = 16;
  const gap = 3.5;
  return (
    <g>
      {Array.from({ length: count }, (_, i) => (
        <rect
          key={i}
          x={x + i * (w + gap)}
          y={y}
          width={w}
          height="30"
          rx="1.5"
          fill={PAPER}
          fillOpacity="0.025"
          stroke={PAPER}
          strokeOpacity="0.12"
          strokeWidth="1"
        />
      ))}
    </g>
  );
}
