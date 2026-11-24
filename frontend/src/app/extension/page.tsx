import type { Metadata } from "next";
import { Download, MousePointerClick, PanelTop, ShieldCheck } from "lucide-react";
import { PublicShell } from "@/components/layout/public-shell";
import { buttonVariants } from "@/components/ui/button";

export const metadata: Metadata = { title: "Browser extension" };

const STEPS = [
  "Download the extension bundle and unzip it.",
  "Open chrome://extensions (Edge: edge://extensions, Brave: brave://extensions).",
  "Turn on Developer mode in the top-right corner.",
  "Click Load unpacked and select the unzipped extension folder.",
  "Pin ScamGuard AI to your browser toolbar.",
];

export default function ExtensionPage() {
  return (
    <PublicShell>
      <div className="border-b border-border pb-6">
        <p className="console-kicker">Browser Extension</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight md:text-4xl">Inspect links without leaving the page</h1>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
          Works across WhatsApp Web, Gmail, Telegram Web, or any web page. Quick checks are zero-storage.
        </p>
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        {[
          [MousePointerClick, "Context-menu check", "Highlight any message or right-click any link → Check with ScamGuard."],
          [PanelTop, "Toolbar popup", "Paste suspicious messages or URLs in one click for an instant risk score."],
          [ShieldCheck, "High-risk alerts", "Visual badge alerts and explainable signals whenever phishing patterns match."],
        ].map(([Icon, title, text]) => {
          const I = Icon as typeof Download;
          return (
            <div key={title as string} className="console-panel p-5">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-primary/30 bg-primary/10 text-primary">
                <I className="h-4.5 w-4.5" aria-hidden="true" />
              </div>
              <p className="mt-3.5 font-display text-base font-semibold text-foreground">{title as string}</p>
              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{text as string}</p>
            </div>
          );
        })}
      </div>

      <div className="mt-6">
        <a href="/downloads/scamguard-extension.zip" download className={buttonVariants({ variant: "primary", size: "lg" })}>
          <Download className="h-4 w-4" aria-hidden="true" /> Download extension (.zip)
        </a>
      </div>

      <section className="console-panel mt-8 p-6">
        <h2 className="text-base font-semibold text-foreground">Install in under a minute</h2>
        <ol className="mt-4 space-y-2.5 text-sm">
          {STEPS.map((s, idx) => (
            <li key={s} className="flex items-start gap-3">
              <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-primary/35 bg-primary/15 font-mono text-[11px] font-semibold text-primary">
                {idx + 1}
              </span>
              <span className="text-foreground/90">{s}</span>
            </li>
          ))}
        </ol>
        <p className="mt-4 border-t border-border/70 pt-3 text-xs text-muted-foreground">
          Supported browsers: Chrome, Microsoft Edge, and Brave (Chromium Manifest V3).
        </p>
      </section>
    </PublicShell>
  );
}
