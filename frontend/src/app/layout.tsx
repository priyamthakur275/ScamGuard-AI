import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import { Providers } from "./providers";

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
};

// Runs before React hydrates, so the correct theme class is present on
// first paint -- prevents a flash of the wrong theme on page load.
//
// IMPORTANT: this exact string is allow-listed in next.config.js via a
// CSP script-src hash. If you edit this script, you MUST recompute that
// hash (see the comment above THEME_SCRIPT_CSP_HASH in next.config.js)
// or dark-mode initialization will silently fail under CSP enforcement.
const THEME_INIT_SCRIPT = `
(function () {
  try {
    var stored = localStorage.getItem("scam_detection_theme");
    var theme = stored === "light" || stored === "dark" ? stored : "dark";
    document.documentElement.classList.toggle("dark", theme === "dark");
  } catch (e) {}
})();
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body className={`min-h-screen ${plexSans.variable} ${plexMono.variable} font-sans antialiased`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
