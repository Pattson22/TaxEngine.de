import Link from "next/link";
import { Button } from "@/components/ui";
import { HeroFormBackdrop } from "@/components/hero-form-backdrop";

// Static pages get a 1-year s-maxage by default (Next.js's documented
// behavior, see node_modules/next/dist/docs/01-app/02-guides/cdn-caching.md)
// and Railway's edge (unlike Vercel) does not purge that cache on
// deploy -- without this, every future homepage edit stays invisible on
// meinetaxengine.de until the cache happens to expire, regardless of how
// many times the service is redeployed. Confirmed live: a real deploy
// sat behind a stale `x-nextjs-cache: HIT` response for the page's full
// s-maxage window even after an explicit container restart.
export const dynamic = "force-dynamic";

export default function Home() {
  return (
    <div>
      {/* Hero: the thesis is the receipt itself, not a claim about it --
          so the backdrop is a drawn German tax form (see
          components/hero-form-backdrop.tsx for what it replaced and why),
          scrimmed toward the centre so the headline keeps full contrast
          while the form stays legible out at the edges. */}
      <section className="relative overflow-hidden bg-ink text-paper">
        <div className="absolute inset-0" aria-hidden="true">
          <HeroFormBackdrop />
        </div>
        <div
          className="absolute inset-0 bg-[radial-gradient(ellipse_58%_62%_at_50%_46%,#14172a_38%,rgba(20,23,42,0.58)_100%)]"
          aria-hidden="true"
        />
        <div className="relative mx-auto max-w-3xl px-6 py-24 text-center lg:py-32">
          <h1 className="font-display text-[2.75rem] leading-[1.05] font-medium tracking-tight text-paper sm:text-[3.4rem]">
            Know your refund
            <br />
            before you file it.
          </h1>
          <p className="mx-auto mt-6 max-w-md text-[15px] leading-relaxed text-paper/65">
            Add your income and deductions and watch the number update as you
            go. Nothing costs anything until you&apos;re ready to send it —
            then it&apos;s one flat fee, €34,90, to file with the Finanzamt
            via ELSTER.
          </p>
          <div className="mt-9 flex flex-wrap items-center justify-center gap-5">
            <Link href="/register">
              <Button variant="hero" size="lg">
                Start your return
              </Button>
            </Link>
            <Link
              href="/login"
              className="border-b border-paper/25 pb-0.5 text-sm text-paper/70 transition-colors hover:border-paper/60 hover:text-paper"
            >
              I already have an account
            </Link>
          </div>
        </div>
      </section>

      {/* The real flow, in the form's own vocabulary — a genuine sequence,
          numbered the way a Steuererklärung numbers its own lines. */}
      <section className="mx-auto max-w-5xl px-6 py-20">
        <div className="grid gap-10 sm:grid-cols-3">
          <Zeile n="1" title="Add your income">
            Wage certificates to start — capital gains, rental, and
            self-employment income all fit in too, whatever applies to you.
          </Zeile>
          <Zeile n="2" title="Claim what's yours">
            Commute, home office, donations, childcare — the deductions
            people forget are usually worth more than the ones they
            remember.
          </Zeile>
          <Zeile n="3" title="File for €34,90">
            Review the number, pay the flat fee, and we submit directly to
            the Finanzamt via ELSTER. No advisory fees, no upsells.
          </Zeile>
        </div>
      </section>
    </div>
  );
}

function Zeile({ n, title, children }: { n: string; title: string; children: React.ReactNode }) {
  return (
    <div className="border-t border-ink/10 pt-5">
      <span className="font-mono text-xs text-brass">Zeile {n}</span>
      <h3 className="mt-2 font-display text-lg font-medium text-ink">{title}</h3>
      <p className="mt-2 text-[14px] leading-relaxed text-ink/55">{children}</p>
    </div>
  );
}
