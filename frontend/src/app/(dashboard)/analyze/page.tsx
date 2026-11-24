import type { Metadata } from "next";
import { BatchScanner } from "./batch-scanner";

export const metadata: Metadata = { title: "Scan for Threats" };

export default function AnalyzePage() {
  return (
    <div className="sg-page mx-auto flex max-w-5xl flex-col gap-8">
      <div className="text-center">
        <p className="console-kicker mb-2">Multimodal Threat Engine</p>
        <h1 className="text-3xl font-bold tracking-tight md:text-4xl">Scan for Threats</h1>
        <p className="mx-auto mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
          Enter a URL, message, email, screenshot, voice call, PDF, or QR code to analyze for scams.
        </p>
      </div>
      <BatchScanner />
    </div>
  );
}
