"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

export function Nav() {
  const { user, logout } = useAuth();
  const router = useRouter();

  function handleLogout() {
    logout();
    router.push("/");
  }

  return (
    <header className="border-b border-ink/10 bg-paper">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-5">
        <Link href="/" className="font-display text-[17px] font-medium tracking-tight text-ink">
          TaxEngine <span className="text-brass">·</span> de
        </Link>
        <nav className="flex items-center gap-6 text-sm">
          {user ? (
            <>
              <Link href="/dashboard" className="text-ink/60 transition-colors hover:text-ink">
                Your returns
              </Link>
              <Link
                href="/profile"
                className="hidden text-ink/35 transition-colors hover:text-ink sm:inline"
              >
                {user.email}
              </Link>
              <button
                onClick={handleLogout}
                className="border-b border-transparent text-ink/60 transition-colors hover:border-ink/30 hover:text-ink"
              >
                Log out
              </button>
            </>
          ) : (
            <>
              <Link href="/login" className="text-ink/60 transition-colors hover:text-ink">
                Log in
              </Link>
              <Link
                href="/register"
                className="border border-ink/20 px-4 py-2 text-ink transition-colors hover:border-ink hover:bg-ink hover:text-paper"
              >
                Start your return
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
