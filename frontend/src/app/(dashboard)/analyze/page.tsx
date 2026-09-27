import type { Metadata } from "next";
import { BatchScanner } from "./batch-scanner";

export const metadata: Metadata = { title: "Analyze Message" };

export default function AnalyzePage() {
  return (
    <div className="sg-page flex flex-col gap-8">
      <div>
        <p className="console-kicker mb-3">New investigation</p>
        <h1 className="text-3xl font-semibold tracking-tight md:text-4xl">What are you investigating?</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">Start with the signal you have. ScamGuard will return a verdict, supporting evidence, entities, and recommended next steps from the real analysis pipeline.</p>
      </div>
      <BatchScanner />
    </div>
  );
}
