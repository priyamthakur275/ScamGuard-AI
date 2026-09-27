import { apiRequest } from "@/lib/api/client";
import type { AnalyticsSummary } from "@/types";

export function getAnalyticsSummary(range: "24h" | "7d" | "30d" | "all" = "all"): Promise<AnalyticsSummary> {
  return apiRequest<AnalyticsSummary>(`/analytics/summary?range=${range}`, { method: "GET" });
}
