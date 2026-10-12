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
