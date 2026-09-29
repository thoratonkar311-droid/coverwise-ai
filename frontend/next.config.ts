import type { NextConfig } from "next";

const backendUrl = (
  process.env.INTERNAL_API_URL ||
  process.env.BACKEND_URL ||
  "http://localhost:8000"
).replace(/\/+$/, "");

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
      {
        source: "/health",
        destination: `${backendUrl}/health`,
      },
    ];
  },
};

export default nextConfig;
