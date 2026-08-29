import Link from "next/link";
import { Button, Card } from "@/components/ui";

export default function Home() {
  return (
    <div className="mx-auto max-w-5xl px-6 py-20">
      <div className="max-w-2xl">
        <h1 className="text-4xl font-bold tracking-tight text-slate-900 sm:text-5xl">
          Your German tax refund,{" "}
          <span className="text-emerald-600">estimated free</span>.
        </h1>
        <p className="mt-6 text-lg text-slate-600">
          Enter your income and deductions, see exactly what you&apos;ll get back —
          then pay a flat <strong>€34.90</strong> to submit directly to the
          Finanzamt via ELSTER. No advisory fees, no surprises.
        </p>
        <div className="mt-8 flex gap-4">
          <Link href="/register">
            <Button className="px-6 py-3 text-base">Start your return — free</Button>
          </Link>
          <Link href="/login">
            <Button variant="secondary" className="px-6 py-3 text-base">
              I already have an account
            </Button>
          </Link>
        </div>
      </div>

      <div className="mt-20 grid gap-6 sm:grid-cols-3">
        <Card>
          <h3 className="font-semibold text-slate-900">1. Enter your data</h3>
          <p className="mt-2 text-sm text-slate-600">
            Wage certificates, commute distance, donations, and more —
            guided step by step.
          </p>
        </Card>
        <Card>
          <h3 className="font-semibold text-slate-900">2. See your refund</h3>
          <p className="mt-2 text-sm text-slate-600">
            Instant calculation covering income tax, Soli, Kirchensteuer,
            and every deduction you qualify for.
          </p>
        </Card>
        <Card>
          <h3 className="font-semibold text-slate-900">3. Submit for €34.90</h3>
          <p className="mt-2 text-sm text-slate-600">
            One flat fee, paid securely by card. We file directly with the
            Finanzamt via ELSTER.
          </p>
        </Card>
      </div>
    </div>
  );
}
