/** @type {import('next').NextConfig} */

// Keep aligned with THEME_INIT_SCRIPT in src/app/layout.tsx. Recompute using:
//   python3 -c "import hashlib,base64; s=open('src/app/layout.tsx').read(); \
//     import re; m=re.search(r'const THEME_INIT_SCRIPT = \`(.*?)\`;', s, re.DOTALL); \
//     print('sha256-' + base64.b64encode(hashlib.sha256(m.group(1).encode()).digest()).decode())"
const THEME_SCRIPT_CSP_HASH = "sha256-VlNa/BXw4f7LgPFa9vvDvmiArIAuuCZ5o0j3Waqm/J8=";

const CONTENT_SECURITY_POLICY = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data:",
  "font-src 'self'",
  "connect-src 'self' https://scamguard-ai-ecnj.onrender.com https://*.onrender.com http://localhost:8000 http://127.0.0.1:8000",
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
].join("; ");

const nextConfig = {
  reactStrictMode: true,
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
  async rewrites() {
    // Runs in the Next.js server (Node process, or Vercel's serverless
    // functions), never in the browser -- so from the browser's point of
    // view, every request stays same-origin.
    let appServiceUrl = process.env.APP_SERVICE_URL;
    if (!appServiceUrl || (!appServiceUrl.startsWith("http://") && !appServiceUrl.startsWith("https://"))) {
      appServiceUrl = process.env.NODE_ENV === "development"
        ? "http://localhost:8000"
        : "https://scamguard-app-service.onrender.com";
    }

    return [{ source: "/backend-api/:path*", destination: `${appServiceUrl}/:path*` }];
  },
};

module.exports = nextConfig;
