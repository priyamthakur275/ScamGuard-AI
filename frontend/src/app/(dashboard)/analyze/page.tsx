import type { Metadata } from "next";
import { BatchScanner } from "./batch-scanner";

export const metadata: Metadata = { title: "Analyze Message" };

export default function AnalyzePage() {
  return (
    <div className="sg-page flex flex-col gap-8">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight md:text-4xl">What are you investigating?</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">Start with the signal you have. ScamGuard returns a verdict, the evidence behind it, the key details and what to do next.</p>
      </div>
      <BatchScanner />
    </div>
  );
}
