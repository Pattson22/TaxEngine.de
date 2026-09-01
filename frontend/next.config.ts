import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs/config";

const nextConfig: NextConfig = {
  // Emits a minimal standalone server (.next/standalone) with only the
  // production dependencies actually traced from the build -- what the
  // Docker image copies, instead of the full node_modules tree.
  output: "standalone",
};

export default withSentryConfig(nextConfig, {
  silent: true,
  telemetry: false,
  // No SENTRY_AUTH_TOKEN/org/project configured yet -- disable source
  // map upload rather than have the build warn/fail trying to reach an
  // account that doesn't exist. Revisit once a real Sentry project is
  // connected.
  sourcemaps: { disable: true },
});
