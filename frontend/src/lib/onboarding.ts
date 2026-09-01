import type { User } from "./types";

// The fields collected by the mandatory post-login onboarding step
// (`/onboarding`), not by registration itself. tax_identification_number
// (Steuer-ID) is deliberately excluded -- that's only required later, at
// submission time (see backend/app/eric/submission_service.py), not as
// part of this basic-profile gate. Split out from isProfileComplete()
// below so /onboarding can tell "needs the whole form" apart from "just
// needs to confirm the privacy notice" and skip re-asking for data
// that's already on file.
export function isBasicProfileComplete(user: User): boolean {
  return Boolean(
    user.date_of_birth &&
      user.street &&
      user.house_number &&
      user.postal_code &&
      user.city &&
      user.steuernummer,
  );
}

// elster_privacy_notice_confirmed_at is required in addition to the basic
// profile fields so that existing users who onboarded before this
// confirmation existed are routed back to /onboarding until they confirm
// it too -- § 5 Abs. 1 of the ERiC-Lizenzvereinbarung requires this
// before software use, not just for new signups (see
// docs/ELSTER_ERIC_INTEGRATION.md section 8).
export function isProfileComplete(user: User): boolean {
  return isBasicProfileComplete(user) && Boolean(user.elster_privacy_notice_confirmed_at);
}
