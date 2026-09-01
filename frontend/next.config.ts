import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Emits a minimal standalone server (.next/standalone) with only the
  // production dependencies actually traced from the build -- what the
  // Docker image copies, instead of the full node_modules tree.
  output: "standalone",
};

export default nextConfig;
