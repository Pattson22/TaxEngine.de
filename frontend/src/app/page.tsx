import Link from "next/link";
import { CountUpEuro, Ledger, LedgerLine } from "@/components/ledger";
import { Button } from "@/components/ui";

export default function Home() {
  return (
    <div>
      {/* Hero: the thesis is the receipt itself, not a claim about it. */}
      <section className="bg-ink text-paper">
        <div className="mx-auto grid max-w-5xl gap-12 px-6 py-20 lg:grid-cols-[1.1fr_1fr] lg:items-center lg:py-28">
          <div>
            <p className="mb-4 text-[11px] font-medium tracking-[0.14em] text-brass-soft uppercase">
              Steuerjahr 2024
            </p>
            <h1 className="font-display text-[2.75rem] leading-[1.05] font-medium tracking-tight text-paper sm:text-[3.4rem]">
              Know your refund
              <br />
              before you file it.
            </h1>
            <p className="mt-6 max-w-md text-[15px] leading-relaxed text-paper/65">
              Add your income and deductions and watch the number update as
              you go. Nothing costs anything until you&apos;re ready to send
              it — then it&apos;s one flat fee, €34,90, to file with the
              Finanzamt via ELSTER.
            </p>
            <div className="mt-9 flex flex-wrap items-center gap-5">
              <Link href="/register">
                <Button className="bg-brass px-6 py-3 text-ink hover:bg-brass-soft">
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

          <div className="border border-paper/15 bg-paper p-6 text-ink shadow-[0_30px_60px_-20px_rgba(0,0,0,0.5)]">
            <p className="mb-1 font-display text-[13px] font-medium tracking-tight text-ink/50">
              Beispielrechnung — sample return
            </p>
            <Ledger className="mt-3">
              <LedgerLine label="Bruttolohn" value="52.000,00 €" delay={0} />
              <LedgerLine label="Werbungskosten" value="−1.890,00 €" delay={90} />
              <LedgerLine label="Sonderausgaben" value="−36,00 €" delay={180} />
              <LedgerLine
                label="Zu versteuerndes Einkommen"
                value="50.074,00 €"
                tone="total"
                delay={270}
              />
              <LedgerLine label="Einkommensteuer" value="−11.207,00 €" delay={360} />
              <LedgerLine label="Bereits einbehalten" value="12.441,00 €" delay={450} />
            </Ledger>
            <div className="mt-4 flex items-baseline justify-between">
              <span className="font-display text-sm font-medium text-ink">Erstattung</span>
              <span className="tabular font-display text-3xl font-medium text-sage">
                <CountUpEuro cents={123_400} />
              </span>
            </div>
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
