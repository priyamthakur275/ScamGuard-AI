import type { Metadata } from "next";
import { Download, MousePointerClick, PanelTop, ShieldCheck } from "lucide-react";
import { PublicShell } from "@/components/layout/public-shell";
import { buttonVariants } from "@/components/ui/button";

export const metadata: Metadata = { title: "Browser extension" };

const STEPS = [
  "Download the extension and unzip it.",
  "Open chrome://extensions (Edge: edge://extensions, Brave: brave://extensions).",
  "Turn on Developer mode (top-right).",
  "Click Load unpacked and choose the unzipped folder.",
  "Pin ScamGuard to the toolbar.",
];

export default function ExtensionPage() {
  return (
    <PublicShell>
      <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">Browser extension</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight md:text-4xl">Check scams without leaving the page</h1>
      <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
        Works on WhatsApp Web, Gmail, Telegram Web or any site. Nothing you check is saved.
      </p>

      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        {[
          [MousePointerClick, "Right-click to check", "Select a message or right-click a link → Check with ScamGuard."],
          [PanelTop, "Toolbar popup", "Paste any message into the popup for an instant verdict."],
          [ShieldCheck, "Clear warnings", "A red badge and notification when something is a likely scam."],
        ].map(([Icon, title, text]) => {
          const I = Icon as typeof Download;
          return (
            <div key={title as string} className="border border-border p-5">
              <I className="h-5 w-5 text-primary" />
              <p className="mt-3 font-semibold">{title as string}</p>
              <p className="mt-1 text-sm text-muted-foreground">{text as string}</p>
            </div>
          );
        })}
      </div>

      <a href="/downloads/scamguard-extension.zip" download className={`${buttonVariants({ variant: "primary" })} mt-6`}>
        <Download className="mr-1.5 h-4 w-4" /> Download extension (.zip)
      </a>

      <section className="mt-8 border border-border p-5">
        <h2 className="text-base font-semibold">Install in 1 minute</h2>
        <ol className="mt-3 list-decimal space-y-1.5 pl-5 text-sm">
          {STEPS.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ol>
        <p className="mt-3 text-xs text-muted-foreground">Chrome, Edge and Brave are supported. Firefox is not supported yet.</p>
      </section>
    </PublicShell>
  );
}
