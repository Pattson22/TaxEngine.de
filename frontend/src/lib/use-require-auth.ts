"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "./auth-context";
import { isProfileComplete } from "./onboarding";

// Client-side route guard: redirects to /login once we know for certain
// there's no valid session (isLoading has settled and there's no user).
// This is a UX convenience, NOT a security boundary -- the actual
// protection is the backend rejecting unauthenticated/invalid-token API
// calls with 401, same as any other client of the API.
export function useRequireAuth() {
  const { user, token, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !token) {
      router.push("/login");
    }
  }, [isLoading, token, router]);

  return { user, token, isLoading };
}

// Same as useRequireAuth, plus: redirects to /onboarding if the basic
// profile (date of birth, address, Steuernummer) hasn't been collected
// yet. Used on every page reachable after login except /onboarding
// itself, /profile, and the auth pages, so a filer completes it before
// doing anything else -- but can still always reach /profile to edit it
// later without re-triggering this redirect.
export function useRequireOnboarding() {
  const { user, token, isLoading } = useRequireAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && user && !isProfileComplete(user)) {
      router.push("/onboarding");
    }
  }, [isLoading, user, router]);

  return { user, token, isLoading };
}
