import { apiRequest } from "@/lib/api/client";
import { cached } from "@/lib/api/cache";
import type { AnalyticsSummary } from "@/types";

export function getAnalyticsSummary(range: "24h" | "7d" | "30d" | "all" = "all"): Promise<AnalyticsSummary> {
  return cached(`analytics:${range}`, () => apiRequest<AnalyticsSummary>(`/analytics/summary?range=${range}`, { method: "GET" }));
}
