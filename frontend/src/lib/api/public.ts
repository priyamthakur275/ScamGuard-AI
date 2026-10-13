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

