"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Button } from "./ui";

export function Nav() {
  const { user, logout } = useAuth();
  const router = useRouter();

  function handleLogout() {
    logout();
    router.push("/");
  }

  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
        <Link href="/" className="text-lg font-semibold text-slate-900">
          TaxEngine<span className="text-emerald-600">.de</span>
        </Link>
        <nav className="flex items-center gap-4 text-sm">
          {user ? (
            <>
              <Link href="/dashboard" className="text-slate-600 hover:text-slate-900">
                Dashboard
              </Link>
              <span className="text-slate-400">{user.email}</span>
              <Button variant="secondary" onClick={handleLogout}>
                Log out
              </Button>
            </>
          ) : (
            <>
              <Link href="/login" className="text-slate-600 hover:text-slate-900">
                Log in
              </Link>
              <Link href="/register">
                <Button>Get started</Button>
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
