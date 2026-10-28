/** @type {import('next').NextConfig} */
const API = process.env.PRICEINTEL_API ?? "http://localhost:8900";

const nextConfig = {
  output: "standalone",
  poweredByHeader: false,
  // The browser only ever talks to Next; Next proxies to the Python API.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API}/v1/:path*` }];
  },
};

export default nextConfig;
