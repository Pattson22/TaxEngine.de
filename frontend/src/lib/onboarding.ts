import type { User } from "./types";

// The fields collected by the mandatory post-login onboarding step
// (`/onboarding`), not by registration itself. tax_identification_number
// (Steuer-ID) is deliberately excluded -- that's only required later, at
// submission time (see backend/app/eric/submission_service.py), not as
// part of this basic-profile gate.
export function isProfileComplete(user: User): boolean {
  return Boolean(
    user.date_of_birth &&
      user.street &&
      user.house_number &&
      user.postal_code &&
      user.city &&
      user.steuernummer,
  );
}
