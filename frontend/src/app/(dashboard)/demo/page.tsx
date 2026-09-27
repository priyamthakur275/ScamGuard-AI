"use client";

import { useEffect, useState } from "react";
import { Sparkles, Landmark, Briefcase, TrendingUp, Package, Link as LinkIcon, MessageCircle } from "lucide-react";
import { listDemoExamples, runDemoExample, type DemoExampleSummary } from "@/lib/api/demo";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert } from "@/components/ui/alert";
import { VerdictCard } from "@/components/analysis/verdict-card";
import type { AnalysisResult } from "@/types";

const EXAMPLE_ICONS: Record<string, typeof Landmark> = {
  bank_otp_scam: Landmark,
  job_scam: Briefcase,
  investment_scam: TrendingUp,
  delivery_scam: Package,
  phishing_url: LinkIcon,
  legitimate_message: MessageCircle,
};

export default function DemoModePage() {
  const [examples, setExamples] = useState<DemoExampleSummary[]>([]);
  const [isLoadingCatalog, setIsLoadingCatalog] = useState(true);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [activeExampleId, setActiveExampleId] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [runError, setRunError] = useState<string | null>(null);

  useEffect(() => {
    listDemoExamples()
      .then(setExamples)
      .catch(() => setCatalogError("Could not load demo examples."))
      .finally(() => setIsLoadingCatalog(false));
  }, []);

  async function handleRun(exampleId: string) {
    setActiveExampleId(exampleId);
    setResult(null);
    setRunError(null);
    try {
      const data = await runDemoExample(exampleId);
      setResult(data);
    } catch {
      setRunError("This example could not be analyzed. Please try again.");
    } finally {
      setActiveExampleId(null);
    }
  }

  return (
    <div className="sg-page flex flex-col gap-6">
      <div className="border border-primary/30 bg-primary/10 p-4">
        <p className="flex items-center gap-2 font-mono text-xs font-semibold uppercase tracking-wide text-primary">
          <Sparkles className="h-4 w-4" />
          Demo Mode
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          These examples run through ScamGuard&apos;s real detection pipeline — the same model, threat
          scoring, and explanations used for a genuine scan. Results here are <strong>never saved</strong> to
          your scan history or analytics, and are clearly labeled so they&apos;re never mistaken for a real scan.
        </p>
      </div>

      {catalogError && <Alert variant="error">{catalogError}</Alert>}

      {isLoadingCatalog ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {examples.map((example) => {
            const Icon = EXAMPLE_ICONS[example.id] ?? Sparkles;
            const isRunning = activeExampleId === example.id;
            return (
              <button type="button" key={example.id} disabled={Boolean(activeExampleId)} className="rounded-lg text-left disabled:opacity-60" onClick={() => handleRun(example.id)}>
              <Card
                className="cursor-pointer transition-colors hover:bg-muted"
              >
                <CardContent className="flex items-center gap-3 p-4">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center border border-primary/25 bg-primary/10 text-primary">
                    <Icon className="h-4 w-4" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-foreground">{example.label}</p>
                    <p className="font-mono text-[11px] uppercase tracking-wide text-muted-foreground">
                      {isRunning ? "Analyzing..." : example.input_type}
                    </p>
                  </div>
                </CardContent>
              </Card></button>
            );
          })}
        </div>
      )}

      {runError && <Alert variant="error">{runError}</Alert>}

      {result && <VerdictCard result={result} />}
    </div>
  );
}
