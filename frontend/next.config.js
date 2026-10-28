/** @type {import('next').NextConfig} */

// Keep aligned with THEME_INIT_SCRIPT in src/app/layout.tsx. Recompute using:
//   python3 -c "import hashlib,base64; s=open('src/app/layout.tsx').read(); \
//     import re; m=re.search(r'const THEME_INIT_SCRIPT = \`(.*?)\`;', s, re.DOTALL); \
//     print('sha256-' + base64.b64encode(hashlib.sha256(m.group(1).encode()).digest()).decode())"
const THEME_SCRIPT_CSP_HASH = "sha256-07k15woImKBCgBrUxzjMxwUqRuWLy6ceVa24IkjMSdE=";

const CONTENT_SECURITY_POLICY = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval'",
  "worker-src 'self' blob:",
  "media-src 'self' blob:",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data:",
  "font-src 'self'",
  "connect-src 'self' https://scamguard-ai-ecnj.onrender.com https://*.onrender.com http://localhost:8000 http://127.0.0.1:8000 https://huggingface.co https://*.huggingface.co https://*.hf.co",
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
].join("; ");

const nextConfig = {
  reactStrictMode: true,
  // The free backend can take 40-90 s to wake from sleep. Next's rewrite
  // proxy gives up after 30 s by default and answers 502 ("backend not
  // available"), so let it wait for the backend instead.
  experimental: { proxyTimeout: 120000 },
  async headers() {
    const securityHeaders = [
      { key: "X-Content-Type-Options", value: "nosniff" },
      { key: "X-Frame-Options", value: "DENY" },
      { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
    ];

    // CSP is production-only: `next dev` relies on eval-based source maps
    // for Fast Refresh, which a script-src without 'unsafe-eval' blocks.
    if (process.env.NODE_ENV === "production") {
      securityHeaders.push({ key: "Content-Security-Policy", value: CONTENT_SECURITY_POLICY });
    }

    return [{ source: "/:path*", headers: securityHeaders }];
  },
  async redirects() {
    // Family guardian and the scam trainer were retired; old links and the
    // installed app's shortcuts land somewhere useful instead of a 404.
    return [
      { source: "/family/:path*", destination: "/dashboard", permanent: true },
      { source: "/family", destination: "/dashboard", permanent: true },
      { source: "/trainer", destination: "/simulator", permanent: true },
      // Scam trends, research lab and guided demo were removed.
      { source: "/trends", destination: "/", permanent: false },
      { source: "/research", destination: "/", permanent: false },
      { source: "/demo", destination: "/", permanent: false },
      { source: "/flashcards", destination: "/", permanent: false },
    ];
  },
  async rewrites() {
    // Runs in the Next.js server (Node process, or Vercel's serverless
    // functions), never in the browser -- so from the browser's point of
    // view, every request stays same-origin.
    let appServiceUrl = process.env.APP_SERVICE_URL;
    if (!appServiceUrl || (!appServiceUrl.startsWith("http://") && !appServiceUrl.startsWith("https://"))) {
      appServiceUrl = process.env.NODE_ENV === "development"
        // 127.0.0.1, not localhost: Node 17+ resolves localhost to IPv6 (::1)
        // first, while uvicorn listens on IPv4 127.0.0.1, so the proxy got
        // "connection refused" and the page said the backend was down.
        ? "http://127.0.0.1:8000"
        : "https://scamguard-ai-ecnj.onrender.com";
    }

    return [{ source: "/backend-api/:path*", destination: `${appServiceUrl}/:path*` }];
  },
};

module.exports = nextConfig;
