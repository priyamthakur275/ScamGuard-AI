import { apiRequest } from "@/lib/api/client";
import type { AnalysisResult } from "@/types";

/** No-login text check; the server runs the real pipeline but stores nothing. */
export function quickCheck(text: string): Promise<AnalysisResult> {
  return apiRequest<AnalysisResult>("/public/quick-check", { method: "POST", body: { text }, auth: false });
}

export async function checkHealth(): Promise<boolean> {
  try {
    await apiRequest<unknown>("/health", { method: "GET", auth: false });
    return true;
  } catch {
    return false;
  }
}

export interface ScamTrends {
  days: number;
  total_scans: number;
  flagged_scans: number;
  flagged_rate: number;
  top_categories: { category: string; count: number }[];
  channels: { input_type: string; count: number }[];
  daily: { date: string; total: number; flagged: number }[];
  generated_at: string;
}

export function getTrends(days: 7 | 30): Promise<ScamTrends> {
  return apiRequest<ScamTrends>(`/public/trends?days=${days}`, { auth: false });
}

export interface TestBenchCase {
  id: number;
  input_type: string;
  expected: "scam" | "legitimate";
  title: string;
  input_text: string | null;
  input_file: string | null;
  extracted_text?: string;
  verdict: "scam" | "legitimate" | "error";
  scam_likelihood?: number;
  model_probability?: number;
  confidence?: number;
  risk_level?: string;
  scam_category?: string | null;
  model?: string;
  correct: boolean;
  seconds: number;
  error?: string;
}

export interface TestBench {
  cases: TestBenchCase[];
  summary: { total: number; correct: number; accuracy: number; precision: number; recall: number; tp: number; tn: number; fp: number; fn: number };
  model: string | null;
  generated_at: string;
}

/** 15 fixed inputs run live through the real pipeline on the server. */
export function getTestBench(fresh = false): Promise<TestBench> {
  return apiRequest<TestBench>(`/public/test-bench${fresh ? "?fresh=true" : ""}`, { auth: false });
}
