import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import "./globals.css";
import { Providers } from "./providers";
import { ServiceWorkerRegister } from "@/components/layout/sw-register";

// Type system: Plex Sans carries general UI text; its mono sibling is
// reserved for system/meta chrome (ids, timestamps, scores, badges).
// Fonts are self-hosted from ./fonts (SIL OFL, see OFL-IBM-Plex.txt) so
// production builds never depend on reaching Google Fonts at build time.
const plexSans = localFont({
  src: [
    { path: "./fonts/ibm-plex-sans-latin-400-normal.woff2", weight: "400", style: "normal" },
    { path: "./fonts/ibm-plex-sans-latin-500-normal.woff2", weight: "500", style: "normal" },
    { path: "./fonts/ibm-plex-sans-latin-600-normal.woff2", weight: "600", style: "normal" },
    { path: "./fonts/ibm-plex-sans-latin-700-normal.woff2", weight: "700", style: "normal" },
  ],
  variable: "--font-sans",
  display: "swap",
});
const bricolage = localFont({
  src: [
    { path: "./fonts/bricolage-grotesque-latin-500-normal.woff2", weight: "500", style: "normal" },
    { path: "./fonts/bricolage-grotesque-latin-600-normal.woff2", weight: "600", style: "normal" },
    { path: "./fonts/bricolage-grotesque-latin-700-normal.woff2", weight: "700", style: "normal" },
    { path: "./fonts/bricolage-grotesque-latin-800-normal.woff2", weight: "800", style: "normal" },
  ],
  variable: "--font-display",
  display: "swap",
});

const plexMono = localFont({
  src: [
    { path: "./fonts/ibm-plex-mono-latin-400-normal.woff2", weight: "400", style: "normal" },
    { path: "./fonts/ibm-plex-mono-latin-500-normal.woff2", weight: "500", style: "normal" },
    { path: "./fonts/ibm-plex-mono-latin-600-normal.woff2", weight: "600", style: "normal" },
  ],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "ScamGuard — AI Scam & Fraud Message Detection",
    template: "%s · ScamGuard",
  },
  description:
    "Detect phishing, OTP scams, and fraudulent messages in real time using AI-powered NLP and machine learning.",
  manifest: "/manifest.webmanifest",
  applicationName: "ScamGuard",
  appleWebApp: { capable: true, title: "ScamGuard", statusBarStyle: "black-translucent" },
  icons: { icon: "/icons/icon-192.png", apple: "/icons/apple-touch-icon.png" },
  // Stop Chrome auto-translate from rewriting React-owned text (see THEME_INIT_SCRIPT).
  other: { google: "notranslate" },
};

export const viewport: Viewport = { themeColor: "#0d1117" };

// Runs before React hydrates, so the correct theme class is present on
// first paint -- prevents a flash of the wrong theme on page load.
//
// IMPORTANT: this exact string is allow-listed in next.config.js via a
// CSP script-src hash. If you edit this script, you MUST recompute that
// hash (see the comment above THEME_SCRIPT_CSP_HASH in next.config.js)
// or dark-mode initialization will silently fail under CSP enforcement.
//
// It also guards React against browser extensions and auto-translate that
// rewrite the page (Google Translate, Grammarly, ...): they move or wrap
// text nodes React owns, and React then crashes with "Failed to execute
// 'removeChild' on 'Node'". The guard makes those two DOM calls tolerate a
// node that is no longer where React left it (facebook/react#11538).
const THEME_INIT_SCRIPT = `
(function () {
  try {
    var stored = localStorage.getItem("scam_detection_theme");
    var theme = stored === "light" || stored === "dark" ? stored : "dark";
    document.documentElement.classList.toggle("dark", theme === "dark");
  } catch (e) {}
  try {
    if (typeof Node === "function" && Node.prototype && !Node.prototype.__sgGuard) {
      var removeChild = Node.prototype.removeChild;
      Node.prototype.removeChild = function (child) {
        if (child && child.parentNode !== this) {
          if (child.parentNode) { return removeChild.call(child.parentNode, child); }
          return child;
        }
        return removeChild.apply(this, arguments);
      };
      var insertBefore = Node.prototype.insertBefore;
      Node.prototype.insertBefore = function (node, ref) {
        if (ref && ref.parentNode !== this) { return insertBefore.call(this, node, null); }
        return insertBefore.apply(this, arguments);
      };
      Node.prototype.__sgGuard = true;
    }
  } catch (e) {}
})();
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" translate="no" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body className={`min-h-screen ${plexSans.variable} ${plexMono.variable} ${bricolage.variable} font-sans antialiased`}>
        <Providers>{children}</Providers>
        <ServiceWorkerRegister />
      </body>
    </html>
  );
}
