import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Server-component-by-default is the Next.js 16 default already (Decision
  // 6 / scoping doc's performance constraint) — nothing to opt into here.
  // Deliberately no `output: "export"`: auth (httpOnly session cookie +
  // server-side /auth/me fetch) needs a real Node/Edge server, not a static
  // export.
  reactStrictMode: true,
};

export default nextConfig;
