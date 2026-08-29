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

The golden path end to end: register → log in → create a filing → add wage
income → add a deduction (all computed categories — commute, home office,
donations, childcare, Handwerkerleistungen — plus flat-amount categories)
→ calculate → view the refund breakdown → pay via Stripe Elements → submit.

```
src/
├── lib/
│   ├── types.ts           Hand-maintained mirror of backend/app/schemas/*.py
│   ├── api.ts              Typed fetch wrapper, one function per backend route
│   ├── auth-context.tsx    Client-side JWT session (see caveat below)
│   ├── use-require-auth.ts Route-guard hook (UX only, not a security boundary)
│   ├── money.ts             Cents <-> EUR formatting/parsing
│   └── stripe.ts            Stripe.js singleton loader
├── components/
│   ├── ui.tsx               Button/Input/Select/Card/StatusBadge/etc.
│   └── nav.tsx               Top nav, auth-aware
└── app/
    ├── page.tsx              Landing page
    ├── register/, login/     Auth
    ├── dashboard/             List/create filings
    └── filings/[id]/
        ├── page.tsx            Filing detail: income, deductions, calculate, results
        ├── wage-income/        Add a Lohnsteuerbescheinigung
        ├── deductions/         Add a deduction (category-aware form)
        └── pay/                 Stripe Elements checkout
```

## Known simplifications

- **Auth token in localStorage, not an httpOnly cookie.** Simplest thing
  that works for an MVP scaffold, but readable by any injected JS. Moving
  to an httpOnly cookie is a backend + frontend co-change (the backend
  would need to set/read the cookie and handle CSRF) — see
  `lib/auth-context.tsx`'s top comment.
- **Only wage income + a subset of deduction categories have a UI.** The
  backend also supports capital gains, rental income, self-employment
  income, and the Kinderfreibetrag/Kindergeld Günstigerprüfung inputs
  (`PATCH /tax-filings/{id}`) — none of those have a form here yet. The API
  client (`lib/api.ts`) only wraps the routes this scaffold's pages
  actually call; extending it to the rest of the backend's surface is
  mechanical (same pattern, see the backend's `docs/TAXFIX_GAP_ANALYSIS.md`
  for the full route list).
- **Types are hand-maintained, not generated.** `lib/types.ts` mirrors the
  backend's Pydantic schemas by hand. Once the API surface stabilizes,
  generating these from the backend's OpenAPI schema (e.g.
  `openapi-typescript`) would remove the risk of the two drifting apart
  silently.
- **No automated frontend tests yet** (no Jest/Playwright/Vitest set up).
  Verification performed instead: `npm run build` (clean), `npm run lint`
  (clean), `tsc --noEmit` (clean), plus a real click-through in an actual
  Chrome browser (register → dashboard → create filing → add wage income →
  add a commute deduction → calculate → view the refund breakdown, with
  every number cross-checked against the backend's own arithmetic). That
  browser run caught a real bug: an unhandled Stripe API error (e.g. an
  invalid key) reached FastAPI as a bare 500 with no CORS headers
  (Starlette's `ServerErrorMiddleware` generates that response outside the
  path `CORSMiddleware` hooks into), so the browser reported an opaque
  "Failed to fetch" instead of a real error — fixed in
  `backend/app/services/payment_service.py` by explicitly catching
  `stripe.StripeError`, with a regression test. **Not yet exercised in a
  browser**: actual Stripe Elements card entry/confirmation (no real test
  keys in that environment — the payment page's error path was verified
  instead), the `/submit` (ELSTER) page, and the deduction categories
  beyond COMMUTE (home office/donations/childcare/Handwerkerleistungen
  render the right dynamic fields per the code, but weren't individually
  clicked through).
