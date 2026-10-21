import type { NextConfig } from "next";

// The browser calls /api/backend/..., and Next.js forwards each request to the FastAPI server,
// so the page and the API share one origin and FastAPI needs no CORS setting.
// `npm run dev` reads BACKEND_API_URL when it starts. `npm run build` saves the address in the
// build, and `npm run start` keeps that saved address: rebuild after changing it.
const backendUrl = process.env.BACKEND_API_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [{ source: "/api/backend/:path*", destination: `${backendUrl}/:path*` }];
  },
};

export default nextConfig;
