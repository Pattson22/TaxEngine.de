# TaxEngine.de — Frontend

Next.js (App Router) + TypeScript + Tailwind CSS. Talks to the FastAPI
backend in `../backend/`.

## Setup

```bash
npm install
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_URL / NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY
npm run dev
# -> http://localhost:3000
```

Requires the backend running (see `../backend/README.md`) with
`CORS_ALLOWED_ORIGINS` including `http://localhost:3000`.

## What's built

The golden path end to end: register → a mandatory post-login onboarding
step (basic profile info) → create a filing (from a year picker sourced
from the backend's supported tax years) → add wage, capital, rental,
and/or self-employment income → add a deduction (all computed categories —
commute, home office, donations, childcare, Handwerkerleistungen — plus
flat-amount categories) → set Kinderfreibetrag inputs → calculate → view
the refund breakdown → confirm withdrawal consent (AGB § 5) and pay via
Stripe Elements → submit to the Finanzamt (async, worker-backed — the page
polls job status and shows submission history, including amendments).
Impressum, Datenschutzerklärung, AGB, and an ELSTER-specific privacy
notice/consent checkbox round out the legally required pages. This is
running live at meinetaxengine.de on Railway.

```
src/
├── lib/
│   ├── types.ts           Hand-maintained mirror of backend/app/schemas/*.py
│   ├── api.ts              Typed fetch wrapper, one function per backend route
│   ├── auth-context.tsx    Client-side JWT session (see caveat below)
│   ├── use-require-auth.ts Route-guard hook (UX only, not a security boundary)
│   ├── onboarding.ts        Fields collected by the mandatory /onboarding step
│   ├── legal-info.ts        Single source of truth for Impressum/Datenschutz business identity
│   ├── money.ts             Cents <-> EUR formatting/parsing
│   └── stripe.ts            Stripe.js singleton loader
├── components/
│   ├── ui.tsx               Button/Input/Select/Card/StatusStamp/Tooltip/etc.
│   ├── ledger.tsx            Ledger/LedgerLine/CountUpEuro — see Design below
│   ├── hero-form-backdrop.tsx  Drawn German tax form behind the homepage hero
│   ├── refund-anchor.tsx     The one dedicated home for the live refund/liability figure
│   ├── bento.tsx             Asymmetrical Bento Grid for the tax-pillar summary
│   ├── slide-over.tsx        Low-contrast slide-over for tax-code explanations
│   ├── tax-form-boxes.tsx    Boxed per-digit cells (DOB/postal code), ELSTER-form style
│   ├── legal.tsx             Shared prose shell for Impressum/Datenschutz
│   ├── footer.tsx            Site footer (legal page links)
│   └── nav.tsx               Top nav, auth-aware
└── app/
    ├── page.tsx              Landing page
    ├── register/, login/     Auth
    ├── onboarding/            Mandatory post-login basic-profile step
    ├── profile/               Edit profile (tax class, church tax, Steuer-ID, ...)
    ├── dashboard/             List/create filings (year picker, see below)
    ├── impressum/, datenschutz/, agb/, elster-datenschutzhinweis/  Legal pages
    ├── global-error.tsx        Root-level error boundary, reports to Sentry
    └── filings/[id]/
        ├── page.tsx            Filing detail: income, deductions, calculate, results,
        │                       submission status/history
        ├── wage-income/        Add a Lohnsteuerbescheinigung
        ├── deductions/         Add a deduction (category-aware form)
        ├── capital-income/     Add capital income (Anlage KAP)
        ├── rental-income/      Add a rental property (Anlage V)
        ├── self-employment/    Add self-employment income (Anlage S / EÜR)
        └── pay/                 Withdrawal consent + Stripe Elements checkout
```

## Design

The visual language is built around "Der Beleg" — the receipt/statement —
since the product's whole job is turning a stack of paperwork into a
trustworthy number. A few deliberate choices, not the default AI-generated
look (no cream+serif, no near-black+neon, no newspaper hairlines):

- **Colors** (`src/app/globals.css` `@theme`): ink navy (`--color-ink`) on
  a cool muted paper (`--color-paper`, #EEEFEA — not the cream #F4F1EA
  cliché), brass as the single accent, sage for money owed *to* you, clay
  for money you owe.
- **Type**: Space Grotesk for display/headlines, IBM Plex Sans for body
  and UI, IBM Plex Mono for every tabular figure (`.tabular` utility —
  `font-variant-numeric: tabular-nums`). Money is never set in the body
  face.
- **Signature component**: `Ledger`/`LedgerLine` (`src/components/ledger.tsx`)
  — a dotted-leader receipt line (label … dots … amount), used identically
  for the marketing demo on the landing page and for real calculation
  results on the filing detail page. Same component, same data shape,
  deliberately not two implementations.
- **`StatusStamp`** (`src/components/ui.tsx`) — a rotated, double-bordered
  "official stamp" for filing status, standing in for a generic colored
  pill badge.
- **"Zeile"** — the landing page's 3-step process section is numbered the
  way a German tax form numbers its lines, not with generic numbered
  circles.
- **The hero backdrop is drawn, not photographed**
  (`components/hero-form-backdrop.tsx`) — an SVG German tax form: real
  Anlage N field names, Zeile numbers in the left margin, the EUR|Ct
  split German amount fields use, and per-digit boxes matching
  `tax-form-boxes.tsx`. It replaced a stock photo that turned out to be
  a US IRS Form 1040 with dollar-denominated standard deductions, which
  is a strange thing to put behind the headline of a service that files
  with a German Finanzamt. Drawing it also costs no image payload and
  stays crisp at any width; see that file's header comment for the two
  layout constraints (full-bleed rows, left-anchored crop) that the
  browser caught and reasoning alone did not.
- **Premium redesign rules** (`components/refund-anchor.tsx`,
  `bento.tsx`, `slide-over.tsx`): one dedicated, unmissable home for the
  live refund/liability figure (`RefundAnchor`) that everything else
  feeds and never repeats; an asymmetrical Bento Grid for the tax-pillar
  summary instead of a uniform list; tax-code explanations pushed into a
  spacious slide-over rather than inline clutter.
- **`tax-form-boxes.tsx`** — boxed, one-cell-per-digit inputs for
  fixed-length fields (date of birth, postal code), matching how a paper
  Finanzamt form (and ELSTER's own online form) presents them.
  Steuernummer is deliberately NOT boxed, since its digit count/grouping
  varies by Bundesland.

## Known simplifications

- **Auth token in localStorage, not an httpOnly cookie.** Simplest thing
  that works for an MVP scaffold, but readable by any injected JS. Moving
  to an httpOnly cookie is a backend + frontend co-change (the backend
  would need to set/read the cookie and handle CSRF) — see
  `lib/auth-context.tsx`'s top comment.
- **Deduction categories beyond the five with a UI still need one.** Wage
  income, capital income, rental income, self-employment income, and
  Kinderfreibetrag/Kindergeld inputs all have forms now (see the file
  structure above); the deductions form covers COMMUTE, HOME_OFFICE,
  DONATIONS, CHILDCARE, HANDWERKERLEISTUNGEN, and flat-amount categories.
  Anything else in the backend's surface not yet wrapped by `lib/api.ts`
  follows the same mechanical pattern — see the backend's
  `docs/TAXFIX_GAP_ANALYSIS.md` for the full route list.
- **Types are hand-maintained, not generated.** `lib/types.ts` mirrors the
  backend's Pydantic schemas by hand. Once the API surface stabilizes,
  generating these from the backend's OpenAPI schema (e.g.
  `openapi-typescript`) would remove the risk of the two drifting apart
  silently.
- **No automated frontend tests yet** (no Jest/Playwright/Vitest set up).
  Verification performed instead: `npm run build` (clean), `npm run lint`
  (clean), `tsc --noEmit` (clean), plus real click-throughs in an actual
  Chrome browser, both against a local dev stack and — for the deploy/
  payment issues below — the live production site.
- **Real click-through history (local dev stack)**: register → dashboard
  → create filing → add wage income → add a commute deduction →
  calculate → view the refund breakdown, with every number cross-checked
  against the backend's own arithmetic. That run caught a real bug: an
  unhandled Stripe API error (e.g. an invalid key) reached FastAPI as a
  bare 500 with no CORS headers (Starlette's `ServerErrorMiddleware`
  generates that response outside the path `CORSMiddleware` hooks into),
  so the browser reported an opaque "Failed to fetch" instead of a real
  error — fixed in `backend/app/services/payment_service.py` by
  explicitly catching `stripe.StripeError`, with a regression test.
  Capital income/rental income/self-employment income/Kinderfreibetrag
  forms were also individually clicked through (Trade Republic capital
  income, a loss-making rental property, a profitable freelance business,
  plus 1 child), with every figure — including the rental loss correctly
  rendering in clay and the Günstigerprüfung note — hand cross-checked;
  and the `/submit` (ELSTER) page's enqueueing flow, including a real
  amendment (recalculate → re-pay → re-submit), was exercised against the
  dev database. **Not yet exercised in a browser**: the deduction
  categories beyond COMMUTE (home office/donations/childcare/
  Handwerkerleistungen render the right dynamic fields per the code, but
  weren't individually clicked through) and a real Finanzamt submission
  reaching `EricBearbeiteVorgang()` through the frontend specifically
  (`NativeEricClient` itself has been verified directly against the real
  `ericapi.dll`, see `../docs/ELSTER_ERIC_INTEGRATION.md`).
- **This site is deployed and has already caught real production-only
  bugs, not just dev ones.** It runs at meinetaxengine.de on Railway with
  real S3 object storage and a live Stripe key. The live
  `<PaymentElement>` silently never mounted at all — root-caused to a
  single mistyped character in the Railway frontend service's
  `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` (an invalid key Stripe rejects
  with a 401), which had no visible symptom because `<PaymentElement>`
  had no `onLoadError` handler; the key has been corrected in Railway's
  variable store and the component now surfaces load errors instead of
  hanging on "Loading..." forever. Since re-verified against production
  in a real browser: the card form mounts and renders correctly, with
  `onReady` firing and the submit button enabling as designed. (Worth
  knowing for the next person who checks: at full-page screenshot
  resolution the mounted Stripe iframe looks like an empty box —
  Stripe's placeholder text is light grey on near-white. Zoom in, or
  inspect the iframe's dimensions, before concluding it is broken.) A
  homepage caching bug was also found and fixed this way:
  Railway's edge, unlike Vercel, doesn't purge its cache on deploy, so
  `export const dynamic = "force-dynamic"` was added to the homepage so
  edits show up immediately.
