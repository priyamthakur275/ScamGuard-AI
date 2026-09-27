import { apiRequest } from "@/lib/api/client";
import type { AnalysisResult } from "@/types";

export interface DemoExampleSummary {
  id: string;
  label: string;
  category: string | null;
  input_type: string;
}

export function listDemoExamples(): Promise<DemoExampleSummary[]> {
  return apiRequest<DemoExampleSummary[]>("/demo/examples", { method: "GET" });
}

export function runDemoExample(exampleId: string): Promise<AnalysisResult> {
  return apiRequest<AnalysisResult>(`/demo/examples/${exampleId}/run`, { method: "POST" });
}
