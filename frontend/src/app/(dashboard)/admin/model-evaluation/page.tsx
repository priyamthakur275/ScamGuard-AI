"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Gauge, AlertTriangle } from "lucide-react";
import { useAuth } from "@/lib/auth/auth-context";
import { getModelEvaluations, type ModelEvaluationEntry } from "@/lib/api/model-evaluation";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert } from "@/components/ui/alert";
import { formatDate, formatPercent } from "@/lib/utils";

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="sg-page flex flex-col gap-1">
      <span className="font-mono text-[11px] uppercase tracking-wide text-muted-foreground">{label}</span>
      <span className="font-sans text-xl font-semibold text-foreground">{value}</span>
    </div>
  );
}

export default function ModelEvaluationPage() {
  const { user } = useAuth();
  const [entries, setEntries] = useState<ModelEvaluationEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const isAdmin = user?.role === "admin";

  useEffect(() => {
    if (!isAdmin) return;
    getModelEvaluations()
      .then(setEntries)
      .catch(() => setError("Could not load model evaluation data."))
      .finally(() => setIsLoading(false));
  }, [isAdmin]);

  if (!isAdmin) {
    return <Alert variant="error">You do not have access to this page.</Alert>;
  }

  return (
    <div className="flex flex-col gap-6">
      <Link href="/admin" className="flex w-fit items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4" /> Back to admin
      </Link>

      <div>
        <h1 className="flex items-center gap-2 font-sans text-2xl font-semibold tracking-tight">
          <Gauge className="h-6 w-6 text-primary" />
          Model evaluation
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Real metrics from the last actual training run, read directly from the model registry.
          This is engineering data about the model itself -- never shown to end users alongside
          their own scan results.
        </p>
      </div>

      {error && <Alert variant="error">{error}</Alert>}

      {isLoading ? (
        <div className="flex flex-col gap-4">
          <Skeleton className="h-48 w-full" />
        </div>
      ) : entries.length === 0 ? (
        <p className="text-sm text-muted-foreground">No models are registered yet.</p>
      ) : (
        <div className="flex flex-col gap-6">
          {entries.map((entry) => (
            <Card key={`${entry.model_name}-${entry.version}`}>
              <CardContent className="flex flex-col gap-5 p-6">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <h2 className="font-sans text-lg font-semibold text-foreground">
                      {entry.model_name} <span className="text-muted-foreground">v{entry.version}</span>
                    </h2>
                    <p className="font-mono text-xs text-muted-foreground">
                      Trained {formatDate(entry.trained_at)}
                    </p>
                  </div>
                  {entry.is_production && <Badge variant="success">Production</Badge>}
                </div>

                {entry.dataset_limitation_note && (
                  <div className="flex items-start gap-2 border border-primary/30 bg-primary/10 p-3">
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                    <p className="text-sm text-foreground">{entry.dataset_limitation_note}</p>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                  <MetricRow label="Accuracy" value={formatPercent(entry.accuracy)} />
                  <MetricRow label="Precision" value={formatPercent(entry.precision)} />
                  <MetricRow label="Recall" value={formatPercent(entry.recall)} />
                  <MetricRow label="F1 score" value={formatPercent(entry.f1)} />
                  <MetricRow label="ROC-AUC" value={formatPercent(entry.roc_auc)} />
                  <MetricRow label="False positive rate" value={formatPercent(entry.false_positive_rate)} />
                  <MetricRow label="Train rows" value={String(entry.train_rows)} />
                  <MetricRow label="Test rows" value={String(entry.test_rows)} />
                </div>

                <div>
                  <p className="mb-2 font-mono text-[11px] font-semibold uppercase tracking-wide text-foreground">
                    Confusion matrix (on the {entry.test_rows}-row test split)
                  </p>
                  <table className="w-full max-w-md border border-border text-sm">
                    <thead>
                      <tr className="border-b border-border">
                        <th className="p-2 text-left font-mono text-[11px] uppercase text-muted-foreground"></th>
                        <th className="p-2 text-left font-mono text-[11px] uppercase text-muted-foreground">Predicted scam</th>
                        <th className="p-2 text-left font-mono text-[11px] uppercase text-muted-foreground">Predicted legitimate</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="border-b border-border">
                        <td className="p-2 font-mono text-[11px] uppercase text-muted-foreground">Actual scam</td>
                        <td className="p-2 font-sans text-foreground">{entry.confusion_matrix.true_positives} (TP)</td>
                        <td className="p-2 font-sans text-foreground">{entry.confusion_matrix.false_negatives} (FN)</td>
                      </tr>
                      <tr>
                        <td className="p-2 font-mono text-[11px] uppercase text-muted-foreground">Actual legitimate</td>
                        <td className="p-2 font-sans text-foreground">{entry.confusion_matrix.false_positives} (FP)</td>
                        <td className="p-2 font-sans text-foreground">{entry.confusion_matrix.true_negatives} (TN)</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
