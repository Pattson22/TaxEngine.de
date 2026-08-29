"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "./auth-context";

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
