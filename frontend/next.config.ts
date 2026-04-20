import type { NextConfig } from "next"

// Server-side URL used by Next.js rewrites to reach the backend container.
// In Docker Compose this is http://backend:8000 (internal network).
// Outside Docker, falls back to localhost for local development.
const INTERNAL_API_URL = process.env.INTERNAL_API_URL ?? "http://localhost:8000"
const PROXY_CLIENT_MAX_BODY_SIZE = "1gb"

const nextConfig: NextConfig = {
  experimental: {
    proxyClientMaxBodySize: PROXY_CLIENT_MAX_BODY_SIZE,
  },
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${INTERNAL_API_URL}/api/v1/:path*`,
      },
    ]
  },
}

export default nextConfig
