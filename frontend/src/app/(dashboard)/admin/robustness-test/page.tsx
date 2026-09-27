"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, FlaskConical, Play, AlertTriangle } from "lucide-react";
import { useAuth } from "@/lib/auth/auth-context";
import { runRobustnessTest, type BaseMessageReport } from "@/lib/api/robustness";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert } from "@/components/ui/alert";
import { formatPercent } from "@/lib/utils";

const STABILITY_VARIANT: Record<string, "default" | "warning" | "destructive"> = {
  stable: "default",
  changed: "warning",
  significantly_changed: "destructive",
  not_applicable: "default",
};

const CATEGORY_LABEL: Record<string, string> = {
  scam: "Scam message",
  benign_scam_vocab: "Benign message (scam-adjacent vocabulary)",
};

export default function RobustnessTestPage() {
  const { user } = useAuth();
  const [reports, setReports] = useState<BaseMessageReport[] | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isAdmin = user?.role === "admin";

  async function handleRun() {
    setIsRunning(true);
    setError(null);
    try {
      const data = await runRobustnessTest();
      setReports(data);
    } catch {
      setError("Robustness test run failed. Please try again.");
    } finally {
      setIsRunning(false);
    }
  }

  if (!isAdmin) {
    return <Alert variant="error">You do not have access to this page.</Alert>;
  }

  return (
    <div className="sg-page flex flex-col gap-6">
      <Link href="/admin" className="flex w-fit items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4" /> Back to admin
      </Link>

      <div className="border border-primary/30 bg-primary/10 p-4">
        <p className="flex items-center gap-2 font-mono text-xs font-semibold uppercase tracking-wide text-primary">
          <FlaskConical className="h-4 w-4" />
          Internal engineering tool — robustness testing
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          Runs real base messages and controlled text transforms (case, whitespace, punctuation,
          spelling, inserted symbols, homoglyph domains, URL obfuscation) through the exact same
          real prediction pipeline as a live scan, and reports the actual measured differences.
          Nothing here is tuned to make the model look better — results are shown as-computed,
          including unfavorable ones. This is not a user-facing feature.
        </p>
      </div>

      <Button onClick={handleRun} disabled={isRunning} className="w-fit">
        <Play className="mr-2 h-4 w-4" />
        {isRunning ? "Running suite..." : "Run robustness suite"}
      </Button>

      {error && <Alert variant="error">{error}</Alert>}

      {reports && (
        <div className="flex flex-col gap-6">
          {reports.map((report) => (
            <Card key={report.message_id}>
              <CardContent className="flex flex-col gap-4 p-5">
                <div>
                  <p className="font-mono text-[11px] uppercase tracking-wide text-muted-foreground">
                    {CATEGORY_LABEL[report.category]}
                  </p>
                  <p className="mt-1 text-sm text-foreground">{report.base_text}</p>
                  <p className="mt-1 font-mono text-xs text-muted-foreground">
                    Base result: {report.base_verdict} ({formatPercent(report.base_probability)})
                  </p>
                </div>

                <div className="overflow-x-auto"><table className="w-full min-w-[520px] text-sm">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="p-2 text-left font-mono text-[11px] uppercase text-muted-foreground">Transform</th>
                      <th className="p-2 text-left font-mono text-[11px] uppercase text-muted-foreground">Result</th>
                      <th className="p-2 text-left font-mono text-[11px] uppercase text-muted-foreground">Delta</th>
                      <th className="p-2 text-left font-mono text-[11px] uppercase text-muted-foreground">Stability</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.transform_results.map((t) => (
                      <tr key={t.transform_code} className="border-b border-border last:border-0">
                        <td className="p-2 text-foreground">{t.transform_label}</td>
                        <td className="p-2 font-mono text-xs text-muted-foreground">
                          {t.stability === "not_applicable"
                            ? "N/A (no change to apply)"
                            : `${t.transformed_verdict} (${formatPercent(t.transformed_probability)})`}
                        </td>
                        <td className="p-2 font-mono text-xs text-muted-foreground">
                          {t.stability === "not_applicable" ? "—" : formatPercent(t.probability_delta)}
                        </td>
                        <td className="p-2">
                          <Badge variant={STABILITY_VARIANT[t.stability]}>
                            {t.stability.replace(/_/g, " ")}
                          </Badge>
                          {t.verdict_changed && (
                            <span className="ml-2 inline-flex items-center gap-1 text-xs text-destructive">
                              <AlertTriangle className="h-3 w-3" /> verdict flipped
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table></div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
