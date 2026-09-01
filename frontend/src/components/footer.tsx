import Link from "next/link";

export function Footer() {
  return (
    <footer className="border-t border-ink/10 bg-paper">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 px-6 py-6 text-xs text-ink/45">
        <span>© {new Date().getFullYear()} TaxEngine · de</span>
        <nav className="flex items-center gap-5">
          <Link href="/impressum" className="transition-colors hover:text-ink">
            Impressum
          </Link>
          <Link href="/datenschutz" className="transition-colors hover:text-ink">
            Datenschutz
          </Link>
          <Link href="/agb" className="transition-colors hover:text-ink">
            AGB
          </Link>
        </nav>
      </div>
    </footer>
  );
}
